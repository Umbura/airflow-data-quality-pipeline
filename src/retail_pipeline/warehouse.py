from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import duckdb
import pandas as pd


def build_warehouse(frames: dict[str, pd.DataFrame], db_path: Path) -> dict[str, pd.DataFrame]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = db_path.with_name(f".{db_path.name}.{uuid4().hex}.tmp")

    try:
        with duckdb.connect(str(temporary_path)) as con:
            con.register("customers_df", frames["customers"])
            con.register("orders_df", frames["orders"])
            con.register("order_items_df", frames["order_items"])
            con.execute("CREATE OR REPLACE TABLE raw_customers AS SELECT * FROM customers_df")
            con.execute("CREATE OR REPLACE TABLE raw_orders AS SELECT * FROM orders_df")
            con.execute("CREATE OR REPLACE TABLE raw_order_items AS SELECT * FROM order_items_df")

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
                    CAST(i.quantity AS DOUBLE) * CAST(i.unit_price AS DOUBLE) AS line_value,
                    CASE WHEN o.status = 'paid' THEN 1 ELSE 0 END AS is_revenue_order
                FROM raw_orders o
                JOIN raw_customers c ON c.customer_id = o.customer_id
                JOIN raw_order_items i ON i.order_id = o.order_id
                """
            )

            daily_revenue = con.execute(
                """
                SELECT
                    order_date,
                    COUNT(DISTINCT order_id) AS total_orders,
                    COUNT(DISTINCT CASE WHEN status = 'paid' THEN order_id END) AS paid_orders,
                    COUNT(DISTINCT CASE WHEN status = 'canceled' THEN order_id END) AS canceled_orders,
                    ROUND(SUM(line_value * is_revenue_order), 2) AS gross_revenue,
                    ROUND(
                        SUM(line_value * is_revenue_order)
                        / NULLIF(COUNT(DISTINCT CASE WHEN status = 'paid' THEN order_id END), 0),
                        2
                    ) AS avg_order_value
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
                    COUNT(DISTINCT order_id) AS total_orders,
                    COUNT(DISTINCT CASE WHEN status = 'paid' THEN order_id END) AS paid_orders,
                    COUNT(DISTINCT CASE WHEN status = 'canceled' THEN order_id END) AS canceled_orders,
                    ROUND(SUM(line_value * is_revenue_order), 2) AS gross_revenue,
                    MAX(CASE WHEN status = 'paid' THEN order_date END) AS last_paid_order_date
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
                    CAST(SUM(quantity * is_revenue_order) AS BIGINT) AS units_sold,
                    CAST(SUM(quantity * (1 - is_revenue_order)) AS BIGINT) AS units_canceled,
                    ROUND(SUM(line_value * is_revenue_order), 2) AS gross_revenue
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
                    COUNT(DISTINCT order_id) AS total_orders,
                    COUNT(DISTINCT CASE WHEN status = 'paid' THEN order_id END) AS paid_orders,
                    COUNT(DISTINCT CASE WHEN status = 'canceled' THEN order_id END) AS canceled_orders,
                    ROUND(SUM(line_value * is_revenue_order), 2) AS gross_revenue
                FROM fact_order_items
                GROUP BY country, segment
                ORDER BY gross_revenue DESC, country
                """
            ).df()

        temporary_path.replace(db_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "daily_revenue": daily_revenue,
        "customer_revenue": customer_revenue,
        "product_revenue": product_revenue,
        "country_revenue": country_revenue,
    }
