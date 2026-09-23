"""Modelos de dominio de AnfitrIA."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import Embedding


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    properties: Mapped[list[Property]] = relationship(back_populates="owner")


class Building(Base):
    """Edificio o grupo de pisos con conocimiento compartido entre todos."""

    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
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
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id"), default=None, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500), default=None)
    default_language: Mapped[str] = mapped_column(String(8), default="es")
    # Si True, la IA responde sola cuando tiene confianza; si no, escala al anfitrión.
    auto_answer: Mapped[bool] = mapped_column(default=True)
    # Número de WhatsApp (phone_number_id de Meta) asignado a este piso, para enrutar la entrada.
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped[User] = relationship(back_populates="properties")
    building: Mapped[Building | None] = relationship(back_populates="properties")
    knowledge: Mapped[list[KnowledgeItem]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(back_populates="property")


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


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    guest_ref: Mapped[str] = mapped_column(String(64), index=True)  # teléfono o id del huésped
    channel: Mapped[str] = mapped_column(String(32), default="sim")
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
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|edited|sent
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
