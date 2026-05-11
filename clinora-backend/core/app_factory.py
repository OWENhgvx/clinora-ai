"""
app_factory.py — FastAPI application setup for Clinora.
"""
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db import init_db
from rag import get_collection_size


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Return a concise, user-friendly 422 error instead of the raw Pydantic dump."""
    errors = []
    for e in exc.errors():
        field = " → ".join(str(x) for x in e["loc"] if x != "body")
        errors.append(f"{field}: {e['msg']}" if field else e["msg"])
    return JSONResponse(status_code=422, content={"detail": "; ".join(errors)})


def _print_rag_status() -> None:
    rag_size = get_collection_size()
    print(f"\n{'='*50}")
    print("  Clinora RAG Knowledge Base")
    print(f"  Documents loaded: {rag_size}")
    if rag_size > 0:
        print("  Status: ✅ Ready")
    else:
        print("  Status: ⚠️  Empty")
    print("  ─────────────────────────────────────")
    print("  Quick commands:")
    print("    python ingest.py              # full ingest (78 terms, ~1000+ articles)")
    print("    python ingest.py --status     # check DB size")
    print("    AUTO_INGEST=1 uvicorn main:app  # auto-ingest on startup")
    print(f"{'='*50}\n")


def _maybe_auto_ingest() -> None:
    # set AUTO_INGEST=1 to pull PubMed articles automatically on startup
    if os.getenv("AUTO_INGEST", "").strip() in ("1", "true", "yes"):
        from ingest import run_ingestion, DEFAULT_TERMS as _INGEST_TERMS

        print("🔄 AUTO_INGEST enabled — starting PubMed ingestion...")
        run_ingestion(_INGEST_TERMS, per_term=15)
        print()


def create_app() -> FastAPI:
    app = FastAPI(title="Clinora API", version="4.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    init_db()
    _print_rag_status()
    _maybe_auto_ingest()
    return app
