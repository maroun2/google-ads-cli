# Google Ads CLI — Analysis and SOP

## Backend Engine

The backend is the [google-ads-python](https://github.com/googleads/google-ads-python) library (version 31.0.0), which is the official Python client for the Google Ads API. It uses gRPC under the hood and supports API versions v21–v24 (default v24).

**Key classes:**
- `GoogleAdsClient` — main entry point, loaded from YAML/dict/env/storage
- `GoogleAdsService` — core query/mutation service, uses GAQL (Google Ads Query Language)
- Service clients — 110+ service clients (CampaignService, AdGroupService, etc.)

Unlike traditional GUI applications, this library wraps a remote API. There are no project files to manipulate — the CLI calls the API directly.

## Architecture

```
google-ads-python library
    ↕ gRPC
Google Ads API (v24)
    ↕
google-ads-cli (this CLI)
    ↕ subprocess/direct
User / AI agent
```

## Authentication

Three modes supported:
1. **OAuth2 Installed App** — developer token + client_id + client_secret + refresh_token (default)
2. **Service Account** — developer token + JSON key file
3. **Application Default Credentials** — for GCP environments

Config stored at `~/.config/google-ads-cli/credentials.yaml` (or `$GOOGLE_ADS_CLI_CONFIG`).

Required fields: `developer_token`, `client_id`, `client_secret`, `refresh_token`, `use_proto_plus`.

Optional: `login_customer_id` (MCC/manager accounts), `endpoint`, `http_proxy`.

## Command Groups

| Group | Purpose | Key Operations |
|-------|---------|----------------|
| `auth` | Credential management | setup, test, show |
| `accounts` | Customer account discovery | list, info, sub-accounts |
| `campaigns` | Campaign CRUD | list, get, create, enable, pause, remove |
| `ad-groups` | Ad group management | list, get, create, enable, pause |
| `budgets` | Budget management | list, get, create, update |
| `keywords` | Keyword management | list, add, enable, pause, remove |
| `reports` | Analytics + GAQL | campaigns, ad-groups, keywords, search-terms, run |

## Data Model

All Google Ads resources use resource names as unique identifiers:
```
customers/{customer_id}/campaigns/{campaign_id}
customers/{customer_id}/adGroups/{ad_group_id}
customers/{customer_id}/campaignBudgets/{budget_id}
customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}
```

Monetary values are in micros (1/1,000,000 of currency unit):
- $5.00 = 5,000,000 micros
- $1.50 = 1,500,000 micros

## GAQL (Google Ads Query Language)

The core query mechanism. Used for all reads:

```sql
SELECT
    campaign.id,
    campaign.name,
    metrics.impressions,
    metrics.clicks,
    metrics.cost_micros
FROM campaign
WHERE campaign.status = 'ENABLED'
  AND segments.date DURING LAST_30_DAYS
ORDER BY metrics.impressions DESC
LIMIT 50
```

Resources: campaign, ad_group, keyword_view, search_term_view, campaign_budget, customer, customer_client

## Key Design Decisions

1. **Direct API calls** — No intermediate files or subprocess wrapping. The google-ads library IS the backend.
2. **Customer ID required for most operations** — Every API call is scoped to a customer account.
3. **Micros throughout** — API uses micros internally; CLI converts at display time.
4. **Default PAUSED for new campaigns** — Safety default to avoid accidental spend.
5. **Streaming queries** — All reads use `search_stream()` for memory efficiency.
6. **Field masks for updates** — Google Ads API requires explicit field masks for partial updates.

## Session State (REPL)

The REPL maintains:
- `customer_id` — the currently selected account (set with `set-customer <ID>`)
- `GoogleAdsClient` instance (lazy-initialized on first API call)
- `api_version` — default v24

There is no project file concept — state is the API itself.

## Error Handling

`GoogleAdsException` wraps gRPC errors with:
- `request_id` — for debugging with Google support
- `failure.errors[]` — list of error objects with message, location (field path), and error code

The CLI translates these to human-readable messages via `translate_google_ads_error()`.

## Limitations

- Requires active Google Ads account with developer token (test accounts available)
- Rate limits apply (default: 15,000 requests/day for basic access)
- Some fields (like ad creative content) require additional approval
- Manager (MCC) accounts need `login_customer_id` set for accessing child accounts
