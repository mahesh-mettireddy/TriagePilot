# TransfersDemoApp Microservice

Target banking microservice for **TriagePilot** evaluation (Google Cloud AI Builder Cup 2026).

## Modules
- `app/transfers/`: Core payment orchestration, cutoff windows, and idempotency handling.
- `app/fees/`: Percentage fee calculation and tier logic.
- `app/notifications/`: SMS notification gateway dispatch.
- `app/limits/`: Retail daily volume limits.
- `app/settlement/`: NEFT batch settlement processing.
- `app/beneficiary/`: Beneficiary validation and registration.

## Running Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
