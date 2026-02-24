"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import calculate, snapshots, mills, export, trends
from .db.database import init_db

app = FastAPI(
    title="Sulfidity Predictor API",
    description="Kraft Mill Sulfidity Predictor - Calculation Engine & API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3005",
        "http://127.0.0.1:3005",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calculate.router)
app.include_router(snapshots.router)
app.include_router(mills.router)
app.include_router(export.router)
app.include_router(trends.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
