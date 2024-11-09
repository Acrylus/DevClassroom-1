from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query
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

from database import get_db, engine, Base
from models import (
    Teacher,
    Student,
    Subject,
    Homework,
    HomeworkSubmission,
    SubmissionStatus,
)
import schemas
from schemas import SubjectDetailResponse, GradeSubmissionRequest


# Create tables
Base.metadata.create_all(bind=engine)

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Appdev Classroom ", description="Google Classroom Clone")


# Helper Functions
def get_password_hash(password: str):
    return pwd_context.hash(password)


def check_submission_status(due_date: str, submission_date: datetime) -> str:
    due_date = datetime.fromisoformat(due_date)
    if submission_date > due_date:
        return SubmissionStatus.LATE
    return SubmissionStatus.COMPLETE


# Teacher Endpoints
@app.post("/teachers/", response_model=schemas.Teacher)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    db_teacher = Teacher(
        firstname=teacher.firstname,
        lastname=teacher.lastname,
        email=teacher.email,
        hashed_password=get_password_hash(teacher.password),
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher


@app.get("/teachers/{teacher_id}/subjects", response_model=List[schemas.Subject])
def get_teacher_subjects(teacher_id: int, db: Session = Depends(get_db)):
    """Get all subjects taught by a specific teacher"""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher.subjects


@app.get("/teachers/{teacher_id}/homeworks", response_model=List[schemas.Homework])
def get_teacher_homeworks(
    teacher_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)
):
    """Get all homeworks created by a teacher across all subjects"""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    homeworks = []
    for subject in teacher.subjects:
        homeworks.extend(subject.homeworks)

    return homeworks[skip : skip + limit]


