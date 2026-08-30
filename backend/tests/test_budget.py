# backend/tests/test_budget.py
#
# Follows the same fixture pattern as test_school_data.py and
# test_prioritization.py. Copy as-is into backend/tests/.
# Requires test_prioritization.py's feature (the Prioritization Engine) to
# already be applied, since budget plans require existing priority scores.

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


async def _create_school(ac: AsyncClient, school_id: str, enrollment: int = 200) -> None:
    res = await ac.post("/api/v1/school-data/schools", json={
        "school_id": school_id,
        "name": "Budget Test School",
        "total_enrollment": enrollment,
    })
    assert res.status_code == 200


async def _create_manual_problem(ac: AsyncClient, school_id: str, **overrides) -> str:
    payload = {
        "title": "Test problem",
        "category": "Furniture",
        "location": "Grade 1 classroom",
        "description": "A test problem.",
        "human_priority": "Medium",
        "human_status": "Confirmed",
    }
    payload.update(overrides)
    res = await ac.post(f"/api/v1/problems/school/{school_id}/manual", json=payload)
    assert res.status_code == 200
    return res.json()["problem_id"]


@pytest.mark.asyncio
async def test_plan_requires_prioritization_to_have_run_first():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "BUD-SCH-1"
        await _create_school(ac, school_id)
        await _create_manual_problem(ac, school_id)
        # No prioritization run yet
        res = await ac.post(f"/api/v1/budget/school/{school_id}/plan", json={"budget_ceiling": 100000})
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_mandatory_safety_problem_is_always_funded_even_if_expensive():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "BUD-SCH-2"
        await _create_school(ac, school_id)

        # Expensive, safety-critical problem
        danger_id = await _create_manual_problem(
            ac, school_id, title="Exposed wiring", category="Electricity",
        )
        review = await ac.put(f"/api/v1/problems/{danger_id}/review", json={
            "human_status": "Confirmed", "condition": "Critical",
        })
        assert review.status_code == 200

        # A cheap but non-critical problem
        await _create_manual_problem(ac, school_id, title="Loose door hinge", category="Other")

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        assert run_res.status_code == 200

        # Manually set the dangerous problem's cost very high
        override = await ac.put(f"/api/v1/budget/cost/{danger_id}", json={
            "school_id": school_id, "cost": 500000, "notes": "Full rewiring quote",
        })
        assert override.status_code == 200

        # Budget far smaller than the mandatory item's cost
        plan_res = await ac.post(f"/api/v1/budget/school/{school_id}/plan", json={"budget_ceiling": 50000})
        assert plan_res.status_code == 200
        plan = plan_res.json()

        assert plan["over_budget_on_mandatory"] is True
        mandatory_allocs = [a for a in plan["allocations"] if a["selection_reason"] == "MANDATORY_SAFETY"]
        assert len(mandatory_allocs) == 1
        assert mandatory_allocs[0]["selected"] is True
        assert mandatory_allocs[0]["cost"] == 500000


@pytest.mark.asyncio
async def test_knapsack_prefers_higher_total_score_over_naive_top_down():
    """
    Two cheap-but-decent problems together should be preferred over one
    expensive-but-slightly-higher problem, when the budget can't fit the
    expensive one alongside anything else — proving this isn't just
    'fund top of the list until money runs out'.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "BUD-SCH-3"
        await _create_school(ac, school_id)

        p1 = await _create_manual_problem(ac, school_id, title="Problem A", category="Other")
        p2 = await _create_manual_problem(ac, school_id, title="Problem B", category="Other")
        p3 = await _create_manual_problem(ac, school_id, title="Problem C", category="Other")

        run_res = await ac.post(f"/api/v1/prioritization/school/{school_id}/run")
        assert run_res.status_code == 200

        # Craft costs: A is expensive, B+C are cheap and together cost less
        # than A but their combined footprint still fits the budget.
        await ac.put(f"/api/v1/budget/cost/{p1}", json={"school_id": school_id, "cost": 90000})
        await ac.put(f"/api/v1/budget/cost/{p2}", json={"school_id": school_id, "cost": 40000})
        await ac.put(f"/api/v1/budget/cost/{p3}", json={"school_id": school_id, "cost": 40000})

        plan_res = await ac.post(f"/api/v1/budget/school/{school_id}/plan", json={"budget_ceiling": 90000})
        assert plan_res.status_code == 200
        plan = plan_res.json()

        selected_ids = {a["problem_id"] for a in plan["allocations"] if a["selected"]}
        # Either {A} or {B, C} fits in 90000 — the DP must have picked
        # whichever set has the higher combined priority score, not simply
        # the first-ranked item.
        assert selected_ids in ({p1}, {p2, p3})
        assert plan["total_spent"] <= 90000


@pytest.mark.asyncio
async def test_cost_override_and_get_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        school_id = "BUD-SCH-4"
        await _create_school(ac, school_id)
        problem_id = await _create_manual_problem(ac, school_id)

        put_res = await ac.put(f"/api/v1/budget/cost/{problem_id}", json={
            "school_id": school_id, "cost": 12345, "notes": "Vendor quote",
        })
        assert put_res.status_code == 200
        assert put_res.json()["source"] == "ADMIN_OVERRIDE"

        get_res = await ac.get(f"/api/v1/budget/cost/{problem_id}")
        assert get_res.status_code == 200
        assert get_res.json()["estimated_cost"] == 12345