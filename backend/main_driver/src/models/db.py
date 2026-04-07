import os
import asyncpg
import ssl
import asyncio
import polars as pl

pool = None

# Create a new asynchronous connection pool
async def init_connection():
    connection_config = {
        "host": os.environ.get("SQL_HOST"),
        "port": 5432,
        "database": os.environ.get("SQL_DATABASE"),
        "user": os.environ.get("SQL_USER"),
        "password": os.environ.get("SQL_PASSWORD"),
    }
    
    # Connect with ssl
    ssl_ctx = ssl.create_default_context(cafile='./global-bundle.pem')
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    ssl_ctx.check_hostname = True

    # Connection pool to run multiple queries at a time
    global pool
    pool = await asyncpg.create_pool(
        ssl=ssl_ctx,
        min_size=2,
        max_size=10,
        **connection_config
    )
    
# Close an asynchronous connection pool
async def close_connection():
    global pool
    pool.close()

# Run a single query with the connection pool
async def run_query(query) -> list[dict]:
    print(query)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        return [ dict(row) for row in rows ]
    
# Rretrieve one or more chunks for a document
async def get_doc_chunks(doc_id: str, chunk_ids: list[int]) -> list[dict]:
    if chunk_ids:
        query = f'''
            SELECT *
            FROM chunks
            WHERE doc_id = { doc_id }
                AND chunk_id IN ({ ", ".join([ str(id) for id in chunk_ids if id is not None ]) })
            ORDER BY chunk_id
        '''
    else:
        query = f'''
            SELECT *
            FROM chunks
            WHERE doc_id = { doc_id }
            ORDER BY chunk_id
        '''
    return await run_query(query)

# Retrieve all relevant chunks for a search
async def get_relevant_chunks(doc_ids: list[str], chunk_ids: list[list[int]]) -> pl.DataFrame:
    # Asynchronously run query to get all chunks
    queries = [ get_doc_chunks(d_id, c_ids) for d_id, c_ids in zip(doc_ids, chunk_ids) ]
    sql_outputs = await asyncio.gather(*queries)
    
    # Convert output to polars
    final_output = [ x for output in sql_outputs for x in output ]
    df = pl.DataFrame(final_output)
    
    # Group by doc id and create a list of chunk texts
    return df \
        .with_columns(pl.col("doc_id").cast(pl.String)) \
        .group_by("doc_id") \
        .agg(chunks = pl.col("text"))
        
# Retrieve narratives for a set of documents by id
async def get_narratives(doc_ids: list[str]) -> pl.DataFrame:
    formatted_ids = ", ".join([ str(id) for id in doc_ids if id is not None ])
    query = f'''
        SELECT *
        FROM narratives
        WHERE doc_id IN ({ formatted_ids })
    '''
    sql_output = await run_query(query)
    
    # Convert to polars
    return pl.DataFrame(sql_output) \
        .with_columns(pl.col("doc_id").cast(pl.String))
            