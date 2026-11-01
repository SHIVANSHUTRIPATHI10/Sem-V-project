from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .schemas import TransactionRequest
from .predictor import predict_transaction
from .database import (
    create_tables, get_previous_transactions, save_transaction,
    get_transaction_history, get_fraud_alerts, get_dashboard_stats,
    get_all_transactions, update_feedback
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="AI Financial Risk & Fraud Detection System",
    description="Multi-model financial fraud detection using XGBoost, LSTM and Autoencoder",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

create_tables()

class FeedbackRequest(BaseModel):
    feedback: str

# ==================================================
# HOME PAGE (NEW)
# ==================================================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="home.html")

# ==================================================
# DASHBOARD
# ==================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.post("/predict")
def predict(transaction: TransactionRequest):
    previous_transactions = get_previous_transactions(transaction.nameDest, limit=5)
    result = predict_transaction(
        transaction_id=transaction.transaction_id,
        amount=transaction.amount,
        oldbalanceOrg=transaction.oldbalanceOrg,
        oldbalanceDest=transaction.oldbalanceDest,
        transaction_type=transaction.type,
        step=transaction.step,
        previous_transactions=previous_transactions
    )

    transaction_data = {
        "transaction_id": transaction.transaction_id, "step": transaction.step,
        "amount": transaction.amount, "oldbalanceOrg": transaction.oldbalanceOrg,
        "oldbalanceDest": transaction.oldbalanceDest, "type": transaction.type,
        "nameDest": transaction.nameDest, "xgb_score": result["xgb_score"],
        "lstm_score": result["lstm_score"], "ae_score": result["ae_score"],
        "reconstruction_error": result["reconstruction_error"], "risk_score": result["risk_score"],
        "risk_level": result["risk_level"], "decision": result["decision"], "alert": result["alert"]
    }

    save_transaction(transaction_data)
    return {**result, "previous_transactions_used": len(previous_transactions)}

@app.get("/transactions/{nameDest}")
def transaction_history(nameDest: str):
    transactions = get_transaction_history(nameDest)
    return {"nameDest": nameDest, "total_transactions": len(transactions), "transactions": transactions}

@app.get("/alerts")
def fraud_alerts():
    alerts = get_fraud_alerts()
    return {"total_alerts": len(alerts), "alerts": alerts}

@app.post("/alerts/{transaction_id}/feedback")
def submit_feedback(transaction_id: str, request: FeedbackRequest):
    update_feedback(transaction_id, request.feedback)
    return {"status": "success", "message": "Feedback saved successfully"}

@app.get("/dashboard/stats")
def dashboard_stats():
    return get_dashboard_stats()

@app.get("/transactions")
def transactions_list():
    transactions = get_all_transactions()
    return {"transactions": transactions}