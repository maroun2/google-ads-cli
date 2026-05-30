"""google-ads-cli — Command-line interface for the Google Ads API.

Usage:
    google-ads-cli [--config PATH] [--customer-id ID] [--version VER] [--json]
    google-ads-cli auth setup
    google-ads-cli campaigns list --customer-id 1234567890
    google-ads-cli reports campaigns --customer-id 1234567890

Enter REPL by running without a subcommand:
    google-ads-cli
"""

import json as _json
import sys
from typing import Optional

import click

from cli_anything.google_ads.core.auth import (
    get_client,
    load_config,
    get_config_path,
    interactive_setup,
    test_credentials,
)

VERSION = "1.0.0"
DEFAULT_API_VERSION = "v24"


# ── Shared context object ─────────────────────────────────────────────────────

class Context:
    def __init__(self):
        self.config_path: Optional[str] = None
        self.customer_id: Optional[str] = None
        self.api_version: str = DEFAULT_API_VERSION
        self.json_output: bool = False
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_client(self.config_path, self.api_version)
        return self._client

    def require_customer(self):
        if not self.customer_id:
            raise click.UsageError(
                "Customer ID required. Pass --customer-id or set GOOGLE_ADS_CUSTOMER_ID env var."
            )
        return self.customer_id.replace("-", "")

    def output(self, data):
        """Print data as JSON or human-readable."""
        if self.json_output:
            click.echo(_json.dumps(data, indent=2, default=str))
        return data


