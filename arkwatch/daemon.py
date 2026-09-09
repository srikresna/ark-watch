"""daemon.py — in-app scheduler: one process, jobs = isolated subprocesses.

A 30-second loop checks the WIB clock and runs due jobs as subprocesses. Each
job is a fresh Python process (crashes/leaks do not spread). The heartbeat
file is refreshed every loop; if it goes stale for more than 5 minutes, the
daemon is dead or hung. A lockfile prevents a second instance (duplicate
briefs).
Run: python -m arkwatch daemon
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HEARTBEAT = ROOT / "data" / "daemon_heartbeat"
LOCKFILE = ROOT / "data" / "daemon.lock"
LOG_DIR = ROOT / "logs"
WIB = ZoneInfo("Asia/Jakarta")

# Schedule entries: (hour, minute, day, job_cmd, description)
# day: daily | monday..saturday | sunday — literal day tokens as used below;
# weekday names accept both short and long forms (both must map to the same
# weekday key)
SCHEDULE = [
    (3, 45, "saturday", "f2", "Saturday: COT post-release (Fri 15:30 ET) BEFORE brief"),
    (4, 15, "saturday", "brief", "Saturday positioning special brief"),
    (6, 0, "daily", "harvest", "Increment harvest for all active registry series"),
    (6, 0, "friday", "soma harvest", "SOMA per-CUSIP weekly harvest"),
    # fiscaldata publishes DTS ~afternoon ET → a 06:10 WIB run catches yesterday;
    # sits after the 06:00 registry harvest (owns FISCAL:DEBT_*) and before the
    # 07:00 brief
    (6, 10, "daily", "fiscalx", "Fiscaldata expansion: auctions + DTS transactions + interest expense/rates"),
    (6, 20, "daily", "instruments sweep", "Last 7 days of prices"),
    (6, 30, "daily", "nyfed ops", "Desk operations tsy/ambs + fxs swap-line watch"),
    (6, 40, "daily", "calendar", "Union-4 calendar"),
    (6, 45, "daily", "surprise", "σ engine + surprise_z + ESI"),
    # pd BEFORE the 07:00 brief (same slot, list order = launch order): the survey
    # release lands Wed night ET = Thu ~06:00 WIB, so the brief sees fresh data
    (7, 0, "thursday", "nyfed pd", "Primary Dealer Positions Survey (release Wed night ET)"),
    (
        7,
        0,
        "daily",
        "brief",
        "Generate brief + outbox (skip if Saturday edition already published)",
    ),
    (7, 5, "daily", "send", "Send brief via Telegram"),
    (7, 15, "daily", "verify", "Truth gate"),
    (8, 15, "daily", "cme", "CME settlements + CVOL + VOI (gray harvester)"),
    (8, 30, "daily", "f2", "COT + flows (Bybit/Farside/PBoC/LBMA/TIC/LME) + FedWatch"),
    (23, 30, "daily", "backup", "VACUUM INTO + verification + rotation"),
    (22, 0, "sunday", "alfred", "Weekly maintenance + vintage audit"),
]
# The watcher is a recurring 60-second task, not part of SCHEDULE — the daemon
# runs it as its own subprocess each cycle
WATCH_INTERVAL_S = 60
RETRY_DELAY_S = 600

DAY_MAP = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}

logger = logging.getLogger("arkwatch.daemon")


def _setup_logging():
    """(Re)install handlers — clear old ones first: re-adding on rotation would
    duplicate lines (2×, 3×, …) and leak file handles."""
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).strftime("%Y%m%d")
    fh = logging.FileHandler(LOG_DIR / f"daemon-{today}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.setLevel(logging.INFO)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("daemon: %(message)s"))
    logger.addHandler(sh)


def _heartbeat():
    HEARTBEAT.parent.mkdir(exist_ok=True)
    HEARTBEAT.write_text(datetime.now(UTC).isoformat(timespec="seconds"))


def _due_jobs(now_wib, last_run: dict[str, str]) -> list[tuple[str, str, str]]:
    """Return [(job_cmd, description, key)] jobs that are due and not yet run.

    The key is PER SCHEDULE ENTRY (hhmm+cmd+date): a cmd+date key would let a
    Saturday 03:45 f2 run block the daily 08:30 f2 (same cmd), leaving
    Saturday flows/COT unrefreshed. The key is built here so it matches
    run_loop exactly."""
    due = []
    wd = now_wib.weekday()  # 0=Monday
    hhmm = now_wib.hour * 100 + now_wib.minute
    for h, m, day, cmd, desc in SCHEDULE:
        if day == "daily" or DAY_MAP.get(day) == wd:
            target = h * 100 + m
            if hhmm >= target:
                key = f"{h:02d}{m:02d}-{cmd}@{now_wib.date()}"
                if key not in last_run:
                    due.append((cmd, desc, key))
    return due


def _run_job(cmd: str, desc: str) -> bool:
    t0 = time.monotonic()
    logger.info(f"▶ {cmd} — {desc}")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "arkwatch"] + cmd.split(),
            cwd=str(ROOT),
            timeout=1800,  # 30-minute hard kill
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        dt = time.monotonic() - t0
        if r.returncode == 0:
            tail = (r.stdout or "").strip().splitlines()
            summary = tail[-1] if tail else "OK"
            logger.info(f"✓ {cmd} ({dt:.0f}s) — {summary[:120]}")
            return True
        err = (r.stderr or r.stdout or "").strip().splitlines()
        logger.error(
            f"✗ {cmd} ({dt:.0f}s) exit={r.returncode} — {(err[-1] if err else 'no output')[:200]}"
        )
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"✗ {cmd} TIMEOUT 30min — hard-kill")
        return False
    except Exception as ex:
        logger.error(f"✗ {cmd} — daemon exception: {ex}")
        return False


def run_loop():
    # Lockfile prevents duplicate instances
    if LOCKFILE.exists():
        try:
            pid = int(LOCKFILE.read_text().strip())
            import os

            os.kill(pid, 0)  # raises if the process is gone
            print(f"another daemon is alive (pid {pid}) — exit")
            return
        except (ValueError, OSError, ImportError):
            pass  # stale lock → take over
    LOCKFILE.parent.mkdir(exist_ok=True)
    LOCKFILE.write_text(str(__import__("os").getpid()))

    _setup_logging()
    logger.info("=== daemon start ===")
    last_run: dict[str, str] = {}
    next_retry: dict[str, float] = {}  # cmd → monotonic retry time (non-blocking)
    cycle = 0
    last_watch = 0.0
    try:
        while True:
            _heartbeat()
            now_wib = datetime.now(WIB)

            # Retry failed jobs (NON-BLOCKING: an inline sleep would freeze the
            # heartbeat and delay every job/watcher cycle)
            for rkey, t in list(next_retry.items()):
                if time.monotonic() >= t:
                    cmd = rkey.split("-", 1)[1].split("@")[0]
                    desc = f"RETRY {cmd}"
                    del next_retry[rkey]
                    if not _run_job(cmd, desc):
                        logger.error(
                            f"{cmd}: retry failed — manual attention needed "
                            f"(the next SCHEDULED run of this job is the natural "
                            f"fallback: daily jobs tomorrow, weekly jobs next week)"
                        )

            # Scheduled jobs — per-entry key (built by _due_jobs, identical format)
            for cmd, desc, key in _due_jobs(now_wib, last_run):
                ok = _run_job(cmd, desc)
                last_run[key] = "1"
                if not ok:
                    next_retry[key] = time.monotonic() + RETRY_DELAY_S
                    logger.warning(f"  retry {cmd} in {RETRY_DELAY_S // 60} minutes")

            # Watcher: run every ~60 seconds
            if time.monotonic() - last_watch >= WATCH_INTERVAL_S:
                last_watch = time.monotonic()
                _run_job("watch", "Alert watcher")

            # Rotate logs daily
            cycle += 1
            if cycle % 2880 == 0:
                _setup_logging()
            time.sleep(30)
    finally:
        LOCKFILE.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arkwatch daemon")
    p.add_argument("--once", action="store_true", help="run the loop once then exit (for testing)")
    a = p.parse_args(argv)
    if a.once:
        _setup_logging()
        _heartbeat()
        now_wib = datetime.now(WIB)
        for cmd, desc, _key in _due_jobs(now_wib, {}):
            _run_job(cmd, desc)
        logger.info("=== daemon --once done ===")
        return 0
    run_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
