"""Unit tests of the alert conditions (RF_CG_3), with the numbers of the RAD scenarios.

Category Partition per condition: (a) Sostenibile / Attenzione / Critico, with or without an
expense on the Critical Date; (b) expense due today, on day 3, on day 4, equal to or greater
than the daily STS; (c) drop of exactly 30%, more than 30%, increase, no previous value.
"""

from datetime import date
from decimal import Decimal

from app.service.alert.alert_rules import (
    ProjectionSnapshot,
    UpcomingExpense,
    evaluate,
    format_day,
    format_euro,
    impending_message,
    risk_message,
    sts_drop_message,
)

TODAY = date(2026, 11, 20)


def projection(risk="Sostenibile", minimum="500", critical=date(2026, 11, 23), daily="20"):
    return ProjectionSnapshot(
        minimum_balance=Decimal(minimum),
        critical_date=critical,
        daily_safe_to_spend=Decimal(daily),
        risk_level=risk,
        safety_buffer=Decimal("200"),
    )


# -- formatting ---------------------------------------------------------------------------


def test_format_euro():
    assert format_euro(Decimal("1500")) == "1.500 €"
    assert format_euro(Decimal("5.68")) == "5,68 €"
    assert format_euro(Decimal("-250.00")) == "−250 €"
    assert format_euro(Decimal("1234.5")) == "1.234,50 €"


def test_format_day():
    assert format_day(date(2026, 11, 23), TODAY) == "23"
    assert format_day(date(2026, 12, 3), TODAY) == "3/12"


# -- (a) risk level -----------------------------------------------------------------------


def test_risk_sustainable_gives_no_alert():
    assert risk_message(projection(), [], TODAY) is None


def test_risk_attention_scenario_sc_rf_cg_3():
    """Chiara: the 480 € car insurance of the 23rd takes the balance to 150 €."""
    insurance = UpcomingExpense("Assicurazione auto", Decimal("480"), date(2026, 11, 23))
    message = risk_message(projection("Attenzione", "150"), [insurance], TODAY)
    assert message == (
        "«Assicurazione auto» di 480 € del 23 porta il saldo a 150 €, "
        "sotto il tuo Safety Buffer di 200 €"
    )


def test_risk_critical_names_the_biggest_expense_and_no_buffer():
    rent = UpcomingExpense("Affitto", Decimal("650"), date(2026, 11, 23))
    gym = UpcomingExpense("Palestra", Decimal("40"), date(2026, 11, 23))
    message = risk_message(projection("Critico", "-250"), [gym, rent], TODAY)
    assert message == "«Affitto» di 650 € del 23 porta il saldo a −250 €"


def test_risk_without_expense_on_critical_date():
    message = risk_message(projection("Attenzione", "150"), [], TODAY)
    assert message == "Il 23 il saldo previsto scende a 150 €, sotto il tuo Safety Buffer di 200 €"


# -- (b) impending expense ----------------------------------------------------------------


def expense(day, amount="100", name="Bolletta"):
    return UpcomingExpense(name, Decimal(amount), day)


def test_impending_today_and_on_day_3_are_included():
    p = projection(daily="20")
    assert impending_message(p, [expense(TODAY)], TODAY) is not None
    assert impending_message(p, [expense(date(2026, 11, 23))], TODAY) is not None


def test_impending_on_day_4_is_excluded():
    assert impending_message(projection(), [expense(date(2026, 11, 24))], TODAY) is None


def test_impending_equal_to_daily_sts_is_excluded():
    assert impending_message(projection(daily="100"), [expense(TODAY, "100")], TODAY) is None


def test_impending_message_and_count_of_others():
    upcoming = [
        expense(date(2026, 11, 22), "650", "Affitto"),
        expense(date(2026, 11, 21), "90", "Bolletta luce"),
        expense(date(2026, 11, 23), "30", "Palestra"),
        expense(date(2026, 11, 21), "10", "Abbonamento"),  # below the daily STS of 20 €
    ]
    message = impending_message(projection(daily="20"), upcoming, TODAY)
    assert message == (
        "«Bolletta luce» di 90 € scade il 21 e supera il tuo STS giornaliero di 20 € "
        "(e ci sono altre 2 uscite nei prossimi 3 giorni)"
    )


# -- (c) STS drop -------------------------------------------------------------------------


def test_sts_drop_scenario_sc_rf_cf_4():
    """Marco: daily STS from 5,68 € to 3,32 € after a 45 € book (−41.5%)."""
    message = sts_drop_message(Decimal("5.68"), Decimal("3.32"))
    assert message == "Il tuo STS giornaliero è sceso da 5,68 € a 3,32 €"


def test_sts_drop_of_exactly_30_percent_is_not_enough():
    assert sts_drop_message(Decimal("10.00"), Decimal("7.00")) is None


def test_sts_drop_just_over_30_percent():
    assert sts_drop_message(Decimal("10.00"), Decimal("6.99")) is not None


def test_sts_increase_or_missing_previous_value():
    assert sts_drop_message(Decimal("5.00"), Decimal("8.00")) is None
    assert sts_drop_message(None, Decimal("3.00")) is None
    assert sts_drop_message(Decimal("0.00"), Decimal("0.00")) is None


# -- all together -------------------------------------------------------------------------


def test_evaluate_returns_every_type():
    result = evaluate(projection(), [], None, TODAY)
    assert result == {"risk_level": None, "impending_expense": None, "sts_drop": None}


def test_evaluate_uses_expenses_on_the_critical_date_for_the_risk():
    insurance = UpcomingExpense("Assicurazione auto", Decimal("480"), date(2026, 11, 23))
    other_day = UpcomingExpense("Cena", Decimal("70"), date(2026, 11, 21))
    result = evaluate(
        projection("Attenzione", "150", daily="5"), [other_day, insurance], None, TODAY
    )
    assert result["risk_level"].startswith("«Assicurazione auto»")
    assert result["impending_expense"].startswith("«Cena» di 70 € scade il 21")
