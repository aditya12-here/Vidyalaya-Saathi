# backend/tests/test_explorer.py
#
# Follows the same fixture pattern as the other test files. Copy as-is into
# backend/tests/.

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.database import engine
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase
from app.models import prioritization as _prioritization_models  # noqa: F401
from app.models import budget as _budget_models  # noqa: F401
from main import app  # must come after the app.models.* imports — see main.py's note


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
async def test_list_schools_reflects_created_school():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/v1/school-data/schools", json={
            "school_id": "EXP-SCH-1", "name": "Explorer Test School", "total_enrollment": 150,
        })
        res = await ac.get("/api/v1/explorer/schools")
        assert res.status_code == 200
        data = res.json()
        ids = [s["school_id"] for s in data["schools"]]
        assert "EXP-SCH-1" in ids


@pytest.mark.asyncio
async def test_school_detail_includes_all_sections():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "EXP-SCH-2"
        await ac.post("/api/v1/school-data/schools", json={
            "school_id": school_id, "name": "Full Detail School", "total_enrollment": 100,
        })
        await ac.post(f"/api/v1/school-data/{school_id}/attendance", json={
            "attendance_percentage": 82, "students_enrolled": 100, "students_present": 82,
        })
        problem_res = await ac.post(f"/api/v1/problems/school/{school_id}/manual", json={
            "title": "Test problem", "category": "Furniture", "description": "desc",
            "human_priority": "Low", "human_status": "Confirmed",
        })
        problem_id = problem_res.json()["problem_id"]

        res = await ac.get(f"/api/v1/explorer/schools/{school_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["school"]["school_id"] == school_id
        assert len(data["school_data"]["attendance"]) == 1
        assert len(data["problems"]) == 1
        assert data["problems"][0]["problem_id"] == problem_id
        # No prioritization run yet -> latest_priority_score should be None
        assert data["problems"][0].get("latest_priority_score") is None
        assert data["latest_prioritization_run"] is None
        assert data["latest_budget_plan"] is None
        assert data["features_detected"]["prioritization_engine"] is True
        assert data["features_detected"]["budget_engine"] is True


@pytest.mark.asyncio
async def test_school_detail_includes_priority_and_budget_after_running_them():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "EXP-SCH-3"
        await ac.post("/api/v1/school-data/schools", json={
            "school_id": school_id, "name": "Full Pipeline School", "total_enrollment": 100,
        })
        await ac.post(f"/api/v1/problems/school/{school_id}/manual", json={
            "title": "Test problem", "category": "Furniture", "description": "desc",
            "human_priority": "Low", "human_status": "Confirmed",
        })
        await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        await ac.post(f"/api/v1/budget/school/{school_id}/plan", json={"budget_ceiling": 500000})

        res = await ac.get(f"/api/v1/explorer/schools/{school_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["problems"][0]["latest_priority_score"] is not None
        assert data["latest_prioritization_run"] is not None
        assert data["latest_budget_plan"] is not None
        assert len(data["latest_budget_plan"]["allocations"]) == 1


@pytest.mark.asyncio
async def test_unknown_school_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/explorer/schools/DOES-NOT-EXIST")
        assert res.status_code == 404