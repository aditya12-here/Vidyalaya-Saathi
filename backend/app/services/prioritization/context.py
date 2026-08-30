# backend/app/services/prioritization/context.py
#
# Builds a `SchoolContext` — an aggregated snapshot of a school's own data
# (attendance, FLN/learning gaps, teacher shortage) pulled from tables the
# team already built (app/models/school_data.py) but that nothing else in
# the codebase currently reads from. This is what lets the S_context
# sub-score in scoring.py say "this Toilets problem should rank higher here
# specifically, because this school's attendance data is already bad."
#
# Read-only: this module never writes to the DB.

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.image import School
from app.models.school_data import StudentAttendance, StudentLearningData, TeacherData

# Thresholds used to derive boolean flags from the raw aggregates below.
# Kept as module-level constants (not magic numbers buried in logic) so they
# can be tuned in one place.
ATTENDANCE_LOW_THRESHOLD_PCT = 75.0
FLN_GAP_HIGH_THRESHOLD_RATIO = 0.40          # >40% of assessed students below expected level
TEACHER_VACANCY_HIGH_THRESHOLD_RATIO = 0.15  # >15% of required posts vacant
STUDENTS_PER_TEACHER_HIGH_THRESHOLD = 40.0


@dataclass
class SchoolContext:
    school_id: str
    total_enrollment: Optional[int]

    attendance_avg_pct: Optional[float]
    attendance_low_flag: bool

    chronic_absenteeism_ratio: Optional[float]

    fln_gap_ratio: Optional[float]
    fln_gap_flag: bool

    teacher_vacancy_ratio: Optional[float]
    avg_students_per_teacher: Optional[float]
    teacher_shortage_flag: bool

    def as_dict(self) -> dict:
        return {
            "school_id": self.school_id,
            "total_enrollment": self.total_enrollment,
            "attendance_avg_pct": self.attendance_avg_pct,
            "attendance_low_flag": self.attendance_low_flag,
            "chronic_absenteeism_ratio": self.chronic_absenteeism_ratio,
            "fln_gap_ratio": self.fln_gap_ratio,
            "fln_gap_flag": self.fln_gap_flag,
            "teacher_vacancy_ratio": self.teacher_vacancy_ratio,
            "avg_students_per_teacher": self.avg_students_per_teacher,
            "teacher_shortage_flag": self.teacher_shortage_flag,
        }


async def get_school_context(db: AsyncSession, school_id: str) -> SchoolContext:
    school = await db.get(School, school_id)
    total_enrollment = school.total_enrollment if school else None

    # --- Attendance aggregate ---
    attendance_rows = (
        await db.execute(
            select(StudentAttendance).where(StudentAttendance.school_id == school_id)
        )
    ).scalars().all()

    attendance_avg_pct = None
    chronic_absenteeism_ratio = None
    if attendance_rows:
        pct_values = [r.attendance_percentage for r in attendance_rows if r.attendance_percentage is not None]
        if pct_values:
            attendance_avg_pct = sum(pct_values) / len(pct_values)

        enrolled_total = sum(r.students_enrolled or 0 for r in attendance_rows)
        chronic_total = sum(r.chronic_absenteeism_count or 0 for r in attendance_rows)
        if enrolled_total > 0:
            chronic_absenteeism_ratio = chronic_total / enrolled_total

    attendance_low_flag = (
        attendance_avg_pct is not None and attendance_avg_pct < ATTENDANCE_LOW_THRESHOLD_PCT
    )

    # --- FLN / learning gap aggregate ---
    learning_rows = (
        await db.execute(
            select(StudentLearningData).where(StudentLearningData.school_id == school_id)
        )
    ).scalars().all()

    fln_gap_ratio = None
    if learning_rows:
        assessed_total = sum(r.students_assessed or 0 for r in learning_rows)
        at_level_total = sum(r.students_at_level or 0 for r in learning_rows)
        if assessed_total > 0:
            below_level_total = max(assessed_total - at_level_total, 0)
            fln_gap_ratio = below_level_total / assessed_total

    fln_gap_flag = fln_gap_ratio is not None and fln_gap_ratio > FLN_GAP_HIGH_THRESHOLD_RATIO

    # --- Teacher shortage aggregate (use the most recent snapshot) ---
    teacher_rows = (
        await db.execute(
            select(TeacherData)
            .where(TeacherData.school_id == school_id)
            .order_by(TeacherData.created_at.desc())
        )
    ).scalars().first()

    teacher_vacancy_ratio = None
    avg_students_per_teacher = None
    if teacher_rows:
        if teacher_rows.teachers_required and teacher_rows.teachers_required > 0 and teacher_rows.vacancies is not None:
            teacher_vacancy_ratio = teacher_rows.vacancies / teacher_rows.teachers_required
        avg_students_per_teacher = teacher_rows.avg_students_per_teacher

    teacher_shortage_flag = (
        (teacher_vacancy_ratio is not None and teacher_vacancy_ratio > TEACHER_VACANCY_HIGH_THRESHOLD_RATIO)
        or (avg_students_per_teacher is not None and avg_students_per_teacher > STUDENTS_PER_TEACHER_HIGH_THRESHOLD)
    )

    return SchoolContext(
        school_id=school_id,
        total_enrollment=total_enrollment,
        attendance_avg_pct=attendance_avg_pct,
        attendance_low_flag=attendance_low_flag,
        chronic_absenteeism_ratio=chronic_absenteeism_ratio,
        fln_gap_ratio=fln_gap_ratio,
        fln_gap_flag=fln_gap_flag,
        teacher_vacancy_ratio=teacher_vacancy_ratio,
        avg_students_per_teacher=avg_students_per_teacher,
        teacher_shortage_flag=teacher_shortage_flag,
    )
