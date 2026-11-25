"""Small helpers shared by the transaction tests."""

from datetime import date, timedelta

from app.service.profile.security import create_access_token


def headers(user: int) -> dict[str, str]:
    token, _ = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


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
