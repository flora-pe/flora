"""Autenticación del frontend con una API privada de Cloud Run."""

from __future__ import annotations

import os


def api_headers(api_url: str) -> dict[str, str]:
    """Devuelve headers autenticados cuando se ejecuta en GCP."""

    mode = os.getenv("FLORA_API_AUTH", "none").lower()

    if mode != "gcp":
        return {}

    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    token = id_token.fetch_id_token(
        Request(),
        api_url.rstrip("/"),
    )

    return {"Authorization": f"Bearer {token}"}
