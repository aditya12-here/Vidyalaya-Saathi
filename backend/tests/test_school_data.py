import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from app.database import engine
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase

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
async def test_create_school():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/school-data/schools", json={
            "school_id": "TEST-SCH-1",
            "name": "Test Primary School",
            "school_code": "SCH-12345",
            "state": "Maharashtra",
            "district": "Pune",
            "school_type": "Primary",
            "grades_served": "1-5"
        })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Primary School"
    assert "school_id" in data
    
@pytest.mark.asyncio
async def test_invalid_fln_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_res = await ac.post("/api/v1/school-data/schools", json={"school_id": "TEST-SCH-2", "name": "FLN Test School"})
        school_id = school_res.json()["school_id"]
        
        response = await ac.post(f"/api/v1/school-data/{school_id}/learning", json={
            "grade": "5",
            "assessment_type": "READING",
            "competency": "Word reading",
            "students_assessed": -10,  # Invalid
            "students_at_level": -5    # Invalid
        })
    assert response.status_code == 422
