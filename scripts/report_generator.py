"""
Executive Sales Report Generator
=================================
Produces a polished, multi-section PDF report by combining:
  - KPI datasets from the processed data layer
  - AI-generated narrative insights
  - Professionally styled matplotlib charts

Output     : Reports/Final_Reports/executive_sales_report.pdf
             Reports/Final_Reports/executive_sales_report_<timestamp>.pdf

FIXES APPLIED:
  1. Monthly revenue chart blank fix — order_month now parsed as string,
     converted to datetime, sorted, and formatted as "Mon YYYY" labels.
  2. Top Products table added to final PDF page (was empty before).
  3. Robust column name fallbacks for top_products CSV variations.
  4. AI insights box-drawing characters replaced before clean_text() runs.
"""

import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from fpdf import FPDF


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_PATH = BASE_DIR / "Data" / "Processed"
AI_REPORT_PATH = BASE_DIR / "Reports" / "AI_Insights"
FINAL_REPORT_PATH = BASE_DIR / "Reports" / "Final_Reports"
CHARTS_PATH = FINAL_REPORT_PATH / "charts"
LOG_PATH = BASE_DIR / "Data" / "Logs"

REPORT_TITLE = "AI-Powered Executive Sales Intelligence Report"
COMPANY_NAME = "Your Company Name"

ACCENT_COLOR = (0, 82, 155)
CHART_STYLE = "seaborn-v0_8-whitegrid"
CHART_DPI = 150
CHART_FIGSIZE = (10, 4.5)

AI_INSIGHTS_CHAR_LIMIT = 5000

KPI_FILES = {
    "monthly_revenue": "monthly_revenue.csv",
    "category_performance": "category_performance.csv",
    "state_performance": "state_performance.csv",
    "top_products": "top_products.csv",
}


