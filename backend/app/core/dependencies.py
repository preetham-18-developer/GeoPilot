from fastapi import Header, HTTPException
from app.core.supabase import supabase_client
import logging

logger = logging.getLogger(__name__)


def _ensure_user_exists(user_id: str, email: str = "") -> None:
    """
    Upsert a row in public.users so every authenticated user always has
    a profile record before any project FK write is attempted.

    MUST use the service-role client so the auth.users → public.users FK
    chain is bypassed for mock/demo tokens whose UUIDs only exist in
    public.users but not in auth.users.
    """
    try:
        from app.core.config import settings
        from supabase import create_client

        # Prefer service_role key (bypasses RLS + auth.users FK for public.users)
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        admin_client = create_client(settings.SUPABASE_URL, key)

        admin_client.table("users").upsert(
            {
                "id": user_id,
                "email": email or f"{user_id[:8]}@aivop.app",
            },
            on_conflict="id",
        ).execute()
        logger.debug(f"[AUTH] ensure_user_exists OK: {user_id}")
    except Exception as e:
        # Non-fatal — log a warning and continue.
        logger.warning(f"[AUTH] ensure_user_exists({user_id}) warning: {e}")


async def get_current_user(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency that parses the JWT token from the Authorization header,
    verifies it against Supabase Auth, and returns the verified user ID.
    Supports a mock token 'Bearer mock-<user-id>' for easy local testing.

    Always calls _ensure_user_exists() so public.users is never missing a row
    that projects.user_id (FK) needs to reference.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Authorization header must be Bearer token"
            )

        token = parts[1]

        # ── Mock / demo token ────────────────────────────────────────────────
        # Format:  Bearer mock-<uuid>
        # Used by the frontend workspace-switcher when no real JWT is present.
        if token.startswith("mock-"):
            mock_user_id = token.replace("mock-", "")
            logger.debug(f"[AUTH] mock-token → user_id={mock_user_id}")
            _ensure_user_exists(
                mock_user_id,
                email=f"mock-{mock_user_id[:8]}@aivop.app",
            )
            return mock_user_id

        # ── Real Supabase JWT ────────────────────────────────────────────────
        user_resp = supabase_client.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid Supabase Auth token"
            )

        real_user = user_resp.user
        real_user_id = real_user.id
        real_email = (real_user.email or "")

        logger.debug(f"[AUTH] real JWT → user_id={real_user_id}, email={real_email}")

        # Ensure public.users row exists (idempotent upsert)
        _ensure_user_exists(real_user_id, email=real_email)

        return real_user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )
