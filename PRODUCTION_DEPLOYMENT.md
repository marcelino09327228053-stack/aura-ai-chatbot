# Production deployment checklist

- Generate independent random values (32+ characters) for `SECRET_KEY`,
  `PAYMENT_WEBHOOK_SECRET`, and `AI_METRICS_BEARER_TOKEN` in a secret manager.
- Configure only server-side AI provider keys; never place them in browser assets.
- Use PostgreSQL with encrypted storage, restricted credentials, and automated daily
  backups. Test restoration regularly and retain copies outside the primary region.
- Use Redis with authentication/TLS where supported. Do not expose port 6379 publicly.
- Terminate TLS at the trusted reverse proxy, preserve forwarded-protocol headers, and
  keep `FORCE_HTTPS=true`.
- Restrict `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to the production domain.
- Protect `/internal/ai/*` with the metrics bearer token and network allow-listing.
- Rotate webhook, provider, metrics, and JWT secrets on a documented schedule.
- Run `python -m compileall -q app tests scripts` and the isolated test suite before deploy.
- Run `scripts/load_test_ai_gateway.py` using staging capacity settings before releases.
- Run `scripts/check_ai_providers.py` only in a controlled provider sandbox because it
  makes billable API calls.
