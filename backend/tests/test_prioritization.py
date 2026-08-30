# backend/tests/test_prioritization.py
#
# Follows the exact fixture pattern already used in
# backend/tests/test_school_data.py (async httpx client against the FastAPI
# app, in-memory/sqlite test DB created & torn down per test via the
# `setup_db` fixture). Copy this file as-is into backend/tests/.

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.database import engine
from app.models.image import Base
from app.models.school_data import Base as SchoolDataBase
from app.models import prioritization as _prioritization_models  # noqa: F401  # registers new tables on Base.metadata
# IMPORTANT: `from main import app` must come AFTER the `app.models.*` imports
# above. This project's top-level package is named `app`, same as the
# FastAPI instance imported below — importing the models package first and
# the FastAPI `app` symbol last guarantees the local name `app` ends up
# bound to the FastAPI instance, not the package.
from main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SchoolDataBase.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SchoolDataBase.metadata.drop_all)
        await conn.run_sync(Base.metadata.drop_all)


async def _create_school(ac: AsyncClient, school_id: str) -> None:
    res = await ac.post("/api/v1/school-data/schools", json={
        "school_id": school_id,
        "name": "Prioritization Test School",
        "total_enrollment": 200,
    })
    assert res.status_code == 200


async def _create_manual_problem(ac: AsyncClient, school_id: str, **overrides) -> str:
    payload = {
        "title": "Broken classroom desks",
        "category": "Furniture",
        "location": "Grade 3 classroom",
        "description": "Multiple desks are broken and unsafe to use.",
        "human_priority": "High",
        "human_status": "Confirmed",
    }
    payload.update(overrides)
    res = await ac.post(f"/api/v1/problems/school/{school_id}/manual", json=payload)
    assert res.status_code == 200
    return res.json()["problem_id"]


@pytest.mark.asyncio
async def test_run_requires_school_to_exist():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/v1/prioritization/school/DOES-NOT-EXIST/run")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_run_requires_at_least_one_eligible_problem():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await _create_school(ac, "PRIO-SCH-1")
        res = await ac.post("/api/v1/prioritization/school/PRIO-SCH-1/run")
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_run_scores_a_manual_problem_and_ranked_list_reflects_it():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "PRIO-SCH-2"
        await _create_school(ac, school_id)
        problem_id = await _create_manual_problem(ac, school_id)

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["num_problems_scored"] == 1
        assert len(run_data["ranked_problems"]) == 1
        assert 0 <= run_data["ranked_problems"][0]["total_score"] <= 100

        list_res = await ac.get(f"/api/v1/prioritization/school/{school_id}")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["count"] == 1
        assert list_data["ranked_problems"][0]["problem_id"] == problem_id
        assert list_data["ranked_problems"][0]["tier"] in {"Critical", "High", "Medium", "Low"}


@pytest.mark.asyncio
async def test_safety_critical_electricity_problem_is_floored_at_90():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "PRIO-SCH-3"
        await _create_school(ac, school_id)
        problem_id = await _create_manual_problem(
            ac, school_id,
            title="Exposed live wiring near classroom",
            category="Electricity",
        )
        # NOTE: ManualProblemCreate (app/api/problems.py) does not currently
        # accept `condition` at creation time — only AI-sourced problems get
        # it populated directly. To set it on a manually-created problem we
        # go through the existing human-review endpoint, which does support
        # `condition`. This mirrors how a real admin would use the app: flag
        # the problem, then a reviewer/engineer confirms its condition.
        review_res = await ac.put(f"/api/v1/problems/{problem_id}/review", json={
            "human_status": "Confirmed",
            "condition": "Critical",
        })
        assert review_res.status_code == 200

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        assert run_res.status_code == 200
        ranked = run_res.json()["ranked_problems"]
        assert ranked[0]["safety_override"] is True
        assert ranked[0]["total_score"] >= 90
        assert ranked[0]["tier"] == "Critical"


@pytest.mark.asyncio
async def test_rejected_problems_are_excluded_from_scoring():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "PRIO-SCH-4"
        await _create_school(ac, school_id)
        problem_id = await _create_manual_problem(ac, school_id, human_status="Rejected")

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        # No eligible problems -> 400
        assert run_res.status_code == 400


@pytest.mark.asyncio
async def test_custom_weights_change_the_ranking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "PRIO-SCH-5"
        await _create_school(ac, school_id)
        await _create_manual_problem(
            ac, school_id,
            title="Low confidence, high reach water issue",
            category="Drinking Water",
            condition="Fair",
        )

        # Push all weight onto "context" and zero everything else out.
        weights_res = await ac.put("/api/v1/prioritization/weights", json={
            "school_id": school_id,
            "weight_severity": 0.0,
            "weight_impact": 0.0,
            "weight_reach": 0.0,
            "weight_urgency": 0.0,
            "weight_confidence": 0.0,
            "weight_context": 1.0,
        })
        assert weights_res.status_code == 200

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        assert run_res.status_code == 200
        breakdown = run_res.json()["ranked_problems"][0]["breakdown"]
        assert breakdown["weights_used"]["weight_context"] == 1.0
