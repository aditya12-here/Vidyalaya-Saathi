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
from app.api.explorer import router as explorer_router  
from app.api.auth import router as auth_router      
from app.api.cbse_routes import router as cbse_router
from contextlib import asynccontextmanager
from app.database import engine, async_session
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase
from app.models import prioritization as _prioritization_models  # noqa: F401
from app.models import budget as _budget_models  # noqa: F401
from app.models.user import User, Role  # noqa: F401
from app.models import cbse_affiliation as _cbse_affiliation_models  # noqa: F401
from app.core.security import get_password_hash
from sqlalchemy.future import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create all database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SchoolDataBase.metadata.create_all)
    
    # 2. Auto-seed default District Officer admin if not exists
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == "admin@vidyalaya.gov.in"))
        admin = result.scalars().first()
        if not admin:
            admin = User(
                email="admin@vidyalaya.gov.in",
                hashed_password=get_password_hash("admin123"),
                role=Role.DISTRICT_OFFICER,
                is_global=True
            )
            session.add(admin)
            await session.commit()
    yield

app = FastAPI(title="Vidyalaya Saathi - Diagnostic Engine API", lifespan=lifespan)

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

app.include_router(auth_router, prefix="/api/v1")
app.include_router(images_router, prefix="/api/v1")
app.include_router(problems_router, prefix="/api/v1")
app.include_router(school_data_router, prefix="/api/v1")
app.include_router(prioritization_router, prefix="/api/v1")
app.include_router(budget_router, prefix="/api/v1")
app.include_router(explorer_router, prefix="/api/v1")  # >>> ADDED
app.include_router(cbse_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Vidyalaya Saathi API"}
