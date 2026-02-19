from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_activity_at: datetime
    balance: int

    model_config = ConfigDict(from_attributes=True)

class UserListResponse(BaseModel):
    users: List[UserBase]

class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)

class WithdrawRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")

class BalanceResponse(BaseModel):
    balance: int