from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from .database import Base

class Student(Base):
    __tablename__ = "students"
    student_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Course(Base):
    __tablename__ = "courses"
    course_id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    max_students = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Enrollment(Base):
    __tablename__ = "enrollments"
    student_id = Column(Integer, ForeignKey("students.student_id"), primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.course_id"), primary_key=True)
    enrollment_date = Column(DateTime, server_default=func.now())
