"""Access control helpers."""

from app.data.enums import StaffRole


def has_role(roles: set[StaffRole], required: StaffRole) -> bool:
    """Check staff role hierarchy."""

    if StaffRole.OWNER in roles:
        return True
    if required == StaffRole.ADMIN:
        return StaffRole.ADMIN in roles
    if required == StaffRole.MANAGER:
        return bool(roles & {StaffRole.MANAGER, StaffRole.ADMIN})
    return required in roles
