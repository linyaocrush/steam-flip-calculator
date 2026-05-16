from pydantic import BaseModel, Field
from typing import Optional


class CalculateRequest(BaseModel):
    unit_cost: float = Field(default=0.0, description="第三方成本（单价）")
    unit_steam_sell: float = Field(default=0.0, description="Steam 售出金额（单价）")
    qty: int = Field(default=1, description="数量")
    use_exchange: bool = Field(default=False, description="是否使用汇率转换")
    exchange_rate: float = Field(default=1.0, description="汇率")
    fee_rate: float = Field(default=0.15, description="手续费率")


class CalculateResponse(BaseModel):
    unit_net: float
    total_cost: float
    total_net: float
    total_steam_sell: float
    ratio: float
    discount: float
    need_sell: float


class SettingsRequest(BaseModel):
    buy_currency: str = Field(default="CNY", description="买入货币")
    buy_currency_symbol: str = Field(default="¥", description="买入货币符号")
    sell_currency: str = Field(default="CNY", description="卖出货币")
    sell_currency_symbol: str = Field(default="¥", description="卖出货币符号")
    exchange_rate: float = Field(default=1.0, description="汇率")
    steam_fee_rate: float = Field(default=0.15, description="Steam 手续费率")
    theme_mode: str = Field(default="LIGHT", description="主题模式")
    my_currency: str = Field(default="CNY", description="我的货币")
    my_currency_symbol: str = Field(default="¥", description="我的货币符号")
    language: str = Field(default="zh", description="语言")


class SettingsResponse(BaseModel):
    buy_currency: str
    buy_currency_symbol: str
    sell_currency: str
    sell_currency_symbol: str
    exchange_rate: float
    steam_fee_rate: float
    theme_mode: str
    my_currency: str
    my_currency_symbol: str
    exchange_rate_updated_at: Optional[str] = None
    language: str


class RecordRequest(BaseModel):
    item_name: str = Field(..., description="物品名称")
    note: str = Field(default="", description="备注")
    unit_cost: float = Field(..., description="单价成本")
    unit_steam_sell: float = Field(..., description="单价售价")
    qty: int = Field(default=1, description="数量")


class RecordResponse(BaseModel):
    id: int
    ts: str
    item_name: str
    note: str
    unit_cost: float
    unit_steam_sell: float
    qty: int
    total_cost: float
    total_net: float
    discount_pct: float


class StatsResponse(BaseModel):
    total_cost: float
    total_net: float
    total_steam_sell: float
    total_qty: int
    ratio: float
    discount: float


class ErrorResponse(BaseModel):
    error: str


class ExchangeRateResponse(BaseModel):
    base: str
    target: str
    rate: float


class SettingsSaveResponse(BaseModel):
    message: str
    auto_fetch_rate: bool
    rate_source: str
    exchange_rate: float
    exchange_rate_updated_at: Optional[str] = None