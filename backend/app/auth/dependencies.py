"""
RBAC dependency injection.

Usage in any route added in later phases:

    from app.auth.dependencies import require_role

    @router.get("/some-student-only-endpoint")
    async def handler(user: dict = Depends(require_role(["student"]))):
        ...

`get_current_user` does the actual token verification + DB lookup.
`require_role` wraps it and additionally checks the role claim, so most
routes only ever need to depend on `require_role(...)`.
"""

from bson import ObjectId
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.security import decode_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.mongodb import get_database

# tokenUrl is just used to populate the "Authorize" button in /docs;
# the actual login endpoint is added in this same phase at /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    if token is None:
        raise UnauthorizedError(detail="Missing authentication token")

    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError(detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError(detail="A valid access token is required")

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if user is None or not user.get("is_active", True):
        raise UnauthorizedError(detail="User not found or inactive")

    return user


def require_role(allowed_roles: list[str]):
    """
    Returns a dependency that both authenticates the request and checks
    the user's role is one of `allowed_roles`. Parent-to-student scoping
    (a parent can only see *their linked* students) is a separate check
    added inside each dashboard endpoint in later phases -- this only
    handles the coarse "is this role allowed to call this endpoint" layer.
    """

    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise ForbiddenError(detail=f"This endpoint requires role: {', '.join(allowed_roles)}")
        return user

    return dependency