# ──────────────────────────────────────────────
# Unicode Safety Helper
# ──────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Replace unsupported Unicode characters for FPDF latin-1 compatibility.
    Prevents PDF crashes from AI-generated or formatted text.
    Now also strips box-drawing characters used in ASCII art banners.
    """
    # Extended replacements including box-drawing characters
    replacements = {
        # Common typographic characters
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "-",   # bullet
        "\u2026": "...", # ellipsis
        # Box-drawing characters (used in ASCII art headers from AI output)
        "\u2554": "+",   # ╔
        "\u2557": "+",   # ╗
        "\u255a": "+",   # ╚
        "\u255d": "+",   # ╝
        "\u2550": "=",   # ═
        "\u2551": "|",   # ║
        "\u2563": "+",   # ╣
        "\u2560": "+",   # ╠
        "\u2566": "+",   # ╦
        "\u2569": "+",   # ╩
        "\u256c": "+",   # ╬
        "\u2502": "|",   # │
        "\u2500": "-",   # ─
        "\u250c": "+",   # ┌
        "\u2510": "+",   # ┐
        "\u2514": "+",   # └
        "\u2518": "+",   # ┘
        "\u251c": "+",   # ├
        "\u2524": "+",   # ┤
        "\u252c": "+",   # ┬
        "\u2534": "+",   # ┴
        "\u253c": "+",   # ┼
        # Star / decorative symbols
        "\u2605": "*",   # ★
        "\u2606": "*",   # ☆
        "\u25cf": "-",   # ●
        "\u25cb": "-",   # ○
        "\u25b6": ">",   # ▶
        "\u25c0": "<",   # ◀
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.encode("latin-1", errors="replace").decode("latin-1")


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"report_gen_{time.strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("ReportGenerator")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
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
# Data Classes
# ──────────────────────────────────────────────

@dataclass
class ReportData:
    monthly_revenue: pd.DataFrame
    category_performance: pd.DataFrame
    state_performance: pd.DataFrame
    top_products: pd.DataFrame
    ai_insights: str


@dataclass
class ChartPaths:
    monthly_revenue: Path
    category_performance: Path
    state_performance: Path


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────

def load_report_data(
    processed_path: Path,
    ai_report_path: Path,
    kpi_files: dict,
) -> ReportData:
    frames = {}

    for name, filename in kpi_files.items():
        file_path = processed_path / filename

        if not file_path.exists():
            raise FileNotFoundError(f"KPI file not found: {file_path}")

        # FIX 1: Load order_month as string to prevent numeric mis-parsing
        if name == "monthly_revenue":
            df = pd.read_csv(file_path, dtype={"order_month": str})
        else:
            df = pd.read_csv(file_path)

        if df.empty:
            raise ValueError(f"KPI file is empty: {filename}")

        frames[name] = df
        logger.debug("Loaded %s (%d rows)", name, len(df))

    insights_file = ai_report_path / "executive_ai_insights.txt"

    if not insights_file.exists():
        raise FileNotFoundError(
            f"AI insights file not found: {insights_file}\n"
            f"Run ai_insights_pipeline.py first."
        )

    ai_insights = insights_file.read_text(encoding="utf-8")

    return ReportData(
        monthly_revenue=frames["monthly_revenue"],
        category_performance=frames["category_performance"],
        state_performance=frames["state_performance"],
        top_products=frames["top_products"],
        ai_insights=ai_insights,
    )


# ──────────────────────────────────────────────
# Chart Styling
# ──────────────────────────────────────────────

def _apply_chart_style() -> None:
    try:
        plt.style.use(CHART_STYLE)
    except OSError:
        plt.style.use("ggplot")

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": CHART_DPI,
    })


def _save_chart(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close()
    logger.debug("Chart saved -> %s", path)


# ──────────────────────────────────────────────
# Chart Generation
# ──────────────────────────────────────────────

def generate_charts(data: ReportData, charts_path: Path) -> ChartPaths:
    charts_path.mkdir(parents=True, exist_ok=True)
    _apply_chart_style()

    accent_hex = "#{:02X}{:02X}{:02X}".format(*ACCENT_COLOR)

    # ── FIX 1: Monthly Revenue ─────────────────────────────────────────────
    # Parse order_month safely, sort chronologically, format as "Mon YYYY"
    mr = data.monthly_revenue.copy()

    # Try multiple common date formats
    for fmt in ("%Y-%m", "%Y-%m-%d", "%m/%Y", "%m-%Y"):
        try:
            mr["order_month_dt"] = pd.to_datetime(mr["order_month"], format=fmt)
            logger.debug("Parsed order_month with format: %s", fmt)
            break
        except (ValueError, TypeError):
            continue
    else:
        # Last resort: let pandas infer the format
        mr["order_month_dt"] = pd.to_datetime(mr["order_month"], infer_datetime_format=True, errors="coerce")
        logger.warning("Used inferred datetime parsing for order_month.")

    # Drop rows where parsing failed
    before = len(mr)
    mr = mr.dropna(subset=["order_month_dt"]).sort_values("order_month_dt")
    after = len(mr)
    if before != after:
        logger.warning("Dropped %d rows with unparseable order_month values.", before - after)

    if mr.empty:
        logger.error(
            "monthly_revenue DataFrame is empty after date parsing. "
            "Check that order_month column contains valid date strings (e.g. '2024-01')."
        )
        raise ValueError(
            "Could not parse any dates from 'order_month' column. "
            "Expected format: YYYY-MM (e.g. '2024-01'). "
            f"Sample values found: {data.monthly_revenue['order_month'].head(5).tolist()}"
        )

    mr["order_month_label"] = mr["order_month_dt"].dt.strftime("%b %Y")

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
    ax.plot(
        mr["order_month_label"],
        mr["monthly_revenue"],
        marker="o",
        linewidth=2.5,
        color=accent_hex,
    )

    ax.fill_between(
        range(len(mr)),        # numeric range for fill_between (x must be numeric)
        mr["monthly_revenue"],
        alpha=0.12,
        color=accent_hex,
    )

    # Re-set xtick positions to match the string labels plotted above
    ax.set_xticks(range(len(mr)))
    ax.set_xticklabels(mr["order_month_label"], rotation=45, ha="right")

    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )

    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (USD)")

    monthly_chart = charts_path / "monthly_revenue.png"
    _save_chart(monthly_chart)
    logger.info("Monthly revenue chart generated with %d data points.", len(mr))

    # ── Category Performance ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    cat_df = data.category_performance.sort_values(
        "total_revenue",
        ascending=True
    )

    bars = ax.barh(
        cat_df["category"],
        cat_df["total_revenue"],
        color=accent_hex,
        alpha=0.85,
    )

    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )

    for bar in bars:
        width = bar.get_width()
        ax.text(
            width * 1.01,
            bar.get_y() + bar.get_height() / 2,
            f"${width:,.0f}",
            va="center",
            fontsize=7,
        )

    ax.set_title("Revenue by Product Category")
    ax.set_xlabel("Revenue (USD)")

    category_chart = charts_path / "category_performance.png"
    _save_chart(category_chart)

    # ── State Performance ──────────────────────────────────────────────────
    top_states = data.state_performance.head(10).sort_values(
        "total_revenue",
        ascending=True
    )

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE)

    ax.barh(
        top_states["state"],
        top_states["total_revenue"],
        color=accent_hex,
        alpha=0.85,
    )

    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:,.0f}")
    )

    ax.set_title("Top 10 States by Revenue")
    ax.set_xlabel("Revenue (USD)")

    state_chart = charts_path / "state_performance.png"
    _save_chart(state_chart)

    logger.info("All 3 charts generated.")

    return ChartPaths(
        monthly_revenue=monthly_chart,
        category_performance=category_chart,
        state_performance=state_chart,
    )


# ──────────────────────────────────────────────
# PDF Report Class
# ──────────────────────────────────────────────

class SalesReport(FPDF):

    def __init__(self, title: str, company: str):
        super().__init__()
        self.report_title = title
        self.company = company
        self.accent_r, self.accent_g, self.accent_b = ACCENT_COLOR
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return

        self.set_fill_color(
            self.accent_r,
            self.accent_g,
            self.accent_b
        )

        self.rect(0, 0, 210, 12, "F")

        self.set_font("Arial", "B", 9)
        self.set_text_color(255, 255, 255)
        self.set_y(3)

        self.cell(
            0,
            6,
            clean_text(self.report_title),
            align="C"
        )

        self.set_text_color(0, 0, 0)
        self.ln(14)

    def footer(self):
        if self.page_no() == 1:
            return

        self.set_y(-13)

        self.set_draw_color(
            self.accent_r,
            self.accent_g,
            self.accent_b
        )

        self.line(10, self.get_y(), 200, self.get_y())

        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)

        footer_text = (
            f"{self.company} | Confidential | Page {self.page_no()}"
        )

        self.cell(
            0,
            8,
            clean_text(footer_text),
            align="C"
        )

        self.set_text_color(0, 0, 0)

    def cover_page(self):
        self.add_page()

        self.set_fill_color(
            self.accent_r,
            self.accent_g,
            self.accent_b
        )

        self.rect(0, 0, 210, 100, "F")

        self.set_y(28)
        self.set_font("Arial", "B", 22)
        self.set_text_color(255, 255, 255)

        self.multi_cell(
            0,
            10,
            clean_text(self.report_title),
            align="C"
        )

        self.ln(4)
        self.set_font("Arial", "", 12)

        self.cell(
            0,
            8,
            clean_text("Confidential - Executive Distribution Only"),
            align="C"
        )

        self.ln(8)
        self.set_font("Arial", "I", 10)

        self.cell(
            0,
            6,
            clean_text(f"Generated: {time.strftime('%B %d, %Y')}"),
            align="C"
        )

        self.set_text_color(0, 0, 0)
        self.set_y(115)

        self.line(20, self.get_y(), 190, self.get_y())

    def section_title(self, title: str):
        self.ln(4)

        self.set_font("Arial", "B", 13)

        self.set_text_color(
            self.accent_r,
            self.accent_g,
            self.accent_b
        )

        self.cell(
            0,
            9,
            clean_text(title),
            ln=True
        )

        self.line(10, self.get_y(), 200, self.get_y())

        self.set_text_color(0, 0, 0)
        self.ln(3)

    def body_text(self, text: str, line_height: int = 6):
        self.set_font("Arial", "", 10)
        self.set_text_color(40, 40, 40)

        self.multi_cell(
            0,
            line_height,
            clean_text(text)
        )

        self.set_text_color(0, 0, 0)
        self.ln(2)

    def insert_chart(
        self,
        chart_path: Path,
        caption: str,
        width: int = 175
    ):
        x = (210 - width) / 2

        self.image(str(chart_path), x=x, w=width)

        self.ln(2)
        self.set_font("Arial", "I", 8)
        self.set_text_color(100, 100, 100)

        self.cell(
            0,
            5,
            clean_text(caption),
            align="C",
            ln=True
        )

        self.set_text_color(0, 0, 0)
        self.ln(4)

    # ── FIX 2: Top Products Table ──────────────────────────────────────────
    def top_products_table(self, df: pd.DataFrame):
        """
        Render the top 10 products as a styled table.
        Handles multiple possible column name variations from different
        upstream CSV schemas.
        """
        # Resolve column names flexibly
        col_map = {
            "product":  next((c for c in df.columns if c in
                              ("product_name", "sku", "style", "product", "item")), None),
            "category": next((c for c in df.columns if "category" in c.lower()), None),
            "revenue":  next((c for c in df.columns if "revenue" in c.lower()), None),
            "units":    next((c for c in df.columns if c in
                              ("units_sold", "quantity", "qty", "units")), None),
            "price":    next((c for c in df.columns if "price" in c.lower()), None),
        }

        logger.debug("top_products column mapping: %s", col_map)

        # Build display columns based on what's available
        display_cols = []
        if col_map["product"]:
            display_cols.append(("Product / SKU",     col_map["product"],  70, False))
        if col_map["category"]:
            display_cols.append(("Category",          col_map["category"], 40, False))
        if col_map["revenue"]:
            display_cols.append(("Revenue (USD)",     col_map["revenue"],  45, True))
        if col_map["units"]:
            display_cols.append(("Units Sold",        col_map["units"],    30, True))
        if col_map["price"]:
            display_cols.append(("Avg Price (USD)",   col_map["price"],    30, True))

        if not display_cols:
            self.body_text("Top products data could not be formatted (no recognised columns).")
            logger.warning("top_products_table: no matching columns found in %s", list(df.columns))
            return

        col_labels  = [c[0] for c in display_cols]
        col_keys    = [c[1] for c in display_cols]
        col_widths  = [c[2] for c in display_cols]
        col_numeric = [c[3] for c in display_cols]

        row_height = 7

        # Header row
        self.set_font("Arial", "B", 8)
        self.set_fill_color(self.accent_r, self.accent_g, self.accent_b)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(200, 200, 200)
        for label, width in zip(col_labels, col_widths):
            self.cell(width, row_height + 1, label, border=1, fill=True, align="C")
        self.ln()

        # Data rows (top 10)
        self.set_font("Arial", "", 8)
        self.set_text_color(40, 40, 40)

        for i, (_, row) in enumerate(df.head(10).iterrows()):
            # Alternating row shading
            if i % 2 == 0:
                self.set_fill_color(240, 245, 252)
            else:
                self.set_fill_color(255, 255, 255)

            for key, width, is_numeric in zip(col_keys, col_widths, col_numeric):
                raw_val = row.get(key, "")
                if is_numeric:
                    try:
                        num = float(raw_val)
                        val = f"${num:,.0f}" if "price" in key.lower() or "revenue" in key.lower() else f"{int(num):,}"
                    except (ValueError, TypeError):
                        val = str(raw_val)
                else:
                    val = str(raw_val)[:22]  # truncate long strings

                self.cell(width, row_height, clean_text(val), border=1, fill=True, align="C" if is_numeric else "L")
            self.ln()

        self.set_text_color(0, 0, 0)
        self.set_draw_color(0, 0, 0)


# ──────────────────────────────────────────────
# PDF Builder
# ──────────────────────────────────────────────

def build_pdf(
    data: ReportData,
    charts: ChartPaths,
    output_path: Path
):
    pdf = SalesReport(
        title=REPORT_TITLE,
        company=COMPANY_NAME
    )

    # Cover Page
    pdf.cover_page()

    pdf.section_title("About This Report")

    pdf.body_text(
        "This report was generated automatically by the AI-Powered Sales "
        "Intelligence Pipeline. It synthesises transactional data across "
        "revenue, product, geography, and customer segments into "
        "actionable insights for senior leadership."
    )

    # AI Insights
    pdf.add_page()

    pdf.section_title("AI-Generated Executive Insights")

    truncated = data.ai_insights[:AI_INSIGHTS_CHAR_LIMIT]

    if len(data.ai_insights) > AI_INSIGHTS_CHAR_LIMIT:
        truncated += (
            "\n\n[...Report truncated. "
            "See full text file for complete insights.]"
        )

    pdf.body_text(truncated)

    # Revenue Trend
    pdf.add_page()

    pdf.section_title("Revenue Trend Analysis")

    pdf.body_text(
        "The chart below illustrates month-over-month revenue "
        "performance. Review peaks and troughs alongside "
        "seasonal campaigns or supply events."
    )

    pdf.insert_chart(
        charts.monthly_revenue,
        "Figure 1 - Monthly Revenue Trend (USD)"
    )

    # Category Performance
    pdf.add_page()

    pdf.section_title("Product Category Performance")

    pdf.body_text(
        "Revenue contribution ranked by product category. "
        "Categories are sorted ascending to highlight "
        "highest-value lines."
    )

    pdf.insert_chart(
        charts.category_performance,
        "Figure 2 - Revenue by Product Category (USD)"
    )

    # Geographic Performance
    pdf.add_page()

    pdf.section_title("Geographic Revenue Distribution")

    pdf.body_text(
        "Top 10 states by total revenue. High geographic "
        "concentration may represent both strength and risk."
    )

    pdf.insert_chart(
        charts.state_performance,
        "Figure 3 - Top 10 States by Revenue (USD)"
    )

    # ── FIX 2: Top Products — now renders an actual table ──────────────────
    pdf.add_page()

    pdf.section_title("Top 10 Products by Revenue")

    pdf.body_text(
        "The highest revenue SKUs ranked by units sold, "
        "revenue, and average unit price."
    )

    pdf.top_products_table(data.top_products)

    # Output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf.output(str(output_path))

    logger.info("PDF saved -> %s", output_path)


# ──────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────

def run_pipeline():
    logger.info("Starting Executive Report Generation Pipeline.")

    start_time = time.perf_counter()

    logger.info("Loading data ...")
    data = load_report_data(
        PROCESSED_PATH,
        AI_REPORT_PATH,
        KPI_FILES
    )

    # Log column names to help debug future issues
    logger.debug("monthly_revenue columns  : %s", list(data.monthly_revenue.columns))
    logger.debug("category_performance cols: %s", list(data.category_performance.columns))
    logger.debug("state_performance cols   : %s", list(data.state_performance.columns))
    logger.debug("top_products columns     : %s", list(data.top_products.columns))
    logger.debug("monthly_revenue sample   :\n%s", data.monthly_revenue.head(3).to_string())

    logger.info("Generating charts ...")
    charts = generate_charts(data, CHARTS_PATH)

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    latest_path = (
        FINAL_REPORT_PATH /
        "executive_sales_report.pdf"
    )

    archive_path = (
        FINAL_REPORT_PATH /
        f"executive_sales_report_{timestamp}.pdf"
    )

    logger.info("Building PDF report ...")
    build_pdf(data, charts, latest_path)

    shutil.copy2(latest_path, archive_path)

    elapsed = time.perf_counter() - start_time

    logger.info(
        "Report generation complete in %.2fs.",
        elapsed
    )

    logger.info("Output -> %s", latest_path)


if __name__ == "__main__":
    try:
        run_pipeline()

    except (FileNotFoundError, ValueError) as exc:
        logger.error("Pipeline aborted: %s", exc)

    except Exception as exc:
        logger.exception("Unexpected pipeline failure: %s", exc)