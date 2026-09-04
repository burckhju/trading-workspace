# Linux quick start

See `docs/technical/LINUX_DEPLOYMENT.md` for the supported ZIP download, Docker Compose configuration, monitoring/Telegram setup, verification and smoke-test procedure.

Quick start after extracting the repository:

```bash
cp docker/.env.example docker/.env
chmod 600 docker/.env
# edit docker/.env and replace the database password; configure EODHD/Telegram only when needed
bash scripts/start-linux.sh
```

Frontend: `http://localhost:8080`

Backend: `http://localhost:8000`
