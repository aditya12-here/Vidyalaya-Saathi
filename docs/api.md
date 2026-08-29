# Vidyalaya Saathi API Documentation

## Schools

### Create School
`POST /api/v1/school-data/schools`
```json
{
  "name": "School Name",
  "school_code": "OPTIONAL_CODE",
  "state": "State",
  "district": "District",
  "school_type": "Primary",
  "grades_served": "1-5",
  "total_enrollment": 150,
  "num_classrooms": 5,
  "num_teachers": 3
}
```

## Student Data

### Add FLN Data
`POST /api/v1/school-data/{school_id}/learning`
```json
{
  "grade": "3",
  "assessment_type": "READING",
  "competency": "Word reading",
  "expected_level": "Grade 3",
  "observed_level": "Grade 1",
  "students_assessed": 30,
  "students_at_level": 12
}
```

### Add Attendance
`POST /api/v1/school-data/{school_id}/attendance`
```json
{
  "grade": "3",
  "time_period": "August 2026",
  "students_enrolled": 35,
  "students_present": 28,
  "attendance_percentage": 80.0,
  "chronic_absenteeism_count": 2
}
```

## Teacher Data

### Update Teacher Workload/Availability
`POST /api/v1/school-data/{school_id}/teachers`
```json
{
  "teachers_required": 5,
  "teachers_sanctioned": 4,
  "teachers_available": 3,
  "vacancies": 1,
  "teachers_absent": 0,
  "avg_students_per_teacher": 50.0
}
```

## Infrastructure

### Add Infrastructure Record
`POST /api/v1/school-data/{school_id}/infrastructure`
```json
{
  "category": "Toilets",
  "availability": "Available",
  "quantity": 2,
  "required_quantity": 4,
  "condition": "Poor",
  "functional_status": "Partially Functional"
}
```
