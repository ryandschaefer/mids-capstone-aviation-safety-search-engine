import polars as pl
import os

# S3 path where ASRS is stored
S3_BUCKET = os.environ.get("S3_BUCKET")
S3_KEY = os.environ.get("S3_KEY")
S3_PATH = f"s3://{S3_BUCKET}/{S3_KEY}"

# Config to access s3
s3_config = {
    "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_S3"),
    "aws_secret_access_key": os.environ.get("AWS_SECRET_KEY_S3"),
    "aws_region": os.environ.get("AWS_REGION_S3"),
}

# Initial scan of data in s3
def scan_data() -> pl.LazyFrame:
    return pl.scan_parquet(S3_PATH, storage_options=s3_config)

# Load the first n records of data as a sample
async def get_sample_data(n: int = 15) -> pl.DataFrame:
    lf = scan_data()
    df = await lf \
        .head(n) \
        .collect_async(gevent=False)
    return df

# Get a set of records by id
async def get_records_by_id(ids: list) -> pl.DataFrame:
    lf = scan_data()
    df = await lf \
        .filter(pl.col("acn_num_ACN").is_in(ids)) \
        .collect_async(gevent=False)
    return df