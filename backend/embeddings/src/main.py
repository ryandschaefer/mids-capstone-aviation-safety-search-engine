from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import search
from src.controllers.search import get_qdrant_status
import os

MAIN_DRIVER_URL = os.environ.get("MAIN_DRIVER_URL")

# Initialize app
app = FastAPI()

# Health endpoint to verify server is running
@app.get("/health")
async def health():
    get_qdrant_status()
    return {
        "service": "embeddings",
        "time": datetime.now()
    }

# Add CORS middleware to choose allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ MAIN_DRIVER_URL if MAIN_DRIVER_URL else "*" ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(search.router)