pass_ctx = click.make_pass_decorator(Context, ensure=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _micros_to_currency(micros: int, decimals: int = 2) -> str:
    return f"{micros / 1_000_000:,.{decimals}f}"


def _print_table(headers: list, rows: list):
    """Simple ASCII table printer."""
    if not rows:
        click.echo("  (no results)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    click.echo(fmt.format(*headers))
    click.echo("  " + "  ".join("-" * w for w in widths))
    for row in rows:
        click.echo(fmt.format(*[str(c) for c in row]))


def _handle_error(ctx_obj: Context, exc: Exception):
    """Print error and exit cleanly."""
    if ctx_obj.json_output:
        click.echo(_json.dumps({"error": str(exc)}, indent=2), err=True)
    else:
        click.echo(f"\n  Error: {exc}", err=True)
    sys.exit(1)


# ── Root group ────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--config", "-c", default=None, envvar="GOOGLE_ADS_CLI_CONFIG",
              help="Path to credentials.yaml (default: ~/.config/google-ads-cli/credentials.yaml)")
@click.option("--customer-id", "-C", default=None, envvar="GOOGLE_ADS_CUSTOMER_ID",
              help="Google Ads customer ID (digits, dashes ignored)")
@click.option("--api-version", default=DEFAULT_API_VERSION, show_default=True,
              help="Google Ads API version")
@click.option("--json", "json_output", is_flag=True, default=False,
              help="Output results as JSON")
@click.version_option(VERSION, prog_name="google-ads-cli")
@click.pass_context
def cli(ctx, config, customer_id, api_version, json_output):
    """Google Ads CLI — manage campaigns, budgets, keywords, and reports."""
    obj = ctx.ensure_object(Context)
    obj.config_path = config
    obj.customer_id = customer_id
    obj.api_version = api_version
    obj.json_output = json_output

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── REPL ──────────────────────────────────────────────────────────────────────

@cli.command(hidden=True)
@pass_ctx
def repl(obj):
    """Enter interactive REPL mode."""
    from cli_anything.google_ads.utils.repl_skin import ReplSkin
    import shlex

    skin = ReplSkin("google_ads", version=VERSION)
    skin.print_banner()

    pt_session = skin.create_prompt_session()
    customer_id = obj.customer_id or ""

    skin.info("Type 'help' for commands, 'quit' to exit.")
    if not customer_id:
        skin.warning("No customer ID set. Use 'set-customer <ID>' or pass --customer-id.")
    else:
        skin.info(f"Customer ID: {customer_id}")
    click.echo()

    REPL_COMMANDS = {
        "auth setup": "Configure OAuth2 credentials",
        "auth test": "Test current credentials",
        "auth show": "Show current config",
        "accounts list": "List accessible accounts",
        "accounts info": "Show account details",
        "campaigns list": "List campaigns",
        "campaigns get <id>": "Get campaign details",
        "campaigns create": "Create a campaign",
        "campaigns enable <id>": "Enable a campaign",
        "campaigns pause <id>": "Pause a campaign",
        "ad-groups list": "List ad groups",
        "ad-groups create": "Create an ad group",
        "budgets list": "List budgets",
        "budgets create": "Create a budget",
        "keywords list": "List keywords",
        "keywords add": "Add keywords",
        "reports campaigns": "Campaign performance",
        "reports ad-groups": "Ad group performance",
        "reports keywords": "Keyword performance",
        "reports search-terms": "Search terms report",
        "reports run <gaql>": "Run raw GAQL query",
        "set-customer <id>": "Set active customer ID",
        "help": "Show this help",
        "quit": "Exit",
    }

    while True:
        try:
            line = skin.get_input(pt_session, context=customer_id or "no account")
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        parts = shlex.split(line) if line.strip() else []
        if not parts:
            continue

        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            skin.print_goodbye()
            break
        elif cmd == "help":
            skin.help(REPL_COMMANDS)
            continue
        elif cmd == "set-customer" and len(parts) >= 2:
            customer_id = parts[1].replace("-", "")
            obj.customer_id = customer_id
            skin.success(f"Customer ID set to {customer_id}")
            continue

        # Route to CLI subcommands
        try:
            args = parts[:]
            if customer_id and "--customer-id" not in args and "-C" not in args:
                args = ["--customer-id", customer_id] + args
            cli.main(args, standalone_mode=False, obj=obj)
        except SystemExit:
            pass
        except click.UsageError as e:
            skin.error(str(e))
        except Exception as e:
            skin.error(str(e))


# ── auth group ────────────────────────────────────────────────────────────────

@cli.group()
def auth():
    """Authentication and credential management."""
    pass


@auth.command("setup")
@click.option("--config", "-c", default=None,
              help="Path to save credentials (default: ~/.config/google-ads-cli/credentials.yaml)")
@pass_ctx
def auth_setup(obj, config):
    """Interactive OAuth2 + developer token setup."""
    path = config or obj.config_path
    try:
        cfg = interactive_setup(path)
        cfg_path = get_config_path(path)
        if not obj.json_output:
            click.echo(f"\n  Credentials saved to: {cfg_path}")
            click.echo("  Testing credentials...")
        result = test_credentials(path, obj.api_version)
        if result["ok"]:
            if obj.json_output:
                obj.output({"saved": str(cfg_path), "test": result})
            else:
                click.echo(f"  Authentication successful! Found {result['customer_count']} account(s).")
        else:
            if obj.json_output:
                obj.output({"saved": str(cfg_path), "test": result})
            else:
                click.echo(f"  Warning: credentials saved but test failed: {result['error']}")
    except Exception as exc:
        _handle_error(obj, exc)


@auth.command("test")
@pass_ctx
def auth_test(obj):
    """Test current credentials by calling the API."""
    try:
        result = test_credentials(obj.config_path, obj.api_version)
        if obj.json_output:
            obj.output(result)
        elif result["ok"]:
            click.echo(f"  Authentication OK — {result['customer_count']} account(s) accessible")
            for rn in result.get("resource_names", []):
                click.echo(f"    {rn}")
        else:
            click.echo(f"  Authentication failed: {result['error']}", err=True)
            sys.exit(1)
    except Exception as exc:
        _handle_error(obj, exc)


@auth.command("show")
@pass_ctx
def auth_show(obj):
    """Show current credentials config (secrets masked)."""
    try:
        cfg = load_config(obj.config_path)
        cfg_path = get_config_path(obj.config_path)
        if not cfg:
            click.echo(f"  No config found at {cfg_path}")
            click.echo("  Run 'google-ads-cli auth setup' to configure.")
            return

        masked = dict(cfg)
        for secret_key in ("client_secret", "refresh_token", "developer_token"):
            if secret_key in masked and masked[secret_key]:
                val = str(masked[secret_key])
                masked[secret_key] = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"

        if obj.json_output:
            obj.output({"config_path": str(cfg_path), "config": masked})
        else:
            click.echo(f"\n  Config: {cfg_path}")
            click.echo()
            for k, v in masked.items():
                click.echo(f"    {k}: {v}")
            click.echo()
    except Exception as exc:
        _handle_error(obj, exc)


# ── accounts group ────────────────────────────────────────────────────────────

@cli.group()
def accounts():
    """Account and customer management."""
    pass


@accounts.command("list")
@pass_ctx
def accounts_list(obj):
    """List all accessible Google Ads accounts."""
    from cli_anything.google_ads.core.accounts import list_accessible_customers
    try:
        results = list_accessible_customers(obj.client)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(["Customer ID", "Resource Name"],
                         [[r["customer_id"], r["resource_name"]] for r in results])
            click.echo(f"\n  Total: {len(results)} account(s)")
    except Exception as exc:
        _handle_error(obj, exc)


@accounts.command("info")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def accounts_info(obj, customer_id):
    """Show account details."""
    from cli_anything.google_ads.core.accounts import get_customer_info
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        info = get_customer_info(obj.client, cid)
        if obj.json_output:
            obj.output(info)
        else:
            for k, v in info.items():
                click.echo(f"  {k}: {v}")
    except Exception as exc:
        _handle_error(obj, exc)


@accounts.command("sub-accounts")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def accounts_sub(obj, customer_id):
    """List sub-accounts under a manager (MCC) account."""
    from cli_anything.google_ads.core.accounts import list_manager_accounts
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = list_manager_accounts(obj.client, cid)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["ID", "Name", "Currency", "Status", "Manager"],
                [[r["id"], r["name"], r["currency"], r["status"], r["is_manager"]]
                 for r in results]
            )
    except Exception as exc:
        _handle_error(obj, exc)


