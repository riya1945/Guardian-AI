from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel



# Paths


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_FILE = (
    BASE_DIR
    / "models"
    / "reward_model.joblib"
)


# Load reward model


print("Loading Guardian AI reward model...")

pipeline = joblib.load(MODEL_FILE)

PREPROCESSOR = pipeline["preprocessor"]
MODEL = pipeline["model"]

print("Reward model loaded successfully.")



# FastAPI


app = FastAPI(
    title="Guardian AI - Regret Engine",
    description=(
        "Off-policy counterfactual regret scoring "
        "for pricing decisions."
    ),
    version="1.0.0",
)


# Decision Input


class Decision(BaseModel):

    decision_id: str
    timestamp: str

    sku: str
    price: float

    # Historical/context information
    previous_units: float
    previous_price: float
    rolling_7d_units: float
    rolling_30d_units: float

    demand_trend: float
    demand_momentum: float

    day_of_week: int
    month: int
    year: int
    is_weekend: int

    historical_avg_price: float

    # Optional contextual fields.
    # They are accepted so the API matches the
    # agreed mock decision structure.
    demand_score: float | None = None
    competitor_price: float | None = None
    inventory: float | None = None
    season: str | None = None



# Candidate prices


N_PRICE_ALTERNATIVES = 5

MIN_PRICE_MULTIPLIER = 0.90
MAX_PRICE_MULTIPLIER = 1.10


def generate_candidate_prices(
    actual_price: float,
):

    multipliers = np.linspace(
        MIN_PRICE_MULTIPLIER,
        MAX_PRICE_MULTIPLIER,
        N_PRICE_ALTERNATIVES,
    )

    candidates = (
        actual_price * multipliers
    )

    # Always include actual price.
    candidates = np.append(
        candidates,
        actual_price,
    )

    candidates = np.round(
        candidates,
        2,
    )

    candidates = np.unique(
        candidates
    )

    candidates = candidates[
        candidates > 0
    ]

    return candidates



# Build model features


def build_features(
    decision: Decision,
    candidate_price: float,
):

    price_change = (
        candidate_price
        - decision.previous_price
    )

    if decision.previous_price != 0:

        price_ratio = (
            candidate_price
            / decision.previous_price
        )

    else:

        price_ratio = 1.0

    if decision.historical_avg_price != 0:

        price_vs_historical_avg = (
            candidate_price
            / decision.historical_avg_price
        )

    else:

        price_vs_historical_avg = 1.0

    return pd.DataFrame(
        [
            {
                "StockCode": decision.sku,

                "price": candidate_price,

                "log_price": np.log1p(
                    candidate_price
                ),

                "price_change":
                    price_change,

                "price_ratio":
                    price_ratio,

                "price_vs_historical_avg":
                    price_vs_historical_avg,

                "previous_units":
                    decision.previous_units,

                "previous_price":
                    decision.previous_price,

                "rolling_7d_units":
                    decision.rolling_7d_units,

                "rolling_30d_units":
                    decision.rolling_30d_units,

                "demand_trend":
                    decision.demand_trend,

                "demand_momentum":
                    decision.demand_momentum,

                "day_of_week":
                    decision.day_of_week,

                "month":
                    decision.month,

                "year":
                    decision.year,

                "is_weekend":
                    decision.is_weekend,
            }
        ]
    )



def predict_demand(
    decision: Decision,
    candidate_price: float,
):

    X = build_features(
        decision,
        candidate_price,
    )

    X_transformed = (
        PREPROCESSOR.transform(X)
    )

    predicted_log_demand = (
        MODEL.predict(
            X_transformed
        )[0]
    )

    predicted_demand = np.expm1(
        predicted_log_demand
    )

    return max(
        0.0,
        float(predicted_demand),
    )

def calculate_regret(
    decision: Decision,
):

    actual_price = float(
        decision.price
    )

    candidate_prices = (
        generate_candidate_prices(
            actual_price
        )
    )

    alternatives = []

    for price in candidate_prices:

        demand = predict_demand(
            decision,
            price,
        )

        revenue = (
            price * demand
        )

        alternatives.append(
            {
                "price": float(price),
                "predicted_demand": demand,
                "predicted_revenue": revenue,
            }
        )

    alternatives_df = pd.DataFrame(
        alternatives
    )

    # Best counterfactual decision
    best_idx = (
        alternatives_df[
            "predicted_revenue"
        ].idxmax()
    )

    best = (
        alternatives_df.loc[
            best_idx
        ]
    )

    # Prediction for actual decision
    actual_idx = (
        (
            alternatives_df["price"]
            - actual_price
        )
        .abs()
        .idxmin()
    )

    actual = (
        alternatives_df.loc[
            actual_idx
        ]
    )

    actual_revenue = float(
        actual["predicted_revenue"]
    )

    best_revenue = float(
        best["predicted_revenue"]
    )

    regret = max(
        0.0,
        best_revenue
        - actual_revenue,
    )

    if actual_revenue > 0:

        regret_percentage = (
            regret
            / actual_revenue
            * 100
        )

    else:

        regret_percentage = 0.0

    if regret_percentage < 5:

        decision_quality = "GOOD"

    elif regret_percentage < 15:

        decision_quality = "QUESTIONABLE"

    else:

        decision_quality = "HIGH_REGRET"

    return {

        "decision_id":
            decision.decision_id,

        "sku":
            decision.sku,

        "actual_price":
            actual_price,

        "best_price":
            float(best["price"]),

        "actual_predicted_demand":
            float(
                actual[
                    "predicted_demand"
                ]
            ),

        "best_predicted_demand":
            float(
                best[
                    "predicted_demand"
                ]
            ),

        "actual_predicted_revenue":
            actual_revenue,

        "best_predicted_revenue":
            best_revenue,

        "regret":
            float(regret),

        "regret_percentage":
            float(regret_percentage),

        "decision_quality":
            decision_quality,

        "currency":
            "INR",
    }



@app.post("/calculate-regret")
def calculate_regret_endpoint(
    decision: Decision,
):

    try:

        result = calculate_regret(
            decision
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "Guardian AI Regret Engine",
        "model_loaded": True,
    }