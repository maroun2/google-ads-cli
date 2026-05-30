"""Unit tests for google-ads-cli core modules.

All tests use synthetic data — no real API calls.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import yaml

# ── Auth tests ────────────────────────────────────────────────────────────────

class TestAuthConfigPath:
    def test_default_path(self):
        from cli_anything.google_ads.core.auth import get_config_path
        result = get_config_path(None)
        assert str(result).endswith("google-ads-cli/credentials.yaml")

    def test_explicit_path(self):
        from cli_anything.google_ads.core.auth import get_config_path
        result = get_config_path("/tmp/my_creds.yaml")
        assert str(result) == "/tmp/my_creds.yaml"

    def test_env_var(self, monkeypatch):
        from cli_anything.google_ads.core.auth import get_config_path
        monkeypatch.setenv("GOOGLE_ADS_CLI_CONFIG", "/tmp/env_creds.yaml")
        result = get_config_path(None)
        assert str(result) == "/tmp/env_creds.yaml"

    def test_explicit_overrides_env(self, monkeypatch):
        from cli_anything.google_ads.core.auth import get_config_path
        monkeypatch.setenv("GOOGLE_ADS_CLI_CONFIG", "/tmp/env_creds.yaml")
        result = get_config_path("/tmp/explicit.yaml")
        assert str(result) == "/tmp/explicit.yaml"


class TestAuthLoadConfig:
    def test_missing_file_returns_empty(self):
        from cli_anything.google_ads.core.auth import load_config
        result = load_config("/nonexistent/path/credentials.yaml")
        assert result == {}

    def test_valid_yaml(self, tmp_path):
        from cli_anything.google_ads.core.auth import load_config
        cfg_file = tmp_path / "credentials.yaml"
        cfg_file.write_text(yaml.dump({
            "developer_token": "test_token",
            "client_id": "client123",
            "client_secret": "secret456",
            "refresh_token": "refresh789",
            "use_proto_plus": False,
        }))
        result = load_config(str(cfg_file))
        assert result["developer_token"] == "test_token"
        assert result["client_id"] == "client123"
        assert result["use_proto_plus"] is False

    def test_empty_yaml_returns_empty(self, tmp_path):
        from cli_anything.google_ads.core.auth import load_config
        cfg_file = tmp_path / "credentials.yaml"
        cfg_file.write_text("")
        result = load_config(str(cfg_file))
        assert result == {}


class TestAuthSaveConfig:
    def test_creates_directory(self, tmp_path):
        from cli_anything.google_ads.core.auth import save_config
        cfg_path = tmp_path / "subdir" / "credentials.yaml"
        config = {"developer_token": "tok", "use_proto_plus": False}
        save_config(config, str(cfg_path))
        assert cfg_path.exists()
        loaded = yaml.safe_load(cfg_path.read_text())
        assert loaded["developer_token"] == "tok"

    def test_overwrites_existing(self, tmp_path):
        from cli_anything.google_ads.core.auth import save_config
        cfg_path = tmp_path / "creds.yaml"
        save_config({"developer_token": "old"}, str(cfg_path))
        save_config({"developer_token": "new"}, str(cfg_path))
        loaded = yaml.safe_load(cfg_path.read_text())
        assert loaded["developer_token"] == "new"


class TestAuthGetClient:
    def test_no_config_raises(self, tmp_path):
        from cli_anything.google_ads.core.auth import get_client
        with pytest.raises(RuntimeError, match="No credentials found"):
            get_client(str(tmp_path / "nonexistent.yaml"))

    def test_missing_developer_token_raises(self, tmp_path):
        from cli_anything.google_ads.core.auth import get_client
        cfg_path = tmp_path / "creds.yaml"
        cfg_path.write_text(yaml.dump({"use_proto_plus": False}))
        with pytest.raises(RuntimeError, match="developer_token"):
            get_client(str(cfg_path))


# ── Backend utils tests ───────────────────────────────────────────────────────

class TestBackendUtils:
    def test_format_customer_id_strips_dashes(self):
        from cli_anything.google_ads.utils.google_ads_backend import format_customer_id
        assert format_customer_id("123-456-7890") == "1234567890"

    def test_format_customer_id_strips_spaces(self):
        from cli_anything.google_ads.utils.google_ads_backend import format_customer_id
        assert format_customer_id("123 456 7890") == "1234567890"

    def test_format_customer_id_already_clean(self):
        from cli_anything.google_ads.utils.google_ads_backend import format_customer_id
        assert format_customer_id("1234567890") == "1234567890"

    def test_micros_to_currency(self):
        from cli_anything.google_ads.utils.google_ads_backend import micros_to_currency
        assert micros_to_currency(5_000_000) == 5.0
        assert micros_to_currency(1_500_000) == 1.5
        assert micros_to_currency(0) == 0.0

    def test_currency_to_micros(self):
        from cli_anything.google_ads.utils.google_ads_backend import currency_to_micros
        assert currency_to_micros(5.0) == 5_000_000
        assert currency_to_micros(1.5) == 1_500_000
        assert currency_to_micros(0.0) == 0

    def test_micros_roundtrip(self):
        from cli_anything.google_ads.utils.google_ads_backend import micros_to_currency, currency_to_micros
        for amount in [1.0, 5.0, 10.50, 100.99]:
            assert micros_to_currency(currency_to_micros(amount)) == round(amount, 2)

    def test_build_resource_name_campaign(self):
        from cli_anything.google_ads.utils.google_ads_backend import build_resource_name
        result = build_resource_name("campaigns", "1234567890", "111")
        assert result == "customers/1234567890/campaigns/111"

    def test_build_resource_name_strips_dashes(self):
        from cli_anything.google_ads.utils.google_ads_backend import build_resource_name
        result = build_resource_name("campaigns", "123-456-7890", "111")
        assert result == "customers/1234567890/campaigns/111"

    def test_translate_error_non_google(self):
        from cli_anything.google_ads.utils.google_ads_backend import translate_google_ads_error
        exc = ValueError("some generic error")
        result = translate_google_ads_error(exc)
        assert "some generic error" in result

    def test_backend_not_configured(self, tmp_path):
        from cli_anything.google_ads.utils.google_ads_backend import GoogleAdsBackend
        backend = GoogleAdsBackend(config_path=str(tmp_path / "no_creds.yaml"))
        assert backend.is_configured() is False

    def test_backend_is_configured(self, tmp_path):
        from cli_anything.google_ads.utils.google_ads_backend import GoogleAdsBackend
        cfg_path = tmp_path / "creds.yaml"
        cfg_path.write_text(yaml.dump({"developer_token": "tok", "use_proto_plus": False}))
        backend = GoogleAdsBackend(config_path=str(cfg_path))
        assert backend.is_configured() is True


# ── CLI structure tests ───────────────────────────────────────────────────────

class TestCLIStructure:
    """Test CLI command structure without API calls."""

    def setup_method(self):
        from click.testing import CliRunner
        from cli_anything.google_ads.google_ads_cli import cli
        self.runner = CliRunner()
        self.cli = cli

    def test_cli_help(self):
        result = self.runner.invoke(self.cli, ["--help"])
        assert result.exit_code == 0
        assert "Google Ads CLI" in result.output

    def test_cli_version(self):
        result = self.runner.invoke(self.cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_auth_help(self):
        result = self.runner.invoke(self.cli, ["auth", "--help"])
        assert result.exit_code == 0
        assert "setup" in result.output
        assert "test" in result.output

    def test_campaigns_help(self):
        result = self.runner.invoke(self.cli, ["campaigns", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output

    def test_ad_groups_help(self):
        result = self.runner.invoke(self.cli, ["ad-groups", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output

    def test_budgets_help(self):
        result = self.runner.invoke(self.cli, ["budgets", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output

    def test_keywords_help(self):
        result = self.runner.invoke(self.cli, ["keywords", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output

    def test_reports_help(self):
        result = self.runner.invoke(self.cli, ["reports", "--help"])
        assert result.exit_code == 0
        assert "campaigns" in result.output
        assert "keywords" in result.output

    def test_auth_show_help(self):
        result = self.runner.invoke(self.cli, ["auth", "show", "--help"])
        assert result.exit_code == 0

    def test_campaigns_list_help(self):
        result = self.runner.invoke(self.cli, ["campaigns", "list", "--help"])
        assert result.exit_code == 0
        assert "--customer-id" in result.output

    def test_campaigns_create_help(self):
        result = self.runner.invoke(self.cli, ["campaigns", "create", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--budget-id" in result.output

    def test_keywords_add_help(self):
        result = self.runner.invoke(self.cli, ["keywords", "add", "--help"])
        assert result.exit_code == 0
        assert "--ad-group-id" in result.output
        assert "--match-type" in result.output

    def test_reports_run_help(self):
        result = self.runner.invoke(self.cli, ["reports", "run", "--help"])
        assert result.exit_code == 0


class TestCLIAuthShow:
    """Test auth show command with mocked config."""

    def setup_method(self):
        from click.testing import CliRunner
        from cli_anything.google_ads.google_ads_cli import cli
        self.runner = CliRunner()
        self.cli = cli

    def test_auth_show_no_config(self, tmp_path):
        result = self.runner.invoke(
            self.cli, ["--config", str(tmp_path / "none.yaml"), "auth", "show"]
        )
        assert result.exit_code == 0
        assert "No config found" in result.output or "auth setup" in result.output

    def test_auth_show_with_config(self, tmp_path):
        cfg = tmp_path / "creds.yaml"
        cfg.write_text(yaml.dump({
            "developer_token": "abcdefghijklmno",
            "client_id": "testclient.apps.googleusercontent.com",
            "client_secret": "secretvalue123",
            "refresh_token": "refreshtokenvalue",
            "use_proto_plus": False,
        }))
        result = self.runner.invoke(
            self.cli, ["--config", str(cfg), "auth", "show"]
        )
        assert result.exit_code == 0
        assert "developer_token" in result.output
        # secrets should be masked
        assert "abcdefghijklmno" not in result.output

    def test_auth_show_json(self, tmp_path):
        cfg = tmp_path / "creds.yaml"
        cfg.write_text(yaml.dump({
            "developer_token": "abcdefghijklmno",
            "use_proto_plus": False,
        }))
        result = self.runner.invoke(
            self.cli, ["--json", "--config", str(cfg), "auth", "show"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "config" in data
        assert "config_path" in data


# ── Context object tests ──────────────────────────────────────────────────────

class TestContext:
    def test_require_customer_missing(self):
        import click
        from cli_anything.google_ads.google_ads_cli import Context
        ctx = Context()
        with pytest.raises(click.UsageError):
            ctx.require_customer()

    def test_require_customer_present(self):
        from cli_anything.google_ads.google_ads_cli import Context
        ctx = Context()
        ctx.customer_id = "123-456-7890"
        result = ctx.require_customer()
        assert result == "1234567890"

    def test_output_json_mode(self, capsys):
        from cli_anything.google_ads.google_ads_cli import Context
        ctx = Context()
        ctx.json_output = True
        ctx.output({"key": "value"})
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["key"] == "value"
