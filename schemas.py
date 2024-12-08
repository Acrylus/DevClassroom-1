from pydantic import BaseModel, EmailStr
from typing import List, Optional
from enum import Enum

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    firstname: str
    lastname: str
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    firstname: str
    lastname: str
    role: str

    class Config:
        orm_mode = True

class UserOut(BaseModel):
    id: int
    email: str
    firstname: str
    lastname: str
    role: str

    class Config:
        orm_mode = True

class SubjectCreate(BaseModel):
    name: str
    code: str

class SubjectOut(BaseModel):
    id: int
    name: str
    code: str
    creator_id: int
    students: List[UserOut] = []

    class Config:
        orm_mode = True

class AssessmentCreate(BaseModel):
    name: str
    description: str
    score: Optional[int]
    attachment: Optional[str] = None

    class Config:
        orm_mode = True

class AssessmentSubmit(BaseModel):
    file_path: str

    class Config:
        orm_mode = True

class AssessmentFeedback(BaseModel):
    score: Optional[int]
    feedback: Optional[str]

    class Config:
        orm_mode = True

class AssessmentOut(BaseModel):
    id: int
    name: str
    description: str
    over: int
    attachment: Optional[str]

    class Config:
        orm_mode = True

class Submission(BaseModel):
    score: Optional[int]
    feedback: Optional[str]
    file_path: Optional[str]

    class Config:
        orm_mode = True