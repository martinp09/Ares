from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient, get_control_plane_client


def test_get_control_plane_client_returns_supabase_adapter_when_requested() -> None:
    settings = Settings(_env_file=None, control_plane_backend="supabase")

    client = get_control_plane_client(settings)

    assert isinstance(client, SupabaseControlPlaneClient)
