from __future__ import annotations

import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder

from regret_engine.src.schemas import (
    Decision,
    DecisionFactor,
    DecisionRecord,
    PriceAlternative,
    RegretResult,
    RiskLevel,
)


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILE = BASE_DIR / "models" / "reward_model.joblib"
DATA_FILE = BASE_DIR / "data" / "synthetic_training_data.csv"
N_PRICE_ALTERNATIVES = 5
MIN_PRICE_MULTIPLIER = 0.90
MAX_PRICE_MULTIPLIER = 1.10


class RegretService:
    """Wraps existing model logic with traceable, dashboard-ready records."""

    def __init__(self, model_file: Path = MODEL_FILE):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipeline = joblib.load(model_file)
            self.model_source = "joblib_artifact"
        except Exception:
            pipeline = self._train_fallback_pipeline()
            self.model_source = "csv_fallback"
        self.preprocessor = pipeline["preprocessor"]
        self.model = pipeline["model"]

    def _train_fallback_pipeline(self) -> dict[str, object]:
        df = pd.read_csv(DATA_FILE, low_memory=False, dtype={"StockCode": str})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").head(12000).reset_index(drop=True)

        features = [
            "StockCode",
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
        x_train = (
            df[features]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        y_train = np.log1p(df["units_sold"].astype(float))

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "sku",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["StockCode"],
                ),
            ],
            remainder="passthrough",
        )
        model = HistGradientBoostingRegressor(
            max_iter=80,
            learning_rate=0.08,
            max_leaf_nodes=15,
            min_samples_leaf=40,
            l2_regularization=2.0,
            random_state=42,
        )
        transformed = preprocessor.fit_transform(x_train)
        model.fit(transformed, y_train)
        return {
            "preprocessor": preprocessor,
            "model": model,
            "features": features,
            "target": "units_sold",
            "target_transform": "log1p",
        }

    def generate_candidate_prices(self, actual_price: float) -> np.ndarray:
        multipliers = np.linspace(
            MIN_PRICE_MULTIPLIER,
            MAX_PRICE_MULTIPLIER,
            N_PRICE_ALTERNATIVES,
        )
        candidates = np.append(actual_price * multipliers, actual_price)
        candidates = np.round(candidates, 2)
        candidates = np.unique(candidates)
        return candidates[candidates > 0]

    def build_features(
        self,
        decision: Decision,
        candidate_price: float,
    ) -> pd.DataFrame:
        price_change = candidate_price - decision.previous_price
        price_ratio = (
            candidate_price / decision.previous_price
            if decision.previous_price
            else 1.0
        )
        price_vs_historical_avg = (
            candidate_price / decision.historical_avg_price
            if decision.historical_avg_price
            else 1.0
        )

        return pd.DataFrame(
            [
                {
                    "StockCode": decision.sku,
                    "price": candidate_price,
                    "log_price": np.log1p(candidate_price),
                    "price_change": price_change,
                    "price_ratio": price_ratio,
                    "price_vs_historical_avg": price_vs_historical_avg,
                    "previous_units": decision.previous_units,
                    "previous_price": decision.previous_price,
                    "rolling_7d_units": decision.rolling_7d_units,
                    "rolling_30d_units": decision.rolling_30d_units,
                    "demand_trend": decision.demand_trend,
                    "demand_momentum": decision.demand_momentum,
                    "day_of_week": decision.day_of_week,
                    "month": decision.month,
                    "year": decision.year,
                    "is_weekend": decision.is_weekend,
                }
            ]
        )

    def predict_demand(
        self,
        decision: Decision,
        candidate_price: float,
    ) -> float:
        features = self.build_features(decision, candidate_price)
        transformed = self.preprocessor.transform(features)
        predicted_log_demand = self.model.predict(transformed)[0]
        predicted_demand = np.expm1(predicted_log_demand)
        return max(0.0, float(predicted_demand))

    def score(self, decision: Decision) -> RegretResult:
        actual_price = float(decision.price)
        candidate_prices = self.generate_candidate_prices(actual_price)
        alternatives: list[PriceAlternative] = []

        for price in candidate_prices:
            demand = self.predict_demand(decision, float(price))
            alternatives.append(
                PriceAlternative(
                    price=float(price),
                    predicted_demand=demand,
                    predicted_revenue=float(price) * demand,
                    is_selected=bool(np.isclose(float(price), actual_price)),
                )
            )

        best_index = max(
            range(len(alternatives)),
            key=lambda idx: alternatives[idx].predicted_revenue,
        )
        actual_index = min(
            range(len(alternatives)),
            key=lambda idx: abs(alternatives[idx].price - actual_price),
        )
        alternatives[best_index].is_best = True
        alternatives[actual_index].is_selected = True

        best = alternatives[best_index]
        actual = alternatives[actual_index]
        regret = max(
            0.0,
            best.predicted_revenue - actual.predicted_revenue,
        )
        regret_percentage = (
            regret / actual.predicted_revenue * 100
            if actual.predicted_revenue > 0
            else 0.0
        )

        if regret_percentage < 5:
            decision_quality = "GOOD"
        elif regret_percentage < 15:
            decision_quality = "QUESTIONABLE"
        else:
            decision_quality = "HIGH_REGRET"

        return RegretResult(
            decision_id=decision.decision_id,
            sku=decision.sku,
            actual_price=actual_price,
            best_price=best.price,
            actual_predicted_demand=actual.predicted_demand,
            best_predicted_demand=best.predicted_demand,
            actual_predicted_revenue=actual.predicted_revenue,
            best_predicted_revenue=best.predicted_revenue,
            regret=float(regret),
            regret_percentage=float(regret_percentage),
            decision_quality=decision_quality,
            alternatives=alternatives,
        )

    def build_record(self, decision: Decision) -> DecisionRecord:
        result = self.score(decision)
        risk_level = self._risk_level(result)
        confidence = self._confidence(decision, result)
        factors = self._factors(decision, result)
        recommendation = self._recommendation(result)

        assumptions = [
            "Reward is modeled as predicted revenue in INR from price times predicted units sold.",
            "Counterfactual prices are evaluated within plus or minus 10 percent of submitted price.",
            "Historical patterns come from the synthetic training data included in this repository.",
        ]
        uncertainties = self._uncertainties(decision, result)

        return DecisionRecord(
            decision_id=decision.decision_id,
            timestamp=decision.timestamp,
            sku=decision.sku,
            price=decision.price,
            recommendation=recommendation,
            regret_score=result.regret,
            regret_percentage=result.regret_percentage,
            risk_level=risk_level,
            confidence=confidence,
            input=decision,
            regret=result,
            factors=factors,
            assumptions=assumptions,
            uncertainties=uncertainties,
        )

    def legacy_result(self, decision: Decision) -> dict[str, float | str]:
        result = self.score(decision)
        return {
            "decision_id": result.decision_id,
            "sku": result.sku,
            "actual_price": result.actual_price,
            "best_price": result.best_price,
            "actual_predicted_demand": result.actual_predicted_demand,
            "best_predicted_demand": result.best_predicted_demand,
            "actual_predicted_revenue": result.actual_predicted_revenue,
            "best_predicted_revenue": result.best_predicted_revenue,
            "regret": result.regret,
            "regret_percentage": result.regret_percentage,
            "decision_quality": result.decision_quality,
            "currency": result.currency,
        }

    def _risk_level(self, result: RegretResult) -> RiskLevel:
        if result.decision_quality == "HIGH_REGRET":
            return "HIGH"
        if result.decision_quality == "QUESTIONABLE":
            return "MEDIUM"
        return "LOW"

    def _confidence(self, decision: Decision, result: RegretResult) -> float:
        trend_penalty = min(abs(decision.demand_momentum) * 0.04, 0.12)
        price_gap = (
            abs(decision.price / decision.historical_avg_price - 1.0)
            if decision.historical_avg_price
            else 0.30
        )
        price_penalty = min(price_gap * 0.25, 0.18)
        regret_penalty = min(result.regret_percentage / 100 * 0.30, 0.20)
        support_bonus = 0.06 if decision.rolling_30d_units > 0 else 0.0
        confidence = 0.78 + support_bonus - trend_penalty - price_penalty - regret_penalty
        return round(float(np.clip(confidence, 0.35, 0.92)), 3)

    def _recommendation(self, result: RegretResult) -> str:
        if result.decision_quality == "GOOD":
            return "Accept submitted price"
        direction = "lower" if result.best_price < result.actual_price else "raise"
        return f"Review price and consider {direction} counterfactual price {result.best_price:.2f} INR"

    def _factors(
        self,
        decision: Decision,
        result: RegretResult,
    ) -> list[DecisionFactor]:
        factors: list[DecisionFactor] = []
        price_gap = (
            decision.price / decision.historical_avg_price - 1.0
            if decision.historical_avg_price
            else 0.0
        )
        factors.append(
            DecisionFactor(
                factor="Price versus historical average",
                impact="negative" if abs(price_gap) > 0.08 else "neutral",
                magnitude=round(min(abs(price_gap), 1.0), 3),
                evidence=(
                    f"Submitted price {decision.price:.2f} INR is "
                    f"{price_gap * 100:.1f}% from historical average "
                    f"{decision.historical_avg_price:.2f} INR."
                ),
            )
        )
        factors.append(
            DecisionFactor(
                factor="Counterfactual revenue gap",
                impact="negative" if result.regret > 0 else "positive",
                magnitude=round(min(result.regret_percentage / 100, 1.0), 3),
                evidence=(
                    f"Best predicted revenue is {result.best_predicted_revenue:.2f} INR "
                    f"versus selected predicted revenue {result.actual_predicted_revenue:.2f} INR."
                ),
            )
        )
        demand_delta = decision.rolling_7d_units - decision.rolling_30d_units
        factors.append(
            DecisionFactor(
                factor="Recent demand movement",
                impact="positive" if demand_delta >= 0 else "negative",
                magnitude=round(
                    min(abs(demand_delta) / max(decision.rolling_30d_units, 1.0), 1.0),
                    3,
                ),
                evidence=(
                    f"Rolling 7-day units {decision.rolling_7d_units:.2f} "
                    f"compared with rolling 30-day units {decision.rolling_30d_units:.2f}."
                ),
            )
        )
        factors.append(
            DecisionFactor(
                factor="Model confidence modifiers",
                impact="negative" if decision.demand_momentum < -0.2 else "neutral",
                magnitude=round(min(abs(decision.demand_momentum), 1.0), 3),
                evidence=(
                    f"Demand momentum is {decision.demand_momentum:.3f}; "
                    f"weekend flag is {decision.is_weekend}."
                ),
            )
        )
        return sorted(factors, key=lambda factor: factor.magnitude, reverse=True)

    def _uncertainties(
        self,
        decision: Decision,
        result: RegretResult,
    ) -> list[str]:
        uncertainties = [
            "The model estimates demand from historical synthetic examples, not live market observations.",
        ]
        if decision.competitor_price is None:
            uncertainties.append("Competitor price was not supplied for this decision.")
        if decision.inventory is None:
            uncertainties.append("Inventory was not supplied for this decision.")
        if result.regret_percentage >= 15:
            uncertainties.append("High regret decisions should be reviewed before automated approval.")
        return uncertainties


