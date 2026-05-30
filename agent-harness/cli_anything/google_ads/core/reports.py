"""Reporting core module — GAQL queries and pre-built reports."""

from typing import Optional


def run_query(client, customer_id: str, query: str) -> list[dict]:
    """Execute a raw GAQL query and return results as list of dicts.

    Each row is a flat dict of field_path -> value.
    """
    ga_service = client.get_service("GoogleAdsService")
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            row_dict = {}
            _flatten_proto(row, row_dict, "")
            result.append(row_dict)
    return result


def campaign_performance(
    client,
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    status_filter: Optional[str] = None,
) -> list[dict]:
    """Campaign performance report."""
    ga_service = client.get_service("GoogleAdsService")
    where_parts = [f"segments.date DURING {date_range}"]
    if status_filter:
        where_parts.append(f"campaign.status = '{status_filter.upper()}'")
    where = "WHERE " + " AND ".join(where_parts)

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc,
            metrics.cost_per_conversion
        FROM campaign
        {where}
        ORDER BY metrics.impressions DESC
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            c = row.campaign
            m = row.metrics
            result.append({
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "status": c.status.name if hasattr(c.status, "name") else str(c.status),
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost_micros": m.cost_micros,
                "cost": m.cost_micros / 1_000_000,
                "conversions": m.conversions,
                "ctr": round(m.ctr * 100, 2),
                "avg_cpc_micros": m.average_cpc,
                "avg_cpc": m.average_cpc / 1_000_000,
                "cost_per_conversion": m.cost_per_conversion / 1_000_000 if m.conversions > 0 else 0,
            })
    return result


def ad_group_performance(
    client,
    customer_id: str,
    campaign_id: Optional[str] = None,
    date_range: str = "LAST_30_DAYS",
) -> list[dict]:
    """Ad group performance report."""
    ga_service = client.get_service("GoogleAdsService")
    conditions = [f"segments.date DURING {date_range}"]
    if campaign_id:
        conditions.append(f"campaign.id = {campaign_id}")
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group
        {where}
        ORDER BY metrics.impressions DESC
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            ag = row.ad_group
            c = row.campaign
            m = row.metrics
            result.append({
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "status": ag.status.name if hasattr(ag.status, "name") else str(ag.status),
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost_micros": m.cost_micros,
                "cost": m.cost_micros / 1_000_000,
                "conversions": m.conversions,
                "ctr": round(m.ctr * 100, 2),
                "avg_cpc": m.average_cpc / 1_000_000,
            })
    return result


def keyword_performance(
    client,
    customer_id: str,
    campaign_id: Optional[str] = None,
    ad_group_id: Optional[str] = None,
    date_range: str = "LAST_30_DAYS",
    limit: int = 100,
) -> list[dict]:
    """Keyword performance report."""
    ga_service = client.get_service("GoogleAdsService")
    conditions = [f"segments.date DURING {date_range}"]
    if campaign_id:
        conditions.append(f"campaign.id = {campaign_id}")
    if ad_group_id:
        conditions.append(f"ad_group.id = {ad_group_id}")
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM keyword_view
        {where}
        ORDER BY metrics.impressions DESC
        LIMIT {limit}
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
                "keyword": kw.keyword.text,
                "match_type": kw.keyword.match_type.name if hasattr(kw.keyword.match_type, "name") else str(kw.keyword.match_type),
                "status": kw.status.name if hasattr(kw.status, "name") else str(kw.status),
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost": m.cost_micros / 1_000_000,
                "conversions": m.conversions,
                "ctr": round(m.ctr * 100, 2),
                "avg_cpc": m.average_cpc / 1_000_000,
            })
    return result


def search_terms_report(
    client,
    customer_id: str,
    campaign_id: Optional[str] = None,
    date_range: str = "LAST_30_DAYS",
    limit: int = 100,
) -> list[dict]:
    """Search terms (actual queries) report."""
    ga_service = client.get_service("GoogleAdsService")
    conditions = [f"segments.date DURING {date_range}"]
    if campaign_id:
        conditions.append(f"campaign.id = {campaign_id}")
    where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            search_term_view.search_term,
            search_term_view.status,
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM search_term_view
        {where}
        ORDER BY metrics.impressions DESC
        LIMIT {limit}
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            st = row.search_term_view
            c = row.campaign
            ag = row.ad_group
            m = row.metrics
            result.append({
                "search_term": st.search_term,
                "status": st.status.name if hasattr(st.status, "name") else str(st.status),
                "campaign_id": str(c.id),
                "campaign_name": c.name,
                "ad_group_id": str(ag.id),
                "ad_group_name": ag.name,
                "impressions": m.impressions,
                "clicks": m.clicks,
                "cost": m.cost_micros / 1_000_000,
                "conversions": m.conversions,
                "ctr": round(m.ctr * 100, 2),
            })
    return result


def _flatten_proto(obj, result: dict, prefix: str):
    """Recursively flatten a proto-plus message to a flat dict."""
    try:
        descriptor = type(obj).meta.pb.DESCRIPTOR
        for field in descriptor.fields:
            val = getattr(obj, field.name, None)
            key = f"{prefix}{field.name}" if prefix else field.name
            if val is None:
                result[key] = None
            elif hasattr(val, "meta"):
                _flatten_proto(val, result, f"{key}.")
            elif hasattr(val, "name"):
                # Enum
                result[key] = val.name
            else:
                result[key] = val
    except (AttributeError, Exception):
        # Fallback for non-proto objects
        try:
            for attr in dir(obj):
                if not attr.startswith("_"):
                    try:
                        val = getattr(obj, attr)
                        if not callable(val):
                            key = f"{prefix}{attr}" if prefix else attr
                            result[key] = str(val)
                    except Exception:
                        pass
        except Exception:
            pass
