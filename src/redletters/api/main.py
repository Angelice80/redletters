"""FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from redletters.api.routes import router

app = FastAPI(
    title="Red Letters Source Reader",
    description="Multi-reading Greek NT tool with interpretive receipts",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Red Letters Source Reader",
        "version": "0.1.0",
        "docs": "/docs",
        "api": "/api/v1",
    }
