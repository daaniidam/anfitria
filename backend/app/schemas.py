"""Esquemas Pydantic (entrada/salida de la API)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PropertyCreate(BaseModel):
    name: str
    address: str | None = None
    default_language: str = "es"


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str | None
    default_language: str


class KnowledgeCreate(BaseModel):
    category: str = "general"
    content: str


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    content: str


class InboundMessage(BaseModel):
    property_id: int
    guest_ref: str
    text: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    direction: str
    text: str
    language: str
    created_at: datetime


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inbound_message_id: int
    text: str
    language: str
    confidence: float
    model: str
    status: str


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    property_id: int
    guest_ref: str
    channel: str


class InboundResult(BaseModel):
    conversation: ConversationOut
    inbound: MessageOut
    draft: DraftOut
    auto_sent: bool


class ApproveRequest(BaseModel):
    edited_text: str | None = None


class InboxItem(BaseModel):
    """Borrador pendiente enriquecido para la bandeja de aprobación."""
    draft: DraftOut
    inbound_text: str
    guest_ref: str
    conversation_id: int
    property_id: int
    property_name: str
