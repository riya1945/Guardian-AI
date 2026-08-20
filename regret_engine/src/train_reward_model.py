import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data" / "synthetic_training_data.csv"

MODEL_DIR = BASE_DIR / "models"

MODEL_FILE = MODEL_DIR / "reward_model.joblib"

METRICS_FILE = MODEL_DIR / "reward_model_metrics.json"

TARGET = "units_sold"


FEATURES = [
    "StockCode",

    # Current pricing
    "price",
    "log_price",
    "price_change",
    "price_ratio",
    "price_vs_historical_avg",

    # Historical demand
    "previous_units",
    "previous_price",
    "rolling_7d_units",
    "rolling_30d_units",
    "demand_trend",
    "demand_momentum",

    # Calendar
    "day_of_week",
    "month",
    "year",
    "is_weekend",
]

CATEGORICAL_FEATURES = [
    "StockCode",
]


NUMERIC_FEATURES = [
    "price",
    "log_price",
    "price_change",
    "price_ratio",
    "price_vs_historical_avg",
    "previous_units",
    "previous_price",
    "rolling_7d_units",
    "rolling_30d_units",
    "demand_trend",
    "demand_momentum",
    "day_of_week",
    "month",
    "year",
    "is_weekend",
]


def load_data():
    print("Loading training data...")

    df = pd.read_csv(
        DATA_FILE,
        low_memory=False,
        dtype={"StockCode": str},
    )

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date").reset_index(drop=True)

    print(f"Total observations: {len(df):,}")

    print(
        f"Date range: "
        f"{df['date'].min().date()} "
        f"to "
        f"{df['date'].max().date()}"
    )

    return df

def split_data(df):
    print("\nCreating time-based train/validation/test split...")

    dates = df["date"].sort_values().unique()

    train_end = dates[int(len(dates) * 0.70)]
    validation_end = dates[int(len(dates) * 0.85)]

    train = df[
        df["date"] < train_end
    ].copy()

    validation = df[
        (df["date"] >= train_end)
        & (df["date"] < validation_end)
    ].copy()

    test = df[
        df["date"] >= validation_end
    ].copy()

    print(
        f"\nTrain:"
        f"       {len(train):,} rows"
        f" | {train['date'].min().date()} → {train['date'].max().date()}"
    )

    print(
        f"Validation:"
        f" {len(validation):,} rows"
        f" | {validation['date'].min().date()} → {validation['date'].max().date()}"
    )

    print(
        f"Test:"
        f"       {len(test):,} rows"
        f" | {test['date'].min().date()} → {test['date'].max().date()}"
    )

    return train, validation, test


def prepare_features(df):

    X = df[FEATURES].copy()

    y = np.log1p(
        df[TARGET].astype(float)
    )
    X = X.replace(
    [np.inf, -np.inf],
    np.nan,
)

    X = X.fillna(0)
    return X, y


def build_model():

    print("\nBuilding reward model...")

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "sku",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="passthrough",
    )

    model = HistGradientBoostingRegressor(
   
    max_iter=120,
learning_rate=0.08,
max_leaf_nodes=15,
min_samples_leaf=50,
l2_regularization=2.0,
)

    return preprocessor, model

def evaluate(
    name,
    pipeline,
    X,
    y_log,
):

    # Model prediction is log(1 + units)
    predictions_log = pipeline.predict(X)

    # Convert back to actual units
    predictions = np.expm1(
        predictions_log
    )

    predictions = np.maximum(
        predictions,
        0,
    )

    # Convert actual target back to units
    actual = np.expm1(y_log)

    mae = mean_absolute_error(
        actual,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predictions,
        )
    )

    r2 = r2_score(
        actual,
        predictions,
    )

    # Also calculate metrics in log space
    log_mae = mean_absolute_error(
        y_log,
        predictions_log,
    )

    log_rmse = np.sqrt(
        mean_squared_error(
            y_log,
            predictions_log,
        )
    )

    log_r2 = r2_score(
        y_log,
        predictions_log,
    )

    print("\n" + "=" * 60)
    print(f"{name.upper()} RESULTS")
    print("=" * 60)

    print("\nOriginal units:")
    print(
        f"MAE:  {mae:.4f}"
    )

    print(
        f"RMSE: {rmse:.4f}"
    )

    print(
        f"R²:   {r2:.4f}"
    )

    print("\nLog demand:")
    print(
        f"MAE:  {log_mae:.4f}"
    )

    print(
        f"RMSE: {log_rmse:.4f}"
    )

    print(
        f"R²:   {log_r2:.4f}"
    )

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
        "log_mae": float(log_mae),
        "log_rmse": float(log_rmse),
        "log_r2": float(log_r2),
    }

def main():

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

   

    df = load_data()



    train, validation, test = split_data(df)

 

    X_train, y_train = prepare_features(train)

    X_validation, y_validation = prepare_features(
        validation
    )

    X_test, y_test = prepare_features(
        test
    )

    print(
        f"\nTraining features: "
        f"{X_train.shape}"
    )

 

    preprocessor, model = build_model()


    print("\nFitting feature preprocessing...")

    X_train_transformed = (
        preprocessor.fit_transform(
            X_train
        )
    )

    X_validation_transformed = (
        preprocessor.transform(
            X_validation
        )
    )

    X_test_transformed = (
        preprocessor.transform(
            X_test
        )
    )

    print(
        "Transformed feature shape:",
        X_train_transformed.shape,
    )


    print("\nTraining reward model...")

    model.fit(
        X_train_transformed,
        y_train,
    )

    print("Training complete.")


    validation_metrics = evaluate(
        "Validation",
        model,
        X_validation_transformed,
        y_validation,
    )

    

    test_metrics = evaluate(
        "Test",
        model,
        X_test_transformed,
        y_test,
    )

  

    pipeline = {
    "preprocessor": preprocessor,
    "model": model,
    "features": FEATURES,
    "target": TARGET,
    "target_transform": "log1p",
}

    joblib.dump(
        pipeline,
        MODEL_FILE,
    )

    print(
        f"\nSaved reward model to:"
    )

    print(MODEL_FILE)


    metrics = {
        "target": TARGET,
        "features": FEATURES,
        "validation": validation_metrics,
        "test": test_metrics,
    }

    with open(
        METRICS_FILE,
        "w",
    ) as f:

        json.dump(
            metrics,
            f,
            indent=4,
        )

    print(
        f"Saved metrics to:"
    )

    print(METRICS_FILE)

    print(
        "\nReward model training complete!"
    )


if __name__ == "__main__":
    main()