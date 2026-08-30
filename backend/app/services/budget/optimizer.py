# backend/app/services/budget/optimizer.py
#
# The actual combinatorial optimization: given a set of (problem, cost,
# priority_score) items and a budget, select the subset maximizing total
# priority score without exceeding the budget. This is the 0/1 knapsack
# problem, solved exactly via dynamic programming for realistic problem
# counts. Pure functions only — no DB access — for easy unit testing.

from dataclasses import dataclass
from typing import List, Dict, Any

# Safety cap on the DP table size (items x discretized_budget_units). A
# single school's open problem list is realistically in the dozens, and
# with the default granularity (~1% of budget) `units` is ~100, so this cap
# (2 million cells) is generous headroom before we'd ever need the fallback.
MAX_DP_CELLS = 2_000_000


@dataclass
class KnapsackItem:
    problem_id: str
    cost: float
    score: float


@dataclass
class KnapsackResult:
    selected: List[KnapsackItem]
    unselected: List[KnapsackItem]
    total_cost: float
    total_score: float
    method: str  # 'exact_dp' or 'greedy_fallback'


def solve_knapsack(items: List[KnapsackItem], budget: float, granularity: float) -> KnapsackResult:
    """
    Exact 0/1 knapsack via DP, discretizing cost into integer units of
    `granularity`. Falls back to a greedy score-per-cost heuristic (still
    respecting the 0/1 constraint — no fractional selection) only if the
    DP table would exceed MAX_DP_CELLS, in which case `method` in the
    result is 'greedy_fallback' so callers/UI can be honest about it.
    """
    if not items or budget <= 0:
        return KnapsackResult(selected=[], unselected=list(items), total_cost=0.0, total_score=0.0, method="exact_dp")

    granularity = max(granularity, 0.01)
    units = max(int(budget // granularity), 0)

    if units == 0:
        return KnapsackResult(selected=[], unselected=list(items), total_cost=0.0, total_score=0.0, method="exact_dp")

    n = len(items)

    if n * (units + 1) > MAX_DP_CELLS:
        return _greedy_fallback(items, budget)

    weights = []
    for item in items:
        w = int(round(item.cost / granularity))
        if item.cost > 0 and w == 0:
            w = 1  # never let a non-trivial cost round down to "free"
        weights.append(w)

    # dp[i][w] = best achievable score using the first i items with budget w units
    dp: List[List[float]] = [[0.0] * (units + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w_i = weights[i - 1]
        s_i = items[i - 1].score
        row_prev = dp[i - 1]
        row_cur = dp[i]
        for w in range(units + 1):
            if w_i <= w:
                row_cur[w] = max(row_prev[w], row_prev[w - w_i] + s_i)
            else:
                row_cur[w] = row_prev[w]

    # Backtrack to find which items were selected
    selected_indices = set()
    w = units
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected_indices.add(i - 1)
            w -= weights[i - 1]

    selected = [items[i] for i in sorted(selected_indices)]
    unselected = [items[i] for i in range(n) if i not in selected_indices]

    return KnapsackResult(
        selected=selected,
        unselected=unselected,
        total_cost=round(sum(i.cost for i in selected), 2),
        total_score=round(sum(i.score for i in selected), 2),
        method="exact_dp",
    )


def _greedy_fallback(items: List[KnapsackItem], budget: float) -> KnapsackResult:
    """
    Used only when the item count is too large for the exact DP to be
    practical. Sorts by score-per-currency-unit and greedily fills the
    budget — a well-known good approximation for 0/1 knapsack, but not
    guaranteed optimal (unlike the DP path). Documented in KnapsackResult
    .method so this is never silently presented as exact.
    """
    ranked = sorted(items, key=lambda it: (it.score / it.cost if it.cost > 0 else 0), reverse=True)
    selected, unselected = [], []
    remaining = budget
    for item in ranked:
        if item.cost <= remaining:
            selected.append(item)
            remaining -= item.cost
        else:
            unselected.append(item)

    return KnapsackResult(
        selected=selected,
        unselected=unselected,
        total_cost=round(sum(i.cost for i in selected), 2),
        total_score=round(sum(i.score for i in selected), 2),
        method="greedy_fallback",
    )