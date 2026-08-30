import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session, engine
from app.models.user import User, Role
from app.core.security import get_password_hash
from app.models.image import Base

async def seed_admin():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        # Check if admin already exists
        from sqlalchemy.future import select
        result = await session.execute(select(User).where(User.email == "admin@vidyalaya.gov.in"))
        admin = result.scalars().first()
        
        if not admin:
            print("Creating default District Officer account...")
            admin = User(
                email="admin@vidyalaya.gov.in",
                hashed_password=get_password_hash("admin123"),
                role=Role.DISTRICT_OFFICER,
                is_global=True
            )
            session.add(admin)
            await session.commit()
            print("Admin account created successfully!")
        else:
            print("Admin account already exists.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
