from streetguard.security.rbac import Permission, Role, has_permission, permissions_for_roles


def test_public_visitor_has_only_public_read_access() -> None:
    permissions = permissions_for_roles({Role.PUBLIC_VISITOR})

    assert permissions == {Permission.VIEW_PUBLIC_REPORTS}
    assert not has_permission({Role.PUBLIC_VISITOR}, Permission.CREATE_REPORT)


def test_reviewer_cannot_manage_models_or_users() -> None:
    assert has_permission({Role.VERIFIED_REVIEWER}, Permission.REVIEW_REPORTS)
    assert not has_permission({Role.VERIFIED_REVIEWER}, Permission.MANAGE_MODELS)
    assert not has_permission({Role.VERIFIED_REVIEWER}, Permission.MANAGE_USERS)


def test_global_administrator_has_every_permission() -> None:
    assert permissions_for_roles({Role.GLOBAL_ADMINISTRATOR}) == frozenset(Permission)


def test_roles_are_additive() -> None:
    permissions = permissions_for_roles({Role.REGISTERED_CITIZEN, Role.MUNICIPAL_AUTHORITY})

    assert Permission.CREATE_REPORT in permissions
    assert Permission.UPDATE_ASSIGNED_REPORTS in permissions
    assert Permission.MANAGE_AUTHORITIES not in permissions
