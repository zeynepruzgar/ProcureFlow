from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.supabase_client import get_admin_client

# Authorization: Bearer <token> basligini okur.
# auto_error=False: baslik yoksa hata firlatmak yerine None doner; kontrolu biz yapariz.
_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    """Istegi yapan, kimligi dogrulanmis kullanici + uygulama rolu."""

    id: str
    email: str | None = None
    full_name: str | None = None
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """Bearer token'i dogrular ve kullaniciyi + rolunu dondurur.

    Adimlar:
    1) Token var mi? Yoksa 401.
    2) Token'i Supabase Auth'a sorup gecerli mi diye kontrol et.
    3) profiles tablosundan kullanicinin rolunu oku.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = credentials.credentials
    client = get_admin_client()

    # 2) Token'i dogrula (gecersizse Supabase hata/None doner).
    try:
        auth_response = client.auth.get_user(token)
    except Exception as exc:  # noqa: BLE001 - dis servis hatasini 401'e ceviriyoruz
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = getattr(auth_response, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # 3) Rolu profiles'tan oku (trigger sayesinde kayit sirasinda olusmus olmali).
    result = (
        client.table("profiles")
        .select("role, full_name")
        .eq("id", user.id)
        .limit(1)
        .execute()
    )
    row = result.data[0] if result.data else None

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=row.get("full_name") if row else None,
        role=row["role"] if row else "employee",
    )


def require_roles(*allowed_roles: str) -> Callable[..., CurrentUser]:
    """Belirli rollere sahip kullanicilara izin veren bir bagimlilik uretir.

    Kullanim: Depends(require_roles("manager", "admin"))
    """

    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return checker
