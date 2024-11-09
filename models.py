from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum

# Association Tables
student_subject = Table(
    "student_subject",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id")),
    Column("subject_id", Integer, ForeignKey("subjects.id")),
)


class SubmissionStatus(str, enum.Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    LATE = "late"


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String(50), index=True)
    lastname = Column(String(50), index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    subjects = relationship("Subject", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String(50), index=True)
    lastname = Column(String(50), index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    subjects = relationship(
        "Subject", secondary=student_subject, back_populates="students"
    )
    submissions = relationship("HomeworkSubmission", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    detail = Column(String(500))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    teacher = relationship("Teacher", back_populates="subjects")
    students = relationship(
        "Student", secondary=student_subject, back_populates="subjects"
    )
    homeworks = relationship("Homework", back_populates="subject")


class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    instructions = Column(String(1000))
    due_date = Column(String(50))
    max_score = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    subject = relationship("Subject", back_populates="homeworks")
    submissions = relationship("HomeworkSubmission", back_populates="homework")


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    submission_date = Column(String(50))
    file_path = Column(String(255))
    grade = Column(Integer, nullable=True)
    feedback = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default=SubmissionStatus.INCOMPLETE)

    homework = relationship("Homework", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")
