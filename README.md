# Rowe Auto backend

FastAPI + SQLite intake service for First Rowe Auto Repairs & Sales.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

The frontend defaults to `http://localhost:8000`. In production set:

- `FRONTEND_ORIGINS=https://your-frontend.example`
- `ROWE_DB_PATH=/persistent/path/roweauto.db`

Endpoints:

- `GET /health`
- `POST /api/intakes`
- `GET /api/intakes`
- `GET /api/intakes/{id}`

Repair records require the operationally important fields: customer name, mobile phone, email, referral source, year, make, model/trim, mileage, VIN, and customer concern. VIN is validated as 17 characters.
