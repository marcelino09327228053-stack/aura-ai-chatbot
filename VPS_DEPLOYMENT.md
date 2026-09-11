# Windows to Linux VPS deployment

## 1. Prepare the VPS

Use Ubuntu 24.04 with at least 2 vCPU, 4 GB RAM, and 40 GB SSD. Point the
customer domain to the VPS. Install Docker Engine, Docker Compose, Git, UFW,
unattended-upgrades, and Tailscale.

Allow only SSH, HTTP, HTTPS, and Tailscale traffic. PostgreSQL (5432), Redis
(6379), the backend (8000), and Owner Console (9000) must never be public.

## 2. Prepare production configuration

Clone the repository, copy `.env.production.example` to `.env`, and replace
every placeholder. Use independent random credentials. URL-encode database and
Redis passwords inside their connection URLs. Never commit `.env`.

Generate Owner Console credentials locally with:

```text
python scripts/setup_owner_console.py
```

Store the generated values in the VPS secret manager and add the TOTP secret to
an authenticator app. Do not send secrets through chat or email.

Run the fail-closed check before starting containers:

```text
python scripts/production_preflight.py --env-file .env
```

## 3. Start the staging deployment

```text
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Caddy obtains and renews the public HTTPS certificate automatically. Nginx
proxies all customer routes to the private backend. PostgreSQL, Redis, and
private uploads use persistent Docker volumes. A PostgreSQL backup is created
daily and retained for 14 days by default.

## 4. Open the private Owner Console

Join the VPS and owner device to the same Tailscale network. Keep port 9000
bound to localhost. Use Tailscale Serve to provide a tailnet-only HTTPS address
that proxies to `http://127.0.0.1:9000`. Log in with the independent owner email,
password, and authenticator code, then add server-side AI provider credentials.

## 5. Verify before accepting customers

- Confirm `https://<domain>/health` returns `status: ok`.
- Test email login, chatbot, subscription blocking, referral attribution,
  agent profile upload, QR link, commissions, and payout requests.
- Confirm the Owner Console is unreachable from the public internet.
- Run a provider smoke test only in a controlled account because it is billable.
- Download a database backup off the VPS and perform a restore drill.
- Configure uptime alerts and encrypted off-server backup retention.

Mock payments are forcibly disabled in production. Customer billing will not
activate until a real payment provider webhook is configured and verified.
