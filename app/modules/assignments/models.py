from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    deadline = Column(DateTime)
    file_path = Column(String(500))
    file_size = Column(Integer)  # в байтах
    file_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    max_grade = Column(Integer, default=5)

    lesson = relationship("Lesson", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    file_path = Column(String(500))
    file_size = Column(Integer)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="submitted")  # submitted, checking, graded, rejected
    grade = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("Student")