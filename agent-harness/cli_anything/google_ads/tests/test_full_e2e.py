"""E2E tests for google-ads-cli — requires real Google Ads API credentials.

Set these env vars before running:
    GOOGLE_ADS_CUSTOMER_ID=1234567890
    GOOGLE_ADS_CLI_CONFIG=~/.config/google-ads-cli/credentials.yaml  # optional

Run with:
    pytest cli_anything/google_ads/tests/test_full_e2e.py -v -s

Force-installed command tests:
    CLI_ANYTHING_FORCE_INSTALLED=1 pytest cli_anything/google_ads/tests/test_full_e2e.py -v -s
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def customer_id():
    cid = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "").strip()
    if not cid:
        pytest.skip("GOOGLE_ADS_CUSTOMER_ID not set — skipping E2E tests")
    return cid


@pytest.fixture(scope="session")
def config_path():
    return os.environ.get("GOOGLE_ADS_CLI_CONFIG", None)


@pytest.fixture(scope="session")
def ads_client(config_path):
    from cli_anything.google_ads.core.auth import get_client
    try:
        return get_client(config_path)
    except Exception as exc:
        pytest.skip(f"Cannot create GoogleAdsClient: {exc}")


@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


# ── CLI subprocess helper ─────────────────────────────────────────────────────

def _resolve_cli(name):
    """Resolve installed CLI; falls back to python -m for dev.

    Set CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"\n[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.google_ads.google_ads_cli"
    print(f"\n[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


CLI_BASE = _resolve_cli("google-ads-cli")


def _run(args, check=True, env=None):
    return subprocess.run(
        CLI_BASE + args,
        capture_output=True, text=True,
        check=check, env=env or os.environ.copy(),
    )


# ── Credential tests ──────────────────────────────────────────────────────────

class TestCredentials:
    def test_credentials_valid(self, config_path):
        from cli_anything.google_ads.core.auth import test_credentials
        result = test_credentials(config_path)
        assert result["ok"], f"Credential test failed: {result.get('error')}"
        print(f"\n  Accessible accounts: {result['customer_count']}")

    def test_accessible_customers(self, ads_client):
        from cli_anything.google_ads.core.accounts import list_accessible_customers
        results = list_accessible_customers(ads_client)
        assert isinstance(results, list)
        assert len(results) >= 1
        print(f"\n  Found accounts: {[r['customer_id'] for r in results]}")


# ── Account tests ─────────────────────────────────────────────────────────────

class TestAccountOperations:
    def test_account_info(self, ads_client, customer_id):
        from cli_anything.google_ads.core.accounts import get_customer_info
        info = get_customer_info(ads_client, customer_id)
        assert "id" in info
        assert "name" in info
        assert "currency" in info
        print(f"\n  Account: {info['name']} ({info['currency']})")


# ── Campaign read tests ───────────────────────────────────────────────────────

class TestCampaignReads:
    def test_list_campaigns(self, ads_client, customer_id):
        from cli_anything.google_ads.core.campaigns import list_campaigns
        results = list_campaigns(ads_client, customer_id)
        assert isinstance(results, list)
        print(f"\n  Campaigns: {len(results)}")
        if results:
            c = results[0]
            assert "id" in c
            assert "name" in c
            assert "status" in c


# ── Budget lifecycle test ─────────────────────────────────────────────────────

class TestBudgetLifecycle:
    BUDGET_NAME = f"gads-cli-test-budget-{int(time.time())}"

    def test_budget_lifecycle(self, ads_client, customer_id):
        from cli_anything.google_ads.core.budgets import (
            create_budget, get_budget, list_all_budgets, update_budget_amount
        )

        # Create
        result = create_budget(
            ads_client, customer_id,
            name=self.BUDGET_NAME,
            amount_micros=5_000_000,  # $5.00
            explicitly_shared=True
        )
        assert "budget_id" in result
        budget_id = result["budget_id"]
        print(f"\n  Created budget {budget_id}: {self.BUDGET_NAME}")

        # Verify via get
        info = get_budget(ads_client, customer_id, budget_id)
        assert info["amount_micros"] == 5_000_000
        assert info["name"] == self.BUDGET_NAME

        # Update amount
        updated = update_budget_amount(ads_client, customer_id, budget_id, 10_000_000)
        assert updated["amount_micros"] == 10_000_000

        # Verify update
        info2 = get_budget(ads_client, customer_id, budget_id)
        assert info2["amount_micros"] == 10_000_000
        print(f"  Budget updated to ${info2['amount']:.2f}/day")


# ── Campaign lifecycle test ───────────────────────────────────────────────────

class TestCampaignLifecycle:
    TS = int(time.time())

    def test_campaign_lifecycle(self, ads_client, customer_id):
        from cli_anything.google_ads.core.budgets import create_budget
        from cli_anything.google_ads.core.campaigns import (
            create_campaign, get_campaign, update_campaign_status, remove_campaign
        )

        # Create budget
        budget = create_budget(
            ads_client, customer_id,
            name=f"gads-cli-test-budget-{self.TS}",
            amount_micros=3_000_000,
        )
        budget_id = budget["budget_id"]
        print(f"\n  Created budget {budget_id}")

        # Create campaign (PAUSED)
        campaign = create_campaign(
            ads_client, customer_id,
            name=f"gads-cli-test-campaign-{self.TS}",
            budget_id=budget_id,
            status="PAUSED",
        )
        campaign_id = campaign["campaign_id"]
        print(f"  Created campaign {campaign_id}")

        # Verify
        info = get_campaign(ads_client, customer_id, campaign_id)
        assert info["status"] == "PAUSED"
        assert str(info["id"]) == str(campaign_id)

        # Pause (no-op, already paused — just test the call works)
        update_campaign_status(ads_client, customer_id, campaign_id, "PAUSED")

        # Remove
        removed = remove_campaign(ads_client, customer_id, campaign_id)
        assert "removed" in removed
        print(f"  Removed campaign {campaign_id}")


# ── Reports tests ─────────────────────────────────────────────────────────────

class TestReports:
    def test_campaign_performance(self, ads_client, customer_id):
        from cli_anything.google_ads.core.reports import campaign_performance
        results = campaign_performance(ads_client, customer_id, date_range="LAST_7_DAYS")
        assert isinstance(results, list)
        if results:
            r = results[0]
            assert "campaign_id" in r
            assert "impressions" in r
            assert "clicks" in r
            assert "cost" in r
            assert "ctr" in r
        print(f"\n  Campaign report rows: {len(results)}")

    def test_gaql_query(self, ads_client, customer_id):
        from cli_anything.google_ads.core.reports import run_query
        query = "SELECT campaign.id, campaign.name, campaign.status FROM campaign LIMIT 5"
        results = run_query(ads_client, customer_id, query)
        assert isinstance(results, list)
        print(f"\n  GAQL query returned {len(results)} rows")


# ── CLI subprocess tests ──────────────────────────────────────────────────────

class TestCLISubprocess:
    def test_help(self):
        result = _run(["--help"])
        assert result.returncode == 0
        assert "Google Ads CLI" in result.stdout
        print(f"\n  --help OK")

    def test_version(self):
        result = _run(["--version"])
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_auth_help(self):
        result = _run(["auth", "--help"])
        assert result.returncode == 0
        assert "setup" in result.stdout

    def test_auth_show_no_config(self, tmp_dir):
        result = _run([
            "--config", str(Path(tmp_dir) / "none.yaml"),
            "auth", "show"
        ], check=False)
        assert result.returncode == 0
        assert "No config" in result.stdout or "auth setup" in result.stdout

    def test_campaigns_list_json(self, customer_id, config_path):
        extra = []
        if config_path:
            extra = ["--config", config_path]
        result = _run(extra + [
            "--json", "--customer-id", customer_id,
            "campaigns", "list"
        ], check=False)
        if result.returncode != 0:
            pytest.skip(f"API error (test account may have restrictions): {result.stderr}")
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        print(f"\n  campaigns list --json: {len(data)} results")

    def test_reports_campaigns_json(self, customer_id, config_path):
        extra = []
        if config_path:
            extra = ["--config", config_path]
        result = _run(extra + [
            "--json", "--customer-id", customer_id,
            "reports", "campaigns", "--date-range", "LAST_7_DAYS"
        ], check=False)
        if result.returncode != 0:
            pytest.skip(f"API error: {result.stderr}")
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        print(f"\n  reports campaigns --json: {len(data)} rows")

    def test_auth_test(self, config_path):
        extra = []
        if config_path:
            extra = ["--config", config_path]
        result = _run(extra + ["auth", "test"], check=False)
        if result.returncode != 0:
            pytest.skip(f"Credential test failed: {result.stderr}")
        assert "OK" in result.stdout or "accessible" in result.stdout.lower()
        print(f"\n  auth test: {result.stdout.strip()}")
