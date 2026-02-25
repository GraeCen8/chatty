from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session, create_tables
from auth import hash_password, verify_password, create_token, decode_token

from pydantic import BaseModel
from models import User, Message, Room
import uvicorn

from fastapi.security.oauth2 import OAuth2PasswordRequestForm, OAuth2PasswordBearer

app = FastAPI()


@app.on_event("startup")
def startup():
    create_tables()


#
# user logins
#


# first start with a new user and then the user loggins
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserCreate(BaseModel):
    username: str
    password: str
    email: str


class UserLogin(BaseModel):
    username: str
    password: str


@app.post("/users/create")
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    existing = session.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
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
    statement = select(User).where(User.username == user.username)
    user = session.exec(statement).first()

    # verify credentials
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPEXception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # create token
    access_token = create_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


