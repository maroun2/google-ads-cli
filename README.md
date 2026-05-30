# google-ads-cli

**A friendly command-line interface for Google Ads, built with CLI-Anything.**

> **Note:** This is not the official google-ads-python library — it is a CLI built on top of it. The official library lives at [googleads/google-ads-python](https://github.com/googleads/google-ads-python). This repo wraps that library in a terminal interface so you can use the Google Ads API without writing Python.

Manage Google Ads campaigns, budgets, keywords, and reports straight from your terminal — no web UI required. Whether you're scripting campaign automation, pulling performance data into pipelines, or just prefer the command line, `google-ads-cli` gives you a clean interface to the full Google Ads API.

---

## 🤖 How this was created

This CLI was auto-generated from the official [google-ads-python](https://github.com/googleads/google-ads-python) library using the **[CLI-Anything](https://github.com/HKUDS/CLI-Anything)** pipeline — a 7-phase process that turns any library or application into an agent-friendly CLI:

1. **Codebase analysis** — read the google-ads-python source, mapped 110+ service clients, authentication flows, and GAQL query patterns
2. **CLI architecture design** — designed command groups matching the API's logical domains (auth, campaigns, budgets, etc.)
3. **Implementation** — built a Click-based CLI with REPL support, `--json` output mode, and a unified terminal skin
4. **Test planning** — wrote a comprehensive TEST.md covering unit and E2E scenarios
5. **Test implementation** — 41 unit tests, E2E tests against the live API, and subprocess tests for the installed binary
6. **Documentation** — SKILL.md for AI agent discovery, README, and analysis docs
7. **Packaging** — `setup.py` with proper namespace packages, installed as `google-ads-cli` on PATH

No hand-written boilerplate. The pipeline read the source, designed the interface, wrote the code, and verified it — all automatically.

---

## Requirements

- Python 3.9+
- A [Google Ads developer token](https://developers.google.com/google-ads/api/docs/first-call/dev-token)
- OAuth2 credentials — Desktop app type, from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

---

## Installation

```bash
git clone https://github.com/maroun2/google-ads-python -b google-ads-cli
cd google-ads-python/agent-harness
pip install -e .
```

Verify it worked:

```bash
google-ads-cli --help
```

---

## ⚡ Quick start

**Step 1 — Set up authentication**

```bash
google-ads-cli auth setup
```

This walks you through entering your developer token, OAuth2 client credentials, and opens a browser for Google account authorization. Credentials are saved to `~/.config/google-ads-cli/credentials.yaml`.

**Step 2 — Find your account ID**

```bash
google-ads-cli accounts list
```

**Step 3 — Start using it**

```bash
# Set your customer ID once (or pass --customer-id on every command)
export GOOGLE_ADS_CUSTOMER_ID=1234567890

# List your campaigns
google-ads-cli campaigns list

# Create a $10/day budget
google-ads-cli budgets create --name "My Budget" --amount 10.00

# Create a paused search campaign
google-ads-cli campaigns create \
  --name "My Campaign" \
  --budget-id 123456 \
  --channel SEARCH \
  --status PAUSED

# Pull a 7-day performance report
google-ads-cli reports campaigns --date-range LAST_7_DAYS

# Run a raw GAQL query
google-ads-cli reports run \
  "SELECT campaign.name, metrics.clicks, metrics.cost_micros FROM campaign ORDER BY metrics.clicks DESC LIMIT 10"
```

**REPL mode** — run `google-ads-cli` with no arguments to enter an interactive session:

```
google-ads-cli

╭────────────────────────────────────────────────────────────────────────╮
│ ◆  cli-anything · Google Ads                                           │
│    v1.0.0                                                              │
│                                                                        │
│    Type help for commands, quit to exit                                │
╰────────────────────────────────────────────────────────────────────────╯

● No customer ID set. Use 'set-customer <ID>' or pass --customer-id.

google_ads [no account] ❯ set-customer 1234567890
  ✓ Customer ID set to 1234567890
google_ads [1234567890] ❯ campaigns list
  ...
google_ads [1234567890] ❯ quit
```

---

## All commands

### `auth` — Credential management

| Command | Description |
|---------|-------------|
| `auth setup` | Interactive OAuth2 + developer token wizard |
| `auth test` | Verify credentials against the live API |
| `auth show` | Display current config (secrets masked) |

### `accounts` — Account discovery

| Command | Description |
|---------|-------------|
| `accounts list` | List all accessible Google Ads accounts |
| `accounts info` | Show account details (name, currency, timezone) |
| `accounts sub-accounts` | List child accounts under a manager (MCC) account |

### `campaigns` — Campaign management

| Command | Description |
|---------|-------------|
| `campaigns list` | List campaigns, optional `--status ENABLED\|PAUSED\|REMOVED` |
| `campaigns get <id>` | Get full details for a campaign |
| `campaigns create` | Create a campaign (`--name`, `--budget-id`, `--channel`, `--status`) |
| `campaigns enable <id>` | Enable a paused campaign |
| `campaigns pause <id>` | Pause a running campaign |
| `campaigns remove <id>` | Delete a campaign (prompts for confirmation) |

### `ad-groups` — Ad group management

| Command | Description |
|---------|-------------|
| `ad-groups list` | List ad groups, optional `--campaign-id`, `--status` |
| `ad-groups get <id>` | Get ad group details |
| `ad-groups create` | Create an ad group (`--name`, `--campaign-id`, `--cpc-bid`) |
| `ad-groups enable <id>` | Enable an ad group |
| `ad-groups pause <id>` | Pause an ad group |

### `budgets` — Budget management

| Command | Description |
|---------|-------------|
| `budgets list` | List shared campaign budgets (`--all` includes non-shared) |
| `budgets get <id>` | Get budget details |
| `budgets create` | Create a budget (`--name`, `--amount` in dollars) |
| `budgets update <id>` | Update a budget's daily amount (`--amount`) |

### `keywords` — Keyword management

| Command | Description |
|---------|-------------|
| `keywords list` | List keywords, optional `--ad-group-id`, `--campaign-id`, `--status` |
| `keywords add` | Add keywords (`-k "text"`, `--match-type BROAD\|PHRASE\|EXACT`) |
| `keywords enable <id>` | Enable a keyword (`--ad-group-id` required) |
| `keywords pause <id>` | Pause a keyword |
| `keywords remove <id>` | Remove a keyword from an ad group |

### `reports` — Analytics and reporting

| Command | Description |
|---------|-------------|
| `reports campaigns` | Campaign performance (`--date-range`, `--status`) |
| `reports ad-groups` | Ad group performance (`--campaign-id`, `--date-range`) |
| `reports keywords` | Keyword performance (`--limit`, `--date-range`) |
| `reports search-terms` | Actual user search queries report |
| `reports run <gaql>` | Execute any raw GAQL query |

---

## Global flags

All commands accept these flags:

| Flag | Env var | Description |
|------|---------|-------------|
| `--config PATH` | `GOOGLE_ADS_CLI_CONFIG` | Path to credentials.yaml |
| `--customer-id ID` | `GOOGLE_ADS_CUSTOMER_ID` | Google Ads customer ID |
| `--api-version VER` | — | API version (default: `v24`) |
| `--json` | — | Output as JSON for scripting |

### JSON output for scripting

Every command supports `--json`:

```bash
# Extract campaign names with jq
google-ads-cli --json campaigns list | jq '.[].name'

# Create a budget and capture the ID
BUDGET_ID=$(google-ads-cli --json budgets create --name "Q4" --amount 50.00 | jq -r .budget_id)

# Get cost by campaign as TSV
google-ads-cli --json reports campaigns | \
  jq -r '.[] | [.campaign_name, .cost] | @tsv'
```

---

## Date ranges for reports

Standard values for `--date-range`:

`TODAY` · `YESTERDAY` · `LAST_7_DAYS` · `LAST_14_DAYS` · `LAST_30_DAYS` · `THIS_WEEK_SUN_TODAY` · `LAST_WEEK_SUN_SAT` · `THIS_MONTH` · `LAST_MONTH` · `THIS_YEAR`

---

## Project structure

```
agent-harness/
├── GOOGLE_ADS.md              # Architecture analysis and design notes
├── setup.py                   # Package config — installs as google-ads-cli
├── skills/
│   └── cli-anything-google-ads/
│       └── SKILL.md           # AI agent skill definition
└── cli_anything/
    └── google_ads/
        ├── google_ads_cli.py  # Main CLI entry point (Click + REPL)
        ├── core/              # API modules (auth, campaigns, budgets…)
        ├── utils/             # Backend wrapper, REPL skin
        └── tests/
            ├── TEST.md        # Test plan + results (41/41 passing)
            ├── test_core.py   # Unit tests
            └── test_full_e2e.py  # E2E tests (requires credentials)
```

---

## Running tests

Unit tests (no credentials needed):

```bash
cd agent-harness
pytest cli_anything/google_ads/tests/test_core.py -v
```

E2E tests (requires real Google Ads account):

```bash
export GOOGLE_ADS_CUSTOMER_ID=1234567890
pytest cli_anything/google_ads/tests/test_full_e2e.py -v -s
```

---

## Contributing

This CLI was generated by CLI-Anything — if you want to extend it, the cleanest approach is to add new commands to `google_ads_cli.py` and corresponding functions to the relevant `core/` module following the existing patterns. Each command gets a `--json` output path and uses `_handle_error()` for consistent error handling.

If you find the generation approach interesting, check out **[HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)** — the pipeline that built this.

Issues and PRs welcome.

---

## License

Apache 2.0 — same as the upstream [google-ads-python](https://github.com/googleads/google-ads-python) library.
