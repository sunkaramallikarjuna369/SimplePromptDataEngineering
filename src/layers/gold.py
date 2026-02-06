import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import settings
from src.utils.llm_client import llm_client
from src.utils.storage import storage
from src.prompts.templates import AGGREGATION_SYSTEM, AGGREGATION_USER

logger = logging.getLogger(__name__)


class GoldLayer:
    """
    Gold Layer: Business-Ready Aggregations with LLM-Generated Logic

    This layer demonstrates how prompt engineering automates:
    - KPI calculation logic generation
    - Business metric aggregation
    - SQL/Pandas query generation from natural language
    """

    def __init__(self):
        self.gold_dir = settings.GOLD_DIR

    def generate_aggregation_code(self, silver_df: pd.DataFrame) -> str:
        logger.info("Generating gold-layer aggregation logic via LLM")
        schema_info = ""
        for col in silver_df.columns:
            dtype = str(silver_df[col].dtype)
            sample = str(silver_df[col].dropna().iloc[:3].tolist()) if len(silver_df) > 0 else "[]"
            schema_info += f"  {col} ({dtype}): {sample}\n"

        sample_data = silver_df.head(5).to_string(index=False)

        prompt = AGGREGATION_USER.format(
            silver_schema=schema_info,
            sample_data=sample_data,
        )
        code = llm_client.ask(AGGREGATION_SYSTEM, prompt)
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()

    def execute_aggregation(self, silver_df: pd.DataFrame, agg_code: str) -> dict:
        logger.info("Executing LLM-generated aggregation logic")
        local_ns = {"pd": pd, "silver_df": silver_df}
        try:
            exec(agg_code, {"pd": pd, "np": __import__("numpy")}, local_ns)
            if "build_gold_layer" in local_ns:
                return local_ns["build_gold_layer"](silver_df)
        except Exception as e:
            logger.warning("LLM aggregation code failed: %s. Using fallback.", e)
        return self._fallback_aggregation(silver_df)

    def _fallback_aggregation(self, df: pd.DataFrame) -> dict:
        logger.info("Applying fallback aggregation logic")
        gold_tables = {}

        if "order_date" in df.columns and "net_amount" in df.columns:
            date_col = pd.to_datetime(df["order_date"], format="mixed", dayfirst=False)
            daily = df.copy()
            daily["order_date_parsed"] = date_col
            daily_agg = daily.groupby(daily["order_date_parsed"].dt.date).agg(
                total_revenue=("net_amount", "sum"),
                order_count=("order_id", "nunique"),
                avg_order_value=("net_amount", "mean"),
                total_quantity=("quantity", "sum"),
            ).reset_index()
            daily_agg.rename(columns={"order_date_parsed": "date"}, inplace=True)
            gold_tables["daily_sales_summary"] = daily_agg

        if "customer_id" in df.columns and "net_amount" in df.columns:
            cust_agg = df.groupby("customer_id").agg(
                total_spent=("net_amount", "sum"),
                order_count=("order_id", "nunique"),
                avg_order_value=("net_amount", "mean"),
                first_order=("order_date", "min"),
                last_order=("order_date", "max"),
            ).reset_index()

            if "customer_segment" in df.columns:
                seg = df.drop_duplicates("customer_id")[["customer_id", "customer_segment"]]
                cust_agg = cust_agg.merge(seg, on="customer_id", how="left")

            if "first_name" in df.columns and "last_name" in df.columns:
                names = df.drop_duplicates("customer_id")[["customer_id", "first_name", "last_name"]]
                cust_agg = cust_agg.merge(names, on="customer_id", how="left")

            gold_tables["customer_analytics"] = cust_agg

        if "product_id" in df.columns and "net_amount" in df.columns:
            prod_agg = df.groupby("product_id").agg(
                total_revenue=("net_amount", "sum"),
                units_sold=("quantity", "sum"),
                order_count=("order_id", "nunique"),
                avg_selling_price=("unit_price", "mean"),
            ).reset_index()

            if "product_name" in prod_agg.columns or "product_name" in df.columns:
                names = df.drop_duplicates("product_id")[["product_id", "product_name"]]
                prod_agg = prod_agg.merge(names, on="product_id", how="left")

            if "category" in df.columns:
                cats = df.drop_duplicates("product_id")[["product_id", "category"]]
                prod_agg = prod_agg.merge(cats, on="product_id", how="left")

            if "unit_cost" in df.columns:
                costs = df.drop_duplicates("product_id")[["product_id", "unit_cost"]]
                prod_agg = prod_agg.merge(costs, on="product_id", how="left")
                prod_agg["total_cost"] = prod_agg["unit_cost"] * prod_agg["units_sold"]
                prod_agg["total_profit"] = prod_agg["total_revenue"] - prod_agg["total_cost"]
                prod_agg["profit_margin_pct"] = (
                    prod_agg["total_profit"] / prod_agg["total_revenue"] * 100
                ).round(2)

            prod_agg = prod_agg.sort_values("total_revenue", ascending=False)
            gold_tables["product_performance"] = prod_agg

        return gold_tables

    def run(self, silver_df: pd.DataFrame) -> dict:
        logger.info("========== GOLD LAYER START ==========")

        agg_code = self.generate_aggregation_code(silver_df)
        code_path = os.path.join(self.gold_dir, "aggregation_rules.py")
        storage.write_text(agg_code, code_path)

        gold_tables = self.execute_aggregation(silver_df, agg_code)

        for table_name, df in gold_tables.items():
            out_path = os.path.join(self.gold_dir, f"{table_name}.csv")
            storage.write_csv(df, out_path)
            logger.info("Gold table '%s': %d rows, %d columns", table_name, len(df), len(df.columns))

        logger.info("========== GOLD LAYER COMPLETE ==========")
        return gold_tables
