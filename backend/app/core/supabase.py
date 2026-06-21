import contextvars
from supabase import create_client, Client
from app.core.config import settings

# Thread/Task-local context for request-scoped supabase clients
_client_ctx = contextvars.ContextVar("supabase_client")

# The global/fallback client
_global_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class RequestScopedSupabaseClientProxy:
    def __getattr__(self, name):
        try:
            client = _client_ctx.get()
        except LookupError:
            client = _global_client
        return getattr(client, name)

# Initialize Supabase client proxy
supabase_client = RequestScopedSupabaseClientProxy()

def get_supabase() -> Client:
    """Returns the current active Supabase client."""
    return supabase_client

