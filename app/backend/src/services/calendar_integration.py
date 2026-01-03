"""Service layer for CalendarIntegration operations."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import decrypt_token, encrypt_token
from src.db.models.calendar_integration import CalendarIntegration, IntegrationStatus
from src.schemas.calendar_integration import (
    CalendarIntegrationCreate,
    CalendarIntegrationUpdate,
)


async def create_integration(
    db: AsyncSession, user_id: uuid.UUID, integration_data: CalendarIntegrationCreate
) -> CalendarIntegration:
    """Create a new calendar integration with encrypted tokens.

    Args:
        db: Database session
        user_id: ID of the user creating the integration
        integration_data: Integration data including OAuth tokens

    Returns:
        Created CalendarIntegration instance

    Raises:
        HTTPException: 409 if integration already exists for this user+provider
    """
    # Encrypt tokens before storage
    encrypted_access = encrypt_token(integration_data.access_token)
    encrypted_refresh = encrypt_token(integration_data.refresh_token)

    integration = CalendarIntegration(
        user_id=user_id,
        provider=integration_data.provider,
        status="ACTIVE",  # Start as active after successful OAuth
        access_token=encrypted_access,
        refresh_token=encrypted_refresh,
        token_expires_at=integration_data.token_expires_at,
        scopes=integration_data.scopes,
        calendars_synced=integration_data.calendars_synced,
        sync_enabled=integration_data.sync_enabled,
    )

    db.add(integration)

    try:
        await db.commit()
        await db.refresh(integration)
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Calendar integration already exists for provider {integration_data.provider.value}",
        ) from err

    return integration


async def get_user_integrations(db: AsyncSession, user_id: uuid.UUID) -> list[CalendarIntegration]:
    """Get all calendar integrations for a user.

    Args:
        db: Database session
        user_id: ID of the user

    Returns:
        List of CalendarIntegration instances
    """
    result = await db.execute(
        select(CalendarIntegration)
        .where(CalendarIntegration.user_id == user_id)
        .order_by(CalendarIntegration.created_at.desc())
    )
    return list(result.scalars().all())


async def get_integration_by_id(
    db: AsyncSession, user_id: uuid.UUID, integration_id: uuid.UUID
) -> CalendarIntegration:
    """Get a specific calendar integration by ID.

    Args:
        db: Database session
        user_id: ID of the user (for authorization)
        integration_id: ID of the integration

    Returns:
        CalendarIntegration instance

    Raises:
        HTTPException: 404 if not found or doesn't belong to user
    """
    result = await db.execute(
        select(CalendarIntegration)
        .where(CalendarIntegration.id == integration_id)
        .where(CalendarIntegration.user_id == user_id)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar integration not found",
        )

    return integration


async def update_integration(
    db: AsyncSession,
    user_id: uuid.UUID,
    integration_id: uuid.UUID,
    update_data: CalendarIntegrationUpdate,
) -> CalendarIntegration:
    """Update a calendar integration.

    Args:
        db: Database session
        user_id: ID of the user (for authorization)
        integration_id: ID of the integration to update
        update_data: Fields to update

    Returns:
        Updated CalendarIntegration instance

    Raises:
        HTTPException: 404 if not found
    """
    integration = await get_integration_by_id(db, user_id, integration_id)

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(integration, field, value)

    await db.commit()
    await db.refresh(integration)

    return integration


async def disconnect_integration(
    db: AsyncSession, user_id: uuid.UUID, integration_id: uuid.UUID
) -> None:
    """Disconnect and delete a calendar integration.

    This will also cascade delete all associated calendar events.

    Args:
        db: Database session
        user_id: ID of the user (for authorization)
        integration_id: ID of the integration to disconnect

    Raises:
        HTTPException: 404 if not found
    """
    integration = await get_integration_by_id(db, user_id, integration_id)

    await db.delete(integration)
    await db.commit()


async def get_decrypted_tokens(
    db: AsyncSession, user_id: uuid.UUID, integration_id: uuid.UUID
) -> tuple[str, str]:
    """Get decrypted access and refresh tokens for an integration.

    This is used internally by sync services, NOT exposed via API.

    Args:
        db: Database session
        user_id: ID of the user
        integration_id: ID of the integration

    Returns:
        Tuple of (access_token, refresh_token) decrypted

    Raises:
        HTTPException: 404 if not found
    """
    integration = await get_integration_by_id(db, user_id, integration_id)

    access_token = decrypt_token(integration.access_token)
    refresh_token = decrypt_token(integration.refresh_token)

    return access_token, refresh_token


async def update_integration_tokens(
    db: AsyncSession,
    integration_id: uuid.UUID,
    new_access_token: str,
    new_token_expires_at: datetime,
) -> None:
    """Update access token after refresh (internal use only).

    Args:
        db: Database session
        integration_id: ID of the integration
        new_access_token: New access token from OAuth refresh
        new_token_expires_at: New expiration timestamp
    """
    result = await db.execute(
        select(CalendarIntegration).where(CalendarIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()

    if integration:
        integration.access_token = encrypt_token(new_access_token)
        integration.token_expires_at = new_token_expires_at
        integration.status = IntegrationStatus.ACTIVE  # Reset status on successful refresh
        await db.commit()
