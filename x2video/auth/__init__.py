"""Browser OAuth for SuperGrok / X Premium+ subscription tokens.

Credentials are stored under ``~/.config/x2video/grok_auth.json`` and
refreshed automatically. See :mod:`x2video.auth.oauth`.
"""

from x2video.auth.oauth import (
    GrokAuthError,
    GrokLoginRequiredError,
    clear_credentials,
    get_access_token,
    get_status,
    login,
    logout,
)

__all__ = [
    "GrokAuthError",
    "GrokLoginRequiredError",
    "clear_credentials",
    "get_access_token",
    "get_status",
    "login",
    "logout",
]
