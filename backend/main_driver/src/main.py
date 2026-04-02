from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import search, db
from src.models.db import init_db
import os

FRONTEND_URL = os.environ.get("FRONTEND_URL")

# Initialize app
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    init_db()


# Health endpoint to verify server is running
@app.get("/health")
async def health():
    return {
        "service": "main",
        "time": datetime.now()
    }


# Add CORS middleware to choose allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ FRONTEND_URL if FRONTEND_URL else "*" ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(search.router)
app.include_router(db.router)
