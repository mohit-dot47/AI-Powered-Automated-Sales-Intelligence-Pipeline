# 🤖 AI-Powered Automated Sales Intelligence Pipeline

> An end-to-end automated pipeline that cleans raw Amazon sales data, loads it into MySQL, computes 11 business KPIs via SQL, generates AI-powered executive insights using **LLaMA 3.3 (Groq)**, and produces a fully styled **PDF report** — with zero manual intervention.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [KPIs Computed](#kpis-computed)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [How to Run](#how-to-run)
- [Output](#output)
- [Design Decisions](#design-decisions)
- [Future Improvements](#future-improvements)

---

## Overview

This project automates the full sales intelligence workflow for an e-commerce business:

1. **Clean** — Raw sales CSVs are validated, deduplicated, and standardised (nulls filled, currencies stripped, SKUs uppercased, date columns auto-detected)
2. **Load** — Cleaned data is loaded into a structured MySQL database (`ai_sales_analytics`) via SQLAlchemy
3. **Analyse** — 11 SQL KPI queries run against the database and export results as CSVs
4. **AI Insights** — KPI data is sent to **LLaMA 3.3-70b** via Groq API, which generates a 7-section executive narrative
5. **Report** — A polished multi-page PDF is built with matplotlib charts, an AI insights section, and a top products table

---

## Pipeline Architecture

```
Data/Raw/ (5 CSV files)
       │
       ▼
┌─────────────────────┐
│  data_cleaning.py   │  Validate, deduplicate, normalise
│                     │  → Data/Cleaned/
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   sql_loader.py     │  Load CSVs → MySQL tables
│                     │  DB: ai_sales_analytics
│                     │  Tables: sales_orders, products,
│                     │          financials, inventory
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  kpi_automation.py  │  11 SQL KPI queries via SQLAlchemy
│                     │  → Data/Processed/ (11 CSVs)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   ai_insights.py    │  Build structured prompt from KPIs
│                     │  → Groq API (llama-3.3-70b-versatile)
│                     │  → Reports/AI_Insights/
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ report_generator.py │  matplotlib charts + fpdf2 layout
│                     │  → Reports/Final_Reports/
│                     │    executive_sales_report.pdf
└─────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Core pipeline logic |
| Database | MySQL | Structured data storage |
| ORM | SQLAlchemy | Database abstraction & query execution |
| Data Processing | Pandas | Cleaning, transformation, chunked loading |
| AI / LLM | Groq API — `llama-3.3-70b-versatile` | Executive narrative generation |
| PDF Generation | fpdf2 | Multi-page styled PDF output |
| Charting | Matplotlib | Revenue, category, and state charts |
| Config | python-dotenv | Secure credential management |
| Logging | Python logging | Console + timestamped file logs |

---

## Project Structure

```
AI-Powered-Automated-Sales-Intelligence-Pipeline/
│
├── Data/
│   ├── Raw/                        # Source CSV files (input)
│   │   ├── Amazon Sale Report.csv
│   │   ├── International sale Report.csv
│   │   ├── May-2022.csv
│   │   ├── pnl_report.csv
│   │   └── Sale Report.csv
│   ├── Cleaned/                    # Output of data_cleaning.py
│   ├── Processed/                  # Output of kpi_automation.py (11 KPI CSVs)
│   └── Logs/                       # Timestamped log files per pipeline run
│
├── Reports/
│   ├── AI_Insights/                # Output of ai_insights.py (.txt)
│   │   └── executive_ai_insights.txt
│   └── Final_Reports/              # Output of report_generator.py (.pdf)
│       └── executive_sales_report.pdf
│
├── scripts/
│   ├── data_cleaning.py            # Step 1: Clean raw CSVs
│   ├── sql_loader.py               # Step 2: Load to MySQL
│   ├── kpi_automation.py           # Step 3: Run KPI SQL queries
│   ├── ai_insights.py              # Step 4: Generate AI executive summary
│   └── report_generator.py         # Step 5: Build final PDF report
│
├── sql/                            # Raw SQL schema and reference queries
├── .env.example                    # Template — copy to .env and fill in values
├── .gitignore
├── requirements.txt
└── README.md
```

---

## KPIs Computed

The pipeline computes 11 KPI datasets via SQL and exports each as a CSV:

| KPI | Description |
|---|---|
| `executive_summary` | Total orders, revenue, AOV, active states/cities, unique SKUs |
| `monthly_revenue` | Month-over-month revenue trend |
| `category_performance` | Revenue, units, and revenue share % per product category |
| `top_products` | Top 10 SKUs by revenue, units sold, and avg unit price |
| `state_performance` | Revenue, orders, and share % per state |
| `customer_segments` | B2B vs B2C split by revenue, orders, and AOV |
| `cancellation_analysis` | Order status breakdown — shipped, cancelled, returned |
| `top_cities` | Top 10 cities by total revenue |
| `courier_performance` | Fulfilment outcome breakdown by courier status |
| `fulfillment_performance` | Amazon vs merchant fulfilment channel comparison |
| `sales_channel_performance` | Revenue and AOV split by sales channel |

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- MySQL Server (local or remote)
- [Groq API key](https://console.groq.com) — free tier is sufficient

### 1. Clone the repository

```bash
git clone https://github.com/mohit-dot47/AI-Powered-Automated-Sales-Intelligence-Pipeline.git
cd AI-Powered-Automated-Sales-Intelligence-Pipeline
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials (see below).

### 5. Create the MySQL database

```bash
mysql -u your_username -p -e "CREATE DATABASE ai_sales_analytics;"
```

### 6. Place your raw data files

Put your CSV files into `Data/Raw/`:

```
Data/Raw/Amazon Sale Report.csv
Data/Raw/International sale Report.csv
Data/Raw/May-2022.csv
Data/Raw/pnl_report.csv
Data/Raw/Sale Report.csv
```

---

## Environment Variables

Copy `.env.example` to `.env` and set the following:

```env
# Groq API (get yours free at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# MySQL Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=ai_sales_analytics
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
```

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore`.

---

## How to Run

Run each script in order from the project root:

```bash
# Step 1 — Clean raw data
python scripts/data_cleaning.py

# Step 2 — Load cleaned data into MySQL
python scripts/sql_loader.py

# Step 3 — Compute KPIs and export to CSV
python scripts/kpi_automation.py

# Step 4 — Generate AI executive insights via Groq
python scripts/ai_insights.py

# Step 5 — Build final PDF report
python scripts/report_generator.py
```

Each script logs progress to the console and writes a timestamped log file to `Data/Logs/`.

---

## Output

After a full pipeline run, you will have:

```
Data/Cleaned/           ← 5 cleaned CSVs (one per source file)
Data/Processed/         ← 11 KPI CSVs
Data/Logs/              ← timestamped logs for each script
Reports/AI_Insights/
  └── executive_ai_insights.txt       ← LLaMA 3.3 narrative report
Reports/Final_Reports/
  └── executive_sales_report.pdf      ← Final styled PDF
  └── executive_sales_report_<timestamp>.pdf   ← Archived copy
```

### What the PDF contains

| Section | Content |
|---|---|
| Cover Page | Title, date, confidentiality label |
| AI Executive Insights | 7-section narrative from LLaMA 3.3 |
| Revenue Trend | Line chart — monthly revenue |
| Category Performance | Horizontal bar chart — revenue by category |
| Geographic Distribution | Horizontal bar chart — top 10 states |
| Top 10 Products | Styled table — SKU, revenue, units, avg price |

---

## Design Decisions

**Why SQLAlchemy instead of raw SQL strings?**
SQLAlchemy makes the connection layer database-agnostic — swapping MySQL for PostgreSQL in a production deployment requires only a change to the connection string. The ORM also provides `pool_pre_ping` for connection health checks, which raw `mysql.connector` doesn't abstract cleanly.

**Why Groq instead of OpenAI?**
Groq's inference speed on LLaMA 3.3-70b (~500 tokens/sec) is significantly faster than OpenAI's GPT-4o for batch report generation. The free tier is also genuinely usable for this workload — no credit card required to reproduce the project.

**Why chunked loading in `data_cleaning.py`?**
Source files over 10 MB are read in 50,000-row chunks to avoid memory issues. This makes the pipeline safe to run on laptops with limited RAM without changing any code.

**Why archive copies in Reports?**
Every pipeline run saves both a `latest` file (overwritten) and a timestamped archive. This means you always have the most recent report at a predictable path (good for automation) while retaining a full history.

---

## Future Improvements

- [ ] Add a master `pipeline.py` runner to execute all 5 steps in one command
- [ ] Dockerize the pipeline for one-command reproducible setup
- [ ] Add Apache Airflow DAG for scheduled daily runs with retry logic
- [ ] Email delivery of the final PDF report via SMTP or SendGrid
- [ ] Add unit tests for KPI SQL queries using pytest + SQLite in-memory DB
- [ ] Add anomaly detection — flag revenue drops > 20% MoM automatically

---

## Author

**Mohit** — [@mohit-dot47](https://github.com/mohit-dot47)

---

## License

MIT License — free to use, modify, and distribute.
