from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.student import Student
from app.schemas.student import Token, StudentCreate, StudentRead

router = APIRouter()

@router.post("/auth/register", response_model=StudentRead)
def register_student(
    student_in: StudentCreate,
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.email == student_in.email).first()
    if student:
        raise HTTPException(
            status_code=400,
            detail="The student with this email already exists in the system",
        )
    student = Student(
        email=student_in.email,
        full_name=student_in.full_name,
        hashed_password=get_password_hash(student_in.password),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.post("/auth/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    student = db.query(Student).filter(Student.email == form_data.username).first()
    if not student or not verify_password(form_data.password, student.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            student.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
