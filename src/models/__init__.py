from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class Currency(BaseModel):
    code: str
    name: str
    symbol: str


class HistoryRecord(BaseModel):
    id: Optional[int] = None
    ts: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    item_name: str
    note: Optional[str] = None
    unit_cost: Decimal
    unit_steam_sell: Decimal
    qty: int
    unit_net: Decimal
    total_cost: Decimal
    total_steam_sell: Decimal
    total_net: Decimal
    sell_currency: str = "CNY"
    sell_currency_symbol: str = "¥"
    buy_currency: str = "CNY"
    buy_currency_symbol: str = "¥"
    exchange_rate: float = 1.0
    my_currency: str = "CNY"
    my_currency_symbol: str = "¥"
    total_cost_in_my_currency: Decimal = Decimal('0')
    total_net_in_my_currency: Decimal = Decimal('0')
    total_steam_sell_in_my_currency: Decimal = Decimal('0')
    discount: Decimal = Decimal('0')
    ratio: Decimal = Decimal('0')

    @field_validator('unit_cost', 'unit_steam_sell', 'unit_net', 'total_cost', 'total_steam_sell', 'total_net', 'exchange_rate', 'discount', 'ratio')
    @classmethod
    def validate_positive_numbers(cls, v):
        if v < 0:
            raise ValueError('数值必须大于等于0')
        return v

    @field_validator('qty')
    @classmethod
    def validate_positive_integer(cls, v):
        if v <= 0:
            raise ValueError('数量必须大于0')
        return v


class Settings(BaseModel):
    buy_currency: str = "CNY"
    buy_currency_symbol: str = "¥"
    sell_currency: str = "CNY"
    sell_currency_symbol: str = "¥"
    exchange_rate: float = 1.0
    steam_fee_rate: float = 0.15
    theme_mode: str = "DARK"
    my_currency: str = "CNY"
    my_currency_symbol: str = "¥"
    exchange_rate_updated_at: Optional[str] = None
    language: str = "zh"
    last_item_name: Optional[str] = None
    last_unit_cost: Optional[float] = None
    last_unit_sell: Optional[float] = None

    @field_validator('exchange_rate', 'steam_fee_rate')
    @classmethod
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('数值必须大于0')
        return v

    @field_validator('steam_fee_rate')
    @classmethod
    def validate_fee_rate(cls, v):
        if v >= 1:
            raise ValueError('手续费率必须小于1')
        return v


class StatsData(BaseModel):
    total_cost: Decimal = Decimal('0')
    total_net: Decimal = Decimal('0')
    total_sell: Decimal = Decimal('0')
    total_qty: int = 0
    avg_ratio: Decimal = Decimal('0')
    avg_discount: Decimal = Decimal('0')


class CalculationResult(BaseModel):
    unit_net: Decimal
    total_cost: Decimal
    total_cost_buy: Decimal = Decimal('0')
    total_net: Decimal
    ratio: Decimal
    discount: Decimal
    need_sell: Decimal = Decimal('0')
    required_qty: Optional[int] = None
    required_cost: Optional[Decimal] = None
    break_even_price: Optional[Decimal] = None