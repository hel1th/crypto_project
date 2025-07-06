from typing import List, Optional, TypedDict
from datetime import datetime
from dataclasses import dataclass


class Db_config(TypedDict):
    dbname: Optional[str]
    user: Optional[str]
    password: Optional[str]
    host: Optional[str]
    port: Optional[str]


@dataclass
class Signal:
    id: int
    message_id: int
    channel_id: int
    symbol: str
    action: str
    stop_loss: float
    leverage: int
    margin_mode: str
    signal_time: datetime
    created_at: datetime
    entry_prices: List[float]
    take_profits: List[float]
    close_time: Optional[datetime]

    @classmethod
    def from_row(cls, row: tuple) -> "Signal":
        return cls(
            id=row[0],
            message_id=row[1],
            channel_id=row[2],
            symbol=row[3],
            action=row[4],
            stop_loss=row[5],
            leverage=row[6],
            margin_mode=row[7],
            signal_time=row[8],
            created_at=row[9],
            entry_prices=row[10],
            take_profits=row[11],
            close_time=row[12],
        )


@dataclass
class Candle:
    time: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_row(cls, row: tuple) -> "Candle":
        return cls(
            time=row[0],
            symbol=row[1],
            open=row[2],
            high=row[3],
            low=row[4],
            close=row[5],
            volume=row[6],
        )
