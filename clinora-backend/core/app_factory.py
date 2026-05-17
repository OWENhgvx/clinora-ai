"""
app_factory.py — FastAPI application setup for Clinora.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import init_db
from app.rag import get_collection_size


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
    print(f"{'='*50}\n")


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
    return app
