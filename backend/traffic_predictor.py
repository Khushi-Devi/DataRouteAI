
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = PROJECT_DIR / "data" / "traffic_history.csv"
MODEL_FILE = PROJECT_DIR / "models" / "best_model.keras"
SCALER_FILE = PROJECT_DIR / "models" / "route_scalers.joblib"
ROUTE_CONFIG_FILE = PROJECT_DIR / "models" / "route_config.json"
MODEL_CONFIG_FILE = PROJECT_DIR / "models" / "model_config.json"


# --------------------------------------------------
# LOAD MODEL AND CONFIGURATIONS
# --------------------------------------------------

model = tf.keras.models.load_model(MODEL_FILE)

route_scalers = joblib.load(SCALER_FILE)

with open(ROUTE_CONFIG_FILE, "r") as file:
    route_config = json.load(file)

with open(MODEL_CONFIG_FILE, "r") as file:
    model_config = json.load(file)


route_ids = route_config["route_ids"]
route_to_index = route_config["route_to_index"]

LOOKBACK = model_config["lookback"]
FEATURE_COUNT = model_config["feature_count"]

BASE_FEATURE_COLUMNS = model_config["base_feature_columns"]


# --------------------------------------------------
# VALIDATE MODEL CONFIGURATION
# --------------------------------------------------

if LOOKBACK != 24:
    raise ValueError(f"Expected lookback 24, got {LOOKBACK}")

if FEATURE_COUNT != 77:
    raise ValueError(f"Expected 77 features, got {FEATURE_COUNT}")

if model.input_shape[1:] != (LOOKBACK, FEATURE_COUNT):
    raise ValueError("Model input shape does not match configuration.")

if set(route_ids) != set(route_scalers.keys()):
    raise ValueError("Route IDs and scaler routes do not match.")


# --------------------------------------------------
# LOAD TRAFFIC HISTORY
# --------------------------------------------------

def load_traffic_data():

    df = pd.read_csv(DATA_FILE)

    required_columns = [
        "timestamp",
        "source_region",
        "destination_region",
        "traffic_volume_gb"
    ]

    if not all(col in df.columns for col in required_columns):
        raise ValueError("Traffic dataset is missing required columns.")

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    df["route_id"] = (
        df["source_region"].astype(str)
        + "->"
        + df["destination_region"].astype(str)
    )

    df["traffic_volume_gb"] = pd.to_numeric(
        df["traffic_volume_gb"],
        errors="raise"
    )

    return df


# --------------------------------------------------
# PREDICT NEXT-HOUR TRAFFIC
# --------------------------------------------------

def predict_traffic(source_region: str, destination_region: str):

    route_id = f"{source_region}->{destination_region}"

    # Check whether the route exists
    if route_id not in route_to_index:
        raise ValueError(f"Unknown route: {route_id}")

    if route_id not in route_scalers:
        raise ValueError(f"No scaler available for route: {route_id}")

    # Load historical traffic
    df = load_traffic_data()

    route_data = df[df["route_id"] == route_id].copy()

    if len(route_data) < LOOKBACK:
        raise ValueError("Not enough historical observations for prediction.")

    route_data = route_data.sort_values("timestamp").reset_index(drop=True)

    # Select latest 24 observations
    latest_data = route_data.tail(LOOKBACK).copy()

    # Verify hourly continuity
    time_differences = latest_data["timestamp"].diff().dropna()

    if not (time_differences == pd.Timedelta(hours=1)).all():
        raise ValueError("Latest 24 observations are not hourly continuous.")

    # --------------------------------------------------
    # RECREATE TRAINING FEATURES
    # --------------------------------------------------

    timestamps = latest_data["timestamp"]

    hour = timestamps.dt.hour.to_numpy()
    dow = timestamps.dt.dayofweek.to_numpy()

    latest_data["hour_sin"] = np.sin(
        2 * np.pi * hour / 24
    )

    latest_data["hour_cos"] = np.cos(
        2 * np.pi * hour / 24
    )

    latest_data["dow_sin"] = np.sin(
        2 * np.pi * dow / 7
    )

    latest_data["dow_cos"] = np.cos(
        2 * np.pi * dow / 7
    )

    # --------------------------------------------------
    # ROUTE-SPECIFIC SCALING
    # --------------------------------------------------

    scaler = route_scalers[route_id]

    traffic_values = latest_data[
        ["traffic_volume_gb"]
    ]

    latest_data["traffic_scaled"] = scaler.transform(
        traffic_values
    ).astype(np.float32)

    # --------------------------------------------------
    # BUILD BASE FEATURES
    # --------------------------------------------------

    base_features = latest_data[
        BASE_FEATURE_COLUMNS
    ].to_numpy(dtype=np.float32)

    # --------------------------------------------------
    # BUILD ROUTE ONE-HOT FEATURES
    # --------------------------------------------------

    route_one_hot = np.zeros(
        len(route_ids),
        dtype=np.float32
    )

    route_index = route_to_index[route_id]

    route_one_hot[route_index] = 1.0

    route_features = np.broadcast_to(
        route_one_hot,
        (LOOKBACK, len(route_ids))
    )

    # --------------------------------------------------
    # COMBINE ALL 77 FEATURES
    # --------------------------------------------------

    features = np.concatenate(
        [base_features, route_features],
        axis=1
    ).astype(np.float32)

    if features.shape != (LOOKBACK, FEATURE_COUNT):
        raise ValueError(
            f"Unexpected feature shape: {features.shape}"
        )

    # Add batch dimension
    model_input = np.expand_dims(features, axis=0)

    # --------------------------------------------------
    # MODEL PREDICTION
    # --------------------------------------------------

    predicted_scaled = model.predict(
        model_input,
        verbose=0
    )

    # Convert prediction back into GB
    predicted_gb = scaler.inverse_transform(
        predicted_scaled.reshape(-1, 1)
    )[0][0]

    last_timestamp = latest_data["timestamp"].iloc[-1]

    prediction_timestamp = (
        last_timestamp + pd.Timedelta(hours=1)
    )

    return {
        "route_id": route_id,
        "source_region": source_region,
        "destination_region": destination_region,
        "last_observation_timestamp": last_timestamp.isoformat(),
        "prediction_timestamp": prediction_timestamp.isoformat(),
        "predicted_traffic_gb": round(float(predicted_gb), 4),
        "unit": "GB",
        "lookback_hours": LOOKBACK
    }
