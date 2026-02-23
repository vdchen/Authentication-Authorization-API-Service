from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User
from app.db.session import get_async_session
from app.dependencies import get_current_admin, get_current_user
from app.services.user_service import UserService
from app.schemas.user import AdminUserListResponse, AdminUserDetail

router = APIRouter(prefix="/admin", tags=["Admin Management"])

# Define common dependencies as Annotated types for cleaner signatures
AsyncDB = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserID = Annotated[int, Depends(get_current_user)]

@router.get("/users", response_model=AdminUserListResponse)
async def list_users_admin(
    db: AsyncDB,
    admin: Annotated[User, Depends(get_current_admin)],
    user_id: int | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    is_blocked: bool | None = None,
    sort_by: str = Query("id", pattern="^(id|balance|last_activity_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
):
    users = await UserService.get_admin_user_list(
        db, user_id, first_name, last_name, is_blocked, sort_by, sort_order
    )

    return {"users": [AdminUserDetail.format_for_admin(u) for u in users]}


@router.patch("/users/{target_id}/block")
async def block_user(
        target_id: int,
        block: bool,
        db: AsyncDB,
        admin: Annotated[User, Depends(get_current_admin)]
):
    # Cannot delete/block oneself
    if admin.id == target_id:
        raise HTTPException(status_code=400,
                            detail="You cannot block yourself.")

    user = await UserService.update_block_status(db, target_id, block)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message": f"User {'blocked' if block else 'unblocked'} successfully"}


@router.get("/users/deleted", response_model=AdminUserListResponse)
async def get_deleted_users(
    db: AsyncDB,
    admin: Annotated[User, Depends(get_current_admin)]
):
    users = await UserService.get_admin_user_list(db, include_deleted=True)
    return {"users": [AdminUserDetail.format_for_admin(u) for u in users]}