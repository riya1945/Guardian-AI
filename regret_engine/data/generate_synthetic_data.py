import numpy as np
import pandas as pd

from pathlib import Path


# ============================================================
# Configuration
# ============================================================

SEED = 42

N_SKUS = 400
OBSERVATIONS_PER_SKU = 150

TOTAL_ROWS = N_SKUS * OBSERVATIONS_PER_SKU

START_DATE = "2009-12-02"

OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "synthetic_training_data.csv"
)

rng = np.random.default_rng(SEED)


# ============================================================
# Generate SKU characteristics
# ============================================================

def generate_sku_profiles():

    profiles = []

    for i in range(N_SKUS):

        stock_code = f"SYN{i:04d}"

        # Base price of the product.
        base_price = rng.uniform(
            0.50,
            25.0,
        )

        # Base daily demand.
        base_demand = rng.lognormal(
            mean=2.0,
            sigma=0.8,
        )

        # Price elasticity.
        #
        # More negative = demand decreases more
        # when price increases.
        elasticity = rng.uniform(
            -2.0,
            -0.3,
        )

        # Product-specific demand volatility.
        volatility = rng.uniform(
            0.05,
            0.30,
        )

        # Seasonal sensitivity.
        seasonality = rng.uniform(
            0.05,
            0.30,
        )

        profiles.append(
            {
                "StockCode": stock_code,
                "base_price": base_price,
                "base_demand": base_demand,
                "elasticity": elasticity,
                "volatility": volatility,
                "seasonality": seasonality,
            }
        )

    return pd.DataFrame(profiles)


# ============================================================
# Generate observations
# ============================================================

