"""Ad group management core module."""

from typing import Optional


def list_ad_groups(
    client, customer_id: str, campaign_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> list[dict]:
    """List ad groups, optionally filtered by campaign."""
    ga_service = client.get_service("GoogleAdsService")
    conditions = []
    if campaign_id:
        conditions.append(f"campaign.id = {campaign_id}")
    if status_filter:
        conditions.append(f"ad_group.status = '{status_filter.upper()}'")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group.type,
            ad_group.cpc_bid_micros,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros
        FROM ad_group
        {where}
        ORDER BY ad_group.id
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            ag = row.ad_group
            c = row.campaign
            m = row.metrics
            result.append({
                "id": str(ag.id),
                "name": ag.name,
                "status": ag.status.name if hasattr(ag.status, "name") else str(ag.status),
                "type": ag.type_.name if hasattr(ag.type_, "name") else str(ag.type_),
                "cpc_bid_micros": ag.cpc_bid_micros,
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost_micros": m.cost_micros,
            })
    return result


def get_ad_group(client, customer_id: str, ad_group_id: str) -> dict:
    """Get details for a single ad group."""
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group.type,
            ad_group.cpc_bid_micros,
            ad_group.target_cpa_micros,
            campaign.id,
            campaign.name
        FROM ad_group
        WHERE ad_group.id = {ad_group_id}
        LIMIT 1
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            ag = row.ad_group
            c = row.campaign
            return {
                "id": str(ag.id),
                "name": ag.name,
                "status": ag.status.name if hasattr(ag.status, "name") else str(ag.status),
                "type": ag.type_.name if hasattr(ag.type_, "name") else str(ag.type_),
                "cpc_bid_micros": ag.cpc_bid_micros,
                "target_cpa_micros": ag.target_cpa_micros,
                "campaign_id": str(c.id),
                "campaign_name": c.name,
            }
    raise ValueError(f"Ad group {ad_group_id} not found")


def create_ad_group(
    client,
    customer_id: str,
    campaign_id: str,
    name: str,
    cpc_bid_micros: int = 1_000_000,
    status: str = "ENABLED",
    group_type: str = "SEARCH_STANDARD",
) -> dict:
    """Create an ad group within a campaign."""
    ag_service = client.get_service("AdGroupService")
    ag_operation = client.get_type("AdGroupOperation")
    ad_group = ag_operation.create

    ad_group.name = name
    ad_group.campaign = f"customers/{customer_id}/campaigns/{campaign_id}"
    ad_group.status = client.enums.AdGroupStatusEnum[status]
    ad_group.type_ = client.enums.AdGroupTypeEnum[group_type]
    ad_group.cpc_bid_micros = cpc_bid_micros

    response = ag_service.mutate_ad_groups(
        customer_id=customer_id, operations=[ag_operation]
    )
    resource_name = response.results[0].resource_name
    ad_group_id = resource_name.split("/")[-1]
    return {"ad_group_id": ad_group_id, "resource_name": resource_name}


def update_ad_group_status(
    client, customer_id: str, ad_group_id: str, status: str
) -> dict:
    """Enable or pause an ad group."""
    ag_service = client.get_service("AdGroupService")
    ag_operation = client.get_type("AdGroupOperation")
    ad_group = ag_operation.update

    ad_group.resource_name = f"customers/{customer_id}/adGroups/{ad_group_id}"
    ad_group.status = client.enums.AdGroupStatusEnum[status]

    field_mask = client.get_type("FieldMask")
    field_mask.paths.append("status")
    ag_operation.update_mask.CopyFrom(field_mask)

    response = ag_service.mutate_ad_groups(
        customer_id=customer_id, operations=[ag_operation]
    )
    return {
        "ad_group_id": ad_group_id,
        "status": status,
        "resource_name": response.results[0].resource_name,
    }
