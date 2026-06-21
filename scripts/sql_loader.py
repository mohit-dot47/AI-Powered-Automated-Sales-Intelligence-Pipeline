import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

# -----------------------------
# Database Config
# -----------------------------
DB_USER = "root"
DB_PASSWORD = "root123"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "ai_sales_analytics"

# -----------------------------
# MySQL Engine
# -----------------------------
engine = create_engine(
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_PATH = BASE_DIR / "Data" / "Cleaned"

# -----------------------------
# File Mapping
# -----------------------------
files_to_tables = {
    "amazon_sales_cleaned.csv": "sales_orders",
    "sale_report_cleaned.csv": "products",
    "pnl_cleaned.csv": "financials",
    "international_sales_cleaned.csv": "inventory"
}

# -----------------------------
# Load Function
# -----------------------------
def load_csv_to_mysql(file_name, table_name):
    file_path = CLEAN_PATH / file_name

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    connection = engine.connect()

    try:
        df = pd.read_csv(file_path, low_memory=False)

        # Clean column names
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace(r"[^\w]", "", regex=True)
        )

        # Convert all object columns to string
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].astype(str)

        print(f"Loading {file_name} → {table_name}")

        df.to_sql(
            name=table_name,
            con=connection,
            if_exists="replace",
            index=False,
            chunksize=5000,
            method="multi"
        )

        print(f"Successfully loaded {table_name}")

    except Exception as e:
        print(f"Error loading {file_name}: {e}")
        connection.rollback()

    finally:
        connection.close()

# -----------------------------
# Main Execution
# -----------------------------
if __name__ == "__main__":
    print("Starting SQL data loading pipeline...\n")

    for file_name, table_name in files_to_tables.items():
        load_csv_to_mysql(file_name, table_name)

    print("\nSQL data loading pipeline completed.") 