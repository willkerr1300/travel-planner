from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)

    # Encrypted at the application layer using Fernet before writing to DB
    passport_number_enc = Column(String, nullable=True)
    tsa_known_traveler_enc = Column(String, nullable=True)

    # Plain-text preferences — not sensitive
    seat_preference = Column(String(50), nullable=True)
    meal_preference = Column(String(50), nullable=True)

    # JSON array of {program: str, number: str}
    loyalty_numbers = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
