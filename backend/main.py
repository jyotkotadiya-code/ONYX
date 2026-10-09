from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router as api_router
from backend.auth.auth_handler import init_db_and_defaults
from backend.core.config import BASE_DIR, settings
from backend.core.logging_config import app_logger
from backend.embeddings.embedding_service import embedding_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (OFFLINE_MODE={settings.OFFLINE_MODE})")
    init_db_and_defaults()
    # Pre-warm embedding service
    embedding_service.load_model()
    yield
    app_logger.info("Shutting down Local Multimodal RAG backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="100% Local & Private Multimodal RAG Knowledge System",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve built frontend static assets if present
frontend_dist = BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        norm = full_path.lstrip("/").lower()
        if norm.startswith(("uploads/", "secure_uploads/", "data/")):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Direct file access is forbidden.")
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend build not found."}