def decision_from_training_row(row: pd.Series, index: int) -> Decision:
    return Decision(
        decision_id=f"demo-{index:03d}-{row['StockCode']}",
        timestamp=pd.Timestamp(row["date"]).isoformat(),
        sku=str(row["StockCode"]),
        price=float(row["price"]),
        previous_units=float(row["previous_units"]),
        previous_price=float(row["previous_price"]),
        rolling_7d_units=float(row["rolling_7d_units"]),
        rolling_30d_units=float(row["rolling_30d_units"]),
        demand_trend=float(row["demand_trend"]),
        demand_momentum=float(row["demand_momentum"]),
        day_of_week=int(row["day_of_week"]),
        month=int(row["month"]),
        year=int(row["year"]),
        is_weekend=int(row["is_weekend"]),
        historical_avg_price=float(row["historical_avg_price"]),
    )


def load_demo_decisions(limit: int = 30, data_file: Path = DATA_FILE) -> list[Decision]:
    df = pd.read_csv(data_file, low_memory=False, dtype={"StockCode": str})
    df["date"] = pd.to_datetime(df["date"])
    sampled = (
        df.sort_values(["date", "StockCode"])
        .iloc[:: max(len(df) // max(limit * 4, 1), 1)]
        .head(limit)
        .reset_index(drop=True)
    )
    return [decision_from_training_row(row, index) for index, row in sampled.iterrows()]
