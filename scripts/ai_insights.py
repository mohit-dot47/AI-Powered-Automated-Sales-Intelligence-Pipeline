"""
AI-Powered Executive Insights Pipeline (Groq Free API Version)
==============================================================
Uses Groq API instead of OpenAI for free/low-cost AI-powered
executive sales insights generation.

"""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# ──────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────

load_dotenv()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_PATH = BASE_DIR / "Data" / "Processed"
REPORTS_PATH = BASE_DIR / "Reports" / "AI_Insights"
LOG_PATH = BASE_DIR / "Data" / "Logs"

# Free Groq-supported models:
# llama3-70b-8192
# llama3-8b-8192
# mixtral-8x7b-32768
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.4
GROQ_MAX_TOKENS = 4096

KPI_FILES = {
    "executive_summary": "executive_summary.csv",
    "monthly_revenue": "monthly_revenue.csv",
    "category_performance": "category_performance.csv",
    "top_products": "top_products.csv",
    "state_performance": "state_performance.csv",
    "customer_segments": "customer_segments.csv",
}

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"ai_insights_{time.strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("AIInsightsPipeline")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


logger = setup_logger(LOG_PATH)

# ──────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────

@dataclass
class KPIDataset:
    executive_summary: pd.DataFrame
    monthly_revenue: pd.DataFrame
    category_performance: pd.DataFrame
    top_products: pd.DataFrame
    state_performance: pd.DataFrame
    customer_segments: pd.DataFrame

# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────

def load_kpi_datasets(processed_path: Path, kpi_files: dict) -> KPIDataset:
    frames = {}

    for name, filename in kpi_files.items():
        file_path = processed_path / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing KPI file: {file_path}\nRun kpi_pipeline.py first."
            )

        df = pd.read_csv(file_path)

        if df.empty:
            raise ValueError(f"KPI file is empty: {filename}")

        logger.debug("Loaded '%s' (%d rows, %d cols)", name, *df.shape)
        frames[name] = df

    return KPIDataset(**frames)

# ──────────────────────────────────────────────
# Prompt Construction
# ──────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a senior business intelligence consultant specialising in "
    "e-commerce and retail analytics. Produce concise, executive-level, "
    "data-driven reports with strategic recommendations."
)

REPORT_SECTIONS = [
    "1. Executive Summary",
    "2. Revenue Insights",
    "3. Product Performance",
    "4. Geographic Analysis",
    "5. Customer Segment Analysis",
    "6. Operational Risks",
    "7. Strategic Recommendations",
]

def build_prompt(kpi: KPIDataset) -> str:
    def fmt(df):
        return df.to_string(index=False)

    return f"""
Analyse the following KPI datasets and create an executive business report.

Sections:
{chr(10).join(REPORT_SECTIONS)}

Requirements:
- Use specific numbers
- Highlight growth, risks, anomalies
- Include actionable recommendations
- Executive-ready language

[Executive Summary]
{fmt(kpi.executive_summary)}

[Monthly Revenue]
{fmt(kpi.monthly_revenue)}

[Category Performance]
{fmt(kpi.category_performance)}

[Top Products]
{fmt(kpi.top_products)}

[State Performance]
{fmt(kpi.state_performance)}

[Customer Segments]
{fmt(kpi.customer_segments)}
"""

# ──────────────────────────────────────────────
# Groq API Call
# ──────────────────────────────────────────────

def generate_insights(prompt: str, client: Groq) -> str:
    logger.info(
        "Calling Groq API (model=%s, temperature=%.1f)...",
        GROQ_MODEL,
        GROQ_TEMPERATURE,
    )

    t0 = time.perf_counter()

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
    )

    elapsed = time.perf_counter() - t0

    logger.info("Groq response received in %.2fs", elapsed)

    return response.choices[0].message.content.strip()

# ──────────────────────────────────────────────
# Report Saving
# ──────────────────────────────────────────────

REPORT_HEADER_TEMPLATE = """\
╔══════════════════════════════════════════════════════════════╗
║          AI-GENERATED EXECUTIVE SALES INSIGHTS REPORT        ║
╚══════════════════════════════════════════════════════════════╝
Generated : {timestamp}
Model     : {model}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

def save_report(content: str, reports_path: Path) -> Path:
    reports_path.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    stamp = time.strftime("%Y%m%d_%H%M%S")

    header = REPORT_HEADER_TEMPLATE.format(
        timestamp=timestamp,
        model=GROQ_MODEL,
    )

    full_content = header + content

    latest_path = reports_path / "executive_ai_insights.txt"
    archive_path = reports_path / f"executive_ai_insights_{stamp}.txt"

    latest_path.write_text(full_content, encoding="utf-8")
    archive_path.write_text(full_content, encoding="utf-8")

    logger.info("Report saved → %s", latest_path)

    return latest_path

# ──────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────

def run_pipeline():
    logger.info("Starting AI Insights Pipeline.")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found in .env file."
        )

    client = Groq(api_key=api_key)

    logger.info("Loading KPI datasets from: %s", PROCESSED_PATH)
    kpi = load_kpi_datasets(PROCESSED_PATH, KPI_FILES)
    logger.info("All KPI datasets loaded successfully.")

    prompt = build_prompt(kpi)

    insights = generate_insights(prompt, client)

    output_path = save_report(insights, REPORTS_PATH)

    logger.info("Pipeline complete. Report generated: %s", output_path)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
