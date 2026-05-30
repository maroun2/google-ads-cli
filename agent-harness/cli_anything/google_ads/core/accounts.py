"""Account / customer management core module."""

from typing import Optional


def list_accessible_customers(client) -> list[dict]:
    """List all customer accounts accessible with current credentials."""
    svc = client.get_service("CustomerService")
    response = svc.list_accessible_customers()
    result = []
    for resource_name in response.resource_names:
        customer_id = resource_name.split("/")[-1]
        result.append({"resource_name": resource_name, "customer_id": customer_id})
    return result


def get_customer_info(client, customer_id: str) -> dict:
    """Get detailed info for a specific customer account."""
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            customer.id,
            customer.descriptive_name,
            customer.currency_code,
            customer.time_zone,
            customer.auto_tagging_enabled,
            customer.status
        FROM customer
        LIMIT 1
    """
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
        for row in batch.results:
            c = row.customer
            return {
                "id": str(c.id),
                "name": c.descriptive_name,
                "currency": c.currency_code,
                "timezone": c.time_zone,
                "auto_tagging": c.auto_tagging_enabled,
                "status": c.status.name if hasattr(c.status, "name") else str(c.status),
            }
    return {"id": customer_id, "name": "Unknown"}


def list_manager_accounts(client, customer_id: str) -> list[dict]:
    """List child customer accounts under a manager (MCC) account."""
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            customer_client.id,
            customer_client.descriptive_name,
            customer_client.currency_code,
            customer_client.time_zone,
            customer_client.status,
            customer_client.level,
            customer_client.manager
        FROM customer_client
        WHERE customer_client.level = 1
        ORDER BY customer_client.id
    """
    result = []
    try:
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            for row in batch.results:
                cc = row.customer_client
                result.append({
                    "id": str(cc.id),
                    "name": cc.descriptive_name,
                    "currency": cc.currency_code,
                    "timezone": cc.time_zone,
                    "status": cc.status.name if hasattr(cc.status, "name") else str(cc.status),
                    "level": cc.level,
                    "is_manager": cc.manager,
                })
    except Exception:
        pass
    return result
