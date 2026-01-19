from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StudentCreate(BaseModel):
    first_name: str
    last_name: str
    email: str


class StudentResponse(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    email: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    code: str
    name: str
    credits: int
    max_students: int


class CourseResponse(BaseModel):
    course_id: int
    code: str
    name: str
    credits: int
    max_students: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int

class EnrollmentResponse(BaseModel):
    student_id: int
    course_id: int
    enrollment_date: Optional[datetime] = None
