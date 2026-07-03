from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


def build_warehouse(frames: dict[str, pd.DataFrame], db_path: Path) -> dict[str, pd.DataFrame]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with duckdb.connect(str(db_path)) as con:
        for table_name, frame in frames.items():
            con.register(f"{table_name}_df", frame)
            con.execute(f"CREATE OR REPLACE TABLE raw_{table_name} AS SELECT * FROM {table_name}_df")

        con.execute(
            """
            CREATE OR REPLACE TABLE fact_order_items AS
            SELECT
                o.order_id,
                o.customer_id,
                c.country,
                c.segment,
                CAST(o.order_date AS DATE) AS order_date,
                o.status,
                i.product_id,
                i.description,
                CAST(i.quantity AS INTEGER) AS quantity,
                CAST(i.unit_price AS DOUBLE) AS unit_price,
                CAST(i.quantity AS DOUBLE) * CAST(i.unit_price AS DOUBLE) AS gross_revenue,
                CASE WHEN o.status = 'canceled' THEN 0 ELSE 1 END AS is_revenue_order
            FROM raw_orders o
            JOIN raw_customers c ON c.customer_id = o.customer_id
            JOIN raw_order_items i ON i.order_id = o.order_id
            """
        )

        daily_revenue = con.execute(
            """
            SELECT
                order_date,
                COUNT(DISTINCT order_id) AS orders,
                ROUND(SUM(gross_revenue * is_revenue_order), 2) AS gross_revenue,
                ROUND(SUM(gross_revenue * is_revenue_order) / NULLIF(COUNT(DISTINCT order_id), 0), 2)
                    AS avg_order_value
            FROM fact_order_items
            GROUP BY order_date
            ORDER BY order_date
            """
        ).df()

        customer_revenue = con.execute(
            """
            SELECT
                customer_id,
                country,
                segment,
                COUNT(DISTINCT order_id) AS orders,
                ROUND(SUM(gross_revenue * is_revenue_order), 2) AS gross_revenue,
                MAX(order_date) AS last_order_date
            FROM fact_order_items
            GROUP BY customer_id, country, segment
            ORDER BY gross_revenue DESC, customer_id
            """
        ).df()

        product_revenue = con.execute(
            """
            SELECT
                product_id,
                description,
                SUM(quantity) AS units_sold,
                ROUND(SUM(gross_revenue * is_revenue_order), 2) AS gross_revenue
            FROM fact_order_items
            GROUP BY product_id, description
            ORDER BY gross_revenue DESC, product_id
            LIMIT 25
            """
        ).df()

        country_revenue = con.execute(
            """
            SELECT
                country,
                segment,
                COUNT(DISTINCT customer_id) AS customers,
                COUNT(DISTINCT order_id) AS orders,
                ROUND(SUM(gross_revenue * is_revenue_order), 2) AS gross_revenue
            FROM fact_order_items
            GROUP BY country, segment
            ORDER BY gross_revenue DESC, country
            """
        ).df()

    return {
        "daily_revenue": daily_revenue,
        "customer_revenue": customer_revenue,
        "product_revenue": product_revenue,
        "country_revenue": country_revenue,
    }
