"""Small helpers shared by the transaction tests."""

from datetime import date, timedelta


def headers(user: int) -> dict[str, str]:
    return {"X-User-Id": str(user)}


def days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def payload(category_id: int, **overrides) -> dict:
    body = {
        "type": "expense",
        "amount": "25.50",
        "transaction_date": days_ago(0),
        "id_category": category_id,
        "description": "Spesa",
    }
    body.update(overrides)
    return body
