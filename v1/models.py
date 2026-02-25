from sqlmodel import (
    Relationship,
    SQLModel,
    Field,
)
from typing import Optional, List
from datetime import datetime


class UserRoomLink(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    room_id: int = Field(foreign_key="room.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(default="", max_length=50, unique=True)
    email: str = Field(default="", max_length=255, unique=True)
    password: str = Field(default="")

    rooms: List["Room"] = Relationship(
        back_populates="users", link_model=UserRoomLink
    )
    messages: List["Message"] = Relationship(back_populates="sender")


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="", max_length=50, unique=True)

    users: List["User"] = Relationship(
        back_populates="rooms", link_model=UserRoomLink
    )
    messages: List["Message"] = Relationship(back_populates="room")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(default="", max_length=(2**16))
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)

    user_id: int = Field(foreign_key="user.id")
    room_id: int = Field(foreign_key="room.id")

    sender: Optional["User"] = Relationship(back_populates="messages")
    room: Optional["Room"] = Relationship(back_populates="messages")
