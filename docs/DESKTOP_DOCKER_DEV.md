# SentinelLab desktop Docker development (opt-in)

This stack runs FastAPI on **127.0.0.1:18765** and MongoDB in a Docker named volume. Tauri remains native. It does **not** change the default compose.yaml deployment and does **not** automatically import Windows MongoDB data.

## Before switching: preserve existing analyst accounts

Do not stop, uninstall, reset, or delete the Windows MongoDB service or its data. First list databases on Windows using the existing Python venv:

```powershell
@'
from pymongo import MongoClient
c = MongoClient('mongodb://127.0.0.1:27017', serverSelectionTimeoutMS=5000)
for n in c.list_database_names():
    if 'users' in c[n].list_collection_names():
        print(n, c[n].users.count_documents({}))
'@ | .\.venv\Scripts\python.exe -
```

Confirm the original database name and user count. Before any migration, take a tested backup with `mongodump` (MongoDB Database Tools) to a **local folder outside the repository**, e.g. `mongodump --uri mongodb://127.0.0.1:27017 --db ORIGINAL_DB_NAME --out C:\\SentinelLabBackups\\before-docker`. Do not upload the backup to GitHub. A new Docker volume will initially be empty and may create only a bootstrap administrator; this does not mean old users were deleted. Migration/import must be verified separately before changing the desktop backend.

## Configure

Create `.env.desktop` in the repo root (gitignored by `.env.*`):

```dotenv
DB_NAME=VERIFIED_ORIGINAL_DB_NAME
JWT_SECRET=REUSE_EXISTING_SECRET
ADMIN_PASSWORD=REUSE_EXISTING_ADMIN_PASSWORD
ADMIN_EMAIL=admin@sentinellab.io
```

Use the exact existing values; never commit them. Ensure Docker Desktop is running. **Stop the existing Python backend on port 18765 before starting the container**, but leave Windows MongoDB intact until backup and migration are verified.

## Run and check

```powershell
docker compose -f compose.desktop.yaml --env-file .env.desktop config --quiet
docker compose -f compose.desktop.yaml --env-file .env.desktop up -d --build
docker compose -f compose.desktop.yaml --env-file .env.desktop ps
Invoke-RestMethod http://127.0.0.1:18765/api/health
```

View logs: `docker compose -f compose.desktop.yaml --env-file .env.desktop logs -f api`.
Stop without deleting data: `docker compose -f compose.desktop.yaml --env-file .env.desktop down`.
**Never use `down -v`** unless you intentionally want to erase Docker's database volume.

## Important migration gate

The Compose stack is provisioned but **not a completed migration**. Before treating it as the canonical backend, import the backed-up original database into the Docker MongoDB instance using MongoDB Database Tools, verify the original user count and sign-in, then test the Role dropdown. Do not point the desktop at a fresh empty MongoDB and assume missing users were deleted. If the API image build fails, retain the original Windows setup and share the Docker build logs.
