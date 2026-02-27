from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import User
from app.auth import require_internal_key, get_current_user_email
from app.encryption import encrypt, decrypt

router = APIRouter(prefix="/profile", tags=["profile"])


class LoyaltyProgram(BaseModel):
    program: str
    number: str


class ProfileIn(BaseModel):
    # Personal info — needed by the booking agent to fill passenger forms
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None   # YYYY-MM-DD
    phone: Optional[str] = None

    passport_number: Optional[str] = None
    tsa_known_traveler: Optional[str] = None
    seat_preference: Optional[str] = None
    meal_preference: Optional[str] = None
    loyalty_numbers: Optional[list[LoyaltyProgram]] = None


class ProfileOut(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    passport_number: Optional[str] = None   # masked
    tsa_known_traveler: Optional[str] = None  # masked
    seat_preference: Optional[str] = None
    meal_preference: Optional[str] = None
    loyalty_numbers: Optional[list[LoyaltyProgram]] = None


def _mask(value: str | None) -> str | None:
    """Return only the last 4 chars, rest replaced with bullets."""
    if not value:
        return None
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


@router.get("", response_model=ProfileOut)
def get_profile(
    email: str = Depends(get_current_user_email),
    _key: str = Depends(require_internal_key),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    decrypted_passport = decrypt(user.passport_number_enc)
    decrypted_tsa = decrypt(user.tsa_known_traveler_enc)

    return ProfileOut(
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        phone=user.phone,
        passport_number=_mask(decrypted_passport),
        tsa_known_traveler=_mask(decrypted_tsa),
        seat_preference=user.seat_preference,
        meal_preference=user.meal_preference,
        loyalty_numbers=[LoyaltyProgram(**lp) for lp in (user.loyalty_numbers or [])],
    )


@router.post("", response_model=ProfileOut, status_code=status.HTTP_200_OK)
def upsert_profile(
    data: ProfileIn,
    email: str = Depends(get_current_user_email),
    _key: str = Depends(require_internal_key),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(email=email)
        db.add(user)

    # Personal info
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.date_of_birth is not None:
        user.date_of_birth = data.date_of_birth
    if data.phone is not None:
        user.phone = data.phone

    # Only overwrite encrypted fields if new values were submitted
    if data.passport_number:
        user.passport_number_enc = encrypt(data.passport_number)
    if data.tsa_known_traveler:
        user.tsa_known_traveler_enc = encrypt(data.tsa_known_traveler)

    if data.seat_preference is not None:
        user.seat_preference = data.seat_preference
    if data.meal_preference is not None:
        user.meal_preference = data.meal_preference
    if data.loyalty_numbers is not None:
        user.loyalty_numbers = [lp.model_dump() for lp in data.loyalty_numbers]

    db.commit()
    db.refresh(user)

    decrypted_passport = decrypt(user.passport_number_enc)
    decrypted_tsa = decrypt(user.tsa_known_traveler_enc)

    return ProfileOut(
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        phone=user.phone,
        passport_number=_mask(decrypted_passport),
        tsa_known_traveler=_mask(decrypted_tsa),
        seat_preference=user.seat_preference,
        meal_preference=user.meal_preference,
        loyalty_numbers=[LoyaltyProgram(**lp) for lp in (user.loyalty_numbers or [])],
    )
