from decimal import Decimal, ROUND_HALF_UP


def money(x: float) -> str:
    return f"{x:,.2f}"


def money_decimal(x: Decimal) -> str:
    return f"{float(x):,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:,.2f}%"


def pct_decimal(x: Decimal) -> str:
    return f"{float(x * Decimal('100')):,.2f}%"


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