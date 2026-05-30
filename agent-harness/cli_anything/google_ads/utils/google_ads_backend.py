"""Google Ads API backend wrapper.

Handles client initialization, error translation, and utility functions
for interacting with the Google Ads API via the google-ads-python library.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def find_google_ads_library() -> str:
    """Verify the google-ads library is importable. Raises RuntimeError if not."""
    try:
        import google.ads.googleads.client  # noqa: F401
        return "google-ads"
    except ImportError:
        raise RuntimeError(
            "google-ads library not found.\n"
            "Install with: pip install google-ads"
        )


def get_api_version_info() -> dict:
    """Return available API version info."""
    try:
        import google.ads.googleads as pkg
        version = getattr(pkg, "__version__", "unknown")
        return {"library_version": version, "default_api_version": "v24"}
    except ImportError:
        return {"library_version": "not installed", "default_api_version": "v24"}


def format_customer_id(customer_id: str) -> str:
    """Normalize a customer ID to digits only (strip dashes/spaces)."""
    return customer_id.replace("-", "").replace(" ", "").strip()


def micros_to_currency(micros: int, decimals: int = 2) -> float:
    """Convert micros to currency units."""
    return round(micros / 1_000_000, decimals)


def currency_to_micros(amount: float) -> int:
    """Convert currency units to micros."""
    return int(amount * 1_000_000)


def translate_google_ads_error(exc) -> str:
    """Extract human-readable error message from GoogleAdsException."""
    try:
        from google.ads.googleads.errors import GoogleAdsException
        if isinstance(exc, GoogleAdsException):
            messages = []
            for error in exc.failure.errors:
                loc = ""
                if error.location:
                    fields = [f.field_name for f in error.location.field_path_elements]
                    loc = f" (field: {'.'.join(fields)})" if fields else ""
                messages.append(f"{error.message}{loc}")
            if messages:
                return "; ".join(messages)
            return f"Google Ads API error (request_id: {exc.request_id})"
    except Exception:
        pass
    return str(exc)


def build_resource_name(resource_type: str, customer_id: str, *ids) -> str:
    """Build a Google Ads resource name.

    Examples:
        build_resource_name("campaigns", "1234567890", "111")
        → "customers/1234567890/campaigns/111"
    """
    cid = format_customer_id(customer_id)
    path = f"customers/{cid}/{resource_type}"
    for id_ in ids:
        path += f"/{id_}"
    return path


class GoogleAdsBackend:
    """Thin wrapper around GoogleAdsClient for the CLI.

    Manages client lifecycle and provides convenience methods.
    """

    def __init__(self, config_path: Optional[str] = None, api_version: str = "v24"):
        self.config_path = config_path
        self.api_version = api_version
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from cli_anything.google_ads.core.auth import get_client
            self._client = get_client(self.config_path, self.api_version)
        return self._client

    def get_service(self, service_name: str):
        """Get a Google Ads service client."""
        return self.client.get_service(service_name)

    def get_type(self, type_name: str):
        """Get a Google Ads message type."""
        return self.client.get_type(type_name)

    def search_stream(self, customer_id: str, query: str):
        """Execute a GAQL query and yield result batches."""
        ga_service = self.client.get_service("GoogleAdsService")
        cid = format_customer_id(customer_id)
        return ga_service.search_stream(customer_id=cid, query=query)

    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        from cli_anything.google_ads.core.auth import load_config
        cfg = load_config(self.config_path)
        return bool(cfg.get("developer_token"))
