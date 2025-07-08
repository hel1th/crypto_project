from app.config import DB_CONFIG, TZ, INTERVALS_TO_DELTA
from app.types import Candle, Signal
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from typing import Dict, List, Optional, Tuple, Union
import aiohttp
import asyncio
import logging
import psycopg


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_candles_until_hit(
    symbol: str,
    signal_time: datetime,
    interval: str,
    stop_loss: float,
    take_profits: List[float],
    post_hit_intervals: int = 10,
) -> Tuple[List[Candle], Optional[datetime]]:
    if signal_time.tzinfo is None:
        signal_time = signal_time.replace(tzinfo=timezone.utc)
    else:
        signal_time = signal_time.astimezone(timezone.utc)

    delta = INTERVALS_TO_DELTA[interval]
    candles: List[Candle] = []
    current_time = signal_time
    post_hit_counter: Optional[int] = None
    hit_time: Optional[datetime] = None

    async with aiohttp.ClientSession() as session:
        while True:
            start_ms = int(current_time.timestamp() * 1000)
            url = (
                f"https://api.binance.com/api/v3/klines"
                f"?symbol={symbol}&interval={interval}&startTime={start_ms}&limit=1000"
            )

            async with session.get(url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Binance API error: {response.status}")
                data_from_api = await response.json()

            if not data_from_api:
                break

            for k in data_from_api:
                candle = Candle(
                    time=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                    symbol=symbol,
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                )

                candles.append(candle)

                if post_hit_counter is not None:
                    post_hit_counter -= 1
                    if post_hit_counter <= 0:
                        return candles, hit_time
                else:
                    if candle.low <= stop_loss:
                        hit_time = candle.time
                        post_hit_counter = post_hit_intervals
                    elif any(candle.high >= tp for tp in take_profits):
                        hit_time = candle.time
                        post_hit_counter = post_hit_intervals

            last_candle_time = candles[-1].time
            current_time = last_candle_time + timedelta(milliseconds=1)

            now = datetime.now(timezone.utc)
            if current_time >= now:
                logger.info(
                    f"BREAK: current_time={current_time}, now={now}, candles={len(candles)}"
                )
                break

            await asyncio.sleep(0.05)

    return candles, hit_time


def save_candles(candles: List[Candle], interval):
    if not candles:
        return
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO candles (time, symbol, open, high, low, close, volume, interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, symbol) DO NOTHING
                """,
                [
                    (
                        c.time.replace(tzinfo=None),
                        c.symbol,
                        c.open,
                        c.high,
                        c.low,
                        c.close,
                        c.volume,
                        interval,
                    )
                    for c in candles
                ],
            )
            logger.info(f"Saved {len(candles)} candles for {candles[0].symbol}")


def update_signal_close_time(signal_id, close_time):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE trading_signals SET close_time = %s WHERE id = %s",
                (close_time, signal_id),
            )
            logger.info(f"Updated close_time for signal {signal_id} to {close_time}")


async def process_signal_row(signal_row: Signal, interval="5m", post_hit_intervals=10):
    signal_id = signal_row.id
    symbol = signal_row.symbol
    signal_time = signal_row.signal_time
    stop_loss = signal_row.stop_loss

    entry_prices = signal_row.entry_prices
    take_profits = signal_row.take_profits

    candles, hit_time = await fetch_candles_until_hit(
        symbol, signal_time, interval, stop_loss, take_profits, post_hit_intervals
    )

    save_candles(candles, interval)
    if hit_time:
        update_signal_close_time(signal_id, hit_time)
        logger.info(f"Signal {signal_id} closed at {hit_time}")
    else:
        logger.info(f"Signal {signal_id} did not hit SL or TP")


async def process_signals(signals: List[Signal], interval="5m", post_hit_intervals=7):
    for signal in signals:
        await process_signal_row(
            signal, interval=interval, post_hit_intervals=post_hit_intervals
        )
