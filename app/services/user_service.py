from typing import Optional, List
from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from sqlalchemy.sql import func
from app.core.exceptions import RedisError
import time


class UserService:
    @staticmethod
    async def get_users(
            db: AsyncSession,
            user_id: int | None = None,
            first_name: str | None = None,
            last_name: str | None = None,
            is_blocked: bool | None = None,
            sort_by: str = "id",
            sort_order: str = "asc"
    ) -> List[User]:
        # ALWAYS filter out deleted users for the public user list
        query = select(User).where(User.is_deleted == False)

        # Filtering
        if user_id is not None:
            query = query.where(User.id == user_id)
        if first_name:
            query = query.where(User.first_name.ilike(f"%{first_name}%"))
        if last_name:
            query = query.where(User.last_name.ilike(f"%{last_name}%"))
        if is_blocked is not None:
            query = query.where(User.is_blocked == is_blocked)

        # Sorting
        column = getattr(User, sort_by, User.id)
        query = query.order_by(
            asc(column) if sort_order == "asc" else desc(column))

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def withdraw_balance(db: AsyncSession, user_id: int,
                               amount: int) -> User:
        # Fetch the user by ID and lock the row
        result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found.")

        # Business Logic
        if not user.first_name or not user.last_name:
            # Raise a custom exception here to catch a 403 in the router
            raise Exception(
                "Profile incomplete. Please set your first and last name.")

        if user.balance < amount:
            raise ValueError("Insufficient funds.")

        user.balance -= amount
        await db.commit()
        await db.refresh(user)
        return user

    #Soft delete service logic
    @staticmethod
    async def soft_delete_user(db: AsyncSession, user: User) -> None:
        """Marks a user as deleted and frees up their email."""
        user.is_deleted = True
        user.deleted_at = func.now()
        # Append timestamp to free up the unique constraint for future registrations
        user.email = f"deleted_{int(time.time())}_{user.email}"

        await db.commit()

    #Admin users
    @staticmethod
    async def get_admin_user_list(
            db: AsyncSession,
            user_id: int | None = None,
            first_name: str | None = None,
            last_name: str | None = None,
            is_blocked: bool | None = None,
            sort_by: str = "id",
            sort_order: str = "asc",
            include_deleted: bool = False
    ) -> List[User]:
        # Filter out deleted users by default unless explicitly requested
        query = select(User).where(User.is_deleted == include_deleted)

        # Filtering
        if user_id is not None:
            query = query.where(User.id == user_id)
        if first_name:
            query = query.where(User.first_name.ilike(f"%{first_name}%"))
        if last_name:
            query = query.where(User.last_name.ilike(f"%{last_name}%"))
        if is_blocked is not None:
            query = query.where(User.is_blocked == is_blocked)

        # Sorting
        column = getattr(User, sort_by, User.id)
        query = query.order_by(
            asc(column) if sort_order == "asc" else desc(column))

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod
    async def update_block_status(db: AsyncSession, target_user_id: int,
                                  block: bool) -> User:
        result = await db.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()

        if not user or user.is_deleted:
            return None  # Handle 404 in router

        user.is_blocked = block
        user.block_at = func.now() if block else None

        await db.commit()
        await db.refresh(user)
        return user