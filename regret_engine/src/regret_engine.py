import joblib
import numpy as np
import pandas as pd

from pathlib import Path



# Paths


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = (
    BASE_DIR
    / "data"
    / "synthetic_training_data.csv"
)

MODEL_FILE = (
    BASE_DIR
    / "models"
    / "reward_model.joblib"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "regret_results.csv"
)

# Configuration


N_PRICE_ALTERNATIVES = 5

MIN_PRICE_MULTIPLIER = 0.90
MAX_PRICE_MULTIPLIER = 1.10

BATCH_SIZE = 5000


MAX_ROWS = None


def load_model():

    print("Loading reward model...")

    pipeline = joblib.load(MODEL_FILE)

    preprocessor = pipeline["preprocessor"]
    model = pipeline["model"]
    features = pipeline["features"]
    target = pipeline["target"]
    target_transform = pipeline["target_transform"]

    print("Reward model loaded.")

    print(f"Target: {target}")
    print(f"Target transform: {target_transform}")
    print(f"Expected features: {len(features)}")

    return preprocessor, model, features



# Load data


def load_data():

    print("\nLoading training data...")

    read_kwargs = {
        "low_memory": False,
        "dtype": {
            "StockCode": str
        },
    }

    if MAX_ROWS is not None:
        read_kwargs["nrows"] = MAX_ROWS

    df = pd.read_csv(
        DATA_FILE,
        **read_kwargs,
    )

    df["date"] = pd.to_datetime(df["date"])

    print(
        f"Total observations: "
        f"{len(df):,}"
    )

    return df


# Generate candidate prices


def generate_candidate_multipliers():

    return np.linspace(
        MIN_PRICE_MULTIPLIER,
        MAX_PRICE_MULTIPLIER,
        N_PRICE_ALTERNATIVES,
    )



# Build batch counterfactual features


def build_batch_features(
    df,
    candidate_prices,
):

    n_rows = len(df)
    n_prices = len(candidate_prices)

    repeated = df.loc[
        df.index.repeat(n_prices)
    ].reset_index(drop=True)

    repeated["candidate_price"] = np.tile(
        candidate_prices,
        n_rows,
    )


    X = pd.DataFrame()

    X["StockCode"] = repeated[
        "StockCode"
    ].astype(str)

    X["price"] = repeated[
        "candidate_price"
    ]

    X["log_price"] = np.log1p(
        repeated["candidate_price"]
    )

    X["price_change"] = (
        repeated["candidate_price"]
        - repeated["previous_price"]
    )

    X["price_ratio"] = (
        repeated["candidate_price"]
        / repeated["previous_price"].replace(
            0,
            np.nan,
        )
    )

    X["price_vs_historical_avg"] = (
        repeated["candidate_price"]
        / repeated[
            "historical_avg_price"
        ].replace(
            0,
            np.nan,
        )
    )

    # Historical demand

    X["previous_units"] = repeated[
        "previous_units"
    ]

    X["previous_price"] = repeated[
        "previous_price"
    ]

    X["rolling_7d_units"] = repeated[
        "rolling_7d_units"
    ]

    X["rolling_30d_units"] = repeated[
        "rolling_30d_units"
    ]

    X["demand_trend"] = repeated[
        "demand_trend"
    ]

    X["demand_momentum"] = repeated[
        "demand_momentum"
    ]

    # Calendar

    X["day_of_week"] = repeated[
        "day_of_week"
    ]

    X["month"] = repeated[
        "month"
    ]

    X["year"] = repeated[
        "year"
    ]

    X["is_weekend"] = repeated[
        "is_weekend"
    ]

    X = X.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    X = X.fillna(0)

    return repeated, X


