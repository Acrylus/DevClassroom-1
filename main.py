from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query, UploadFile, Body, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uvicorn
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import os
from uuid import uuid4
from sqlalchemy import desc
from typing import Dict, List
from datetime import datetime
from passlib.context import CryptContext
from datetime import datetime, timedelta
from database import get_db, engine, Base
from models import (
    User,
    Subject,
)
import schemas
from enum import Enum
import models, schemas, auth
from auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware 
import shutil
import logging
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.DEBUG)

class UserType(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Appdev Classroom ", description="Google Classroom Clone")

# Create tables
Base.metadata.create_all(bind=engine)

UPLOAD_DIR = os.path.join(os.getcwd(), "files")
app.mount("/files", StaticFiles(directory="files"), name="files")

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Password Hashing


origins = [
    "http://localhost:3000",  # Frontend React app (adjust if needed)
    "http://localhost:8000",  # Backend API
    "*",  # Allow all origins (not recommended for production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows only these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper Functions
def get_password_hash(password: str):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if user and auth.verify_password(password, user.password):  # Corrected line
        return user
    return None

@app.get("/files/{filename}")
async def serve_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    logging.info(f"Attempting to serve file: {file_path}")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/users/details", response_model=schemas.UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/user/{userID}")
def get_user_name(userID: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == userID).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"firstName": user.firstname, "lastName": user.lastname}

