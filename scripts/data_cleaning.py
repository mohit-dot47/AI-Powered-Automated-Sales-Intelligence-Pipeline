import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_PATH = BASE_DIR / "Data" / "Raw"
CLEAN_PATH = BASE_DIR / "Data" / "Cleaned"
LOG_PATH = BASE_DIR / "Data" / "Logs"

CHUNK_SIZE = 50_000
NULL_OBJECT_FILL = "Unknown"
NULL_NUMERIC_FILL = 0

FILES: dict[str, str] = {
    "amazon_sales": "Amazon Sale Report.csv",
    "international_sales": "International sale Report.csv",
    "may_sales": "May-2022.csv",
    "pnl": "pnl_report.csv",
    "sale_report": "Sale Report.csv",
}

# ──────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────

def setup_logger(log_dir: Path) -> logging.Logger:
    """Configure logger for console + file logging."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"pipeline_{time.strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("DataCleaningPipeline")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    # File
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


logger = setup_logger(LOG_PATH)

# ──────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────

@dataclass
class CleaningReport:
    """Stores cleaning stats for each file."""
    name: str
    raw_rows: int = 0
    clean_rows: int = 0
    duplicates_removed: int = 0
    empty_rows_removed: int = 0
    null_fills: dict = field(default_factory=dict)
    columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""

# ──────────────────────────────────────────────
# Cleaning Functions
# ──────────────────────────────────────────────

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert columns to clean snake_case."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df


def detect_and_cast_dates(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Detect likely date columns and convert."""
    for col in df.select_dtypes(include="object").columns:
        if any(keyword in col for keyword in ("date", "time", "dt")):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                logger.debug("Parsed '%s' as datetime.", col)
            except Exception as exc:
                warning = f"Could not parse '{col}' as datetime: {exc}"
                report.warnings.append(warning)
                logger.warning(warning)
    return df


def fill_nulls(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Fill null values intelligently."""
    null_counts = {}

    # Object columns
    for col in df.select_dtypes(include="object").columns:
        missing = int(df[col].isna().sum())
        if missing:
            df[col] = df[col].fillna(NULL_OBJECT_FILL)
            null_counts[col] = missing

    # Numeric columns
    for col in df.select_dtypes(include=["int64", "float64"]).columns:
        missing = int(df[col].isna().sum())
        if missing:
            df[col] = df[col].fillna(NULL_NUMERIC_FILL)
            null_counts[col] = missing

    report.null_fills = null_counts
    return df


def clean_dataframe(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    """Main cleaning process."""
    report.raw_rows = len(df)

    # Standardize columns
    df = standardize_columns(df)

    # Remove duplicates
    before = len(df)
    df.drop_duplicates(inplace=True)
    report.duplicates_removed = before - len(df)

    # Remove empty rows
    before = len(df)
    df.dropna(how="all", inplace=True)
    report.empty_rows_removed = before - len(df)

    # Date conversion
    df = detect_and_cast_dates(df, report)

    # Fill nulls
    df = fill_nulls(df, report)

    # Strip string whitespace
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # -----------------------------
    # Revenue / Amount Cleaning
    # -----------------------------
    for col in df.columns:
        if any(keyword in col for keyword in ["amount", "revenue", "sales", "price", "mrp"]):
            try:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace("₹", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

                # Prevent negative values
                df[col] = df[col].apply(lambda x: max(x, 0))

            except Exception as exc:
                warning = f"Revenue cleaning failed for '{col}': {exc}"
                report.warnings.append(warning)

    # -----------------------------
    # SKU Standardization
    # -----------------------------
    for col in df.columns:
        if "sku" in col:
            df[col] = (
                df[col]
                .astype(str)
                .str.upper()
                .str.strip()
            )

    # -----------------------------
    # Category / Region Standardization
    # -----------------------------
    for col in df.columns:
        if any(keyword in col for keyword in ["category", "state", "city", "country"]):
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.title()
            )

    report.clean_rows = len(df)
    report.columns = df.columns.tolist()

    return df

# ──────────────────────────────────────────────
# File Handling
# ──────────────────────────────────────────────

def read_csv_file(file_path: Path) -> pd.DataFrame:
    """
    Read CSV with:
    - UTF-8 fallback
    - Latin1 fallback
    - Chunked loading for large files
    """
    size_mb = file_path.stat().st_size / (1024 ** 2)
    encodings = ["utf-8", "latin1"]

    for encoding in encodings:
        try:
            if size_mb > 10:
                logger.info("Large file (%.1f MB) — reading in chunks.", size_mb)
                chunks = pd.read_csv(
                    file_path,
                    chunksize=CHUNK_SIZE,
                    encoding=encoding,
                    low_memory=False
                )
                return pd.concat(chunks, ignore_index=True)

            return pd.read_csv(
                file_path,
                encoding=encoding,
                low_memory=False
            )

        except UnicodeDecodeError:
            logger.warning("Encoding %s failed for %s", encoding, file_path)

    raise ValueError(f"Could not read file due to encoding issues: {file_path}")


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Save cleaned CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

# ──────────────────────────────────────────────
# Summary Reporting
# ──────────────────────────────────────────────

def print_summary(reports: list[CleaningReport]) -> None:
    """Display full pipeline summary."""
    divider = "─" * 70

    logger.info("\n%s", divider)
    logger.info("PIPELINE SUMMARY")
    logger.info("%s", divider)

    for report in reports:
        status = "✓ SUCCESS" if report.success else f"✗ FAILED — {report.error}"
        logger.info("%-25s %s", report.name, status)

        if report.success:
            logger.info(
                "Rows: %d → %d | Duplicates Removed: %d | Empty Rows Removed: %d",
                report.raw_rows,
                report.clean_rows,
                report.duplicates_removed,
                report.empty_rows_removed,
            )

            if report.null_fills:
                logger.info("Null fills: %s", report.null_fills)

            if report.warnings:
                for warning in report.warnings:
                    logger.warning("⚠ %s", warning)

    success_count = sum(1 for report in reports if report.success)

    logger.info("%s", divider)
    logger.info("%d / %d files cleaned successfully.", success_count, len(reports))
    logger.info("%s", divider)

# ──────────────────────────────────────────────
# Main Pipeline
# ──────────────────────────────────────────────

def run_pipeline(
    files: dict[str, str],
    raw_path: Path,
    clean_path: Path,
) -> list[CleaningReport]:
    """Run full data cleaning pipeline."""
    reports = []

    for name, filename in files.items():
        report = CleaningReport(name=name)
        file_path = raw_path / filename

        logger.info("Processing '%s' (%s)", name, filename)

        if not file_path.exists():
            report.error = f"File not found: {file_path}"
            logger.error(report.error)
            reports.append(report)
            continue

        try:
            df = read_csv_file(file_path)

            logger.info("Loaded %d rows, %d columns", df.shape[0], df.shape[1])

            df = clean_dataframe(df, report)

            output_path = clean_path / f"{name}_cleaned.csv"
            save_csv(df, output_path)

            report.success = True
            logger.info("Saved cleaned file → %s", output_path)

        except Exception as exc:
            report.error = str(exc)
            logger.exception("Error processing '%s': %s", name, exc)

        reports.append(report)

    return reports

# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting Data Cleaning Pipeline")
    logger.info("BASE_DIR: %s", BASE_DIR)
    logger.info("RAW_PATH: %s", RAW_PATH)
    logger.info("CLEAN_PATH: %s", CLEAN_PATH)

    reports = run_pipeline(FILES, RAW_PATH, CLEAN_PATH)

    print_summary(reports)

    logger.info("Data cleaning pipeline completed.")