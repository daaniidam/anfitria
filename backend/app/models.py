"""Modelos de dominio de AnfitrIA."""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import Embedding


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Organization(Base):
    """Cuenta/equipo del cliente. Los pisos, edificios y reservas son de la org,
    no de un usuario suelto: así varios empleados comparten la misma cartera."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    # Plan de suscripción: free | starter | pro | business
    plan: Mapped[str] = mapped_column(String(16), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[list[User]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="owner")  # owner | member
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    # Se incrementa al cerrar sesión en todos los dispositivos: invalida los JWT previos.
    token_version: Mapped[int] = mapped_column(default=0)
    # Identificador del último refresh token válido (rotación de un solo uso).
    refresh_jti: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    organization: Mapped[Organization | None] = relationship(back_populates="members")
    properties: Mapped[list[Property]] = relationship(back_populates="owner")


class Building(Base):
    """Edificio o grupo de pisos con conocimiento compartido entre todos."""

    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    properties: Mapped[list[Property]] = relationship(back_populates="building")
    knowledge: Mapped[list[KnowledgeItem]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id"), default=None, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500), default=None)
    default_language: Mapped[str] = mapped_column(String(8), default="es")
    # Si True, la IA responde sola cuando tiene confianza; si no, escala al anfitrión.
    auto_answer: Mapped[bool] = mapped_column(default=True)
    # Umbral de confianza propio del piso (0-1). Si None, usa el global de la app.
    auto_answer_threshold: Mapped[float | None] = mapped_column(Float, default=None)
    # Número de WhatsApp (phone_number_id de Meta) asignado a este piso, para enrutar la entrada.
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(
        String(64), default=None, index=True
    )
    # Referencia del piso en el PMS de origen (para sincronizar sin duplicar).
    external_ref: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped[User] = relationship(back_populates="properties")
    building: Mapped[Building | None] = relationship(back_populates="properties")
    knowledge: Mapped[list[KnowledgeItem]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(back_populates="property")
    reservations: Mapped[list[Reservation]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )


class KnowledgeItem(Base):
    """Fragmento de conocimiento de un piso (wifi, check-in, normas...).

    En Fase 3 se añade una columna de embedding (pgvector) para el RAG.
    """

    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Pertenece a un piso concreto o a un edificio (conocimiento compartido). Exactamente uno.
    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"), default=None, index=True
    )
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id"), default=None, index=True
    )
    category: Mapped[str] = mapped_column(String(64), default="general")
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Embedding(), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    property: Mapped[Property | None] = relationship(back_populates="knowledge")
    building: Mapped[Building | None] = relationship(back_populates="knowledge")


class Reservation(Base):
    """Reserva de un huésped en un piso. Da a la IA el contexto de la estancia
    (fase pre-llegada / durante / salida) para responder con datos concretos."""

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    guest_name: Mapped[str] = mapped_column(String(160))
    guest_ref: Mapped[str] = mapped_column(String(64), index=True)  # teléfono del huésped
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    # upcoming | active | past | cancelled
    status: Mapped[str] = mapped_column(String(16), default="upcoming")
    # De dónde viene la reserva: booking | airbnb | direct | other
    source: Mapped[str] = mapped_column(String(16), default="direct")
    code: Mapped[str | None] = mapped_column(String(32), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    property: Mapped[Property] = relationship(back_populates="reservations")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    guest_ref: Mapped[str] = mapped_column(String(64), index=True)  # teléfono o id del huésped
    channel: Mapped[str] = mapped_column(String(32), default="sim")
    # Reserva a la que pertenece esta conversación (para tenerlo todo relacionado).
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id"), default=None, index=True
    )
    # Handoff en vivo: si True, la IA se aparta y responde una persona del equipo.
    handoff: Mapped[bool] = mapped_column(default=False)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    property: Mapped[Property] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(8))  # "in" | "out"
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8), default="es")
    # ID externo del canal (p. ej. el message id de WhatsApp). Único: sirve para
    # descartar reintentos del webhook y no procesar dos veces el mismo mensaje.
    external_id: Mapped[str | None] = mapped_column(
        String(128), default=None, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    draft: Mapped[Draft | None] = relationship(
        back_populates="inbound_message", cascade="all, delete-orphan", uselist=False
    )


class Draft(Base):
    """Borrador de respuesta generado por la IA para un mensaje entrante."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    inbound_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8), default="es")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    model: Mapped[str] = mapped_column(String(64), default="mock")
    # Por qué actuó así: auto | manual | sin_info | poca_confianza
    reason: Mapped[str | None] = mapped_column(String(24), default=None)
    # pending | approved | edited | sent
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    inbound_message: Mapped[Message] = relationship(back_populates="draft")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(32))  # "ai" | "host"
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, default=None)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), default=None, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Integration(Base):
    """Conexión de la organización con un PMS / Channel Manager (Guesty, etc.)."""

    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="connected")  # connected | disconnected
    account: Mapped[str | None] = mapped_column(String(120), default=None)
    # Estado específico del proveedor (p. ej. phone_number_id y plantillas de WhatsApp).
    config: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Notification(Base):
    """Aviso para el anfitrión (p. ej. una escalada que requiere su respuesta).

    Permite alertar cuando algo se escala aunque no esté mirando el panel.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), default=None, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), default="escalation")
    message: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
