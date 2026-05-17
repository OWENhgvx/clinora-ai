from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import (
    create_token,
    require_user,
    user_create,
    user_get_by_username,
    verify_password,
)
from schemas.api import RegisterInput

router = APIRouter()


@router.post("/api/auth/register")
def register(body: RegisterInput):
    """Register a new user account."""
    user = user_create(
        body.username,
        body.email,
        body.password,
        body.full_name,
        body.role,
        body.profile_data(),
    )
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": user}


@router.post("/api/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form login."""
    user = user_get_by_username(form.username)
    if not user or not verify_password(form.password, user["password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token(user["id"], user["username"])
    user.pop("password", None)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/api/auth/login/json")
def login_json(body: dict):
    """JSON body login — returns a JWT token."""
    username = body.get("username", "")
    password = body.get("password", "")
    user = user_get_by_username(username)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(401, "Incorrect username or password")
    token = create_token(user["id"], user["username"])
    user.pop("password", None)
    return {"token": token, "user": user}


@router.get("/api/auth/me")
def me(user=Depends(require_user)):
    """Return the currently authenticated user's profile."""
    return user
