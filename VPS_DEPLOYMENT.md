# Windows to Linux VPS deployment

1. Create an Ubuntu 24.04 VPS with at least 2 vCPU, 4 GB RAM, and 40 GB SSD.
2. Point the customer domain to the VPS. Keep the Owner Console DNS-free/private.
3. Install Docker, Docker Compose, Git, UFW, unattended-upgrades, and Tailscale.
4. Allow only SSH, HTTP, HTTPS, and Tailscale; never expose PostgreSQL, Redis, or port 9000:
   `ufw default deny incoming`, `ufw allow OpenSSH`, `ufw allow 80/tcp`,
   `ufw allow 443/tcp`, then `ufw enable`.
5. Clone the repository on the VPS. Copy `.env.production.example` to `.env` and
   supply secrets using the VPS secret manager—not Git.
6. On the Windows development machine run `scripts/setup_owner_console.py`. Store its
   password hash, console secret, and TOTP secret in the VPS secret manager. Add the
   TOTP secret to an authenticator application.
7. Start PostgreSQL, Redis, backend, frontend, and Owner Console with
   `docker compose up -d --build`.
8. Put the public site behind Caddy, Nginx, or a managed HTTPS load balancer. Enable
   automatic TLS renewal and forwarded-protocol headers.
9. Join the VPS and owner device to the same Tailscale network. Keep port 9000 bound
   to `127.0.0.1`; access it using an SSH tunnel (`ssh -L 9000:127.0.0.1:9000 user@vps`)
   or a Tailscale Serve rule restricted to the tailnet.
10. Open `https://localhost:9000` through the tunnel, log in with the independent owner
    password and authenticator code, then add server provider credentials.
11. Run the staging Test Center, load test, provider smoke check, webhook test, database
    backup, and restore drill before accepting customers.
12. Enable daily encrypted PostgreSQL backups, off-server retention, uptime alerts,
    log rotation, monthly dependency updates, and quarterly credential rotation.
