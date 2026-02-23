from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_session
from app.db.models import User, Role
from app.dependencies import get_current_user_obj
from app.schemas.user import UserListResponse, UserBase, UserUpdate, WithdrawRequest, BalanceResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

# Define common dependencies as Annotated types for cleaner signatures
AsyncDB = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUser = Annotated[User, Depends(get_current_user_obj)]

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
    _: CurrentUser,
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
        current_user: CurrentUser
) -> User:

    if not current_user.first_name or not current_user.last_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please update your profile with first and last name."
        )
    return current_user


@router.patch(
    "/me",
    response_model=UserBase,
    summary="Update profile"
)
async def update_profile(
        data: UserUpdate,
        db: AsyncDB,
        current_user: CurrentUser
) -> User:

    if data.first_name: current_user.first_name = data.first_name
    if data.last_name: current_user.last_name = data.last_name

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get(
    "/me/balance",
    response_model=BalanceResponse,
    summary="Get current balance",
    description="Retrieve only the user's balance. Optimized for speed."
)
async def get_balance(
        db: AsyncDB,
        current_user: CurrentUser,
) -> dict:
    if current_user.role == Role.ADMIN:
        raise HTTPException(status_code=400,
                            detail="Admins do not have a balance.")
    # only 'balance' column is selected, not the whole User object
    result = await db.execute(select(User.balance).where(User.id == current_user.id))
    balance = result.scalar()

    if balance is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"balance": balance}


@router.post(
    "/me/withdraw",
    response_model=BalanceResponse,
    summary="Withdraw funds",
    description="Decrease user balance. Requires profile to be complete (first/last name)."
)
async def withdraw(
        request: WithdrawRequest,
        db: AsyncDB,
        current_user: CurrentUser,
) -> dict:

    if current_user.role == Role.ADMIN:
        raise HTTPException(status_code=400,
                            detail="Admins cannot perform financial transactions.")

    try:
        updated_user = await UserService.withdraw_balance(
            db,
            user_id=current_user.id,
            amount=request.amount
        )
        return {"balance": updated_user.balance}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))
    except Exception as e:
        # Catching the 403 logic if it's moved to the service
        raise HTTPException(status_code=403, detail=str(e))


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my account"
)
async def delete_my_account(
        db: AsyncDB,
        current_user: CurrentUser
) -> None:
    #Perform Soft Delete (is_deleted = True, update email)
    await UserService.soft_delete_user(db, current_user)
    return None