from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.security import get_current_user
from sqlalchemy import func

from app import models, schemas, cache
from app.database import get_db
from app.security import create_access_token, hash_password, verify_password

app = FastAPI(title="Job Tracker API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return schemas.Token(access_token=create_access_token(user.id))

@app.get("/me", response_model=schemas.UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.post("/applications", response_model=schemas.ApplicationRead, status_code=201)
def create_application(
    data: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = models.Application(**data.model_dump(), user_id=current_user.id)
    db.add(application)
    db.flush()  # assigns application.id without committing
    db.add(models.StatusHistory(
        application_id=application.id, old_status=None, new_status=application.status
    ))
    db.commit()
    cache.invalidate_stats(current_user.id)
    db.refresh(application)
    return application

@app.get("/applications", response_model=list[schemas.ApplicationRead])
def list_applications(
    status: str | None = None,
    company: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Application).filter(models.Application.user_id == current_user.id)
    if status:
        query = query.filter(models.Application.status == status)
    if company:
        query = query.filter(models.Application.company.ilike(f"%{company}%"))
    return (
        query.order_by(models.Application.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.patch("/applications/{application_id}", response_model=schemas.ApplicationRead)
def update_application(
    application_id: int,
    data: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = (
        db.query(models.Application)
        .filter(models.Application.id == application_id, models.Application.user_id == current_user.id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    changes = data.model_dump(exclude_unset=True)
    old_status = application.status
    for field, value in changes.items():
        setattr(application, field, value)
    if "status" in changes and application.status != old_status:
        db.add(models.StatusHistory(
            application_id=application.id,
            old_status=old_status,
            new_status=application.status,
        ))

    db.commit()
    cache.invalidate_stats(current_user.id)
    db.refresh(application)
    return application

@app.delete("/applications/{application_id}", status_code=204)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = (
        db.query(models.Application)
        .filter(models.Application.id == application_id, models.Application.user_id == current_user.id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(application)
    db.commit()
    cache.invalidate_stats(current_user.id)

@app.get("/applications/{application_id}/history", response_model=list[schemas.StatusHistoryRead])
def application_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = (
        db.query(models.Application)
        .filter(models.Application.id == application_id, models.Application.user_id == current_user.id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application.history


@app.get("/stats", response_model=schemas.Stats)
def stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cached = cache.get_cached_stats(current_user.id)
    if cached is not None:
        return cached

    rows = (
        db.query(models.Application.status, func.count(models.Application.id))
        .filter(models.Application.user_id == current_user.id)
        .group_by(models.Application.status)
        .all()
    )
    by_status = {status_name: count for status_name, count in rows}
    result = schemas.Stats(total=sum(by_status.values()), by_status=by_status)
    cache.set_cached_stats(current_user.id, result.model_dump())
    return result