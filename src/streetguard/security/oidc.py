from collections.abc import Awaitable, Callable
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from streetguard.config import Settings, get_settings
from streetguard.security.principal import Principal
from streetguard.security.rbac import Permission, Role, has_permission

bearer = HTTPBearer(auto_error=False)


def extract_roles(claims: dict[str, Any]) -> set[Role]:
    raw_roles: list[Any] = []
    claims_roles = claims.get("roles")
    if isinstance(claims_roles, list):
        raw_roles.extend(claims_roles)
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict) and isinstance(realm_access.get("roles"), list):
        raw_roles.extend(realm_access["roles"])

    roles: set[Role] = set()
    for value in raw_roles:
        try:
            roles.add(Role(str(value)))
        except ValueError:
            continue
    return roles


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}:
            raise ValueError("Unsupported JWT algorithm")
        signing_key = jwt.PyJWKClient(str(settings.oidc_jwks_url)).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[str(header["alg"])],
            audience=settings.oidc_audience,
            issuer=str(settings.oidc_issuer_url).rstrip("/"),
            options={"require": ["sub", "iss", "aud", "exp"]},
        )
    except (jwt.PyJWTError, ValueError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The bearer token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = str(claims["sub"])
    email = claims.get("email")
    return Principal(
        subject=subject,
        email=str(email) if isinstance(email, str) else None,
        email_verified=claims.get("email_verified") is True,
        roles=extract_roles(claims),
    )


def require_permission(permission: Permission) -> Callable[..., Awaitable[Principal]]:
    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if not has_permission(principal.roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current principal lacks {permission.value}",
            )
        return principal

    return dependency