# ── campaigns group ───────────────────────────────────────────────────────────

@cli.group()
def campaigns():
    """Campaign management (list, create, enable, pause, remove)."""
    pass


@campaigns.command("list")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--status", default=None, type=click.Choice(["ENABLED", "PAUSED", "REMOVED"],
              case_sensitive=False), help="Filter by status")
@pass_ctx
def campaigns_list(obj, customer_id, status):
    """List campaigns."""
    from cli_anything.google_ads.core.campaigns import list_campaigns
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = list_campaigns(obj.client, cid, status)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["ID", "Name", "Status", "Channel", "Budget"],
                [[r["id"], r["name"][:35], r["status"], r["channel"],
                  f"${_micros_to_currency(r['budget_micros'])}/day"]
                 for r in results]
            )
            click.echo(f"\n  Total: {len(results)} campaign(s)")
    except Exception as exc:
        _handle_error(obj, exc)


@campaigns.command("get")
@click.argument("campaign_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def campaigns_get(obj, campaign_id, customer_id):
    """Get campaign details."""
    from cli_anything.google_ads.core.campaigns import get_campaign
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = get_campaign(obj.client, cid, campaign_id)
        if obj.json_output:
            obj.output(result)
        else:
            for k, v in result.items():
                click.echo(f"  {k}: {v}")
    except Exception as exc:
        _handle_error(obj, exc)


@campaigns.command("create")
@click.option("--name", "-n", required=True, help="Campaign name")
@click.option("--budget-id", required=True, help="Budget ID or resource name")
@click.option("--channel", default="SEARCH", show_default=True,
              type=click.Choice(["SEARCH", "DISPLAY", "SHOPPING", "VIDEO", "SMART"],
                                case_sensitive=False))
@click.option("--status", default="PAUSED", show_default=True,
              type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@click.option("--start-date", default=None, help="Start date YYYYMMDD (default: today)")
@click.option("--end-date", default=None, help="End date YYYYMMDD (optional)")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def campaigns_create(obj, name, budget_id, channel, status, start_date, end_date, customer_id):
    """Create a new campaign."""
    from cli_anything.google_ads.core.campaigns import create_campaign
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = create_campaign(
            obj.client, cid, name=name, budget_id=budget_id,
            channel_type=channel.upper(), status=status.upper(),
            start_date=start_date, end_date=end_date
        )
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Created campaign {result['campaign_id']}: {name}")
    except Exception as exc:
        _handle_error(obj, exc)


@campaigns.command("enable")
@click.argument("campaign_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def campaigns_enable(obj, campaign_id, customer_id):
    """Enable a paused campaign."""
    from cli_anything.google_ads.core.campaigns import update_campaign_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_campaign_status(obj.client, cid, campaign_id, "ENABLED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Campaign {campaign_id} enabled")
    except Exception as exc:
        _handle_error(obj, exc)


@campaigns.command("pause")
@click.argument("campaign_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def campaigns_pause(obj, campaign_id, customer_id):
    """Pause an enabled campaign."""
    from cli_anything.google_ads.core.campaigns import update_campaign_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_campaign_status(obj.client, cid, campaign_id, "PAUSED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Campaign {campaign_id} paused")
    except Exception as exc:
        _handle_error(obj, exc)


@campaigns.command("remove")
@click.argument("campaign_id")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@pass_ctx
def campaigns_remove(obj, campaign_id, customer_id, yes):
    """Remove (delete) a campaign."""
    from cli_anything.google_ads.core.campaigns import remove_campaign
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        if not yes:
            click.confirm(f"  Remove campaign {campaign_id}? This cannot be undone.", abort=True)
        result = remove_campaign(obj.client, cid, campaign_id)
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Campaign {campaign_id} removed")
    except click.Abort:
        click.echo("  Aborted")
    except Exception as exc:
        _handle_error(obj, exc)


# ── ad-groups group ───────────────────────────────────────────────────────────

@cli.group(name="ad-groups")
def ad_groups():
    """Ad group management (list, create, enable, pause)."""
    pass


@ad_groups.command("list")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--campaign-id", default=None, help="Filter by campaign ID")
@click.option("--status", default=None,
              type=click.Choice(["ENABLED", "PAUSED", "REMOVED"], case_sensitive=False))
@pass_ctx
def ad_groups_list(obj, customer_id, campaign_id, status):
    """List ad groups."""
    from cli_anything.google_ads.core.ad_groups import list_ad_groups
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = list_ad_groups(obj.client, cid, campaign_id, status)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["ID", "Name", "Status", "Campaign", "CPC Bid"],
                [[r["id"], r["name"][:30], r["status"], r["campaign_name"][:20],
                  f"${_micros_to_currency(r['cpc_bid_micros'])}"]
                 for r in results]
            )
            click.echo(f"\n  Total: {len(results)} ad group(s)")
    except Exception as exc:
        _handle_error(obj, exc)


@ad_groups.command("get")
@click.argument("ad_group_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def ad_groups_get(obj, ad_group_id, customer_id):
    """Get ad group details."""
    from cli_anything.google_ads.core.ad_groups import get_ad_group
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = get_ad_group(obj.client, cid, ad_group_id)
        if obj.json_output:
            obj.output(result)
        else:
            for k, v in result.items():
                click.echo(f"  {k}: {v}")
    except Exception as exc:
        _handle_error(obj, exc)


@ad_groups.command("create")
@click.option("--name", "-n", required=True, help="Ad group name")
@click.option("--campaign-id", required=True, help="Parent campaign ID")
@click.option("--cpc-bid", default=1.0, show_default=True,
              type=float, help="CPC bid in dollars (e.g. 1.50)")
@click.option("--status", default="ENABLED", show_default=True,
              type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def ad_groups_create(obj, name, campaign_id, cpc_bid, status, customer_id):
    """Create an ad group."""
    from cli_anything.google_ads.core.ad_groups import create_ad_group
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = create_ad_group(
            obj.client, cid, campaign_id=campaign_id, name=name,
            cpc_bid_micros=int(cpc_bid * 1_000_000), status=status.upper()
        )
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Created ad group {result['ad_group_id']}: {name}")
    except Exception as exc:
        _handle_error(obj, exc)


@ad_groups.command("enable")
@click.argument("ad_group_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def ad_groups_enable(obj, ad_group_id, customer_id):
    """Enable an ad group."""
    from cli_anything.google_ads.core.ad_groups import update_ad_group_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_ad_group_status(obj.client, cid, ad_group_id, "ENABLED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Ad group {ad_group_id} enabled")
    except Exception as exc:
        _handle_error(obj, exc)


@ad_groups.command("pause")
@click.argument("ad_group_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def ad_groups_pause(obj, ad_group_id, customer_id):
    """Pause an ad group."""
    from cli_anything.google_ads.core.ad_groups import update_ad_group_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_ad_group_status(obj.client, cid, ad_group_id, "PAUSED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Ad group {ad_group_id} paused")
    except Exception as exc:
        _handle_error(obj, exc)


# ── budgets group ─────────────────────────────────────────────────────────────

@cli.group()
def budgets():
    """Campaign budget management (list, create, update)."""
    pass


@budgets.command("list")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--all", "show_all", is_flag=True, help="Include non-shared budgets")
@pass_ctx
def budgets_list(obj, customer_id, show_all):
    """List campaign budgets."""
    from cli_anything.google_ads.core.budgets import list_budgets, list_all_budgets
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = list_all_budgets(obj.client, cid) if show_all else list_budgets(obj.client, cid)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["ID", "Name", "Daily Amount", "Period", "Campaigns", "Status"],
                [[r["id"], r["name"][:30], f"${r['amount']:,.2f}",
                  r["period"], r["reference_count"], r["status"]]
                 for r in results]
            )
            click.echo(f"\n  Total: {len(results)} budget(s)")
    except Exception as exc:
        _handle_error(obj, exc)


@budgets.command("get")
@click.argument("budget_id")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def budgets_get(obj, budget_id, customer_id):
    """Get budget details."""
    from cli_anything.google_ads.core.budgets import get_budget
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = get_budget(obj.client, cid, budget_id)
        if obj.json_output:
            obj.output(result)
        else:
            for k, v in result.items():
                click.echo(f"  {k}: {v}")
    except Exception as exc:
        _handle_error(obj, exc)


@budgets.command("create")
@click.option("--name", "-n", required=True, help="Budget name")
@click.option("--amount", required=True, type=float, help="Daily amount in your account currency")
@click.option("--shared/--no-shared", default=True, show_default=True,
              help="Make this a shared budget")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def budgets_create(obj, name, amount, shared, customer_id):
    """Create a campaign budget."""
    from cli_anything.google_ads.core.budgets import create_budget
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = create_budget(
            obj.client, cid, name=name,
            amount_micros=int(amount * 1_000_000),
            explicitly_shared=shared
        )
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Created budget {result['budget_id']}: {name} (${amount:,.2f}/day)")
    except Exception as exc:
        _handle_error(obj, exc)


@budgets.command("update")
@click.argument("budget_id")
@click.option("--amount", required=True, type=float, help="New daily amount")
@click.option("--customer-id", "-C", required=False, default=None)
@pass_ctx
def budgets_update(obj, budget_id, amount, customer_id):
    """Update a budget's daily amount."""
    from cli_anything.google_ads.core.budgets import update_budget_amount
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_budget_amount(
            obj.client, cid, budget_id, int(amount * 1_000_000)
        )
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Budget {budget_id} updated to ${amount:,.2f}/day")
    except Exception as exc:
        _handle_error(obj, exc)


# ── keywords group ────────────────────────────────────────────────────────────

@cli.group()
def keywords():
    """Keyword management (list, add, enable, pause, remove)."""
    pass


@keywords.command("list")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--ad-group-id", default=None)
@click.option("--campaign-id", default=None)
@click.option("--status", default=None,
              type=click.Choice(["ENABLED", "PAUSED", "REMOVED"], case_sensitive=False))
@pass_ctx
def keywords_list(obj, customer_id, ad_group_id, campaign_id, status):
    """List keywords."""
    from cli_anything.google_ads.core.keywords import list_keywords
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = list_keywords(obj.client, cid, ad_group_id, campaign_id, status)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["ID", "Keyword", "Match Type", "Status", "Ad Group", "Clicks"],
                [[r["criterion_id"], r["text"][:30], r["match_type"],
                  r["status"], r["ad_group_name"][:20], r["clicks"]]
                 for r in results]
            )
            click.echo(f"\n  Total: {len(results)} keyword(s)")
    except Exception as exc:
        _handle_error(obj, exc)


@keywords.command("add")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--ad-group-id", required=True, help="Ad group to add keywords to")
@click.option("--keywords", "-k", "kw_list", required=True, multiple=True,
              help="Keyword text (use multiple times for multiple keywords)")
@click.option("--match-type", default="BROAD",
              type=click.Choice(["BROAD", "PHRASE", "EXACT"], case_sensitive=False))
@click.option("--cpc-bid", default=None, type=float, help="Optional CPC bid in dollars")
@pass_ctx
def keywords_add(obj, customer_id, ad_group_id, kw_list, match_type, cpc_bid):
    """Add keywords to an ad group.

    Example:
        google-ads-cli keywords add --ad-group-id 12345 -k "running shoes" -k "buy sneakers"
    """
    from cli_anything.google_ads.core.keywords import add_keywords
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        kws = [
            {
                "text": kw,
                "match_type": match_type.upper(),
                **({"cpc_bid_micros": int(cpc_bid * 1_000_000)} if cpc_bid else {}),
            }
            for kw in kw_list
        ]
        results = add_keywords(obj.client, cid, ad_group_id, kws)
        if obj.json_output:
            obj.output(results)
        else:
            for res in results:
                click.echo(f"  Added keyword {res['criterion_id']}")
    except Exception as exc:
        _handle_error(obj, exc)


@keywords.command("enable")
@click.argument("criterion_id")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--ad-group-id", required=True)
@pass_ctx
def keywords_enable(obj, criterion_id, customer_id, ad_group_id):
    """Enable a keyword."""
    from cli_anything.google_ads.core.keywords import update_keyword_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_keyword_status(obj.client, cid, ad_group_id, criterion_id, "ENABLED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Keyword {criterion_id} enabled")
    except Exception as exc:
        _handle_error(obj, exc)


@keywords.command("pause")
@click.argument("criterion_id")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--ad-group-id", required=True)
@pass_ctx
def keywords_pause(obj, criterion_id, customer_id, ad_group_id):
    """Pause a keyword."""
    from cli_anything.google_ads.core.keywords import update_keyword_status
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = update_keyword_status(obj.client, cid, ad_group_id, criterion_id, "PAUSED")
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Keyword {criterion_id} paused")
    except Exception as exc:
        _handle_error(obj, exc)


@keywords.command("remove")
@click.argument("criterion_id")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--ad-group-id", required=True)
@pass_ctx
def keywords_remove(obj, criterion_id, customer_id, ad_group_id):
    """Remove a keyword."""
    from cli_anything.google_ads.core.keywords import remove_keyword
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        result = remove_keyword(obj.client, cid, ad_group_id, criterion_id)
        if obj.json_output:
            obj.output(result)
        else:
            click.echo(f"  Keyword {criterion_id} removed")
    except Exception as exc:
        _handle_error(obj, exc)


# ── reports group ─────────────────────────────────────────────────────────────

@cli.group()
def reports():
    """Reporting and analytics (GAQL queries and pre-built reports)."""
    pass


@reports.command("run")
@click.argument("query", required=False)
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--query", "-q", "query_opt", default=None, help="GAQL query string")
@click.option("--limit", default=50, show_default=True, type=int)
@pass_ctx
def reports_run(obj, query, customer_id, query_opt, limit):
    """Run a raw GAQL query.

    Example:
        google-ads-cli reports run "SELECT campaign.id, campaign.name FROM campaign LIMIT 10"
    """
    from cli_anything.google_ads.core.reports import run_query
    gaql = query or query_opt
    if not gaql:
        raise click.UsageError("Provide GAQL query as argument or with --query")
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = run_query(obj.client, cid, gaql)
        if obj.json_output:
            obj.output(results[:limit])
        else:
            if results:
                headers = list(results[0].keys())
                rows = [[str(r.get(h, "")) for h in headers] for r in results[:limit]]
                _print_table(headers, rows)
                click.echo(f"\n  Rows: {min(len(results), limit)} (of {len(results)})")
            else:
                click.echo("  (no results)")
    except Exception as exc:
        _handle_error(obj, exc)


@reports.command("campaigns")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--date-range", default="LAST_30_DAYS", show_default=True,
              help="GAQL date range (LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH, etc.)")
@click.option("--status", default=None,
              type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@pass_ctx
def reports_campaigns(obj, customer_id, date_range, status):
    """Campaign performance report."""
    from cli_anything.google_ads.core.reports import campaign_performance
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = campaign_performance(obj.client, cid, date_range, status)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["Campaign", "Status", "Impressions", "Clicks", "Cost", "CTR%", "Avg CPC"],
                [[r["campaign_name"][:30], r["status"], f"{r['impressions']:,}",
                  f"{r['clicks']:,}", f"${r['cost']:,.2f}", f"{r['ctr']:.2f}%",
                  f"${r['avg_cpc']:,.2f}"]
                 for r in results]
            )
            click.echo(f"\n  Period: {date_range} | Campaigns: {len(results)}")
    except Exception as exc:
        _handle_error(obj, exc)


@reports.command("ad-groups")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--campaign-id", default=None)
@click.option("--date-range", default="LAST_30_DAYS", show_default=True)
@pass_ctx
def reports_ad_groups(obj, customer_id, campaign_id, date_range):
    """Ad group performance report."""
    from cli_anything.google_ads.core.reports import ad_group_performance
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = ad_group_performance(obj.client, cid, campaign_id, date_range)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["Ad Group", "Campaign", "Impressions", "Clicks", "Cost", "CTR%"],
                [[r["ad_group_name"][:25], r["campaign_name"][:20],
                  f"{r['impressions']:,}", f"{r['clicks']:,}",
                  f"${r['cost']:,.2f}", f"{r['ctr']:.2f}%"]
                 for r in results]
            )
            click.echo(f"\n  Period: {date_range} | Ad groups: {len(results)}")
    except Exception as exc:
        _handle_error(obj, exc)


@reports.command("keywords")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--campaign-id", default=None)
@click.option("--ad-group-id", default=None)
@click.option("--date-range", default="LAST_30_DAYS", show_default=True)
@click.option("--limit", default=50, show_default=True, type=int)
@pass_ctx
def reports_keywords(obj, customer_id, campaign_id, ad_group_id, date_range, limit):
    """Keyword performance report."""
    from cli_anything.google_ads.core.reports import keyword_performance
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = keyword_performance(obj.client, cid, campaign_id, ad_group_id, date_range, limit)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["Keyword", "Match", "Impressions", "Clicks", "Cost", "CTR%"],
                [[r["keyword"][:30], r["match_type"], f"{r['impressions']:,}",
                  f"{r['clicks']:,}", f"${r['cost']:,.2f}", f"{r['ctr']:.2f}%"]
                 for r in results]
            )
            click.echo(f"\n  Period: {date_range} | Keywords: {len(results)}")
    except Exception as exc:
        _handle_error(obj, exc)


@reports.command("search-terms")
@click.option("--customer-id", "-C", required=False, default=None)
@click.option("--campaign-id", default=None)
@click.option("--date-range", default="LAST_30_DAYS", show_default=True)
@click.option("--limit", default=50, show_default=True, type=int)
@pass_ctx
def reports_search_terms(obj, customer_id, campaign_id, date_range, limit):
    """Search terms (actual user queries) report."""
    from cli_anything.google_ads.core.reports import search_terms_report
    try:
        cid = (customer_id or obj.require_customer()).replace("-", "")
        results = search_terms_report(obj.client, cid, campaign_id, date_range, limit)
        if obj.json_output:
            obj.output(results)
        else:
            _print_table(
                ["Search Term", "Campaign", "Impressions", "Clicks", "Cost"],
                [[r["search_term"][:40], r["campaign_name"][:20],
                  f"{r['impressions']:,}", f"{r['clicks']:,}", f"${r['cost']:,.2f}"]
                 for r in results]
            )
            click.echo(f"\n  Period: {date_range} | Terms: {len(results)}")
    except Exception as exc:
        _handle_error(obj, exc)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli(auto_envvar_prefix="GOOGLE_ADS_CLI")


if __name__ == "__main__":
    main()
