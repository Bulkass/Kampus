from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Enum, Float, Text, Time
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
import datetime


# ============================================
# ENUM
# ============================================
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


# ============================================
# ПОЛЬЗОВАТЕЛИ
# ============================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    student_profile = relationship("Student", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False)

    students = relationship("Student", back_populates="group")
    lessons = relationship("Lesson", back_populates="group")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    student_id_number = Column(String(50), unique=True)

    user = relationship("User", back_populates="student_profile")
    group = relationship("Group", back_populates="students")
    submissions = relationship("Submission", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    grades = relationship("Grade", back_populates="student")


class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    department = Column(String(255))
    employee_id = Column(String(50), unique=True)

    user = relationship("User", back_populates="teacher_profile")
    lessons = relationship("Lesson", back_populates="teacher")


# ============================================
# РАСПИСАНИЕ
# ============================================
class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False)

    lessons = relationship("Lesson", back_populates="subject")


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String(50))
    week_type = Column(String(20), default="both")

    group = relationship("Group", back_populates="lessons")
    subject = relationship("Subject", back_populates="lessons")
    teacher = relationship("Teacher", back_populates="lessons")
    replacements = relationship("Replacement", back_populates="lesson")
    assignments = relationship("Assignment", back_populates="lesson")
    attendances = relationship("Attendance", back_populates="lesson")
    grades = relationship("Grade", back_populates="lesson")


class Replacement(Base):
    __tablename__ = "replacements"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    new_room = Column(String(50))
    new_teacher_id = Column(Integer, ForeignKey("teachers.id"))
    status = Column(String(20), default="active")
    reason = Column(String(255))

    lesson = relationship("Lesson", back_populates="replacements")
    new_teacher = relationship("Teacher")


# ============================================
# ЗАДАНИЯ
# ============================================
class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    deadline = Column(DateTime)
    file_path = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    max_grade = Column(Integer, default=5)

    lesson = relationship("Lesson", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="submitted")
    grade = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")


# ============================================
# ЖУРНАЛ
# ============================================
class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    is_present = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    reason = Column(String(255))

    lesson = relationship("Lesson", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")


class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    grade_value = Column(Integer)
    grade_type = Column(String(20), default="numeric")
    date = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(String(255))

    student = relationship("Student", back_populates="grades")
    subject = relationship("Subject")
    lesson = relationship("Lesson", back_populates="grades")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    text = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("Student")