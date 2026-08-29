from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.images import router as images_router
from app.api.problems import router as problems_router
from app.api.school_data import router as school_data_router
from app.database import engine
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase

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

app.include_router(images_router, prefix="/api/v1")
app.include_router(problems_router, prefix="/api/v1")
app.include_router(school_data_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Vidyalaya Saathi API"}
