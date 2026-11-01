from pathlib import Path
import joblib
import shap
import xgboost as xgb
from tensorflow.keras.models import load_model

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

XGB_PATH = MODEL_DIR / "xgboost_model.json"
LSTM_PATH = MODEL_DIR / "lstm_model.keras"
AE_PATH = MODEL_DIR / "autoencoder.keras"
LSTM_SCALER_PATH = MODEL_DIR / "scaler_lstm.pkl"
AE_SCALER_PATH = MODEL_DIR / "scaler_ae.pkl"

print("\nModel directory:", MODEL_DIR)
print("\nChecking model files...")

for path in [XGB_PATH, LSTM_PATH, AE_PATH, LSTM_SCALER_PATH, AE_SCALER_PATH]:
    print(path.name, "->", "FOUND" if path.exists() else "MISSING")

xgb_model = xgb.XGBClassifier()
xgb_model.load_model(str(XGB_PATH))

lstm_model = load_model(str(LSTM_PATH))
autoencoder = load_model(str(AE_PATH))

scaler_lstm = joblib.load(LSTM_SCALER_PATH)
scaler_ae = joblib.load(AE_SCALER_PATH)

shap_explainer = shap.TreeExplainer(xgb_model)

print("\nAll models loaded successfully!")
print("SHAP explainer loaded successfully!")