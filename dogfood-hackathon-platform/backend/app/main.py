from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
<<<<<<< HEAD
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import SessionLocal, init_db
from .routers import admin, auth, judge, participant, results
=======
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database import SessionLocal, init_db
from .routers import admin, auth, export, judge, participant, results
>>>>>>> 97e6bd8 (Initial hackathon submission)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_demo_data:
        from .seed import seed

        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(
    title="Dogfood Hackathon Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/api/health", tags=["health"])
def health():
<<<<<<< HEAD
    return {"status": "ok"}


for module in (auth, participant, judge, admin, results):
=======
    """Liveness plus a real read from the users table, so the Docker healthcheck
    only reports healthy when the API can actually reach SQLite."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "detail": "Database unavailable."})
    return {"status": "ok"}


for module in (auth, participant, judge, admin, export, results):
>>>>>>> 97e6bd8 (Initial hackathon submission)
    app.include_router(module.router)


# ------------------------------------------------------------------ frontend
# In Docker the built React app lives in STATIC_DIR and is served from here,
# so the whole product is one container on one port.
static_dir = settings.static_dir
index_file = static_dir / "index.html"

if (static_dir / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not found.")
    if not index_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="Frontend not built. Run the app with Docker, or start Vite in /frontend.",
        )
    candidate = (static_dir / full_path).resolve()
    # Serve real files (favicon etc.) but never anything outside static_dir.
    if full_path and candidate.is_file() and candidate.is_relative_to(static_dir):
        return FileResponse(candidate)
    return FileResponse(index_file)
