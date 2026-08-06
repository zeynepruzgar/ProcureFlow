from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUser)
def read_me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Giris yapmis kullanicinin profilini ve rolunu dondurur."""
    return user


@router.get("/admin/check", response_model=CurrentUser)
def admin_only(
    user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> CurrentUser:
    """RBAC ornegi: yalnizca 'admin' veya 'manager' erisebilir.

    Diger roller 403 (Forbidden) alir. Ileriki fazlarda gercek uclarda
    ayni desen kullanilacak.
    """
    return user
