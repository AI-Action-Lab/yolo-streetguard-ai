from collections.abc import Set
from enum import StrEnum


class Role(StrEnum):
    PUBLIC_VISITOR = "public_visitor"
    REGISTERED_CITIZEN = "registered_citizen"
    VERIFIED_REVIEWER = "verified_reviewer"
    MUNICIPAL_AUTHORITY = "municipal_authority"
    REGIONAL_ADMINISTRATOR = "regional_administrator"
    GLOBAL_ADMINISTRATOR = "global_administrator"


class Permission(StrEnum):
    VIEW_PUBLIC_REPORTS = "reports:public:view"
    CREATE_REPORT = "reports:create"
    VIEW_OWN_REPORTS = "reports:own:view"
    REVIEW_REPORTS = "reports:review"
    UPDATE_ASSIGNED_REPORTS = "reports:assigned:update"
    MANAGE_AUTHORITIES = "authorities:manage"
    MANAGE_MODELS = "models:manage"
    MANAGE_USERS = "users:manage"
    VIEW_AUDIT_LOGS = "audit:view"
    MANAGE_SYSTEM = "system:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.PUBLIC_VISITOR: frozenset({Permission.VIEW_PUBLIC_REPORTS}),
    Role.REGISTERED_CITIZEN: frozenset(
        {
            Permission.VIEW_PUBLIC_REPORTS,
            Permission.VIEW_OWN_REPORTS,
            Permission.CREATE_REPORT,
        }
    ),
    Role.VERIFIED_REVIEWER: frozenset(
        {
            Permission.VIEW_PUBLIC_REPORTS,
            Permission.VIEW_OWN_REPORTS,
            Permission.REVIEW_REPORTS,
            Permission.CREATE_REPORT,
        }
    ),
    Role.MUNICIPAL_AUTHORITY: frozenset(
        {
            Permission.VIEW_PUBLIC_REPORTS,
            Permission.VIEW_OWN_REPORTS,
            Permission.UPDATE_ASSIGNED_REPORTS,
        }
    ),
    Role.REGIONAL_ADMINISTRATOR: frozenset(
        {
            Permission.VIEW_PUBLIC_REPORTS,
            Permission.VIEW_OWN_REPORTS,
            Permission.REVIEW_REPORTS,
            Permission.UPDATE_ASSIGNED_REPORTS,
            Permission.MANAGE_AUTHORITIES,
            Permission.VIEW_AUDIT_LOGS,
        }
    ),
    Role.GLOBAL_ADMINISTRATOR: frozenset(Permission),
}


def permissions_for_roles(roles: Set[Role]) -> frozenset[Permission]:
    permissions: set[Permission] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS[role])
    return frozenset(permissions)


def has_permission(roles: Set[Role], permission: Permission) -> bool:
    return permission in permissions_for_roles(roles)
