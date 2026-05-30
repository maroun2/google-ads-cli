"""Authentication and configuration management for google-ads-cli.

Handles OAuth2 setup, credential storage, and client initialization.
Config stored at ~/.config/google-ads-cli/credentials.yaml
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "google-ads-cli"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "credentials.yaml"

GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_AUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"


def get_config_path(path: Optional[str] = None) -> Path:
    """Resolve config path: explicit arg > GOOGLE_ADS_CLI_CONFIG env > default."""
    if path:
        return Path(path)
    env = os.environ.get("GOOGLE_ADS_CLI_CONFIG")
    if env:
        return Path(env)
    return DEFAULT_CONFIG_PATH


def load_config(path: Optional[str] = None) -> dict:
    """Load credentials.yaml. Returns empty dict if not found."""
    config_path = get_config_path(path)
    if not config_path.exists():
        return {}
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return data


def save_config(config: dict, path: Optional[str] = None):
    """Save config dict to credentials.yaml."""
    config_path = get_config_path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_client(config_path: Optional[str] = None, version: str = "v24"):
    """Build and return a GoogleAdsClient from stored credentials.

    Raises:
        RuntimeError: if config is missing or invalid.
    """
    from google.ads.googleads.client import GoogleAdsClient

    config = load_config(config_path)
    if not config:
        cfg = get_config_path(config_path)
        raise RuntimeError(
            f"No credentials found at {cfg}.\n"
            "Run 'google-ads-cli auth setup' to configure."
        )
    required = ["developer_token"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise RuntimeError(
            f"Config missing required fields: {', '.join(missing)}.\n"
            "Run 'google-ads-cli auth setup' to reconfigure."
        )

    # Ensure use_proto_plus is set (required by GoogleAdsClient)
    if "use_proto_plus" not in config:
        config["use_proto_plus"] = False

    try:
        return GoogleAdsClient.load_from_dict(config, version=version)
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize Google Ads client: {exc}") from exc


def test_credentials(config_path: Optional[str] = None, version: str = "v24") -> dict:
    """Test credentials by listing accessible customers.

    Returns:
        dict with 'ok', 'customer_count', and optional 'error' keys.
    """
    try:
        client = get_client(config_path, version)
        svc = client.get_service("CustomerService")
        response = svc.list_accessible_customers()
        customers = list(response.resource_names)
        return {"ok": True, "customer_count": len(customers), "resource_names": customers}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_oauth2_flow(client_id: str, client_secret: str) -> str:
    """Run OAuth2 installed-app flow and return refresh token.

    Opens browser for user consent, then returns the refresh token.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_AUTH_TOKEN_URI,
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config, scopes=[GOOGLE_ADS_SCOPE]
    )
    credentials = flow.run_local_server(port=0, prompt="consent",
                                        authorization_prompt_message="")
    return credentials.refresh_token


def interactive_setup(config_path: Optional[str] = None) -> dict:
    """Interactive auth setup wizard. Returns saved config dict."""
    print()
    print("  Google Ads CLI — Authentication Setup")
    print("  ──────────────────────────────────────")
    print()
    print("  You need:")
    print("  1. A Google Ads developer token")
    print("     → https://developers.google.com/google-ads/api/docs/first-call/dev-token")
    print("  2. OAuth2 client ID + secret (Desktop app type)")
    print("     → https://console.cloud.google.com/apis/credentials")
    print()

    developer_token = _prompt("  Developer token: ").strip()
    client_id = _prompt("  OAuth2 client ID: ").strip()
    client_secret = _prompt("  OAuth2 client secret: ").strip()

    print()
    print("  Opening browser for Google account authorization...")
    print("  (If browser doesn't open, copy the URL shown below)")
    print()

    try:
        refresh_token = run_oauth2_flow(client_id, client_secret)
    except Exception as exc:
        raise RuntimeError(f"OAuth2 flow failed: {exc}") from exc

    print()
    login_customer_id = _prompt(
        "  Manager account ID (leave blank if not using MCC): "
    ).strip().replace("-", "")

    config = {
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "use_proto_plus": False,
    }
    if login_customer_id:
        config["login_customer_id"] = login_customer_id

    save_config(config, config_path)
    return config


def _prompt(msg: str) -> str:
    """Prompt with fallback for non-interactive environments."""
    try:
        return input(msg)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