def generate_data():

    print("=" * 60)
    print("GENERATING SYNTHETIC GUARDIAN AI DATASET")
    print("=" * 60)

    profiles = generate_sku_profiles()

    start_date = pd.Timestamp(
        START_DATE
    )

    all_rows = []

    for _, sku in profiles.iterrows():

        previous_units = None
        previous_price = None

        historical_prices = []

        historical_demands = []

        for t in range(
            OBSERVATIONS_PER_SKU
        ):

            date = (
                start_date
                + pd.Timedelta(
                    days=t
                )
            )

            # ------------------------------------------------
            # Calendar effects
            # ------------------------------------------------

            day_of_week = (
                date.dayofweek
            )

            month = date.month

            year = date.year

            is_weekend = int(
                day_of_week >= 5
            )

            # Weekend effect.
            weekend_factor = (
                0.80
                if is_weekend
                else 1.0
            )

            # Seasonal effect.
            seasonal_factor = (
                1
                + sku["seasonality"]
                * np.sin(
                    2
                    * np.pi
                    * t
                    / 365
                )
            )

            # ------------------------------------------------
            # Generate actual price
            # ------------------------------------------------

            if previous_price is None:

                price = sku[
                    "base_price"
                ]

            else:

                # Most price changes are small.
                change = rng.choice(
                    [
                        -0.15,
                        -0.10,
                        -0.05,
                        0.0,
                        0.0,
                        0.0,
                        0.05,
                        0.10,
                        0.15,
                    ]
                )

                price = (
                    previous_price
                    * (1 + change)
                )

                # Keep prices reasonable.
                price = np.clip(
                    price,
                    sku["base_price"] * 0.70,
                    sku["base_price"] * 1.30,
                )

            price = round(
                float(price),
                2,
            )

            # ------------------------------------------------
            # Demand response to price
            # ------------------------------------------------

            price_ratio = (
                price
                / sku["base_price"]
            )

            price_effect = (
                price_ratio
                ** sku["elasticity"]
            )

            expected_demand = (
                sku["base_demand"]
                * price_effect
                * weekend_factor
                * seasonal_factor
            )

            # ------------------------------------------------
            # Add demand trend
            # ------------------------------------------------

            if len(
                historical_demands
            ) > 0:

                recent_mean = np.mean(
                    historical_demands[
                        -7:
                    ]
                )

                trend_factor = (
                    0.85
                    + 0.15
                    * (
                        recent_mean
                        / max(
                            sku[
                                "base_demand"
                            ],
                            1,
                        )
                    )
                )

                expected_demand *= (
                    np.clip(
                        trend_factor,
                        0.70,
                        1.30,
                    )
                )

            # ------------------------------------------------
            # Random demand noise
            # ------------------------------------------------

            noise = rng.normal(
                1.0,
                sku["volatility"],
            )

            noise = max(
                noise,
                0.20,
            )

            expected_demand *= noise

            # ------------------------------------------------
            # Actual observed demand
            # ------------------------------------------------

            units_sold = max(
                1,
                int(
                    rng.poisson(
                        max(
                            expected_demand,
                            0.1,
                        )
                    )
                ),
            )

            revenue = (
                price
                * units_sold
            )

            # ------------------------------------------------
            # Historical features
            # ------------------------------------------------

            if previous_units is None:

                previous_units_value = (
                    units_sold
                )

            else:

                previous_units_value = (
                    previous_units
                )

            if previous_price is None:

                previous_price_value = (
                    price
                )

            else:

                previous_price_value = (
                    previous_price
                )

            if len(
                historical_demands
            ) > 0:

                rolling_7d = np.mean(
                    historical_demands[
                        -7:
                    ]
                )

                rolling_30d = np.mean(
                    historical_demands[
                        -30:
                    ]
                )

            else:

                rolling_7d = units_sold
                rolling_30d = units_sold

            if len(
                historical_prices
            ) > 0:

                historical_avg_price = (
                    np.mean(
                        historical_prices
                    )
                )

            else:

                historical_avg_price = (
                    price
                )

            # ------------------------------------------------
            # Derived features
            # ------------------------------------------------

            price_change = (
                price
                - previous_price_value
            )

            price_ratio_current = (
                price
                / max(
                    previous_price_value,
                    0.01,
                )
            )

            price_vs_historical_avg = (
                price
                / max(
                    historical_avg_price,
                    0.01,
                )
            )

            log_price = np.log1p(
                price
            )

            demand_trend = (
                rolling_7d
                / max(
                    rolling_30d,
                    0.01,
                )
            )

            demand_momentum = (
                rolling_7d
                - rolling_30d
            )

            # ------------------------------------------------
            # Store observation
            # ------------------------------------------------

            all_rows.append(
                {
                    "date": date,
                    "StockCode": sku[
                        "StockCode"
                    ],

                    "price": price,

                    "units_sold":
                        units_sold,

                    "revenue":
                        revenue,

                    "transaction_count":
                        rng.integers(
                            1,
                            5,
                        ),

                    "previous_units":
                        previous_units_value,

                    "previous_price":
                        previous_price_value,

                    "rolling_7d_units":
                        rolling_7d,

                    "rolling_30d_units":
                        rolling_30d,

                    "historical_avg_price":
                        historical_avg_price,

                    "price_change":
                        price_change,

                    "price_ratio":
                        price_ratio_current,

                    "price_vs_historical_avg":
                        price_vs_historical_avg,

                    "log_price":
                        log_price,

                    "demand_trend":
                        demand_trend,

                    "demand_momentum":
                        demand_momentum,

                    "day_of_week":
                        day_of_week,

                    "month":
                        month,

                    "year":
                        year,

                    "is_weekend":
                        is_weekend,
                }
            )

            previous_units = (
                units_sold
            )

            previous_price = (
                price
            )

            historical_demands.append(
                units_sold
            )

            historical_prices.append(
                price
            )

    df = pd.DataFrame(
        all_rows
    )

    return df


# ============================================================
# Validate dataset
# ============================================================

def validate_dataset(df):

    print(
        "\n"
        + "=" * 60
    )

    print(
        "DATASET VALIDATION"
    )

    print(
        "=" * 60
    )

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print(
        f"SKUs: "
        f"{df['StockCode'].nunique():,}"
    )

    print(
        f"Date range: "
        f"{df['date'].min().date()} "
        f"→ "
        f"{df['date'].max().date()}"
    )

    print(
        "\nMissing values:"
    )

    print(
        df.isna()
        .sum()
        .sum()
    )

    print(
        "\nPrice statistics:"
    )

    print(
        df["price"].describe()
    )

    print(
        "\nDemand statistics:"
    )

    print(
        df["units_sold"].describe()
    )

    print(
        "\nPrice variation:"
    )

    price_variation = (
        df.groupby(
            "StockCode"
        )["price"]
        .nunique()
    )

    print(
        price_variation.describe()
    )

    print(
        "\nDataset looks ready."
    )


# ============================================================
# Save
# ============================================================

def save_dataset(df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        "\nSaved synthetic dataset:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# Main
# ============================================================

def main():

    df = generate_data()

    validate_dataset(
        df
    )

    save_dataset(
        df
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "SYNTHETIC DATA GENERATION COMPLETE!"
    )

    print(
        f"Generated {len(df):,} observations."
    )


if __name__ == "__main__":
    main()