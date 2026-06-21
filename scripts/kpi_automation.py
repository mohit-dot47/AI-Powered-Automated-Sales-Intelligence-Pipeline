"""
KPI Automation Pipeline
=======================
Executes advanced business intelligence SQL queries against the
sales analytics database and exports each KPI result set as CSV.

Database : ai_sales_analytics
Table    : sales_orders
"""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ──────────────────────────────────────────────
# Environment Config
# ──────────────────────────────────────────────

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_PATH = BASE_DIR / "Data" / "Processed"
LOG_PATH = BASE_DIR / "Data" / "Logs"

DB_CONFIG = {
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root123"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_NAME", "ai_sales_analytics"),
}

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"kpi_pipeline_{time.strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("KPIPipeline")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger(LOG_PATH)

# ──────────────────────────────────────────────
# KPI QUERIES
# ──────────────────────────────────────────────

KPI_QUERIES = {

    "executive_summary": """
        SELECT
            COUNT(DISTINCT order_id) AS total_orders,
            SUM(qty) AS total_units_sold,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(AVG(amount), 2) AS avg_order_value,
            COUNT(DISTINCT shipstate) AS active_states,
            COUNT(DISTINCT shipcity) AS active_cities,
            COUNT(DISTINCT category) AS product_categories,
            COUNT(DISTINCT sku) AS unique_products
        FROM sales_orders;
    """,

    "monthly_revenue": """
        SELECT
            DATE_FORMAT(date, '%Y-%m') AS order_month,
            ROUND(SUM(amount), 2) AS monthly_revenue
        FROM sales_orders
        GROUP BY DATE_FORMAT(date, '%Y-%m')
        ORDER BY order_month ASC;
    """,

    "category_performance": """
        SELECT
            category,
            COUNT(DISTINCT order_id) AS total_orders,
            SUM(qty) AS units_sold,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(
                SUM(amount) * 100.0 /
                SUM(SUM(amount)) OVER (),
                2
            ) AS revenue_share_pct
        FROM sales_orders
        GROUP BY category
        ORDER BY total_revenue DESC;
    """,

    "top_products": """
        SELECT
            sku,
            SUM(qty) AS units_sold,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(
                SUM(amount) / NULLIF(SUM(qty), 0),
                2
            ) AS avg_unit_price
        FROM sales_orders
        GROUP BY sku
        ORDER BY total_revenue DESC
        LIMIT 10;
    """,

    "state_performance": """
        SELECT
            shipstate AS state,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(AVG(amount), 2) AS avg_order_value,
            ROUND(
                SUM(amount) * 100.0 /
                SUM(SUM(amount)) OVER (),
                2
            ) AS revenue_share_pct
        FROM sales_orders
        GROUP BY shipstate
        ORDER BY total_revenue DESC;
    """,

    "customer_segments": """
        SELECT
            CASE
                WHEN b2b = 1 THEN 'B2B (Business)'
                ELSE 'B2C (Consumer)'
            END AS customer_segment,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(AVG(amount), 2) AS avg_order_value,
            ROUND(
                SUM(amount) * 100.0 /
                SUM(SUM(amount)) OVER (),
                2
            ) AS revenue_share_pct
        FROM sales_orders
        GROUP BY b2b
        ORDER BY total_revenue DESC;
    """
}

# ──────────────────────────────────────────────
# ADDITIONAL KPI EXPORTS
# ──────────────────────────────────────────────

KPI_QUERIES.update({

    "cancellation_analysis": """
        SELECT
            status,
            COUNT(*) AS total_orders,
            ROUND(SUM(amount), 2) AS revenue,
            ROUND(
                COUNT(*) * 100.0 /
                SUM(COUNT(*)) OVER (),
                2
            ) AS order_share_pct
        FROM sales_orders
        GROUP BY status
        ORDER BY total_orders DESC;
    """,

    "top_cities": """
        SELECT
            shipcity AS city,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue
        FROM sales_orders
        GROUP BY shipcity
        ORDER BY total_revenue DESC
        LIMIT 10;
    """,

    "courier_performance": """
        SELECT
            courier_status,
            COUNT(*) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue
        FROM sales_orders
        GROUP BY courier_status
        ORDER BY total_orders DESC;
    """,

    "fulfillment_performance": """
        SELECT
            fulfilment AS fulfillment_channel,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(AVG(amount), 2) AS avg_order_value
        FROM sales_orders
        GROUP BY fulfilment
        ORDER BY total_orders DESC;
    """,

    "sales_channel_performance": """
        SELECT
            sales_channel,
            COUNT(DISTINCT order_id) AS total_orders,
            ROUND(SUM(amount), 2) AS total_revenue,
            ROUND(AVG(amount), 2) AS avg_order_value
        FROM sales_orders
        GROUP BY sales_channel
        ORDER BY total_revenue DESC;
    """
})

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class ExportResult:
    name: str
    rows: int = 0
    output_path: str = ""
    elapsed_sec: float = 0.0
    success: bool = False
    error: str = ""

# ──────────────────────────────────────────────
# DATABASE ENGINE
# ──────────────────────────────────────────────

def build_engine(cfg: dict) -> Engine:
    db_url = (
        f"mysql+mysqlconnector://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    )
    return create_engine(db_url, pool_pre_ping=True)

# ──────────────────────────────────────────────
# EXPORT FUNCTION
# ──────────────────────────────────────────────

def export_kpi(name: str, sql: str, engine: Engine, output_dir: Path) -> ExportResult:
    result = ExportResult(name=name)
    start_time = time.perf_counter()

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)

        output_file = output_dir / f"{name}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")

        result.rows = len(df)
        result.output_path = str(output_file)
        result.success = True

        logger.info(
            "  %-25s %4d rows → %s",
            name,
            result.rows,
            output_file.name
        )

    except Exception as e:
        result.error = str(e)
        logger.exception("Failed exporting '%s': %s", name, e)

    finally:
        result.elapsed_sec = round(time.perf_counter() - start_time, 3)

    return result

# ──────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────

def print_summary(results: list[ExportResult], total_elapsed: float):
    divider = "─" * 70

    logger.info("\n%s", divider)
    logger.info("KPI PIPELINE EXPORT SUMMARY")
    logger.info("%s", divider)

    for result in results:
        status = "✓ OK" if result.success else "✗ FAIL"
        logger.info(
            "%-25s %-8s %-6s %.3fs",
            result.name,
            status,
            result.rows if result.success else "-",
            result.elapsed_sec
        )

    successful = sum(1 for r in results if r.success)

    logger.info("%s", divider)
    logger.info(
        "%d/%d exports successful | Total Time: %.2fs",
        successful,
        len(results),
        total_elapsed
    )
    logger.info("%s", divider)

# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────

def run_pipeline():
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

    logger.info("Starting KPI automation pipeline...")
    logger.info("Export path: %s", PROCESSED_PATH)

    engine = build_engine(DB_CONFIG)

    results = []
    pipeline_start = time.perf_counter()

    for name, sql in KPI_QUERIES.items():
        logger.info("Exporting '%s'...", name)
        results.append(
            export_kpi(
                name=name,
                sql=sql,
                engine=engine,
                output_dir=PROCESSED_PATH
            )
        )

    total_time = time.perf_counter() - pipeline_start

    print_summary(results, total_time)

    engine.dispose()


if __name__ == "__main__":
    run_pipeline()