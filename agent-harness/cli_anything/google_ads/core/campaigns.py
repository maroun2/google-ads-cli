"""Campaign management core module."""

from typing import Optional


def list_campaigns(client, customer_id: str, status_filter: Optional[str] = None) -> list[dict]:
    """List campaigns for a customer.

    Args:
        client: GoogleAdsClient instance.
        customer_id: Google Ads customer ID (digits only).
        status_filter: Optional status filter: ENABLED, PAUSED, REMOVED, or None for all.
    """
    ga_service = client.get_service("GoogleAdsService")
    where_clause = ""
    if status_filter:
        where_clause = f"WHERE campaign.status = '{status_filter.upper()}'"

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.start_date,
            campaign.end_date,
            campaign_budget.amount_micros,
            campaign_budget.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros
        FROM campaign
        {where_clause}
        ORDER BY campaign.id
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            c = row.campaign
            b = row.campaign_budget
            m = row.metrics
            result.append({
                "id": str(c.id),
                "name": c.name,
                "status": c.status.name if hasattr(c.status, "name") else str(c.status),
                "channel": c.advertising_channel_type.name if hasattr(c.advertising_channel_type, "name") else str(c.advertising_channel_type),
                "bidding": c.bidding_strategy_type.name if hasattr(c.bidding_strategy_type, "name") else str(c.bidding_strategy_type),
                "start_date": c.start_date,
                "end_date": c.end_date,
                "budget_micros": b.amount_micros,
                "budget_name": b.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost_micros": m.cost_micros,
            })
    return result


def get_campaign(client, customer_id: str, campaign_id: str) -> dict:
    """Get details for a single campaign."""
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.start_date,
            campaign.end_date,
            campaign.serving_status,
            campaign_budget.amount_micros,
            campaign_budget.name,
            campaign_budget.period
        FROM campaign
        WHERE campaign.id = {campaign_id}
        LIMIT 1
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            c = row.campaign
            b = row.campaign_budget
            return {
                "id": str(c.id),
                "name": c.name,
                "status": c.status.name if hasattr(c.status, "name") else str(c.status),
                "serving_status": c.serving_status.name if hasattr(c.serving_status, "name") else str(c.serving_status),
                "channel": c.advertising_channel_type.name if hasattr(c.advertising_channel_type, "name") else str(c.advertising_channel_type),
                "bidding": c.bidding_strategy_type.name if hasattr(c.bidding_strategy_type, "name") else str(c.bidding_strategy_type),
                "start_date": c.start_date,
                "end_date": c.end_date,
                "budget_micros": b.amount_micros,
                "budget_name": b.name,
                "budget_period": b.period.name if hasattr(b.period, "name") else str(b.period),
            }
    raise ValueError(f"Campaign {campaign_id} not found")


def create_campaign(
    client,
    customer_id: str,
    name: str,
    budget_id: str,
    channel_type: str = "SEARCH",
    status: str = "PAUSED",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Create a new campaign.

    Args:
        client: GoogleAdsClient instance.
        customer_id: Google Ads customer ID.
        name: Campaign name.
        budget_id: Resource name or ID of an existing budget.
        channel_type: SEARCH, DISPLAY, SHOPPING, VIDEO, etc.
        status: ENABLED or PAUSED (default PAUSED for safety).
        start_date: YYYYMMDD format, defaults to today.
        end_date: YYYYMMDD format, optional.

    Returns:
        dict with 'campaign_id' and 'resource_name'.
    """
    from datetime import date

    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create

    campaign.name = name
    campaign.status = client.enums.CampaignStatusEnum[status]
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum[channel_type]

    # Manual CPC bidding (simplest default)
    campaign.manual_cpc.enhanced_cpc_enabled = False

    # Budget resource name
    if "/" not in budget_id:
        budget_id = f"customers/{customer_id}/campaignBudgets/{budget_id}"
    campaign.campaign_budget = budget_id

    # Dates
    if start_date:
        campaign.start_date = start_date
    else:
        campaign.start_date = date.today().strftime("%Y%m%d")
    if end_date:
        campaign.end_date = end_date

    # Network settings for SEARCH
    if channel_type == "SEARCH":
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_operation]
    )
    resource_name = response.results[0].resource_name
    campaign_id = resource_name.split("/")[-1]
    return {"campaign_id": campaign_id, "resource_name": resource_name}


def update_campaign_status(
    client, customer_id: str, campaign_id: str, status: str
) -> dict:
    """Enable or pause a campaign.

    Args:
        status: ENABLED or PAUSED.
    """
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.update

    campaign.resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
    campaign.status = client.enums.CampaignStatusEnum[status]

    field_mask = client.get_type("FieldMask")
    field_mask.paths.append("status")
    campaign_operation.update_mask.CopyFrom(field_mask)

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_operation]
    )
    return {
        "campaign_id": campaign_id,
        "status": status,
        "resource_name": response.results[0].resource_name,
    }


def remove_campaign(client, customer_id: str, campaign_id: str) -> dict:
    """Remove (delete) a campaign."""
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"
    campaign_operation.remove = resource_name
    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_operation]
    )
    return {"removed": campaign_id, "resource_name": resource_name}
