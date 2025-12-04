import os
import pandas as pd
import numpy as np
import joblib

# If you trained using xgboost, the imported classes will be inside joblib file.
# No need to import xgboost explicitly here, but it's fine if you do.


MODEL_PATH = os.path.join("models", "xgb_missing_values.pkl")

_xgb_model = None  # cached model


def _load_model():
    """Lazy-load the XGBoost model from disk."""
    global _xgb_model

    if _xgb_model is not None:
        return _xgb_model

    if not os.path.exists(MODEL_PATH):
        print(f"[ml_utils] WARNING: model file not found at {MODEL_PATH}. "
              f"Skipping imputation.")
        _xgb_model = None
        return None

    try:
        _xgb_model = joblib.load(MODEL_PATH)
        print("[ml_utils] Loaded XGBoost model from", MODEL_PATH)
    except Exception as e:
        print("[ml_utils] ERROR loading model:", e)
        _xgb_model = None

    return _xgb_model


def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing CO2_per_kg using the XGBoost model.

    IMPORTANT:
    - You must adapt `feature_cols` to match what you used in Colab.
    - Model must be trained to predict CO2_per_kg.

    If model is not available, returns df unchanged.
    """

    model = _load_model()
    if model is None:
        # no model available; do nothing
        return df

    if "CO2_per_kg" not in df.columns:
        # nothing to do
        return df

    # 👇 EXAMPLE feature columns – CHANGE THESE to your real ones
    feature_cols = [
        # "energy_kwh_per_kg",
        # "recycling_rate",
        # "ore_grade",
        # "region_index",
    ]

    # If you haven't added those columns yet, just return df
    if not set(feature_cols).issubset(df.columns):
        print("[ml_utils] Feature columns missing; skipping imputation.")
        return df

    mask = df["CO2_per_kg"].isna()
    if not mask.any():
        return df

    X = df.loc[mask, feature_cols].values

    try:
        y_pred = model.predict(X)
        df.loc[mask, "CO2_per_kg"] = y_pred
        print(f"[ml_utils] Imputed {mask.sum()} missing CO2_per_kg values.")
    except Exception as e:
        print("[ml_utils] ERROR during prediction:", e)

    return df
