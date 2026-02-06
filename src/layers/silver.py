import json
import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import settings
from src.utils.llm_client import llm_client
from src.utils.storage import storage
from src.prompts.templates import (
    CLEANING_RULES_SYSTEM,
    CLEANING_RULES_USER,
    TRANSFORMATION_RULES_SYSTEM,
    TRANSFORMATION_RULES_USER,
)

logger = logging.getLogger(__name__)


class SilverLayer:
    """
    Silver Layer: Data Cleaning & Transformation with LLM-Powered Rules

    This layer demonstrates how prompt engineering automates:
    - Data cleaning rule generation
    - Data transformation logic
    - Table joins and enrichment
    - Business-meaningful derived columns
    """

    def __init__(self):
        self.bronze_dir = settings.BRONZE_DIR
        self.silver_dir = settings.SILVER_DIR

    def generate_cleaning_code(self, table_name: str, schema: dict, profile: dict, columns: list) -> str:
        logger.info("Generating cleaning rules for: %s", table_name)
        prompt = CLEANING_RULES_USER.format(
            file_name=table_name,
            schema=json.dumps(schema, indent=2),
            profile=json.dumps(profile, indent=2),
            columns=", ".join(columns),
            table_name=table_name,
        )
        code = llm_client.ask(CLEANING_RULES_SYSTEM, prompt)
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()

    def execute_cleaning(self, df: pd.DataFrame, cleaning_code: str, table_name: str) -> pd.DataFrame:
        logger.info("Executing LLM-generated cleaning for: %s", table_name)
        local_ns = {"pd": pd, "df": df.copy()}
        try:
            exec(cleaning_code, {"pd": pd, "np": __import__("numpy")}, local_ns)
            func_name = f"clean_{table_name}"
            if func_name in local_ns:
                return local_ns[func_name](df.copy())
        except Exception as e:
            logger.warning("LLM cleaning code failed for %s: %s. Using fallback.", table_name, e)
        return self._fallback_clean(df, table_name)

    def _fallback_clean(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        logger.info("Applying fallback cleaning for: %s", table_name)
        cleaned = df.copy()
        cleaned = cleaned.drop_duplicates()
        for col in cleaned.select_dtypes(include=["object"]).columns:
            cleaned[col] = cleaned[col].str.strip()
        date_cols = [c for c in cleaned.columns if "date" in c.lower()]
        for col in date_cols:
            try:
                cleaned[col] = pd.to_datetime(cleaned[col], format="mixed", dayfirst=False)
            except Exception:
                pass
        return cleaned

    def generate_transformation_code(self, source_tables: dict) -> str:
        logger.info("Generating transformation rules for silver layer")
        tables_desc = ""
        for name, df in source_tables.items():
            tables_desc += f"\nTable: {name}\n"
            tables_desc += f"Columns: {', '.join(df.columns.tolist())}\n"
            tables_desc += f"Sample:\n{df.head(3).to_string(index=False)}\n"

        prompt = TRANSFORMATION_RULES_USER.format(source_tables=tables_desc)
        code = llm_client.ask(TRANSFORMATION_RULES_SYSTEM, prompt)
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        return code.strip()

    def execute_transformation(self, tables: dict, transform_code: str) -> pd.DataFrame:
        logger.info("Executing LLM-generated transformation")
        local_ns = {"pd": pd, "tables": tables}
        try:
            exec(transform_code, {"pd": pd, "np": __import__("numpy")}, local_ns)
            if "transform_to_silver" in local_ns:
                return local_ns["transform_to_silver"](tables)
        except Exception as e:
            logger.warning("LLM transformation code failed: %s. Using fallback.", e)
        return self._fallback_transform(tables)

    def _fallback_transform(self, tables: dict) -> pd.DataFrame:
        logger.info("Applying fallback transformation")
        orders = tables.get("orders", pd.DataFrame())
        customers = tables.get("customers", pd.DataFrame())
        products = tables.get("products", pd.DataFrame())

        if orders.empty:
            return pd.DataFrame()

        merged = orders.copy()
        if not customers.empty:
            merged = merged.merge(customers, on="customer_id", how="left")
        if not products.empty:
            merged = merged.merge(products, on="product_id", how="left")

        if "quantity" in merged.columns and "unit_price" in merged.columns:
            merged["gross_amount"] = merged["quantity"] * merged["unit_price"]
            if "discount" in merged.columns:
                merged["discount_amount"] = merged["gross_amount"] * merged["discount"]
                merged["net_amount"] = merged["gross_amount"] - merged["discount_amount"]
            else:
                merged["net_amount"] = merged["gross_amount"]

        if "unit_cost" in merged.columns and "quantity" in merged.columns:
            merged["total_cost"] = merged["unit_cost"] * merged["quantity"]
            merged["profit"] = merged["net_amount"] - merged["total_cost"]
            merged["profit_margin_pct"] = (merged["profit"] / merged["net_amount"] * 100).round(2)

        date_col = "order_date"
        if date_col in merged.columns:
            merged[date_col] = pd.to_datetime(merged[date_col], format="mixed", dayfirst=False)
            merged["order_year"] = merged[date_col].dt.year
            merged["order_month"] = merged[date_col].dt.month
            merged["order_quarter"] = merged[date_col].dt.quarter
            merged["order_day_of_week"] = merged[date_col].dt.day_name()

        return merged

    def run(self, bronze_metadata: dict) -> pd.DataFrame:
        logger.info("========== SILVER LAYER START ==========")

        cleaned_tables = {}
        for table_name, metadata in bronze_metadata.items():
            file_path = os.path.join(self.bronze_dir, f"{table_name}.csv")
            df = storage.read_csv(file_path)
            schema = metadata.get("schema", {})
            profile = metadata.get("profile", {})

            cleaning_code = self.generate_cleaning_code(
                table_name, schema, profile, df.columns.tolist()
            )
            code_path = os.path.join(self.silver_dir, f"{table_name}_cleaning_rules.py")
            storage.write_text(cleaning_code, code_path)

            cleaned_df = self.execute_cleaning(df, cleaning_code, table_name)
            cleaned_tables[table_name] = cleaned_df

            clean_path = os.path.join(self.silver_dir, f"{table_name}_cleaned.csv")
            storage.write_csv(cleaned_df, clean_path)
            logger.info("Cleaned %s: %d rows", table_name, len(cleaned_df))

        transform_code = self.generate_transformation_code(cleaned_tables)
        transform_path = os.path.join(self.silver_dir, "transformation_rules.py")
        storage.write_text(transform_code, transform_path)

        silver_df = self.execute_transformation(cleaned_tables, transform_code)

        silver_path = os.path.join(self.silver_dir, "silver_enriched.csv")
        storage.write_csv(silver_df, silver_path)
        logger.info("Silver layer complete: %d rows, %d columns", len(silver_df), len(silver_df.columns))
        logger.info("========== SILVER LAYER COMPLETE ==========")
        return silver_df
