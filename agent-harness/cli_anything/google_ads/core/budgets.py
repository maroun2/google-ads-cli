"""Campaign budget management core module."""

from typing import Optional


def list_budgets(client, customer_id: str) -> list[dict]:
    """List all shared campaign budgets."""
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            campaign_budget.id,
            campaign_budget.name,
            campaign_budget.amount_micros,
            campaign_budget.period,
            campaign_budget.status,
            campaign_budget.total_amount_micros,
            campaign_budget.explicitly_shared,
            campaign_budget.reference_count
        FROM campaign_budget
        WHERE campaign_budget.explicitly_shared = TRUE
        ORDER BY campaign_budget.id
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            b = row.campaign_budget
            result.append({
                "id": str(b.id),
                "name": b.name,
                "amount_micros": b.amount_micros,
                "amount": b.amount_micros / 1_000_000,
                "period": b.period.name if hasattr(b.period, "name") else str(b.period),
                "status": b.status.name if hasattr(b.status, "name") else str(b.status),
                "total_amount_micros": b.total_amount_micros,
                "explicitly_shared": b.explicitly_shared,
                "reference_count": b.reference_count,
            })
    return result


def list_all_budgets(client, customer_id: str) -> list[dict]:
    """List all budgets including non-shared ones."""
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            campaign_budget.id,
            campaign_budget.name,
            campaign_budget.amount_micros,
            campaign_budget.period,
            campaign_budget.status,
            campaign_budget.explicitly_shared,
            campaign_budget.reference_count
        FROM campaign_budget
        ORDER BY campaign_budget.id
    """
    result = []
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            b = row.campaign_budget
            result.append({
                "id": str(b.id),
                "name": b.name,
                "amount_micros": b.amount_micros,
                "amount": b.amount_micros / 1_000_000,
                "period": b.period.name if hasattr(b.period, "name") else str(b.period),
                "status": b.status.name if hasattr(b.status, "name") else str(b.status),
                "explicitly_shared": b.explicitly_shared,
                "reference_count": b.reference_count,
            })
    return result


def get_budget(client, customer_id: str, budget_id: str) -> dict:
    """Get details for a specific budget."""
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign_budget.id,
            campaign_budget.name,
            campaign_budget.amount_micros,
            campaign_budget.period,
            campaign_budget.status,
            campaign_budget.total_amount_micros,
            campaign_budget.explicitly_shared,
            campaign_budget.reference_count
        FROM campaign_budget
        WHERE campaign_budget.id = {budget_id}
        LIMIT 1
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            b = row.campaign_budget
            return {
                "id": str(b.id),
                "name": b.name,
                "amount_micros": b.amount_micros,
                "amount": b.amount_micros / 1_000_000,
                "period": b.period.name if hasattr(b.period, "name") else str(b.period),
                "status": b.status.name if hasattr(b.status, "name") else str(b.status),
                "total_amount_micros": b.total_amount_micros,
                "explicitly_shared": b.explicitly_shared,
                "reference_count": b.reference_count,
            }
    raise ValueError(f"Budget {budget_id} not found")


def create_budget(
    client,
    customer_id: str,
    name: str,
    amount_micros: int,
    period: str = "DAILY",
    explicitly_shared: bool = True,
) -> dict:
    """Create a new campaign budget.

    Args:
        amount_micros: Budget amount in micros (e.g. 5000000 = $5.00).
        period: DAILY or FIXED_DAILY (default DAILY).
        explicitly_shared: If True, budget can be shared across campaigns.
    """
    budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")
    budget = budget_operation.create

    budget.name = name
    budget.amount_micros = amount_micros
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum["STANDARD"]
    budget.period = client.enums.BudgetPeriodEnum[period]
    budget.explicitly_shared = explicitly_shared

    response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[budget_operation]
    )
    resource_name = response.results[0].resource_name
    budget_id = resource_name.split("/")[-1]
    return {
        "budget_id": budget_id,
        "resource_name": resource_name,
        "amount_micros": amount_micros,
        "amount": amount_micros / 1_000_000,
    }


def update_budget_amount(
    client, customer_id: str, budget_id: str, amount_micros: int
) -> dict:
    """Update a budget's daily amount."""
    budget_service = client.get_service("CampaignBudgetService")
    budget_operation = client.get_type("CampaignBudgetOperation")
    budget = budget_operation.update

    budget.resource_name = f"customers/{customer_id}/campaignBudgets/{budget_id}"
    budget.amount_micros = amount_micros

    field_mask = client.get_type("FieldMask")
    field_mask.paths.append("amount_micros")
    budget_operation.update_mask.CopyFrom(field_mask)

    response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[budget_operation]
    )
    return {
        "budget_id": budget_id,
        "amount_micros": amount_micros,
        "amount": amount_micros / 1_000_000,
        "resource_name": response.results[0].resource_name,
    }
