"""
SimplePromptDataEngineering - End-to-End Pipeline Orchestrator

This orchestrator runs the complete ETL pipeline using prompt engineering
at every stage of the medallion architecture:

    Raw Data → [Bronze] → [Silver] → [Gold] → [Reports]

Each layer uses LLM prompts to automate data engineering tasks that
traditionally require manual coding and domain expertise.

Usage:
    python main.py                  # Run full pipeline
    python main.py --layer bronze   # Run only bronze layer
    python main.py --layer silver   # Run only silver layer
    python main.py --layer gold     # Run only gold layer
    python main.py --layer reports  # Run only report generation
"""

import argparse
import json
import logging
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import settings
from src.layers.bronze import BronzeLayer
from src.layers.silver import SilverLayer
from src.layers.gold import GoldLayer
from src.reports.generator import ReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline")


def run_bronze() -> dict:
    logger.info(">>> Starting Bronze Layer (Raw Ingestion + Schema Detection)")
    bronze = BronzeLayer()
    return bronze.run()


def run_silver(bronze_metadata: dict) -> pd.DataFrame:
    logger.info(">>> Starting Silver Layer (Cleaning + Transformation)")
    silver = SilverLayer()
    return silver.run(bronze_metadata)


def run_gold(silver_df: pd.DataFrame) -> dict:
    logger.info(">>> Starting Gold Layer (Aggregations + KPIs)")
    gold = GoldLayer()
    return gold.run(silver_df)


def run_reports(gold_tables: dict) -> dict:
    logger.info(">>> Starting Report Generation (Narratives + Anomalies)")
    reporter = ReportGenerator()
    return reporter.run(gold_tables)


def load_bronze_metadata() -> dict:
    metadata = {}
    bronze_dir = settings.BRONZE_DIR
    if not os.path.exists(bronze_dir):
        return metadata
    for f in os.listdir(bronze_dir):
        if f.endswith("_metadata.json"):
            table_name = f.replace("_metadata.json", "")
            with open(os.path.join(bronze_dir, f)) as fh:
                metadata[table_name] = json.load(fh)
    return metadata


def load_silver_data() -> pd.DataFrame:
    silver_path = os.path.join(settings.SILVER_DIR, "silver_enriched.csv")
    if os.path.exists(silver_path):
        return pd.read_csv(silver_path)
    return pd.DataFrame()


def load_gold_tables() -> dict:
    gold_tables = {}
    gold_dir = settings.GOLD_DIR
    if not os.path.exists(gold_dir):
        return gold_tables
    for f in os.listdir(gold_dir):
        if f.endswith(".csv"):
            table_name = f.replace(".csv", "")
            gold_tables[table_name] = pd.read_csv(os.path.join(gold_dir, f))
    return gold_tables


def run_full_pipeline():
    logger.info("=" * 70)
    logger.info("  PROMPT-DRIVEN DATA ENGINEERING PIPELINE")
    logger.info("  Use Case: E-Commerce Sales Analytics")
    logger.info("  Architecture: Medallion (Bronze → Silver → Gold → Reports)")
    logger.info("=" * 70)
    start = time.time()

    bronze_metadata = run_bronze()
    silver_df = run_silver(bronze_metadata)
    gold_tables = run_gold(silver_df)
    report_results = run_reports(gold_tables)

    elapsed = time.time() - start
    logger.info("=" * 70)
    logger.info("  PIPELINE COMPLETE in %.1f seconds", elapsed)
    logger.info("  Bronze tables: %d", len(bronze_metadata))
    logger.info("  Silver rows: %d", len(silver_df))
    logger.info("  Gold tables: %d", len(gold_tables))
    logger.info("  Reports: %d", len(report_results))
    logger.info("=" * 70)

    print("\n--- OUTPUT FILES ---")
    for layer_dir, label in [
        (settings.BRONZE_DIR, "Bronze"),
        (settings.SILVER_DIR, "Silver"),
        (settings.GOLD_DIR, "Gold"),
        (settings.REPORTS_DIR, "Reports"),
    ]:
        if os.path.exists(layer_dir):
            files = [f for f in os.listdir(layer_dir) if not f.startswith(".")]
            print(f"\n{label} Layer ({layer_dir}):")
            for f in sorted(files):
                size = os.path.getsize(os.path.join(layer_dir, f))
                print(f"  {f} ({size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(
        description="Prompt-Driven Data Engineering Pipeline"
    )
    parser.add_argument(
        "--layer",
        choices=["bronze", "silver", "gold", "reports", "all"],
        default="all",
        help="Which layer to run (default: all)",
    )
    args = parser.parse_args()

    if args.layer == "all":
        run_full_pipeline()
    elif args.layer == "bronze":
        run_bronze()
    elif args.layer == "silver":
        metadata = load_bronze_metadata()
        if not metadata:
            logger.error("No bronze metadata found. Run bronze layer first.")
            sys.exit(1)
        run_silver(metadata)
    elif args.layer == "gold":
        silver_df = load_silver_data()
        if silver_df.empty:
            logger.error("No silver data found. Run silver layer first.")
            sys.exit(1)
        run_gold(silver_df)
    elif args.layer == "reports":
        gold_tables = load_gold_tables()
        if not gold_tables:
            logger.error("No gold tables found. Run gold layer first.")
            sys.exit(1)
        run_reports(gold_tables)


if __name__ == "__main__":
    main()
