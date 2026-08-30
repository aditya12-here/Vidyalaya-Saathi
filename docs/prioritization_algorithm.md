# Prioritization Algorithm — Methodology

## Why this exists

`docs/architecture.md` draws a hard line: AI perceives, it does not decide. Step 4 of
the pipeline ("VIDYALAYA SAATHI LOGIC — determining severity and priority") was
previously unimplemented. This document describes the deterministic engine that fills
that gap.

## Method family

This is a **weighted multi-criteria decision analysis (MCDA)** model — the same family
of scoring approach used in real-world infrastructure triage and public-health resource
allocation: decompose "how important is this?" into independent, measurable criteria,
score each on a common [0,1] scale, combine with explicit weights, and keep every
intermediate number so the final rank is auditable rather than a black box.

## The six criteria

| Criterion  | Symbol       | What it measures                                                                         | Primary inputs                                            |
| ---------- | ------------ | ---------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Severity   | S_severity   | How bad is the assessed condition?                                                       | `severity_estimate`, `condition`                          |
| Impact     | S_impact     | How much does it hurt students'/teachers' ability to function?                           | `student_impact`, `teacher_impact`                        |
| Reach      | S_reach      | What fraction of the school population is affected?                                      | `scale_estimate`, `category`, school `total_enrollment`   |
| Urgency    | S_urgency    | Does it need physical inspection? Has it sat unresolved?                                 | `requires_inspection`, `created_at`, `lifecycle_status`   |
| Confidence | S_confidence | How much do we trust this evidence?                                                      | `source`, `confidence`, `human_status`, `human_override`  |
| Context    | S_context    | Does the school's own data corroborate this category of problem is actually biting here? | `StudentAttendance`, `StudentLearningData`, `TeacherData` |

Each is computed in `[0, 1]`. Full formulas live in
`backend/app/services/prioritization/scoring.py` with inline comments; summarized below.

### Severity

`0.7 × severity_map(severity_estimate) + 0.3 × condition_map(condition)`
Severity map: Critical=1.0, High=0.75, Medium=0.5, Low=0.25, Unknown=0.35.
Condition map: Critical=1.0, Poor=0.8, Fair=0.5, Good=0.1, Unknown=0.4.
Two related-but-distinct AI fields are blended so a single mislabeled field doesn't
dominate the score.

### Impact

`0.6 × student_impact_level + 0.4 × teacher_impact_level + breadth_bonus`
Level map: High=1.0, Medium=0.6, Low=0.3, Unknown=0.4. Student impact is weighted
higher because the product's stated mission is student outcomes. `breadth_bonus` adds
up to +0.15 for problems that touch more distinct impact `areas` (safety, hygiene,
learning_environment, etc.) — a problem hurting four different areas is worse than one
hurting a single narrow area, even at the same "level."

### Reach

