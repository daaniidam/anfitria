"""Esquemas Pydantic (entrada/salida de la API)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: str = "owner"
    org_id: int | None = None


class MemberCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="member", pattern="^(owner|member)$")


class MemberRoleUpdate(BaseModel):
    role: str = Field(pattern="^(owner|member)$")


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class OnboardingStatus(BaseModel):
    has_property: bool
    has_knowledge: bool
    has_whatsapp: bool
    has_conversation: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    default_language: str = Field(default="es", max_length=8)
    auto_answer: bool = True
    auto_answer_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    whatsapp_phone_number_id: str | None = Field(default=None, max_length=64)
    building_id: int | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_language: str | None = Field(default=None, max_length=8)
    auto_answer: bool | None = None
    auto_answer_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    whatsapp_phone_number_id: str | None = Field(default=None, max_length=64)


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    address: str | None
    default_language: str
    auto_answer: bool
    auto_answer_threshold: float | None
    whatsapp_phone_number_id: str | None
    building_id: int | None


class KnowledgeCreate(BaseModel):
    category: str = Field(default="general", max_length=64)
    content: str = Field(min_length=1, max_length=4000)


class KnowledgeUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=64)
    content: str | None = Field(default=None, min_length=1, max_length=4000)


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    content: str


class KnowledgeImportOut(BaseModel):
    imported: int  # nº de fragmentos añadidos a la ficha


class ReservationCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=160)
    guest_ref: str = Field(min_length=1, max_length=64)
    check_in: date
    check_out: date
    source: str = Field(default="direct", pattern="^(booking|airbnb|direct|other)$")
    code: str | None = Field(default=None, max_length=32)


class ReservationUpdate(BaseModel):
    guest_name: str | None = Field(default=None, min_length=1, max_length=160)
    guest_ref: str | None = Field(default=None, min_length=1, max_length=64)
    check_in: date | None = None
    check_out: date | None = None
    status: str | None = Field(default=None, max_length=16)
    source: str | None = Field(default=None, pattern="^(booking|airbnb|direct|other)$")
    code: str | None = Field(default=None, max_length=32)


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    property_id: int
    guest_name: str
    guest_ref: str
    check_in: date
    check_out: date
    status: str
    source: str
    code: str | None


class ReservationListItem(ReservationOut):
    property_name: str  # para la vista global (todas las reservas del propietario)


class ReservationImportOut(BaseModel):
    imported: int
    source: str


class InboundMessage(BaseModel):
    property_id: int
    guest_ref: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=2000)


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
    reason: str | None = None
    status: str


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    property_id: int
    guest_ref: str
    channel: str
    reservation_id: int | None = None
    handoff: bool = False
    assigned_to: int | None = None


class InboundResult(BaseModel):
    conversation: ConversationOut
    inbound: MessageOut
    draft: DraftOut | None  # None si la conversación está en atención en vivo (handoff)
    answered: bool  # True: la IA respondió sola; False: se escaló al anfitrión


class LiveReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ApproveRequest(BaseModel):
    edited_text: str | None = Field(default=None, max_length=4000)
    save_to_knowledge: bool = False  # guardar la respuesta en la ficha del piso


class InboxItem(BaseModel):
    """Borrador pendiente enriquecido para la bandeja de aprobación."""
    draft: DraftOut
    inbound_text: str
    guest_ref: str
    conversation_id: int
    property_id: int
    property_name: str


class MetricsPoint(BaseModel):
    date: str  # YYYY-MM-DD
    auto_answered: int
    escalated: int


class MetricsOut(BaseModel):
    properties: int
    conversations: int
    messages_in: int
    messages_out: int
    auto_answered: int
    escalated: int
    pending: int
    auto_rate: float  # 0..1
    minutes_saved: int
    daily: list[MetricsPoint] = []  # últimos días (tendencia)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    message: str
    read: bool
    conversation_id: int | None
    created_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor: str
    action: str
    detail: str | None
    conversation_id: int | None
    created_at: datetime
