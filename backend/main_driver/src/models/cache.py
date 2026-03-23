import boto3
import json
import time
import os
from datetime import datetime
import hashlib
import src.schemas.search as schemas

client_config = {
    "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_S3"),
    "aws_secret_access_key": os.environ.get("AWS_SECRET_KEY_S3"),
    "region_name": os.environ.get("AWS_REGION_S3"),
}
dynamodb = boto3.resource("dynamodb", **client_config)

TABLE_NAME = os.environ.get("CACHE_TABLE")
table = dynamodb.Table(TABLE_NAME)

# Create a cache key from a json object
def create_key(params: dict) -> str:
    params_sorted = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_sorted.encode()).hexdigest()

# Delete a key from the cache
def delete_cache(key: str) -> None:
    """Explicitly remove an entry from the cache."""
    table.delete_item(Key={'cache_key': key})

# Check if a key exists in the cache
def key_exists(key: str) -> bool:
    response = table.get_item(
        Key={'cache_key': key},
        ProjectionExpression='cache_key, #t',
        ExpressionAttributeNames={'#t': 'ttl'},
    )
    item = response.get('Item')

    # Key does not exist
    if not item:
        return False
    
    # Key is expired (delete the key)
    if int(item.get('ttl', 0)) < int(time.time()):
        delete_cache(key)
        return False

    return True

# Retrieve key from cache (None if key does not exist or is expired)
def get_cache(key: str) -> None | list[schemas.SearchResult]:
    """Read a value from the cache. Returns None on miss or expiry."""
    response = table.get_item(Key={'cache_key': key})
    item = response.get('Item')

    if not item:
        print(f"Cache miss: '{key}'")
        return None

    # Guard against items that haven't been reaped by DynamoDB yet
    if int(item.get('ttl', 0)) < int(time.time()):
        print(f"Cache expired: '{key}'")
        delete_cache(key)
        return None

    print(f"Cache hit: '{key}'")
    return json.loads(item['value'])

# Write a new key to the cache
def set_cache(key: str, value: list[schemas.SearchResult], ttl_seconds: int = 86400) -> None:
    """Write a value to the cache with an optional TTL (default: 24 hours)."""
    expiry = int(time.time()) + ttl_seconds

    table.put_item(
        Item={
            'cache_key': key,
            'value': json.dumps(value),   # Serialize so any type is supported
            'ttl': expiry,
            'created_at': datetime.now().isoformat(),
        }
    )
    print(f"Cached '{key}' (expires in {ttl_seconds}s)")