# Student Endpoints
@app.post("/students/", response_model=schemas.Student)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(
        firstname=student.firstname,
        lastname=student.lastname,
        email=student.email,
        hashed_password=get_password_hash(student.password),
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@app.get("/students/{student_id}/subjects", response_model=List[schemas.Subject])
def get_student_subjects(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student.subjects


@app.get("/students/{student_id}/homeworks", response_model=List[schemas.Homework])
def get_student_homeworks(
    student_id: int,
    status: Optional[str] = Query(None, enum=["pending", "submitted"]),
    db: Session = Depends(get_db),
):
    """Get all homeworks assigned to a student with optional status filter"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    homeworks = []
    for subject in student.subjects:
        for homework in subject.homeworks:
            submission = (
                db.query(HomeworkSubmission)
                .filter(
                    HomeworkSubmission.homework_id == homework.id,
                    HomeworkSubmission.student_id == student_id,
                )
                .first()
            )

            if status == "pending" and not submission:
                homeworks.append(homework)
            elif status == "submitted" and submission:
                homeworks.append(homework)
            elif not status:
                homeworks.append(homework)

    return homeworks


@app.get("/students/{student_id}/submissions", response_model=List[schemas.Submission])
def get_student_submissions(student_id: int, db: Session = Depends(get_db)):
    """Get all homework submissions for a student"""
    submissions = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.student_id == student_id)
        .all()
    )
    return submissions


# Subject Endpoints
@app.post("/subjects/", response_model=schemas.Subject)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    db_subject = Subject(**subject.dict())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


@app.put("/subjects/{subject_id}", response_model=schemas.Subject)
def update_subject(
    subject_id: int, subject_update: schemas.SubjectBase, db: Session = Depends(get_db)
):
    """Update subject details"""
    db_subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    for key, value in subject_update.dict().items():
        setattr(db_subject, key, value)

    db.commit()
    db.refresh(db_subject)
    return db_subject


@app.post("/subjects/{subject_id}/enroll/{student_id}")
def enroll_student(subject_id: int, student_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    student = db.query(Student).filter(Student.id == student_id).first()

    if not subject or not student:
        raise HTTPException(status_code=404, detail="Subject or student not found")

    subject.students.append(student)
    db.commit()

    return {"message": "Student enrolled successfully"}


@app.delete("/subjects/{subject_id}/unenroll/{student_id}")
def unenroll_student(subject_id: int, student_id: int, db: Session = Depends(get_db)):
    """Remove a student from a subject"""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    student = db.query(Student).filter(Student.id == student_id).first()

    if not subject or not student:
        raise HTTPException(status_code=404, detail="Subject or student not found")

    if student in subject.students:
        subject.students.remove(student)
        db.commit()
        return {"message": "Student unenrolled successfully"}

    raise HTTPException(status_code=400, detail="Student not enrolled in this subject")


@app.get("/subjects/{subject_id}/homeworks", response_model=List[schemas.Homework])
def get_subject_homeworks(subject_id: int, db: Session = Depends(get_db)):
    return db.query(Homework).filter(Homework.subject_id == subject_id).all()


# Homework Endpoints
@app.post("/homeworks/", response_model=schemas.Homework)
def create_homework(homework: schemas.HomeworkCreate, db: Session = Depends(get_db)):
    db_homework = Homework(**homework.dict())
    db.add(db_homework)
    db.commit()
    db.refresh(db_homework)
    return db_homework


@app.put("/homeworks/{homework_id}", response_model=schemas.Homework)
def update_homework(
    homework_id: int,
    homework_update: schemas.HomeworkBase,
    db: Session = Depends(get_db),
):
    """Update homework details"""
    db_homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    for key, value in homework_update.dict().items():
        setattr(db_homework, key, value)

    db.commit()
    db.refresh(db_homework)
    return db_homework


@app.delete("/homeworks/{homework_id}")
def delete_homework(homework_id: int, db: Session = Depends(get_db)):
    """Delete a homework assignment"""
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    db.delete(homework)
    db.commit()
    return {"message": "Homework deleted successfully"}


# Submission Endpoints
@app.post("/submissions/{homework_id}/{student_id}")
async def submit_homework(
    homework_id: int,
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    os.makedirs("uploads", exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = f"uploads/{unique_filename}"

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    submission_date = datetime.now()
    status = check_submission_status(homework.due_date, submission_date)

    submission = HomeworkSubmission(
        homework_id=homework_id,
        student_id=student_id,
        submission_date=submission_date.isoformat(),
        file_path=file_path,
        status=status,
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "message": "Homework submitted successfully",
        "status": status,
        "submission_date": submission_date.isoformat(),
    }


@app.put("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    grade_request: GradeSubmissionRequest,
    db: Session = Depends(get_db),
):
    submission = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    homework = db.query(Homework).filter(Homework.id == submission.homework_id).first()
    if grade_request.grade > homework.max_score:
        raise HTTPException(
            status_code=400,
            detail=f"Grade cannot exceed maximum score of {homework.max_score}",
        )

    submission.grade = grade_request.grade
    submission.feedback = grade_request.feedback
    submission.status = SubmissionStatus.COMPLETE
    db.commit()

    return {
        "message": "Submission graded successfully",
        "grade": grade_request.grade,
        "feedback": grade_request.feedback,
    }


@app.get("/homeworks/{homework_id}/submission-status")
def get_homework_submission_status(homework_id: int, db: Session = Depends(get_db)):
    """
    Get submission status for all students enrolled in the subject for a specific homework
    Returns detailed status including:
    - Whether they've submitted
    - If submitted, whether it was on time or late
    - Their grade if graded
    - Missing submissions
    """
    # Get the homework and associated subject
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    subject = homework.subject
    due_date = datetime.fromisoformat(homework.due_date)

    # Initialize response structure
    submission_status = {
        "homework_name": homework.name,
        "due_date": homework.due_date,
        "subject_name": subject.name,
        "total_students": len(subject.students),
        "submitted_count": 0,
        "pending_count": 0,
        "student_statuses": [],
    }

    # Check submission status for each enrolled student
    for student in subject.students:
        submission = (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id == homework_id,
                HomeworkSubmission.student_id == student.id,
            )
            .first()
        )

        student_status = {
            "student_id": student.id,
            "student_name": f"{student.firstname} {student.lastname}",
            "submitted": False,
            "submission_date": None,
            "status": "Not Submitted",
            "grade": None,
            "feedback": None,
            "days_overdue": None,
        }

        if submission:
            submission_status["submitted_count"] += 1
            submission_date = datetime.fromisoformat(submission.submission_date)

            student_status.update(
                {
                    "submitted": True,
                    "submission_date": submission.submission_date,
                    "status": submission.status,
                    "grade": submission.grade,
                    "feedback": submission.feedback,
                }
            )

            # Calculate days overdue if submitted late
            if submission_date > due_date:
                days_overdue = (submission_date - due_date).days
                student_status["days_overdue"] = days_overdue
        else:
            submission_status["pending_count"] += 1
            # Calculate days overdue for non-submissions if past due date
            if datetime.now() > due_date:
                days_overdue = (datetime.now() - due_date).days
                student_status["days_overdue"] = days_overdue

        submission_status["student_statuses"].append(student_status)

    # Add summary statistics
    submission_status.update(
        {
            "submission_rate": f"{(submission_status['submitted_count'] / len(subject.students) * 100):.1f}%",
            "graded_count": len(
                [
                    s
                    for s in submission_status["student_statuses"]
                    if s["grade"] is not None
                ]
            ),
            "late_submissions": len(
                [
                    s
                    for s in submission_status["student_statuses"]
                    if s.get("status") == "late"
                ]
            ),
            "on_time_submissions": len(
                [
                    s
                    for s in submission_status["student_statuses"]
                    if s.get("status") == "complete"
                ]
            ),
        }
    )

    return submission_status


@app.get("/subjects/{subject_id}/all-homework-status")
def get_subject_homework_status(subject_id: int, db: Session = Depends(get_db)):
    """
    Get submission status for all homeworks in a subject
    Provides an overview of submission rates and student performance
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    homework_status = {
        "subject_name": subject.name,
        "total_students": len(subject.students),
        "total_homeworks": len(subject.homeworks),
        "homeworks": [],
    }

    for homework in subject.homeworks:
        homework_data = {
            "homework_id": homework.id,
            "homework_name": homework.name,
            "due_date": homework.due_date,
            "max_score": homework.max_score,
            "submission_summary": {
                "total_submissions": 0,
                "pending_submissions": len(subject.students),
                "late_submissions": 0,
                "on_time_submissions": 0,
                "average_grade": 0,
            },
            "student_status": {},
        }

        total_grade = 0
        graded_count = 0

        for student in subject.students:
            submission = (
                db.query(HomeworkSubmission)
                .filter(
                    HomeworkSubmission.homework_id == homework.id,
                    HomeworkSubmission.student_id == student.id,
                )
                .first()
            )

            student_status = {
                "submitted": False,
                "status": "Not Submitted",
                "grade": None,
            }

            if submission:
                homework_data["submission_summary"]["total_submissions"] += 1
                homework_data["submission_summary"]["pending_submissions"] -= 1

                student_status.update(
                    {
                        "submitted": True,
                        "status": submission.status,
                        "grade": submission.grade,
                        "submission_date": submission.submission_date,
                    }
                )

                if submission.status == "late":
                    homework_data["submission_summary"]["late_submissions"] += 1
                elif submission.status == "complete":
                    homework_data["submission_summary"]["on_time_submissions"] += 1

                if submission.grade is not None:
                    total_grade += submission.grade
                    graded_count += 1

            homework_data["student_status"][student.id] = student_status

        # Calculate average grade
        if graded_count > 0:
            homework_data["submission_summary"]["average_grade"] = round(
                total_grade / graded_count, 2
            )

        homework_status["homeworks"].append(homework_data)

    return homework_status


# Analytics Endpoints
@app.get("/subjects/{subject_id}/analytics")
def get_subject_analytics(subject_id: int, db: Session = Depends(get_db)):
    """Get analytics for a subject"""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    total_students = len(subject.students)
    total_homeworks = len(subject.homeworks)

    submissions_stats = {
        "total_submissions": 0,
        "on_time_submissions": 0,
        "late_submissions": 0,
        "pending_submissions": 0,
    }

    for homework in subject.homeworks:
        for submission in homework.submissions:
            submissions_stats["total_submissions"] += 1
            if submission.status == SubmissionStatus.COMPLETE:
                submissions_stats["on_time_submissions"] += 1
            elif submission.status == SubmissionStatus.LATE:
                submissions_stats["late_submissions"] += 1
            else:
                submissions_stats["pending_submissions"] += 1

    return {
        "subject_name": subject.name,
        "total_students": total_students,
        "total_homeworks": total_homeworks,
        "submissions_stats": submissions_stats,
    }


@app.get("/students/{student_id}/analytics")
def get_student_analytics(student_id: int, db: Session = Depends(get_db)):
    """Get analytics for a student"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    analytics = {
        "total_subjects": len(student.subjects),
        "total_submissions": len(student.submissions),
        "submission_status": {"complete": 0, "late": 0, "incomplete": 0},
        "average_grade": 0,
        "grades_by_subject": {},
    }

    total_grade = 0
    graded_submissions = 0

    for submission in student.submissions:
        analytics["submission_status"][submission.status] += 1

        if submission.grade is not None:
            total_grade += submission.grade
            graded_submissions += 1

            subject_name = submission.homework.subject.name
            if subject_name not in analytics["grades_by_subject"]:
                analytics["grades_by_subject"][subject_name] = {
                    "total_grade": 0,
                    "count": 0,
                    "average": 0,
                }

            analytics["grades_by_subject"][subject_name][
                "total_grade"
            ] += submission.grade
            analytics["grades_by_subject"][subject_name]["count"] += 1

    if graded_submissions > 0:
        analytics["average_grade"] = total_grade / graded_submissions

        for subject in analytics["grades_by_subject"]:
            subject_stats = analytics["grades_by_subject"][subject]
            if subject_stats["count"] > 0:
                subject_stats["average"] = (
                    subject_stats["total_grade"] / subject_stats["count"]
                )

    return analytics


@app.get("/subjects/{subject_id}/details", response_model=SubjectDetailResponse)
def get_subject_details(subject_id: int, db: Session = Depends(get_db)):
    """
    Get comprehensive details of a subject including:
    - Subject information
    - Teacher information
    - List of enrolled students
    - Summary statistics
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Get the latest homework if any exists
    latest_homework = None
    if subject.homeworks:
        latest_homework = max(subject.homeworks, key=lambda h: h.due_date)

    response = {
        "id": subject.id,
        "name": subject.name,
        "detail": subject.detail,
        "teacher": subject.teacher,
        "students": subject.students,
        "total_students": len(subject.students),
        "total_homeworks": len(subject.homeworks),
        "latest_homework": latest_homework,
    }

    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
