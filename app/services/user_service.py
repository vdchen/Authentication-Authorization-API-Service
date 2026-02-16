from typing import Optional, List
from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.core.exceptions import RedisError


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
        query = select(User)

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
    async def withdraw_balance(db: AsyncSession, user: User,
                               amount: int) -> User:
        if not user.first_name or not user.last_name:
            raise ValueError(
                "Profile must have first and last name to withdraw.")

        if user.balance < amount:
            raise ValueError("Insufficient funds.")

        user.balance -= amount
        await db.commit()
        await db.refresh(user)
        return user