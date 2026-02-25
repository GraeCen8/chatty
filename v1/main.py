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


#
# rooms
#


class RoomCreate(BaseModel):
    name: str


@app.post("/rooms/create")
async def create_room(room: RoomCreate, session: Session = Depends(get_session)):
    expression = select(Room).where(Room.name == room.name)
    existing = session.exec(expression).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Room name already exists"
        )

    db_room = Room(
        name=room.name,
    )

    session.add(db_room)
    session.commit()
    session.refresh(db_room)
    return db_room


@app.delete("/rooms/{room_id}")
async def delete_room(room_id: int, session: Session = Depends(get_session)):
    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    session.delete(room)
    session.commit()
    return room


@app.get("/rooms/{room_id}")
async def get_room(room_id: int, session: Session = Depends(get_session)):
    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    session.refresh(room)
    return room


@app.get("/rooms")
async def get_rooms(session: Session = Depends(get_session)):
    rooms = session.query(Room).order_by(Room.name).all()
    return rooms


@app.post("/rooms/{room_id}/join/{user_id}")
async def join_room(
    room_id: int, user_id: int, session: Session = Depends(get_session)
):
    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    room.users.append(user)
    session.commit()
    session.refresh(room)
    return room


@app.delete("/rooms/{room_id}/leave/{user_id}")
async def leave_room(
    room_id: int, user_id: int, session: Session = Depends(get_session)
):
    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    room.users.remove(user)
    session.commit()
    session.refresh(room)
    return room


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: int, session: Session = Depends(get_session)):
    room = session.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    users = room.users
    session.refresh(users)
    return users


#
# messages
#


class MessageCreate(BaseModel):
    room_id: int
    text: str


@app.post("/messages/create")
async def create_message(
    message: MessageCreate, session: Session = Depends(get_session)
):
    room = session.query(Room).filter(Room.id == message.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    db_message = Message(text=message.text, room=room)
    session.add(db_message)
    session.commit()
    session.refresh(db_message)
    return db_message


@app.delete("/messages/{message_id}")
async def delete_message(message_id: int, session: Session = Depends(get_session)):
    message = session.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    session.delete(message)
    session.commit()
    session.refresh(message)
    return message


if __name__ == "__main__":
    create_tables()
    uvicorn.run(app, host="0.0.0.0", port=8000)