def process_batch(
    df_batch,
    preprocessor,
    model,
):

    multipliers = generate_candidate_multipliers()


    actual_prices = (
        df_batch["price"]
        .to_numpy(
            dtype=float
        )
    )

    candidate_matrix = (
        actual_prices[:, None]
        * multipliers[None, :]
    )

    candidate_matrix = np.concatenate(
        [
            candidate_matrix,
            actual_prices[:, None],
        ],
        axis=1,
    )


    candidate_matrix = np.round(
        candidate_matrix,
        2,
    )

    flat_prices = (
        candidate_matrix
        .reshape(-1)
    )

    n_rows = len(df_batch)
    n_candidates = candidate_matrix.shape[1]


    repeated = df_batch.loc[
        df_batch.index.repeat(
            n_candidates
        )
    ].reset_index(drop=True)

    repeated["candidate_price"] = (
        flat_prices
    )


    X = pd.DataFrame()

    X["StockCode"] = repeated[
        "StockCode"
    ].astype(str)

    X["price"] = repeated[
        "candidate_price"
    ]

    X["log_price"] = np.log1p(
        repeated["candidate_price"]
    )

    X["price_change"] = (
        repeated["candidate_price"]
        - repeated["previous_price"]
    )

    X["price_ratio"] = (
        repeated["candidate_price"]
        / repeated["previous_price"].replace(
            0,
            np.nan,
        )
    )

    X["price_vs_historical_avg"] = (
        repeated["candidate_price"]
        / repeated[
            "historical_avg_price"
        ].replace(
            0,
            np.nan,
        )
    )

    X["previous_units"] = repeated[
        "previous_units"
    ]

    X["previous_price"] = repeated[
        "previous_price"
    ]

    X["rolling_7d_units"] = repeated[
        "rolling_7d_units"
    ]

    X["rolling_30d_units"] = repeated[
        "rolling_30d_units"
    ]

    X["demand_trend"] = repeated[
        "demand_trend"
    ]

    X["demand_momentum"] = repeated[
        "demand_momentum"
    ]

    X["day_of_week"] = repeated[
        "day_of_week"
    ]

    X["month"] = repeated[
        "month"
    ]

    X["year"] = repeated[
        "year"
    ]

    X["is_weekend"] = repeated[
        "is_weekend"
    ]

    X = X.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    X = X.fillna(0)


    X_transformed = (
        preprocessor.transform(X)
    )

    predicted_log = model.predict(
        X_transformed
    )

    predicted_demand = np.expm1(
        predicted_log
    )

    predicted_demand = np.maximum(
        predicted_demand,
        0,
    )

  
    predicted_revenue = (
        flat_prices
        * predicted_demand
    )

    predicted_revenue = (
        predicted_revenue
        .reshape(
            n_rows,
            n_candidates,
        )
    )

    predicted_demand = (
        predicted_demand
        .reshape(
            n_rows,
            n_candidates,
        )
    )


    best_indices = (
        predicted_revenue
        .argmax(
            axis=1
        )
    )

    row_indices = np.arange(
        n_rows
    )

    best_prices = (
        candidate_matrix[
            row_indices,
            best_indices,
        ]
    )

    best_demands = (
        predicted_demand[
            row_indices,
            best_indices,
        ]
    )

    best_revenues = (
        predicted_revenue[
            row_indices,
            best_indices,
        ]
    )

   
    actual_predicted_demand = (
        predicted_demand[:, -1]
    )

    actual_predicted_revenue = (
        predicted_revenue[:, -1]
    )

    regret = (
        best_revenues
        - actual_predicted_revenue
    )

    regret = np.maximum(
        regret,
        0,
    )

    regret_percentage = np.where(
        actual_predicted_revenue > 0,
        regret
        / actual_predicted_revenue
        * 100,
        0,
    )

 

    decision_quality = np.where(
        regret_percentage < 5,
        "GOOD",
        np.where(
            regret_percentage < 15,
            "QUESTIONABLE",
            "HIGH_REGRET",
        ),
    )

    results = pd.DataFrame(
        {
            "date":
                df_batch["date"].to_numpy(),

            "StockCode":
                df_batch["StockCode"].to_numpy(),

            "actual_price":
                actual_prices,

            "actual_units_sold":
                df_batch[
                    "units_sold"
                ].to_numpy(),

            "actual_revenue":
                df_batch[
                    "revenue"
                ].to_numpy(),

            "actual_predicted_demand":
                actual_predicted_demand,

            "actual_predicted_revenue":
                actual_predicted_revenue,

            "best_price":
                best_prices,

            "best_predicted_demand":
                best_demands,

            "best_predicted_revenue":
                best_revenues,

            "regret":
                regret,

            "regret_percentage":
                regret_percentage,

            "decision_quality":
                decision_quality,
        }
    )

    return results


# ============================================================
# Run engine
# ============================================================

def run_regret_engine(
    df,
    preprocessor,
    model,
):

    print(
        "\nRunning Optimized Regret Engine..."
    )

    all_results = []

    total = len(df)

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        end = min(
            start + BATCH_SIZE,
            total,
        )

        df_batch = df.iloc[
            start:end
        ].copy()

        batch_results = process_batch(
            df_batch,
            preprocessor,
            model,
        )

        all_results.append(
            batch_results
        )

        print(
            f"Processed "
            f"{end:,} / "
            f"{total:,}"
        )

    return pd.concat(
        all_results,
        ignore_index=True,
    )



def save_results(results):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        "\nSaved regret results to:"
    )

    print(
        OUTPUT_FILE
    )



def print_summary(results):

    print(
        "\n"
        + "=" * 60
    )

    print(
        "REGRET ENGINE SUMMARY"
    )

    print(
        "=" * 60
    )

    print(
        f"Decisions analyzed: "
        f"{len(results):,}"
    )

    print(
        "\nDecision quality:"
    )

    print(
        results[
            "decision_quality"
        ].value_counts()
    )

    print(
        "\nRegret statistics:"
    )

    print(
        f"Average regret: "
        f"£{results['regret'].mean():.2f}"
    )

    print(
        f"Median regret: "
        f"£{results['regret'].median():.2f}"
    )

    print(
        f"Total estimated regret: "
        f"£{results['regret'].sum():,.2f}"
    )

    print(
        f"Average regret %: "
        f"{results['regret_percentage'].mean():.2f}%"
    )

    print(
        "\nTop 10 highest-regret decisions:"
    )

    columns = [
        "date",
        "StockCode",
        "actual_price",
        "best_price",
        "actual_revenue",
        "regret",
        "regret_percentage",
        "decision_quality",
    ]

    top = (
        results
        .nlargest(
            10,
            "regret",
        )[columns]
    )

    print(
        top.to_string(
            index=False
        )
    )


def main():

    preprocessor, model, features = (
        load_model()
    )

    df = load_data()

    expected_features = [
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

    if features != expected_features:

        raise ValueError(
            "Model feature configuration "
            "does not match regret engine."
        )

    print(
        "\nFeature compatibility check: PASSED"
    )

    results = run_regret_engine(
        df,
        preprocessor,
        model,
    )

    save_results(
        results
    )

    print_summary(
        results
    )

    print(
        "\nRegret Engine complete!"
    )


if __name__ == "__main__":
    main()