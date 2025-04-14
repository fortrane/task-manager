from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_active_user
from app.models import TelegramUser, User
from app.schemas import (
    TelegramUser as TelegramUserSchema,
    TelegramUserCreate,
    TelegramUserUpdate,
)

router = APIRouter()


@router.post("/connect", response_model=TelegramUserSchema)
async def connect_telegram(
        telegram_data: TelegramUserCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    # Check if user already has a connected Telegram account
    existing_connection = (
        db.query(TelegramUser)
        .filter(TelegramUser.user_id == current_user.id)
        .first()
    )

    if existing_connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a connected Telegram account",
        )

    # Create new Telegram connection
    telegram_user = TelegramUser(
        **telegram_data.dict(),
        user_id=current_user.id,
    )

    db.add(telegram_user)
    db.commit()
    db.refresh(telegram_user)

    return telegram_user


@router.get("/connection", response_model=TelegramUserSchema)
async def get_telegram_connection(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    telegram_user = (
        db.query(TelegramUser)
        .filter(TelegramUser.user_id == current_user.id)
        .first()
    )

    if not telegram_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram connection found",
        )

    return telegram_user


@router.put("/connection", response_model=TelegramUserSchema)
async def update_telegram_connection(
        telegram_data: TelegramUserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> Any:
    telegram_user = (
        db.query(TelegramUser)
        .filter(TelegramUser.user_id == current_user.id)
        .first()
    )

    if not telegram_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram connection found",
        )

    update_data = telegram_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(telegram_user, field, value)

    db.add(telegram_user)
    db.commit()
    db.refresh(telegram_user)

    return telegram_user


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def delete_telegram_connection(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
) -> None:
    telegram_user = (
        db.query(TelegramUser)
        .filter(TelegramUser.user_id == current_user.id)
        .first()
    )

    if not telegram_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram connection found",
        )

    db.delete(telegram_user)
    db.commit()


@router.post("/webhook")
async def telegram_webhook(
        update: Dict[str, Any] = Body(...),
        db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Endpoint for Telegram webhook.
    This endpoint will be called by Telegram when there's a new message.
    The actual processing of the webhook will be handled by the Telegram bot service.
    """
    # This endpoint just accepts the webhook and returns a success response
    # The actual processing will be done by the Telegram bot service
    # Not for local development!

    return {"status": "success"}