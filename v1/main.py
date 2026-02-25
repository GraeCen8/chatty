from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session, create_tables
from auth import hash_password, verify_password, create_token, decode_token

from pydantic import BaseModel, EmailStr
from models import User, Message, Room, UserRead, RoomRead, MessageRead
import uvicorn
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi.security.oauth2 import OAuth2PasswordRequestForm, OAuth2PasswordBearer


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(lifespan=lifespan)

#
# user logins
#

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@app.post("/users/create", response_model=UserRead)
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(User).where((User.username == user.username) | (User.email == user.email))
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )
    hashed_pw = hash_password(user.password)
    db_user = User(username=user.username, password=hashed_pw, email=user.email)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@app.post("/users/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    # get user
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    # verify credentials
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # create token
    access_token = create_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
