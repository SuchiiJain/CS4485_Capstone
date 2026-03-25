# Team Setup: Scanner DB + API + Frontend

This guide makes the Docrot backend usable by any team member with the same steps.

## 1. Clone and install

From the scanner repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install flask
```

## 2. Generate local scan data (optional if pulling DB updates from branch)

```powershell
python -m src.run .
```

This updates `.docrot-fingerprints.json` and may create `.docrot-report.json`.

## 3. Start API server

```powershell
.\scripts\start_api.ps1 -Port 8010 -Token "team-shared-token"
```

Default database path is `database/docrot.db`.

If needed, override DB location:

```powershell
.\scripts\start_api.ps1 -Port 8010 -Token "team-shared-token" -DbPath "C:\path\to\docrot.db"
```

## 4. Verify DB content quickly

```powershell
.\.venv\Scripts\python.exe .\scripts\check_db.py
```

## 5. Connect frontend repo

In frontend `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8010/api
VITE_DOCROT_TOKEN=team-shared-token
```

## 6. Frontend endpoints to call

- `GET /api/health`
- `GET /api/scans`
- `GET /api/scans/:scan_id`
- `GET /api/scans/:scan_id/issues`
- `GET /api/scans/:scan_id/docs`
- `GET /api/scans/:scan_id/report`
- `GET /api/fingerprints/summary`

## Team workflow recommendation

- Use one branch as source of truth for generated DB artifacts (for now).
- GitHub Action writes updates to `database/docrot.db` and `.docrot-fingerprints.json`.
- Team members run `git pull` before local frontend testing.
- Long-term: move DB to hosted Postgres and keep this API layer as read service.
