from fastapi import Header, HTTPException, Depends
from app.core.supabase import supabase_client
import logging

logger = logging.getLogger(__name__)

async def get_current_user(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency that parses the JWT token from the Authorization header,
    verifies it against Supabase Auth, and returns the verified user ID.
    Supports a mock token 'bearer mock-user-id' for easy local testing.
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
        
        # Local development / Testing helper: allow mock tokens
        if token.startswith("mock-"):
            mock_user_id = token.replace("mock-", "")
            # Ensure mock user exists in public.users to avoid foreign key errors
            # We can upsert a mock user profile
            try:
                supabase_client.table("users").upsert({
                    "id": mock_user_id,
                    "email": f"{mock_user_id}@example.com",
                    "full_name": f"Mock User {mock_user_id[:4]}",
                    "company_name": f"Mock Company {mock_user_id[:4]}",
                    "role": "customer",
                    "subscription_plan": "pro"
                }).execute()
            except Exception as e:
                logger.error(f"Error upserting mock user: {e}")
            return mock_user_id
            
        # Verify token using Supabase auth
        user_resp = supabase_client.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid Supabase Auth token"
            )
            
        return user_resp.user.id
    except Exception as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )
