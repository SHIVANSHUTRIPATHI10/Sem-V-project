import numpy as np
import pandas as pd

from .model_loader import (
    xgb_model, lstm_model, autoencoder,
    scaler_lstm, scaler_ae, shap_explainer
)

XGB_FEATURES = [
    "step", "amount", "oldbalanceOrg", "oldbalanceDest",
    "amount_to_sender_balance", "amount_to_receiver_balance",
    "type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"
]

AE_FEATURES = [
    "amount", "oldbalanceOrg", "oldbalanceDest",
    "amount_to_sender_balance", "amount_to_receiver_balance",
    "type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"
]

LSTM_FEATURES = [
    "step", "amount", "oldbalanceOrg", "oldbalanceDest",
    "amount_to_sender_balance", "amount_to_receiver_balance",
    "type_CASH_IN", "type_CASH_OUT", "type_DEBIT", "type_PAYMENT", "type_TRANSFER"
]

AE_THRESHOLD = 0.009602353463509097

FEATURE_EXPLANATIONS = {
    "amount_to_sender_balance": "Transaction amount is very high relative to the sender's available balance",
    "amount": "Transaction involves a very large amount",
    "oldbalanceOrg": "Sender has a large balance involved in the transaction",
    "oldbalanceDest": "Receiver has a large existing balance",
    "amount_to_receiver_balance": "Transaction amount is significant relative to the receiver's balance",
    "step": "Transaction timing contributed to the risk assessment"
}


def encode_transaction(transaction):
    amount = transaction["amount"]
    oldbalance_org = transaction["oldbalanceOrg"]
    oldbalance_dest = transaction["oldbalanceDest"]

    result = {
        "step": transaction["step"],
        "amount": amount,
        "oldbalanceOrg": oldbalance_org,
        "oldbalanceDest": oldbalance_dest,
        "amount_to_sender_balance": amount / (oldbalance_org + 1),
        "amount_to_receiver_balance": amount / (oldbalance_dest + 1),
        "type_CASH_IN": 0, "type_CASH_OUT": 0, "type_DEBIT": 0, "type_PAYMENT": 0, "type_TRANSFER": 0
    }
    
    transaction_type = transaction["type"]
    column = f"type_{transaction_type}"
    if column in result:
        result[column] = 1
    return result


def get_lstm_score(previous_transactions):
    if previous_transactions is None or len(previous_transactions) < 5:
        return None

    previous_transactions = previous_transactions[-5:]
    encoded_transactions = [encode_transaction(tx) for tx in previous_transactions]
    df_lstm = pd.DataFrame(encoded_transactions)

    try:
        X = df_lstm[LSTM_FEATURES].values.astype(float)
    except KeyError as e:
        print("LSTM feature error:", e)
        return None

    X = X.reshape(1, 5, 11)
    X_flat = X.reshape(-1, 11)
    X_scaled = scaler_lstm.transform(X_flat)
    X_scaled = X_scaled.reshape(1, 5, 11)

    score = lstm_model.predict(X_scaled, verbose=0)[0][0]
    return float(score)


