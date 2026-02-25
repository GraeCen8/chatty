from sqlmodel import (
    Relationship,
    SQLModel,
    Field,
)
from pydantic import Optional, List
from datetime import datetime


class UserRoomLink(SQlModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    project_id: int = Field(foreign_key="project.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(default="", max_length=50, unique=True)
    email: str = Field(default="", max_length=255, unique=True)
    password: str = Field(default="", unique=True)

    rooms: Optional[List] = Relationship(
        back_populates="users", link_model=UserRoomLink
    )


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="", max_length=50, unique=True)

    users: Optional[List] = Relationship(
        back_populates="rooms", link_model=UserRoomLink
    )

    messages: Optional[List] = Relationship(
        back_populates="room", link_model="messages"
    )


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(default="", max_length=(2**16))
    timestamp: datetime = Field(default=datetime.now())

    send_user: User = Relationship(back_populates="messages")
    room: Room = Relationship(back_populates="messages")
