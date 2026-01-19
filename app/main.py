from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db
from . import models
from .schemas import StudentCreate, StudentResponse , CourseResponse, CourseCreate , EnrollmentCreate , EnrollmentResponse


import os
app = FastAPI()
@app.get("/debug-env")
def debug_env():
    return {
        "DATABASE_URL": os.getenv("DATABASE_URL")
    }
#for local  debugging
@app.get("/debug-db-url")
def debug_db_url():
    return {"DATABASE_URL": os.getenv("DATABASE_URL")}

@app.get("/")
def read_root():
    return {"message": "University API connected to PostgreSQL"}


@app.get("/test-db")
def test_db():
    return {"ok": True}

@app.post("/students/", response_model=StudentResponse)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    result = db.execute(text("SELECT student_id FROM students WHERE email = :email"),
                        {"email": student.email}).fetchone()
    if result:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Insert new student and get ID
    result = db.execute(text("""
        INSERT INTO students (first_name, last_name, email) 
        VALUES (:first_name, :last_name, :email) 
        RETURNING student_id
    """), {
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email
    })
    student_id = result.fetchone()[0]
    db.commit()

    # Return the created student (no refresh needed for raw SQL)
    return StudentResponse(
        student_id=student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email
    )


@app.get("/students/", response_model=list[StudentResponse])
def list_students(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM students ORDER BY created_at DESC"))
    students = []
    for row in result:
        students.append(StudentResponse(
            student_id=row[0], first_name=row[1], last_name=row[2],
            email=row[3], created_at=row[4]
        ))
    return students


# ADD THESE ENDPOINTS (after students endpoints)

@app.post("/courses/", response_model=CourseResponse)
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    result = db.execute(text("INSERT INTO courses (code, name, credits, max_students) VALUES (:code, :name, :credits, :max_students) RETURNING course_id"), {
        "code": course.code, "name": course.name, "credits": course.credits, "max_students": course.max_students
    })
    course_id = result.fetchone()[0]
    db.commit()
    return CourseResponse(course_id=course_id, **course.dict())

@app.get("/courses/", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM courses ORDER BY created_at DESC"))
    courses = []
    for row in result:
        courses.append(CourseResponse(course_id=row[0], code=row[1], name=row[2], credits=row[3], max_students=row[4]))
    return courses

@app.get("/courses/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM courses WHERE course_id = :id"), {"id": course_id}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(course_id=result[0], code=result[1], name=result[2], credits=result[3], max_students=result[4])


@app.post("/enrollments/", response_model=EnrollmentResponse)
def create_enrollment(enrollment: EnrollmentCreate, db: Session = Depends(get_db)):
    student_id = enrollment.student_id
    course_id = enrollment.course_id

    # Check if student exists
    student_check = db.execute(text("SELECT student_id FROM students WHERE student_id = :id"),
                               {"id": student_id}).fetchone()
    if not student_check:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check if course exists
    course_check = db.execute(text("SELECT course_id, max_students FROM courses WHERE course_id = :id"),
                              {"id": course_id}).fetchone()
    if not course_check:
        raise HTTPException(status_code=404, detail="Course not found")

    current_enrollments = db.execute(text("""
        SELECT COUNT(*) FROM enrollments WHERE course_id = :course_id
    """), {"course_id": course_id}).scalar()

    # Check capacity
    if current_enrollments >= course_check[1]:
        raise HTTPException(status_code=400, detail="Course is full")

    # Check for duplicate enrollment (composite PK prevents this anyway)
    duplicate_check = db.execute(text("""
        SELECT 1 FROM enrollments WHERE student_id = :student_id AND course_id = :course_id
    """), {"student_id": student_id, "course_id": course_id}).fetchone()

    if duplicate_check:
        raise HTTPException(status_code=400, detail="Student already enrolled in this course")

    # Create enrollment
    result = db.execute(text("""
        INSERT INTO enrollments (student_id, course_id) 
        VALUES (:student_id, :course_id) 
        RETURNING student_id, course_id, enrollment_date
    """), {"student_id": student_id, "course_id": course_id})

    enrollment_data = result.fetchone()
    db.commit()

    return EnrollmentResponse(
        student_id=enrollment_data[0],
        course_id=enrollment_data[1],
        enrollment_date=enrollment_data[2]
    )


@app.get("/students/{student_id}/courses", response_model=list[CourseResponse])
def get_student_courses(student_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT c.* FROM courses c
        JOIN enrollments e ON c.course_id = e.course_id
        WHERE e.student_id = :student_id
        ORDER BY c.name
    """), {"student_id": student_id})

    courses = []
    for row in result:
        courses.append(CourseResponse(course_id=row[0], code=row[1], name=row[2],
                                      credits=row[3], max_students=row[4]))
    return courses


@app.get("/courses/{course_id}/students", response_model=list[StudentResponse])
def get_course_students(course_id: int, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT s.* FROM students s
        JOIN enrollments e ON s.student_id = e.student_id
        WHERE e.course_id = :course_id
        ORDER BY s.last_name, s.first_name
    """), {"course_id": course_id})

    students = []
    for row in result:
        students.append(StudentResponse(student_id=row[0], first_name=row[1],
                                        last_name=row[2], email=row[3]))
    return students


@app.get("/report/enrollment-stats")
def enrollment_stats(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            c.code, c.name, 
            COUNT(e.student_id) as enrolled,
            c.max_students,
            ROUND((COUNT(e.student_id)::float / c.max_students * 100), 1) as capacity_pct
        FROM courses c
        LEFT JOIN enrollments e ON c.course_id = e.course_id
        GROUP BY c.course_id, c.code, c.name, c.max_students
        ORDER BY capacity_pct DESC
    """))

    stats = []
    for row in result:
        stats.append({
            "course_code": row[0],
            "course_name": row[1],
            "enrolled": row[2],
            "max_capacity": row[3],
            "capacity_used": f"{row[4]}%"
        })
    return stats
