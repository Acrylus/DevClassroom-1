from pydantic import BaseModel, EmailStr
from typing import List, Optional
from enum import Enum


class SubmissionStatus(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    LATE = "late"


class TeacherBase(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr


class TeacherCreate(TeacherBase):
    password: str


class Teacher(TeacherBase):
    id: int

    class Config:
        orm_mode = True


class StudentBase(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr


class StudentCreate(StudentBase):
    password: str


class Student(StudentBase):
    id: int

    class Config:
        orm_mode = True


class SubjectBase(BaseModel):
    name: str
    detail: str


class SubjectCreate(SubjectBase):
    teacher_id: int


class Subject(SubjectBase):
    id: int
    teacher_id: int

    class Config:
        orm_mode = True


class HomeworkBase(BaseModel):
    name: str
    instructions: str
    due_date: str
    max_score: int


class HomeworkCreate(HomeworkBase):
    subject_id: int


class Homework(HomeworkBase):
    id: int
    subject_id: int

    class Config:
        orm_mode = True


class GradeSubmissionRequest(BaseModel):
    grade: int
    feedback: str


class SubmissionBase(BaseModel):
    homework_id: int
    student_id: int


class SubmissionCreate(SubmissionBase):
    pass


class Submission(SubmissionBase):
    id: int
    submission_date: str
    file_path: str
    grade: Optional[int]
    feedback: Optional[str]
    status: SubmissionStatus

    class Config:
        orm_mode = True


class StudentInfo(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: EmailStr

    class Config:
        orm_mode = True


class TeacherInfo(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: EmailStr

    class Config:
        orm_mode = True


class SubjectDetailResponse(BaseModel):
    id: int
    name: str
    detail: str
    teacher: TeacherInfo
    students: List[StudentInfo]
    total_students: int
    total_homeworks: int
    latest_homework: Optional[HomeworkBase] = None

    class Config:
        orm_mode = True
