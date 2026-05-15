def money(x: float) -> str:
    return f"{x:,.2f}"


def pct(x: float) -> str:
    return f"{x * 100:,.2f}%"


def safe_float(s: str) -> float:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def safe_int(s: str) -> int:
    try:
        s = (s or "").strip().replace(",", "")
        if s == "":
            return 1
        v = int(float(s))
        return max(v, 1)
    except Exception:
        return 1