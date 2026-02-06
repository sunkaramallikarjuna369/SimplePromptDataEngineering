import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import settings
from src.utils.llm_client import llm_client
from src.utils.storage import storage
from src.prompts.templates import (
    REPORT_NARRATIVE_SYSTEM,
    REPORT_NARRATIVE_USER,
    ANOMALY_DETECTION_SYSTEM,
    ANOMALY_DETECTION_USER,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Report Generation: LLM-Powered Business Insights & Narratives

    This module demonstrates how prompt engineering automates:
    - Executive summary generation from data
    - Anomaly detection and explanation
    - Natural language report creation
    - Actionable recommendation generation
    """

    def __init__(self):
        self.reports_dir = settings.REPORTS_DIR

    def _summarize_df(self, df: pd.DataFrame, max_rows: int = 20) -> str:
        if df.empty:
            return "No data available."
        summary = df.head(max_rows).to_string(index=False)
        if len(df) > max_rows:
            summary += f"\n... ({len(df)} total rows)"
        return summary

    def _compute_overall_metrics(self, gold_tables: dict) -> str:
        metrics = {}
        daily = gold_tables.get("daily_sales_summary", pd.DataFrame())
        if not daily.empty and "total_revenue" in daily.columns:
            metrics["total_revenue"] = f"${daily['total_revenue'].sum():,.2f}"
            metrics["total_orders"] = int(daily["order_count"].sum())
            metrics["avg_daily_revenue"] = f"${daily['total_revenue'].mean():,.2f}"
            metrics["peak_day_revenue"] = f"${daily['total_revenue'].max():,.2f}"

        customers = gold_tables.get("customer_analytics", pd.DataFrame())
        if not customers.empty:
            metrics["total_customers"] = len(customers)
            if "total_spent" in customers.columns:
                metrics["avg_customer_spend"] = f"${customers['total_spent'].mean():,.2f}"
                metrics["top_customer_spend"] = f"${customers['total_spent'].max():,.2f}"

        products = gold_tables.get("product_performance", pd.DataFrame())
        if not products.empty:
            metrics["total_products_sold"] = len(products)
            if "total_revenue" in products.columns:
                top = products.nlargest(1, "total_revenue")
                if not top.empty and "product_name" in top.columns:
                    metrics["top_product"] = top.iloc[0]["product_name"]
                    metrics["top_product_revenue"] = f"${top.iloc[0]['total_revenue']:,.2f}"

        lines = [f"  {k}: {v}" for k, v in metrics.items()]
        return "\n".join(lines)

    def generate_narrative_report(self, gold_tables: dict) -> str:
        logger.info("Generating narrative report via LLM")
        period = "January - February 2024"

        prompt = REPORT_NARRATIVE_USER.format(
            period=period,
            daily_sales=self._summarize_df(gold_tables.get("daily_sales_summary", pd.DataFrame())),
            customer_analytics=self._summarize_df(gold_tables.get("customer_analytics", pd.DataFrame())),
            product_performance=self._summarize_df(gold_tables.get("product_performance", pd.DataFrame())),
            overall_metrics=self._compute_overall_metrics(gold_tables),
        )
        report = llm_client.ask(REPORT_NARRATIVE_SYSTEM, prompt)
        return report

    def detect_anomalies(self, gold_tables: dict) -> dict:
        logger.info("Running anomaly detection via LLM")
        daily = gold_tables.get("daily_sales_summary", pd.DataFrame())
        summary_parts = []
        for name, df in gold_tables.items():
            if not df.empty:
                summary_parts.append(f"Table: {name} ({len(df)} rows)")
                numeric_cols = df.select_dtypes(include=["number"]).columns
                for col in numeric_cols[:5]:
                    summary_parts.append(
                        f"  {col}: min={df[col].min():.2f}, max={df[col].max():.2f}, "
                        f"mean={df[col].mean():.2f}, std={df[col].std():.2f}"
                    )

        distribution = ""
        if not daily.empty and "total_revenue" in daily.columns:
            distribution = daily[["total_revenue", "order_count"]].describe().to_string()

        trends = ""
        if not daily.empty and "date" in daily.columns:
            trends = daily[["date", "total_revenue", "order_count"]].to_string(index=False)

        prompt = ANOMALY_DETECTION_USER.format(
            summary="\n".join(summary_parts),
            distribution=distribution,
            trends=trends,
        )
        anomalies = llm_client.ask_json(ANOMALY_DETECTION_SYSTEM, prompt)
        return anomalies

    def run(self, gold_tables: dict) -> dict:
        logger.info("========== REPORT GENERATION START ==========")
        results = {}

        narrative = self.generate_narrative_report(gold_tables)
        report_path = os.path.join(self.reports_dir, "executive_report.md")
        storage.write_text(narrative, report_path)
        results["narrative_report"] = report_path
        logger.info("Executive report saved: %s", report_path)

        anomalies = self.detect_anomalies(gold_tables)
        anomaly_path = os.path.join(self.reports_dir, "anomaly_report.json")
        storage.write_json(json.dumps(anomalies, indent=2), anomaly_path)
        results["anomaly_report"] = anomaly_path
        logger.info("Anomaly report saved: %s", anomaly_path)

        metadata = {
            "generated_at": datetime.now().isoformat(),
            "gold_tables_used": list(gold_tables.keys()),
            "reports_generated": list(results.keys()),
        }
        meta_path = os.path.join(self.reports_dir, "report_metadata.json")
        storage.write_json(json.dumps(metadata, indent=2), meta_path)

        logger.info("========== REPORT GENERATION COMPLETE ==========")
        return results
