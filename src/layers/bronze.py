import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import settings
from src.utils.llm_client import llm_client
from src.utils.storage import storage
from src.prompts.templates import (
    SCHEMA_DETECTION_SYSTEM,
    SCHEMA_DETECTION_USER,
    DATA_PROFILING_SYSTEM,
    DATA_PROFILING_USER,
)

logger = logging.getLogger(__name__)


class BronzeLayer:
    """
    Bronze Layer: Raw Data Ingestion with LLM-Powered Schema Detection & Profiling

    This layer demonstrates how prompt engineering automates:
    - Schema detection from raw CSV/JSON files
    - Data profiling and quality assessment
    - Metadata generation for data catalogs
    """

    def __init__(self):
        self.raw_dir = settings.RAW_DIR
        self.bronze_dir = settings.BRONZE_DIR

    def detect_schema(self, file_path: str) -> dict:
        logger.info("Detecting schema for: %s", file_path)
        df = storage.read_csv(file_path)
        file_name = os.path.basename(file_path)
        headers = ", ".join(df.columns.tolist())
        sample_rows = df.head(5).to_string(index=False)

        prompt = SCHEMA_DETECTION_USER.format(
            file_name=file_name,
            headers=headers,
            sample_rows=sample_rows,
        )
        schema = llm_client.ask_json(SCHEMA_DETECTION_SYSTEM, prompt)
        logger.info("Schema detected for %s: %d columns", file_name, len(schema.get("columns", [])))
        return schema

    def profile_data(self, file_path: str, schema: dict) -> dict:
        logger.info("Profiling data for: %s", file_path)
        df = storage.read_csv(file_path)
        file_name = os.path.basename(file_path)

        statistics = df.describe(include="all").to_string()
        null_counts = df.isnull().sum().to_string()
        sample_values = ""
        for col in df.columns:
            unique_vals = df[col].dropna().unique()[:5]
            sample_values += f"{col}: {list(unique_vals)}\n"

        prompt = DATA_PROFILING_USER.format(
            file_name=file_name,
            schema=json.dumps(schema, indent=2),
            statistics=statistics,
            null_counts=null_counts,
            sample_values=sample_values,
        )
        profile = llm_client.ask_json(DATA_PROFILING_SYSTEM, prompt)
        logger.info("Data profile complete. Quality score: %s", profile.get("overall_quality_score"))
        return profile

    def ingest_to_bronze(self, file_path: str) -> dict:
        logger.info("=== Bronze Layer: Ingesting %s ===", file_path)
        df = storage.read_csv(file_path)
        file_name = os.path.basename(file_path)
        table_name = os.path.splitext(file_name)[0]

        schema = self.detect_schema(file_path)
        profile = self.profile_data(file_path, schema)

        bronze_data_path = os.path.join(self.bronze_dir, file_name)
        storage.write_csv(df, bronze_data_path)

        metadata = {
            "source_file": file_name,
            "table_name": table_name,
            "schema": schema,
            "profile": profile,
            "row_count": len(df),
            "column_count": len(df.columns),
        }
        metadata_path = os.path.join(self.bronze_dir, f"{table_name}_metadata.json")
        storage.write_json(json.dumps(metadata, indent=2), metadata_path)

        logger.info("Bronze ingestion complete: %s (%d rows)", table_name, len(df))
        return metadata

    def run(self) -> dict:
        logger.info("========== BRONZE LAYER START ==========")
        raw_files = storage.list_files(self.raw_dir, ".csv")
        results = {}
        for file_path in raw_files:
            table_name = os.path.splitext(os.path.basename(file_path))[0]
            results[table_name] = self.ingest_to_bronze(file_path)
        logger.info("========== BRONZE LAYER COMPLETE ==========")
        return results
