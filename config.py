import os

CURRENCIES = [
    {"code": "CNY", "name": "人民币", "symbol": "¥"},
    {"code": "USD", "name": "美元", "symbol": "$"},
    {"code": "JPY", "name": "日元", "symbol": "¥"},
    {"code": "EUR", "name": "欧元", "symbol": "€"},
    {"code": "GBP", "name": "英镑", "symbol": "£"},
    {"code": "KRW", "name": "韩元", "symbol": "₩"},
    {"code": "HKD", "name": "港币", "symbol": "HK$"},
    {"code": "AUD", "name": "澳元", "symbol": "A$"},
    {"code": "CAD", "name": "加元", "symbol": "C$"},
    {"code": "SGD", "name": "新加坡元", "symbol": "S$"},
]

CURRENCY_CODES = [c["code"] for c in CURRENCIES]
CURRENCY_SYMBOLS = {c["code"]: c["symbol"] for c in CURRENCIES}
CURRENCY_NAMES = {c["code"]: c["name"] for c in CURRENCIES}

DEFAULT_SETTINGS = {
    "buy_currency": "CNY",
    "buy_currency_symbol": "¥",
    "sell_currency": "CNY",
    "sell_currency_symbol": "¥",
    "exchange_rate": 1.0,
    "steam_fee_rate": 0.15,
    "theme_mode": "LIGHT",
    "my_currency": "CNY",
    "my_currency_symbol": "¥",
    "exchange_rate_updated_at": None,
    "language": "zh",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "steam_flip.db")
CACHE_TTL = 5