def predict_transaction(transaction_id, amount, oldbalanceOrg, oldbalanceDest, transaction_type, step, previous_transactions):
    current_transaction = {
        "step": step, "amount": amount, "oldbalanceOrg": oldbalanceOrg,
        "oldbalanceDest": oldbalanceDest, "type": transaction_type
    }
    encoded = encode_transaction(current_transaction)

    # ========================================================
    # RULE-BASED OVERRIDE (Business Logic Layer)
    # ========================================================
    # If the amount exceeds the sender's balance, it's an automatic HIGH risk.
    # This bypasses the ML model because no legitimate transaction can do this.
    if amount > oldbalanceOrg:
        return {
            "transaction_id": transaction_id,
            "xgb_score": 1.0,
            "lstm_score": None,
            "ae_score": 1.0,
            "reconstruction_error": 0.0,
            "risk_score": 1.0,
            "risk_level": "HIGH",
            "decision": "MANUAL REVIEW",
            "alert": True,
            "explanations": [
                {
                    "feature": "amount_vs_balance",
                    "value": 1.0,
                    "text": f"CRITICAL: Transfer amount (${amount:,.2f}) exceeds sender's balance (${oldbalanceOrg:,.2f}). Overdraft attempt detected."
                }
            ]
        }

    # ========================================================
    # ML PREDICTION (Existing logic continues below)
    # ========================================================
    # XGBOOST
    xgb_input = pd.DataFrame([[encoded[col] for col in XGB_FEATURES]], columns=XGB_FEATURES)
    xgb_score = float(xgb_model.predict_proba(xgb_input)[0][1])

    # SHAP EXPLANATION (Dynamic and corrected)
    shap_values = shap_explainer.shap_values(xgb_input)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    shap_values = np.array(shap_values).flatten()

    feature_importance = pd.DataFrame({"feature": XGB_FEATURES, "shap_value": shap_values})
    feature_importance["abs_shap"] = feature_importance["shap_value"].abs()
    top_features = feature_importance.sort_values("abs_shap", ascending=False).head(5)

    explanations = []
    for _, row in top_features.iterrows():
        feature = row["feature"]
        shap_value = row["shap_value"]
        actual_value = encoded.get(feature, 0)
        
        impact = "increased" if shap_value > 0 else "decreased"
        
        # DYNAMIC TEXT GENERATION
        if feature.startswith("type_"):
            tx_type = feature.replace("type_", "")
            if actual_value == 1:
                text = f"Transaction IS a {tx_type}"
            else:
                text = f"Transaction is NOT a {tx_type}"
        else:
            base_text = FEATURE_EXPLANATIONS.get(feature, f"{feature} impacted the decision")
            if feature == "amount_to_sender_balance":
                text = f"{base_text} (Ratio: {actual_value:.2f})"
            elif feature == "amount_to_receiver_balance":
                text = f"{base_text} (Ratio: {actual_value:.2f})"
            elif feature == "amount":
                text = f"{base_text} (Amount: {actual_value})"
            else:
                text = base_text

        explanations.append({
            "feature": feature,
            "value": round(float(shap_value), 4),
            "text": f"{text} ({impact} risk)"
        })

    # AUTOENCODER
    ae_input = np.array([[encoded[col] for col in AE_FEATURES]], dtype=float)
    ae_scaled = scaler_ae.transform(ae_input)
    reconstruction = autoencoder.predict(ae_scaled, verbose=0)
    reconstruction_error = float(np.mean(np.square(ae_scaled - reconstruction), axis=1)[0])
    ae_score = min(reconstruction_error / AE_THRESHOLD, 1.0)

    # LSTM
    lstm_score = get_lstm_score(previous_transactions)

    # RISK ENGINE
    if lstm_score is not None:
        risk_score = (0.4 * xgb_score + 0.3 * lstm_score + 0.3 * ae_score)
    else:
        risk_score = (0.5714 * xgb_score + 0.4286 * ae_score)

    if risk_score < 0.20:
        risk_level = "LOW"
    elif risk_score < 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    if risk_level == "HIGH":
        decision = "MANUAL REVIEW"
    elif risk_level == "MEDIUM":
        decision = "ADDITIONAL VERIFICATION"
    else:
        decision = "APPROVE"

    alert = risk_level in ["MEDIUM", "HIGH"]

    return {
        "transaction_id": transaction_id,
        "xgb_score": round(xgb_score, 4),
        "lstm_score": None if lstm_score is None else round(lstm_score, 4),
        "ae_score": round(ae_score, 4),
        "reconstruction_error": round(reconstruction_error, 6),
        "risk_score": round(risk_score, 4),
        "risk_level": risk_level,
        "decision": decision,
        "alert": alert,
        "explanations": explanations
    }