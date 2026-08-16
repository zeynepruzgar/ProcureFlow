from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_admin_client() -> Client:
    """Servis rolu (service_role) ile Supabase istemcisi dondurur.

    Servis rolu RLS'i bypass eder; bu yuzden YALNIZCA backend'de kullanilir,
    asla tarayiciya sizdirilmez. Token dogrulama ve profil okuma icin kullaniriz.

    Not: Bu fonksiyon YALNIZCA gercekten DB/Auth cagrisi yapilinca cagrilmali.
    Service dependency factory'leri istemciyi lazy acar; boyce auth-only
    testler (401) CI'da env olmadan da calisir.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env."
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
