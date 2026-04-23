from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
import datetime

Base = declarative_base()


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Связи
    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    student_id_number = Column(String(50), unique=True)

    user = relationship("User", back_populates="student_profile")
    group = relationship("Group", back_populates="students")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    department = Column(String(255))
    employee_id = Column(String(50), unique=True)

    user = relationship("User", back_populates="teacher_profile")
    lessons = relationship("Lesson", back_populates="teacher")