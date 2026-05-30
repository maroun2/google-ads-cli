"""Keyword management core module."""

from typing import Optional


def list_keywords(
    client, customer_id: str, ad_group_id: Optional[str] = None,
    campaign_id: Optional[str] = None, status_filter: Optional[str] = None
) -> list[dict]:
    """List keywords, optionally filtered by ad group or campaign."""
    ga_service = client.get_service("GoogleAdsService")
    conditions = []
    if ad_group_id:
        conditions.append(f"ad_group.id = {ad_group_id}")
    if campaign_id:
        conditions.append(f"campaign.id = {campaign_id}")
    if status_filter:
        conditions.append(f"ad_group_criterion.status = '{status_filter.upper()}'")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group_criterion.cpc_bid_micros,
            ad_group_criterion.quality_info.quality_score,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.average_cpc
        FROM keyword_view
        {where}
        ORDER BY ad_group_criterion.criterion_id
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            kw = row.ad_group_criterion
            ag = row.ad_group
            c = row.campaign
            m = row.metrics
            result.append({
                "criterion_id": str(kw.criterion_id),
                "text": kw.keyword.text,
                "match_type": kw.keyword.match_type.name if hasattr(kw.keyword.match_type, "name") else str(kw.keyword.match_type),
                "status": kw.status.name if hasattr(kw.status, "name") else str(kw.status),
                "cpc_bid_micros": kw.cpc_bid_micros,
                "quality_score": kw.quality_info.quality_score if kw.quality_info else None,
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost_micros": m.cost_micros,
                "average_cpc": m.average_cpc,
            })
    return result


def add_keywords(
    client,
    customer_id: str,
    ad_group_id: str,
    keywords: list[dict],
) -> list[dict]:
    """Add keywords to an ad group.

    Args:
        keywords: List of dicts with 'text', 'match_type' (BROAD/PHRASE/EXACT),
                  and optional 'cpc_bid_micros'.
    """
    ag_criterion_service = client.get_service("AdGroupCriterionService")
    operations = []

    for kw in keywords:
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        criterion.ad_group = f"customers/{customer_id}/adGroups/{ad_group_id}"
        criterion.status = client.enums.AdGroupCriterionStatusEnum["ENABLED"]
        criterion.keyword.text = kw["text"]
        criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum[
            kw.get("match_type", "BROAD").upper()
        ]
        if kw.get("cpc_bid_micros"):
            criterion.cpc_bid_micros = kw["cpc_bid_micros"]
        operations.append(op)

    response = ag_criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id, operations=operations
    )
    result = []
    for res in response.results:
        criterion_id = res.resource_name.split("/")[-1]
        result.append({"criterion_id": criterion_id, "resource_name": res.resource_name})
    return result


def update_keyword_status(
    client, customer_id: str, ad_group_id: str, criterion_id: str, status: str
) -> dict:
    """Enable or pause a keyword."""
    ag_criterion_service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.update
    criterion.resource_name = f"customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"
    criterion.status = client.enums.AdGroupCriterionStatusEnum[status.upper()]

    field_mask = client.get_type("FieldMask")
    field_mask.paths.append("status")
    op.update_mask.CopyFrom(field_mask)

    response = ag_criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id, operations=[op]
    )
    return {
        "criterion_id": criterion_id,
        "status": status,
        "resource_name": response.results[0].resource_name,
    }


def remove_keyword(
    client, customer_id: str, ad_group_id: str, criterion_id: str
) -> dict:
    """Remove a keyword from an ad group."""
    ag_criterion_service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    resource_name = f"customers/{customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"
    op.remove = resource_name
    ag_criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id, operations=[op]
    )
    return {"removed": criterion_id, "resource_name": resource_name}
