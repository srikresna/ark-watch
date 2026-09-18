# Server ops runbook

## Deploy (satu perintah, di server)

```bash
cd ~/ark-watch && bash scripts/deploy.sh
```

Pull + restart **terverifikasi** (bukti: `ExecMainStartTimestamp` berubah) +
cuplikan log. Deploy gagal = skrip exit non-zero dengan pesan jelas.

## Prasyarat (sekali saja, sebagai root)

Aturan sudoers agar restart tidak pernah bergantung pada password yang
di-pipe (sumber dua kegagalan senyap 2026-09-17):

```bash
sudo tee /etc/sudoers.d/arkwatch-restart >/dev/null <<'EOF'
kresna ALL=(root) NOPASSWD: /bin/systemctl restart arkwatch, /bin/systemctl start arkwatch, /bin/systemctl stop arkwatch
EOF
sudo chmod 440 /etc/sudoers.d/arkwatch-restart
sudo visudo -c   # harus: parsed OK
```

## Aturan emas

> **`is-active` bukan bukti restart** — proses lama pun "active".
> Bukti restart = timestamp mulai proses BERUBANG.
# (verifikasi: `systemctl show arkwatch -p ExecMainStartTimestamp`)

Selalu gunakan `scripts/restart-verified.sh`; jangan pernah
`systemctl restart` telanjang lewat SSH + pipe password.
