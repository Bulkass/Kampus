from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    date = Column(DateTime, nullable=False)
    is_present = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    reason = Column(String(255))

    lesson = relationship("Lesson")
    student = relationship("Student")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    grade_value = Column(Integer)  # 2,3,4,5 или 0 для зачета
    grade_type = Column(String(20))  # "numeric", "pass_fail"
    date = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(String(255))

    student = relationship("Student")
    subject = relationship("Subject")
    lesson = relationship("Lesson")