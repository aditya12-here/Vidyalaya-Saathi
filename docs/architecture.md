# Vidyalaya Saathi Architecture

## Core Philosophy
Vidyalaya Saathi separates the role of AI (Data Gathering & Perception) from deterministic business logic (Diagnosis & Prioritization).

1. **DATA** (Student FLN, Attendance, Teacher Workload, Infrastructure Specs)
2. **AI ANALYSIS** (Vision AI extracting issues from images)
3. **STRUCTURED EVIDENCE** (Both paths end up safely stored in PostgreSQL)
4. **VIDYALAYA SAATHI LOGIC** (Determining the severity and priority of gathered evidence)
5. **BUDGET OPTIMIZATION** (Selecting highest ROI interventions based on deterministic calculations)

## Folder Structure
- `/frontend`: React/Next logic. Communicates exclusively with our backend.
- `/backend`: FastAPI Python server. Holds the single integration point to the Vision AI model.
- `/database`: Migration scripts (`.sql`) modeling the relational ties between Schools, Evidence, Images, and Problems.
- `/docs`: This directory.

## Databases & Relationships
A `School` acts as the root node. Attached to a school are:
- `student_learning_data`
- `student_attendance`
- `teacher_data`
- `infrastructure_data`
- `school_images`
- `problems` (A many-to-many relationship links problems back to images via `problem_evidence`, allowing AI deduplication without losing original trace evidence).

## AI Constraints
- AI MUST NOT calculate final budgets or priorities.
- AI must explicitly document `confidence`, distinguish `observation` from `inference`, and flag `requires_inspection`.
