# backend/main.py
#
# FULL REPLACEMENT FILE — supersedes the main.py from the Budget Engine
# feature. Adds the read-only Data Explorer router on top of everything
# already there (Prioritization Engine + Budget Engine). Use this wholesale.
#
# Same import-order rule as before: `from app.models import X as _alias`,
# never `import app.models.X`, so the bare name `app` is never rebound away
# from the FastAPI instance. The explorer router itself needs no model
# import here since app/api/explorer.py imports its own dependencies
# directly and doesn't define any new tables.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.images import router as images_router
from app.api.problems import router as problems_router
from app.api.school_data import router as school_data_router
from app.api.prioritization import router as prioritization_router
from app.api.budget import router as budget_router
from app.api.explorer import router as explorer_router  # >>> ADDED
from app.api.auth import router as auth_router            # >>> ADDED
from app.database import engine
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase
from app.models import prioritization as _prioritization_models  # noqa: F401
from app.models import budget as _budget_models  # noqa: F401
from app.models import user as _user_models # noqa: F401

app = FastAPI(title="Vidyalaya Saathi - Diagnostic Engine API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SchoolDataBase.metadata.create_all)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(images_router, prefix="/api/v1")
app.include_router(problems_router, prefix="/api/v1")
app.include_router(school_data_router, prefix="/api/v1")
app.include_router(prioritization_router, prefix="/api/v1")
app.include_router(budget_router, prefix="/api/v1")
app.include_router(explorer_router, prefix="/api/v1")  # >>> ADDED

@app.get("/")
def read_root():
    return {"message": "Welcome to Vidyalaya Saathi API"}