If `scale_estimate` contains a parseable headcount (e.g. "Approximately 4 damaged
desks" → 4) and the school's `total_enrollment` is known, reach uses
`0.7 × (headcount / enrollment) + 0.3 × category_baseline`. Otherwise it falls back
fully to a **category baseline** — e.g. `Drinking Water` and `Toilets` default to
affecting most/all of the school (0.9–1.0), while `Furniture` defaults to a narrow
subset (0.2), because a broken water point stops the whole school, while a few broken
desks affect one classroom.

### Urgency

`0.6 × inspection_component + 0.4 × staleness_component`. `inspection_component` is
1.0 if `requires_inspection` is true (AI/human flagged it as needing physical
verification), else a 0.3 baseline. `staleness_component` grows with days-open on a
saturating curve (`1 − e^(−days/30)`) — an unresolved problem accrues urgency pressure
the longer it sits untouched, but with diminishing returns, so month-old and year-old
untouched problems aren't wildly different. Resolved/closed problems score 0 urgency.

### Confidence

AI-sourced problems start from the model's own `confidence` (0–1), then get scaled
down to 60% if a human hasn't confirmed them yet (`human_status = 'Pending Review'`) —
this deliberately prevents unverified AI hallucinations from dominating a ranked list
before a human has looked at them, while still surfacing them for review. Human-entered
problems (`ADMINISTRATOR`/`ENGINEER` source) start from a high trust baseline (0.85,
or 1.0 once confirmed) since a person directly observed and typed it. An explicit
human edit (`human_override = true`) adds a small +0.05 trust bump.

### Context (the cross-module correlation signal)

This is what makes the engine "diagnostic" instead of "sort by severity." It reads
aggregated signals from tables the AI/image pipeline never touches:

- **Attendance** (`StudentAttendance`): if average attendance is below 75%, problems in
  categories empirically linked to attendance — Toilets, Drinking Water,
  Boundary/School Premises, Road/Access to School — get a context boost. (Poor toilet
  facilities, particularly, are a well-documented driver of absenteeism.)
- **FLN/learning gaps** (`StudentLearningData`): if more than 40% of assessed students
  are below their expected level, Classroom/Furniture/School Building problems (the
  learning environment) get boosted — a crumbling classroom compounds an existing
  learning crisis.
- **Teacher shortage** (`TeacherData`): if vacancy ratio exceeds 15% or
  students-per-teacher exceeds 40, classroom/environment problems get a smaller boost,
  reflecting that an overstretched teaching staff can't compensate for infrastructure
  gaps the way a well-staffed school might.
- If none of these rules fire (either because the school's data genuinely looks fine, or
  because the school hasn't logged that data yet), context defaults to a **neutral 0.2**
  rather than 0 — a missing data-collection module shouldn't be read as "this problem is
  unimportant."

Each fired rule is recorded by name in the score's `breakdown.context_rules_fired` list,
so the UI can literally say _why_ a problem ranked where it did.

## Combining into a final score

```
total = 100 × ( 0.30·S_severity + 0.25·S_impact + 0.15·S_reach
              + 0.10·S_urgency  + 0.10·S_confidence + 0.10·S_context )
```

Weights are **not hardcoded in the sense of being unchangeable** — they're read from
the database (`prioritization_weight_configs`) at scoring time, resolved per-school with
a fallback to a global default, and can be updated live via
`PUT /api/v1/prioritization/weights`. This lets an administrator say "for this district,
weight reach and confidence more heavily than urgency" and immediately see the ranking
respond, without a code change or redeploy.

## Safety override

Independent of the weighted formula, any problem where:

- `condition == 'Critical'` **and** category is one of `Electricity`,
  `Boundary/School Premises`, `School Building`, `Drinking Water` (categories where
  "critical condition" plausibly means physical danger, not just disrepair), **or**
- `student_impact.level == 'High'` **and** `'safety'` appears among its impact `areas`

has its score floored at **90** and is flagged `safety_override: true` in the
breakdown. This exists because a purely additive weighted-sum model can, in principle,
let a genuinely dangerous issue slip down the list if it happens to score moderately on
a couple of dimensions (e.g. low reach because only one classroom is affected, or
lower confidence because the AI wasn't fully certain). Physical danger to children
should never be silently outranked by aggregate math.

## Tiers

`total_score ≥ 85` → **Critical**, `≥ 65` → **High**, `≥ 40` → **Medium**, else **Low**.
Tiers exist for the UI/filtering layer and for stakeholders who want a quick read
without parsing a numeric score.

## Auditability

Every run of the engine is versioned:

- `prioritization_runs` stores exactly which weights and which aggregated school
  context were used for that run.
- `problem_priority_scores` keeps history per problem — old scores aren't overwritten,
  just marked `is_latest = false` — so you can show how a problem's priority shifted
  after, say, new attendance data came in or an admin confirmed it.

## Explicitly out of scope for this engine (future work / the "Budget Engine")

This engine ranks problems by _importance_, not by _what to fund given a fixed budget_.
A follow-up **Budget Optimization Engine** (architecture doc step 5) is expected to take
this ranked list plus a per-intervention cost estimate and solve a constrained
selection problem (e.g. a knapsack-style ROI optimization: maximize total priority score
covered within a budget ceiling). That is intentionally a separate, second engine/service
that consumes this one's output — keeping "how important is this" and "what can we
afford to fix" as cleanly separated concerns, matching the project's own architectural
philosophy.
