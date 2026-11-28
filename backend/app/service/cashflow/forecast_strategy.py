from abc import ABC, abstractmethod
from decimal import ROUND_HALF_UP, Decimal


class ForecastStrategy(ABC):
    @abstractmethod
    def estimate(self, daily_expenses: list[Decimal]) -> Decimal:
        """Estimate daily spending for one category from its observed daily totals."""
        ...


class Percentile75Strategy(ForecastStrategy):
    def estimate(self, daily_expenses: list[Decimal]) -> Decimal:
        if not daily_expenses:
            raise ValueError("At least one observed day is required.")

        ordered = sorted(daily_expenses)
        position = Decimal("0.75") * (len(ordered) - 1)

        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = position - lower

        estimate = ordered[lower] + fraction * (ordered[upper] - ordered[lower])
        return estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
