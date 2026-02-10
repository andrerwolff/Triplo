import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory (parent of app/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import projects, constants, pipeline_audit
from app.ingestion.router import router as ingestion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


# CORS: dev origins + production frontend URL from env (e.g. https://your-app.vercel.app)
_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://triplosbmtl.vercel.app",  # production frontend
]
if os.getenv("CORS_ORIGINS"):
    _cors_origins.extend(o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip())

app = FastAPI(
    title="Sbmtl API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(constants.router, prefix="/api", tags=["constants"])
app.include_router(pipeline_audit.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(ingestion_router, prefix="/api/ingestion", tags=["ingestion"])


@app.get("/health")
def health():
    return {"status": "ok"}
