"""CLI: connect SuperGrok / X Premium+ via browser OAuth."""

from __future__ import annotations

from datetime import datetime, timezone

import typer

from x2video.auth.oauth import (
    GrokAuthError,
    clear_credentials,
    get_status,
    login,
)

app = typer.Typer(
    help="Manage SuperGrok subscription login (browser OAuth).",
    no_args_is_help=True,
)


def _fmt_expires(expires_at: int | float | None) -> str:
    if expires_at is None:
        return "unknown"
    try:
        dt = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError, OSError):
        return str(expires_at)


@app.command("login")
def auth_login(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-authorize even if a session already exists.",
    ),
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Print the authorize URL instead of opening a browser.",
    ),
) -> None:
    """Open the browser to authorize X2Video with your SuperGrok account.

    Flow: local callback ← accounts.x.ai consent (same pattern as Grok Build).
    Tokens are stored under ~/.config/x2video/grok_auth.json and refreshed
    automatically. Usage then bills against your SuperGrok token quota.
    """
    try:
        auth = login(force=force, no_browser=no_browser)
    except GrokAuthError as exc:
        typer.secho(f"Login failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho("Login successful.", fg=typer.colors.GREEN)
    typer.echo(f"  expires_at: {_fmt_expires(auth.get('expires_at'))}")
    typer.echo("  next: set [source].provider = \"grok\" then run `x2video fetch`")


@app.command("status")
def auth_status() -> None:
    """Show whether a SuperGrok OAuth session is stored and valid."""
    status = get_status()
    if not status["logged_in"]:
        typer.echo("Not logged in.")
        typer.echo("  Run: x2video auth login")
        raise typer.Exit(code=1)

    expired = status.get("expired")
    color = typer.colors.YELLOW if expired else typer.colors.GREEN
    typer.secho("Logged in." if not expired else "Logged in (access token expired).", fg=color)
    typer.echo(f"  path:       {status['path']}")
    typer.echo(f"  expires_at: {_fmt_expires(status.get('expires_at'))}")
    typer.echo(f"  refresh:    {'yes' if status.get('has_refresh_token') else 'no'}")
    if status.get("scope"):
        typer.echo(f"  scope:      {status['scope']}")
    if expired and status.get("has_refresh_token"):
        typer.echo("  note: access token will refresh automatically on next API call")


@app.command("logout")
def auth_logout() -> None:
    """Delete the stored SuperGrok OAuth session."""
    removed = clear_credentials()
    if removed:
        typer.secho("Logged out. Credentials removed.", fg=typer.colors.GREEN)
    else:
        typer.echo("No stored credentials to remove.")
