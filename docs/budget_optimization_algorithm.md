# Budget Optimization Algorithm — Methodology

## The question this answers

The Prioritization Engine (see `docs/prioritization_algorithm.md`) answers "how
important is this problem?" This engine answers a different, harder question:
**given a fixed budget, which specific problems should actually get funded?**

## Why not just fund the top-ranked problems until the money runs out?

That greedy approach ("sort by priority score, fund top-down") is intuitive but
provably suboptimal. Concrete example: with a ₹90,000 budget, one ₹90,000 problem
scoring 70 leaves zero budget for anything else. Two separate ₹40,000 problems scoring
45 each, funded together for ₹80,000, deliver a combined score of 90 — more total
impact, for less money, with ₹10,000 to spare. A naive top-down list would pick the
single ₹90,000 problem first (higher individual score) and never consider the pair.

This is the textbook **0/1 knapsack problem**: choose a subset of items, each with a
cost and a value, maximizing total value without exceeding a weight (here, budget)
limit, where each item is either fully taken or not taken at all (no partial funding
of a broken toilet block). It's solved here **exactly**, via dynamic programming, not
approximated — see `test_budget.py::test_knapsack_prefers_higher_total_score_over_naive_top_down`
for a test that specifically proves the engine picks the higher-value combination.

## Step 1 — Costs

Every problem needs an estimated repair/replacement cost before it can be optimized
over. `cost_estimator.py` provides a category-based heuristic default (e.g. a
Drinking Water problem defaults to a flat baseline; a Furniture problem scales with
the number of damaged items parsed from `scale_estimate`), adjusted by a condition
multiplier (a "Critical" instance of a category typically costs more to fully remediate
than a "Fair" one). These are placeholder defaults meant to be tuned per deployment —
an administrator can override any of them with a real vendor quote via
`PUT /api/v1/budget/cost/{problem_id}`, which is preserved with its own audit trail
(`source: ADMIN_OVERRIDE` vs `HEURISTIC`) the same way manual priority overrides are.

## Step 2 — Mandatory-first rule

Before any optimization happens, every problem the Prioritization Engine flagged with
`safety_override = true` (physical danger to students/staff) is funded unconditionally,
off the top of the budget. This is a deliberate departure from "pure" knapsack
optimization: a mathematically optimal solution might, in principle, decide a live
electrical hazard isn't worth its cost relative to funding five cheaper furniture
problems instead. That is not an acceptable trade-off for a tool making
recommendations about children's physical safety, so it's enforced as a hard
constraint rather than left to the objective function. If the mandatory items alone
exceed the available budget, the plan is flagged (`over_budget_on_mandatory: true`) so
an administrator sees immediately that the budget doesn't even cover life-safety
fixes — a signal that should be impossible to miss in the UI.

## Step 3 — Knapsack optimization on the remainder

Whatever budget is left after mandatory items is handed to `optimizer.py`, which
solves 0/1 knapsack exactly via dynamic programming:

```
dp[i][w] = best total priority score achievable using the first i problems
           with at most w budget-units to spend
```

Costs are discretized into integer units (default granularity: 1% of the budget
ceiling, minimum ₹100) because DP requires an integer weight axis; this is standard
practice for knapsack over continuous costs and keeps the DP table small (typically
under 200x200) even though the underlying costs are exact currency amounts. The
`granularity_used` is always recorded on the plan for transparency.

For unusually large problem lists (beyond realistic single-school scale), the engine
automatically falls back to a greedy score-per-rupee heuristic rather than letting the
DP table grow unbounded — and the plan honestly reports `optimization_method:
"greedy_fallback"` in that case rather than silently claiming exactness it didn't
achieve.

## Step 4 — Output

Every problem for the school ends up tagged with exactly one status:

- `MANDATORY_SAFETY` — funded, safety-critical, non-negotiable.
- `OPTIMIZED` — funded, selected by the knapsack solver as part of the best
  combination within the remaining budget.
- `NOT_SELECTED` — not funded this round; still visible, sorted by priority score, so
  an administrator can see exactly what a larger budget would buy next.

The plan also reports `coverage_pct` — the share of total available priority score
(across every open problem) actually addressed at this budget level — which is a
natural quantity to track over successive budget cycles ("we went from covering 40%
of total need to 65% this year").

## Relationship to the Prioritization Engine

This engine strictly consumes the Prioritization Engine's output (`ProblemPriorityScore`
rows) — it never re-derives severity, impact, or context itself. Running a new
prioritization run and then a new budget plan is how the two are meant to be chained:
prioritize, then budget against the current priorities. If school data changes
(attendance improves, a teacher vacancy is filled) and prioritization is re-run, the
next budget plan will reflect the updated scores automatically.
