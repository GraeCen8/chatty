from sqlmodel import (
    Relationship,
    SQLModel,
    Field,
)
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr


class UserRoomLink(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    room_id: int = Field(foreign_key="room.id", primary_key=True)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(default="", max_length=50, unique=True, index=True)
    email: str = Field(default="", max_length=255, unique=True, index=True)
    password: str = Field(default="")

    rooms: List["Room"] = Relationship(
        back_populates="users", link_model=UserRoomLink
    )
    messages: List["Message"] = Relationship(back_populates="sender")


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="", max_length=50, unique=True, index=True)

    users: List["User"] = Relationship(
        back_populates="rooms", link_model=UserRoomLink
    )
    messages: List["Message"] = Relationship(
        back_populates="room", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(default="", max_length=(2**16))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user_id: int = Field(foreign_key="user.id")
    room_id: int = Field(foreign_key="room.id")

    sender: Optional["User"] = Relationship(back_populates="messages")
    room: Optional["Room"] = Relationship(back_populates="messages")


# Pydantic models for API
class UserRead(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class RoomRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class MessageRead(BaseModel):
    id: int
    content: str
    timestamp: datetime
    user_id: int
    room_id: int
    sender: Optional[UserRead] = None

    class Config:
        from_attributes = True


UserRead.model_rebuild()
RoomRead.model_rebuild()
MessageRead.model_rebuild()
