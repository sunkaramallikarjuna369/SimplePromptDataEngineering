import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")

    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "prompt-data-engineering")

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    RAW_DIR: str = os.path.join(DATA_DIR, "raw")
    BRONZE_DIR: str = os.path.join(DATA_DIR, "bronze")
    SILVER_DIR: str = os.path.join(DATA_DIR, "silver")
    GOLD_DIR: str = os.path.join(DATA_DIR, "gold")
    REPORTS_DIR: str = os.path.join(DATA_DIR, "reports")


settings = Settings()
