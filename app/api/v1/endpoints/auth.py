"""Authentication endpoints."""
from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException

from app.core.exceptions import BlockedUserError
from app.db.models import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    PasswordChange,
    TokenResponse,
    UserResponse,
    MessageResponse,
)
from app.services.auth_service import AuthService
from app.dependencies import get_auth_service, get_current_user_obj, get_session_id

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new user with email and password. Password must meet complexity requirements."
)
async def register(
        user_data: UserRegister,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data
        auth_service: Authentication service

    Returns:
        Created user information
    """
    user = await auth_service.register_user(user_data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user and receive access token and session ID."
)
async def login(
        credentials: UserLogin,
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenResponse:
    """
    Login user and create session.

    Args:
        credentials: User login credentials
        auth_service: Authentication service

    Returns:
        access, refresh, session_id, and user
    """
    try:
        access_token, refresh_token, session_id, user = await auth_service.login_user(
            credentials)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=session_id
        )
    except BlockedUserError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=str(e))

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
        # Expect the refresh token in the body or header
        refresh_token: str,
        auth_service: Annotated[AuthService, Depends(get_auth_service)],
        # Get the session_id so we can return it in the response
        session_id: Annotated[str, Depends(get_session_id)]
):
    """Endpoint to exchange a refresh token for a new access token."""
    new_access, current_refresh = await auth_service.refresh_session(
        refresh_token)

    return TokenResponse(
        access_token=new_access,
        refresh_token=current_refresh,
        # session_id stays the same
        session_id=session_id
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout user by invalidating the session."
)
async def logout(
        session_id: Annotated[str, Depends(get_session_id)],
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponse:
    """
    Logout user.

    Args:
        session_id: Session identifier from token
        auth_service: Authentication service

    Returns:
        Success message
    """
    await auth_service.logout_user(session_id)

    return MessageResponse(message="Successfully logged out")


@router.put(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change the current user's password. Requires authentication."
)
async def change_password(
        password_data: PasswordChange,
        current_user: Annotated[User, Depends(get_current_user_obj)],
        auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponse:
    """
    Change user password.

    Args:
        password_data: Password change data
        current_user: Current user ID
        auth_service: Authentication service

    Returns:
        Success message
    """
    await auth_service.change_password(current_user.id, password_data)

    return MessageResponse(message="Password changed successfully")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get details of the currently authenticated user based on the session token."
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user_obj)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> UserResponse:
    """
    Get current user details.

    Args:
        current_user: ID extracted from the valid session/token
    """
    return UserResponse.model_validate(current_user)