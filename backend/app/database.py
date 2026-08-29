from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# We need an async postgres URL. 
# For testing locally, replace with your DB URL or rely on env var.
# Example: postgresql+asyncpg://user:pass@localhost:5432/vidyalaya
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db") 
# Note: Since the prompt specified PostgreSQL but didn't provide a DB, 
# I will structure this to allow easy swapping to asyncpg via DATABASE_URL,
# but fallback to sqlite just so it can run if no DB is provided.
# Actually, the requirements specify asyncpg and sqlalchemy. 
# Let's assume the user will set DATABASE_URL appropriately. 
# For safety, if it's not set, we'll raise an error or use a dummy for now.

if "sqlite" in SQLALCHEMY_DATABASE_URL:
     engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
     engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        yield session
