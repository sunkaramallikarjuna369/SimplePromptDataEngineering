import os
import sys
import logging

import boto3
import pandas as pd

sys.path.insert(0, ".")
from config.settings import settings

logger = logging.getLogger(__name__)


class StorageManager:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        if self.backend == "s3":
            self.s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            self.bucket = settings.S3_BUCKET

    def read_csv(self, file_path: str) -> pd.DataFrame:
        if self.backend == "s3":
            obj = self.s3.get_object(Bucket=self.bucket, Key=file_path)
            return pd.read_csv(obj["Body"])
        return pd.read_csv(file_path)

    def write_csv(self, df: pd.DataFrame, file_path: str) -> str:
        if self.backend == "s3":
            csv_buffer = df.to_csv(index=False)
            self.s3.put_object(
                Bucket=self.bucket, Key=file_path, Body=csv_buffer
            )
            return f"s3://{self.bucket}/{file_path}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False)
        return file_path

    def write_text(self, content: str, file_path: str) -> str:
        if self.backend == "s3":
            self.s3.put_object(
                Bucket=self.bucket, Key=file_path, Body=content
            )
            return f"s3://{self.bucket}/{file_path}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def write_json(self, content: str, file_path: str) -> str:
        return self.write_text(content, file_path)

    def list_files(self, directory: str, extension: str = ".csv") -> list:
        if self.backend == "s3":
            response = self.s3.list_objects_v2(
                Bucket=self.bucket, Prefix=directory
            )
            return [
                obj["Key"]
                for obj in response.get("Contents", [])
                if obj["Key"].endswith(extension)
            ]
        if not os.path.exists(directory):
            return []
        return [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.endswith(extension)
        ]


storage = StorageManager()
