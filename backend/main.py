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


from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    # Create a default room if none exists
    from database import get_session

    session_gen = get_session()
    session = next(session_gen)
    try:
        existing = session.exec(select(Room)).first()
        if not existing:
            general = Room(name="General")
            session.add(general)
            session.commit()
    finally:
        session.close()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)
) -> User:
    payload = decode_token(token)
    if not payload:
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
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@app.get("/users/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


#
# rooms
#


class RoomCreate(BaseModel):
    name: str


@app.post("/rooms/create", response_model=RoomRead)
async def create_room(
    room: RoomCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    expression = select(Room).where(Room.name == room.name)
    existing = session.exec(expression).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Room name already exists"
        )

    db_room = Room(name=room.name)
    session.add(db_room)
    session.commit()
    session.refresh(db_room)
    return db_room


@app.delete("/rooms/{room_id}")
async def delete_room(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    session.delete(room)
    session.commit()
    return {"ok": True}


@app.get("/rooms/{room_id}", response_model=RoomRead)
async def get_room(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return room


@app.get("/rooms", response_model=List[RoomRead])
async def get_rooms(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rooms = session.exec(select(Room).order_by(Room.name)).all()
    return rooms


@app.post("/rooms/{room_id}/join")
async def join_room(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    if current_user in room.users:
        return room
    room.users.append(current_user)
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


@app.delete("/rooms/{room_id}/leave")
async def leave_room(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    if current_user not in room.users:
        return room
    room.users.remove(current_user)
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


@app.get("/rooms/{room_id}/users", response_model=List[UserRead])
async def get_room_users(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return room.users


#
# messages
#


class MessageCreate(BaseModel):
    room_id: int
    content: str


def format_message(db_message: Message):
    return {
        "id": db_message.id,
        "content": db_message.content,
        "room_id": db_message.room_id,
        "sender": {"id": db_message.sender.id, "username": db_message.sender.username},
        "timestamp": db_message.timestamp.isoformat() if db_message.timestamp else None,
    }


@app.post("/messages/create", response_model=MessageRead)
async def create_message(
    message: MessageCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, message.room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    db_message = Message(content=message.content, room=room, sender=current_user)
    session.add(db_message)
    session.commit()
    session.refresh(db_message)

    # Broadcast via WebSocket as well
    await manager.broadcast(
        {"type": "message", "data": format_message(db_message)}
    )

    return db_message


@app.websocket("/ws")
async def handle_messages(
    websocket: WebSocket, 
    token: Optional[str] = None
):
    # Auth for WebSocket (usually passed via query param)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Use a fresh session for the WS loop
    from database import get_session
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        username = payload.get("sub")
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                
                # Expected format: {"room_id": int, "content": str}
                room_id = data.get("room_id")
                content = data.get("content")
                
                if room_id and content:
                    room = session.get(Room, room_id)
                    if room:
                        db_message = Message(content=content, room=room, sender=user)
                        session.add(db_message)
                        session.commit()
                        session.refresh(db_message)
                        
                        # Broadcast message to everyone
                        await manager.broadcast({
                            "type": "message", 
                            "data": format_message(db_message)
                        })
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    finally:
        session.close()


@app.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    message = session.get(Message, message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    if message.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages",
        )
    session.delete(message)
    session.commit()
    return {"ok": True, "deleted_id": message_id}


@app.get("/rooms/{room_id}/messages", response_model=List[MessageRead])
async def get_room_messages(
    room_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )
    return room.messages


#
# run the app
#


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
