import polars as pl
import os
import src.schemas.search as schemas

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

# Get records that match the given metadata filters
async def get_metadata_filters(metadata_filters: dict[str, schemas.FilterInput] | None = None, only_ids: bool = True) -> pl.DataFrame | None:
    if metadata_filters:
        lf = scan_data()
        
        # Apply the filters for each column
        for col, filters in metadata_filters.items():
            # Convert all constraints to a polars expression
            constraint_expressions: list[pl.Expr] = []
            for constraint in filters.constraints:
                match constraint.matchMode:
                    case "contains":
                        constraint_expressions.append(pl.col(col).str.contains(str(constraint.value), literal=True))
                    case "notContains":
                        constraint_expressions.append(pl.col(col).str.contains(str(constraint.value), literal=True).not_())
                    case "startsWith":
                        constraint_expressions.append(pl.col(col).str.starts_with(str(constraint.value)))
                    case "endsWith":
                        constraint_expressions.append(pl.col(col).str.ends_with(str(constraint.value)))
                    case "equals":
                        constraint_expressions.append(pl.col(col) == constraint.value)
                    case "notEquals":
                        constraint_expressions.append(pl.col(col) != constraint.value)
            
            # Move on if no expressions for this column
            if not constraint_expressions:
                continue
            
            # Create expression with all filters for this column
            col_expression = constraint_expressions[0]
            if filters.operator.lower() == "and":
                for expr in constraint_expressions[1:]:
                    col_expression = col_expression & expr
            else:
                for expr in constraint_expressions[1:]:
                    col_expression = col_expression | expr
                    
            # Apply filters to data
            lf = lf.filter(col_expression)
            
        # Optionally only return ids of relevant reports
        if only_ids:
            lf = lf.select("acn_num_ACN")
            
        # Collect filtered data
        df = await lf.collect_async(gevent=False)
        
        return df
    else:
        return None