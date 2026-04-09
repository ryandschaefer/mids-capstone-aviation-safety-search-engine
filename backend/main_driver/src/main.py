from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import search, db
from src.models.db import init_connection, close_connection
from contextlib import asynccontextmanager

# FRONTEND_URL = os.environ.get("FRONTEND_URL")
FRONTEND_URL = "*"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_connection()
    
    yield
    
    await close_connection()

# Initialize app
app = FastAPI(lifespan=lifespan)

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
