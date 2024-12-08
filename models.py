from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Enum, Text
from sqlalchemy.orm import relationship
from database import Base
import enum
from pydantic import BaseModel

student_subject = Table(
    'student_subject',
    Base.metadata,
    Column('student_id', Integer, ForeignKey('users.id')),
    Column('subject_id', Integer, ForeignKey('subjects.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password = Column(String(100))
    firstname = Column(String(50), index=True)
    lastname = Column(String(50), index=True)
    role = Column(String(50), index=True)

    created_subjects = relationship('Subject', back_populates='creator')

    enrolled_subjects = relationship(
        'Subject',
        secondary=student_subject,
        back_populates='students'
    )

    submissions = relationship("Submission", back_populates="student")

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    code = Column(String(30), unique=True, index=True)
    creator_id = Column(Integer, ForeignKey('users.id'))

    creator = relationship('User', back_populates='created_subjects')

    students = relationship(
        'User',
        secondary=student_subject,
        back_populates='enrolled_subjects'
    )

    assessments = relationship("Assessment", back_populates="subject")

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text)
    over = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    attachment = Column(String(100), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    subject = relationship("Subject", back_populates="assessments")
    submissions = relationship("Submission", back_populates="assessments")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    file_path = Column(String(100), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    assessment_id = Column(Integer, ForeignKey('assessments.id'))

    student = relationship("User", back_populates="submissions")
    assessments = relationship("Assessment", back_populates="submissions")
