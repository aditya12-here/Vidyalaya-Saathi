import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from app.database import engine
from app.models.image import Base, School
from app.models.school_data import Base as SchoolDataBase
from app.models.user import User, Role
from app.core.security import get_password_hash

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SchoolDataBase.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SchoolDataBase.metadata.drop_all)
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_auth_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a test school
        await ac.post("/api/v1/school-data/schools", json={
            "school_id": "AUTH-SCH-1",
            "name": "Auth Test School"
        })

        # Seed admin directly
        from app.database import async_session
        async with async_session() as session:
            admin = User(
                email="admin@test.gov.in",
                hashed_password=get_password_hash("password123"),
                role=Role.DISTRICT_OFFICER,
                is_global=True
            )
            session.add(admin)
            await session.commit()

        # 1. Login as District Officer
        login_res = await ac.post("/api/v1/auth/token", data={
            "username": "admin@test.gov.in",
            "password": "password123"
        })
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["role"] == "DISTRICT_OFFICER"
        admin_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Get /auth/me
        me_res = await ac.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "admin@test.gov.in"
        assert me_res.json()["role"] == "DISTRICT_OFFICER"

        # 3. Invite a School Management user
        invite_res = await ac.post("/api/v1/auth/invite", headers=headers, json={
            "email": "principal@school.edu",
            "password": "principal123",
            "role": "SCHOOL_MANAGEMENT",
            "school_id": "AUTH-SCH-1"
        })
        assert invite_res.status_code == 200
        assert invite_res.json()["role"] == "SCHOOL_MANAGEMENT"
        assert invite_res.json()["school_id"] == "AUTH-SCH-1"

        # 4. Login as School Management user
        sm_login = await ac.post("/api/v1/auth/token", data={
            "username": "principal@school.edu",
            "password": "principal123"
        })
        assert sm_login.status_code == 200
        sm_token = sm_login.json()["access_token"]
        sm_headers = {"Authorization": f"Bearer {sm_token}"}

        # School management should NOT be able to invite users (requires DISTRICT_OFFICER)
        failed_invite = await ac.post("/api/v1/auth/invite", headers=sm_headers, json={
            "email": "another@school.edu",
            "password": "password123",
            "role": "SURVEYOR"
        })
        assert failed_invite.status_code == 403

        # 5. Community Signup
        comm_signup = await ac.post("/api/v1/auth/signup/community", json={
            "email": "student@test.com",
            "password": "studentpassword123",
            "school_id": "AUTH-SCH-1",
            "community_id_number": "STU-9901"
        })
        assert comm_signup.status_code == 200
        assert comm_signup.json()["role"] == "COMMUNITY"
