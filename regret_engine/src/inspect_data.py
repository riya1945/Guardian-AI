import pandas as pd
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "training_data.csv"
)


def main():

    print("Loading prepared dataset...")

    df = pd.read_csv(
        DATA_FILE,
        low_memory=False,
        dtype={"StockCode": str},
    )

    print("\n" + "=" * 60)
    print("DATASET SHAPE")
    print("=" * 60)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\n" + "=" * 60)
    print("COLUMNS")
    print("=" * 60)

    print(df.columns.tolist())

    print("\n" + "=" * 60)
    print("FIRST 5 ROWS")
    print("=" * 60)

    print(df.head().to_string())

    print("\n" + "=" * 60)
    print("MISSING VALUES")
    print("=" * 60)

    print(df.isna().sum())

    print("\n" + "=" * 60)
    print("NUMERIC SUMMARY")
    print("=" * 60)

    numeric_columns = [
        "price",
        "units_sold",
        "revenue",
        "transaction_count",
        "previous_units",
        "previous_price",
        "rolling_7d_units",
        "rolling_30d_units",
        "historical_avg_price",
        "price_change",
        "price_vs_historical_avg",
    ]

    print(
        df[numeric_columns]
        .describe()
        .round(2)
    )

    print("\n" + "=" * 60)
    print("UNIQUE SKUs")
    print("=" * 60)

    print(
        f"Unique SKUs: "
        f"{df['StockCode'].nunique():,}"
    )

    print("\n" + "=" * 60)
    print("OBSERVATIONS PER SKU")
    print("=" * 60)

    sku_counts = (
        df.groupby("StockCode")
        .size()
    )

    print(
        sku_counts
        .describe()
        .round(2)
    )

    print("\nTop 10 SKUs by observations:")

    print(
        sku_counts
        .sort_values(ascending=False)
        .head(10)
    )

    print("\n" + "=" * 60)
    print("PRICE VARIATION")
    print("=" * 60)

    price_stats = (
        df.groupby("StockCode")["price"]
        .agg(
            observations="size",
            unique_prices="nunique",
            min_price="min",
            max_price="max",
            median_price="median",
        )
    )

    print(
        price_stats
        .sort_values(
            "observations",
            ascending=False,
        )
        .head(20)
        .to_string()
    )

    print("\n" + "=" * 60)
    print("PRICE VARIATION COUNTS")
    print("=" * 60)

    print(
        "SKUs with >= 3 prices:",
        (
            price_stats["unique_prices"] >= 3
        ).sum(),
    )

    print(
        "SKUs with >= 5 prices:",
        (
            price_stats["unique_prices"] >= 5
        ).sum(),
    )

    print(
        "SKUs with >= 10 prices:",
        (
            price_stats["unique_prices"] >= 10
        ).sum(),
    )

    print("\n" + "=" * 60)
    print("EXTREME PRICES")
    print("=" * 60)

    print(
        df.nlargest(
            15,
            "price",
        )[
            [
                "StockCode",
                "date",
                "price",
                "units_sold",
                "revenue",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()