# Register user endpoint
@app.post("/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.hash_password(user.password)
    new_user = models.User(
        email=user.email,
        password=hashed_password,
        firstname=user.firstname,
        lastname=user.lastname,
        role = user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Login user endpoint
@app.post("/login")
def login_user(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth.create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/subjects", response_model=schemas.SubjectCreate)
def create_subject(
    subject: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create subjects")
    
    existing_subject = db.query(models.Subject).filter(models.Subject.code == subject.code).first()
    if existing_subject:
        raise HTTPException(status_code=400, detail="Subject code already exists")
    
    new_subject = models.Subject(
        name=subject.name,
        code=subject.code,
        creator_id=current_user.id
    )
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return new_subject

@app.post("/subjects/{subject_id}/student/{student_id}", response_model=schemas.SubjectOut)
def add_student_to_subject(
    subject_id: int,
    student_id: int,  # The student ID to add to the subject
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Ensure only teachers can add students to subjects
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can add students to subjects")
    
    # Get the subject by ID
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Get the student by ID
    student = db.query(models.User).filter(models.User.id == student_id, models.User.role == "Student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or the user is not a student")

    # Add the student to the subject if not already added
    if student in subject.students:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this subject")
    
    # Add the student to the subject
    subject.students.append(student)
    db.commit()
    db.refresh(subject)

    return subject

@app.post("/subjects/{subject_code}", response_model=schemas.SubjectOut)
def join_subject_using_code(
    subject_code: str,  # The subject code to join
    student: models.User = Depends(get_current_user),  # Get the current student user
    db: Session = Depends(get_db)
):
    # Ensure the user is a student
    if student.role != "student":
        raise HTTPException(status_code=403, detail="Only students can join subjects")
    
    # Get the subject by code
    subject = db.query(models.Subject).filter(models.Subject.code == subject_code).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Check if the student is already enrolled in the subject
    if student in subject.students:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this subject")

    # Add the student to the subject
    subject.students.append(student)
    db.commit()
    db.refresh(subject)

    return subject

@app.post("/subjects/{subject_id}/assessments", response_model=schemas.AssessmentOut)
def create_assessment(
    subject_id: str,
    name: str = Form(...),
    description: str = Form(...),
    over: str = Form(...),
    attachment: UploadFile = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create assessments")
    
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    file_path = None
    if attachment:
        try:
            # Define the directory to store files
            upload_dir = "files/teachers"
            os.makedirs(upload_dir, exist_ok=True)  # Ensure the directory exists

            # Sanitize the file name (e.g., replace spaces with underscores)
            sanitized_filename = f"{subject_id}_{attachment.filename}".replace(" ", "_")
            file_path = os.path.join(upload_dir, sanitized_filename)

            # Save the file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

        except Exception as e:
            # Handle any errors during the file upload process
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

    
    # Create the assessment
    new_assessment = models.Assessment(
        name=name,
        description=description,
        over=over,
        attachment=file_path,
        subject_id=subject.id
    )
    
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    
    return new_assessment

@app.post("/submission/{assessment_id}")
def submit_assessment(
    assessment_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure the current user is a student
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit assessments")

    # Check if the assessment exists
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Verify the student is enrolled in the subject
    subject = db.query(models.Subject).filter(models.Subject.id == assessment.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    if current_user.id not in [student.id for student in subject.students]:
        raise HTTPException(status_code=403, detail="You are not enrolled in this subject")

    # Handle file upload
    file_path = None
    try:
        # Define the directory to store files
        upload_dir = "files/students"
        os.makedirs(upload_dir, exist_ok=True)  # Ensure the directory exists

        # Sanitize the file name (e.g., replace spaces with underscores)
        sanitized_filename = f"{assessment_id}_{current_user.id}_{file.filename}".replace(" ", "_")
        file_path = os.path.join(upload_dir, sanitized_filename)

        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        # Handle any errors during the file upload process
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

    # Check if the student has already submitted for this assessment
    existing_submission = db.query(models.Submission).filter(
        models.Submission.assessment_id == assessment_id,
        models.Submission.student_id == current_user.id
    ).first()

    if existing_submission:
        raise HTTPException(status_code=400, detail="You have already submitted this assessment")

    # Create a new submission
    new_submission = models.Submission(
        student_id=current_user.id,
        assessment_id=assessment_id,
        file_path=file_path
    )

    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    return {"message": "Submission successful", "submission": new_submission}

@app.get("/submission/view/{submission_id}")
def view_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if the user is a student or teacher
    if current_user.role not in ["student", "teacher"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Retrieve the submission query
    submission_query = db.query(models.Submission).filter(models.Submission.id == submission_id)

    submission = submission_query.first()

    # Check if submission exists
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "submission_id": submission.id,
        "assessment_id": submission.assessment_id,
        "file_path": submission.file_path,
        "student": {
                "id": current_user.id,
                "name": f"{current_user.firstname} {current_user.lastname}",
                "email": current_user.email
            },
        "score": submission.score,
        "feedback": submission.feedback
    }

@app.get("/submission/student/{assessment_id}")
def student_submission(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if the user is a student or teacher
    if current_user.role not in ["student", "teacher"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Retrieve the submission
    submission_query = db.query(models.Submission).filter(models.Submission.assessment_id == assessment_id)

    # If the user is a student, only fetch their submission
    if current_user.role == "student":
        submission_query = submission_query.filter(models.Submission.student_id == current_user.id)

    submission = submission_query.first()

    # Check if submission exists
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Response for student
    return {
        "submission_id": submission.id,
        "assessment_id": submission.assessment_id,
        "file_path": submission.file_path,
        "student": {
                "id": current_user.id,
                "name": f"{current_user.firstname} {current_user.lastname}",
                "email": current_user.email
            },
        "score": submission.score,
        "feedback": submission.feedback
    }

@app.get("/submission/check/{assessment_id}")
def student_submission_for_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if the user is a student or teacher
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    # Retrieve submissions for the student in the given assessment
    submission_query = db.query(models.Submission).filter(
        models.Submission.assessment_id == assessment_id,
        models.Submission.student_id == current_user.id
    )

    submission = submission_query.first()

    # Check if submission exists
    if not submission:
        return {"submission_exists": False}  # No submission found for the student in this assessment

    # If submission exists, return submission details
    return {
        "submission_exists": True,
        "submission_id": submission.id,
        "file_path": submission.file_path,
        "score": submission.score,
        "feedback": submission.feedback
    }

@app.get("/submissions/view/{assessment_id}")
def view_submissions(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if the user is a student or teacher
    if current_user.role not in ["student", "teacher"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Retrieve the assessment to ensure it exists
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # If the user is a student, only fetch their submission
    if current_user.role == "student":
        submission = (
            db.query(models.Submission)
            .filter(
                models.Submission.assessment_id == assessment_id,
                models.Submission.student_id == current_user.id,
            )
            .first()
        )

        # Check if submission exists
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Response for student
        return {
            "submission_id": submission.id,
            "assessment_id": submission.assessment_id,
            "file_path": submission.file_path,
            "score": submission.score,
            "feedback": submission.feedback,
        }

    # If the user is a teacher, fetch all submissions for the assessment
    if current_user.role == "teacher":
        submissions = (
            db.query(models.Submission)
            .filter(models.Submission.assessment_id == assessment_id)
            .all()
        )

        # If no submissions exist
        if not submissions:
            raise HTTPException(status_code=404, detail="No submissions found for this assessment")

        # Format the response for teacher
        result = []
        for submission in submissions:
            student = db.query(models.User).filter(models.User.id == submission.student_id).first()
            result.append({
                "submission_id": submission.id,
                "student": {
                    "id": student.id,
                    "name": f"{student.firstname} {student.lastname}",
                    "email": student.email,
                },
                "file_path": submission.file_path,
                "score": submission.score,
                "feedback": submission.feedback,
            })

        return {
            "assessment_id": assessment_id,
            "assessment_name": assessment.name,
            "submissions": result,
        }


@app.put("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    grade_data: schemas.AssessmentFeedback,
    teacher: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify the user's role
    if teacher.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can grade submissions")

    # Fetch the submission
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Verify the teacher is the creator of the subject related to this submission's assessment
    assessment = db.query(models.Assessment).filter(models.Assessment.id == submission.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Associated assessment not found")

    subject = db.query(models.Subject).filter(models.Subject.id == assessment.subject_id).first()
    if not subject or subject.creator_id != teacher.id:
        raise HTTPException(status_code=403, detail="You are not authorized to grade this submission")

    # Update score and feedback for the submission
    if grade_data.score is not None:
        if not (0 <= grade_data.score <= 100):
            raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
        submission.score = grade_data.score
    if grade_data.feedback:
        submission.feedback = grade_data.feedback

    # Commit changes to the database
    db.commit()
    db.refresh(submission)

    return {
        "message": "Submission graded successfully",
        "submission": {
            "id": submission.id,
            "assessment_id": submission.assessment_id,
            "student_id": submission.student_id,
            "score": submission.score,
            "feedback": submission.feedback
        }
    }

# Endpoint for teachers to get all subjects they created
@app.get("/teacher/subjects", response_model=List[schemas.SubjectOut])
def get_teacher_subjects(current_user: schemas.UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all subjects created by the teacher
    subjects = db.query(Subject).filter(Subject.creator_id == current_user.id).all()
    return subjects

# Endpoint for students to get only the subjects they are enrolled in
@app.get("/student/subjects", response_model=List[schemas.SubjectOut])
def get_student_subjects(current_user: schemas.UserOut = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all subjects where the student is enrolled
    subjects = db.query(Subject).join(Subject.students).filter(User.id == current_user.id).all()
    return subjects

@app.get("/assessments/{subject_id}", response_model=List[schemas.AssessmentOut])
def get_assessments_by_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    assessments = db.query(models.Assessment).filter(models.Assessment.subject_id == subject_id).all()
    return assessments

@app.get("/assessments/id/{assessment_id}", response_model=schemas.AssessmentOut)
def get_assessment_by_id(
    assessment_id: int,
    db: Session = Depends(get_db),
):
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
