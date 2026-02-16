from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.user import UserListResponse, UserBase, UserUpdate, WithdrawRequest, BalanceResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

# Define common dependencies as Annotated types for cleaner signatures
AsyncDB = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserID = Annotated[int, Depends(get_current_user)]

@router.get(
    "/",
    # Return a list directly or wrapped in a dict
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users",
    description="Retrieve a filtered and sorted list of users. Requires authentication."
)
async def list_users(
    db: AsyncDB,
    _: CurrentUserID,
    user_id: int | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    is_blocked: bool | None = None,
    sort_by: str = Query("id", pattern="^(id|balance|last_activity_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
) -> dict:
    users = await UserService.get_users(
        db, user_id, first_name, last_name, is_blocked, sort_by, sort_order
    )
    return {"users": users}


@router.get(
    "/me",
    response_model=UserBase,
    summary="Get profile",
    description="Get details of the currently authenticated user."
)
async def get_my_profile(
        db: AsyncDB,
        user_id: CurrentUserID
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.first_name or not user.last_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please update your profile with first and last name."
        )
    return user


@router.patch(
    "/me",
    response_model=UserBase,
    summary="Update profile"
)
async def update_profile(
        data: UserUpdate,
        db: AsyncDB,
        user_id: CurrentUserID
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if data.first_name: user.first_name = data.first_name
    if data.last_name: user.last_name = data.last_name

    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/me/withdraw",
    response_model=BalanceResponse,
    summary="Withdraw funds"
)
async def withdraw(
        request: WithdrawRequest,
        db: AsyncDB,
        user_id: CurrentUserID
) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    try:
        updated_user = await UserService.withdraw_balance(db, user,
                                                          request.amount)
        return {"balance": updated_user.balance}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))