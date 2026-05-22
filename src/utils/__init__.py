from decimal import Decimal, ROUND_HALF_UP
import threading
import time


class Debouncer:
    """Debounce calls to a function — the last call within `delay_ms` wins."""

    def __init__(self, delay_ms=200):
        self.delay = delay_ms / 1000.0
        self._timer = None

    def __call__(self, fn):
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
        self._timer = threading.Timer(self.delay, fn)
        self._timer.daemon = True
        self._timer.start()

    def cancel(self):
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
            self._timer = None


def money(x: float) -> str:
    return f"{x:,.2f}"


def money_decimal(x: Decimal) -> str:
    return f"{x:,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:,.2f}%"


def pct_raw(x: float) -> str:
    """Format an already-percentage value (e.g. 17.65 -> '17.65%')."""
    return f"{x:,.2f}%"


def pct_decimal(x: Decimal) -> str:
    return f"{x * Decimal('100'):,.2f}%"


def safe_float(s: str) -> float:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def safe_decimal(s: str) -> Decimal:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return Decimal('0')
        return Decimal(s)
    except Exception:
        return Decimal('0')


def safe_int(s: str) -> int:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 1
        v = int(float(s))
        return max(v, 1)
    except Exception:
        return 1