from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.db.models import User, Role


#  Shared Base
class UserCore(BaseModel):
    """Fields common to all User-related responses"""
    id: int
    first_name: str | None = None
    last_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_activity_at: datetime

    model_config = ConfigDict(from_attributes=True)


# UserRole
class UserBase(UserCore):
    balance: int


class UserListResponse(BaseModel):
    users: List[UserBase]


# AdminRole
class AdminUserDetail(UserCore):
    """Expanded details for Admin eyes only"""
    user_id: int = Field(validation_alias="id") # Added specifically to match the internal requirement
    is_blocked: bool = Field(alias="block")
    block_at: datetime | None = None
    role: Role  # Enum directly for validation
    balance: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def format_for_admin(cls, user: User) -> Dict[int, Any]:
        """Specific helper to handle the {id: {data}} requirement"""
        # Business logic: Admins don't have balances
        balance = None if user.role == Role.ADMIN else user.balance

        # We validate the data into the schema
        data = cls.model_validate(user)
        # Manually override the balance and ensure user_id is set
        data_dict = data.model_dump(by_alias=True)
        data_dict["balance"] = balance
        data_dict["user_id"] = user.id

        return {user.id: data_dict}



class AdminUserListResponse(BaseModel):
    # Handles the specific list-of-dicts format: [ { "1": {details} } ]
    users: List[Dict[int, AdminUserDetail]]


# Action Models (Update/Requests)
class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)

class WithdrawRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")

class BalanceResponse(BaseModel):
    balance: int