from collections.abc import Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from streetguard.security.rbac import Role


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    user_id: UUID | None = None
    email: str | None = None
    email_verified: bool = False
    roles: Set[Role] = frozenset({Role.PUBLIC_VISITOR})
