from app.config import DB_CONFIG
from app.types import Candle, Signal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional, Tuple, Union
import aiohttp
import asyncio
import logging
import psycopg


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_candles_until_close(
    symbol: str,
    signal_time: datetime,
    interval: str,
    stop_loss: float,
    take_profits: List[float],
    post_close_candles: int = 10,
) -> Tuple[List[Candle], Optional[datetime], Optional[Literal["success", "fail"]]]:
    if signal_time.tzinfo is None:
        signal_time = signal_time.replace(tzinfo=timezone.utc)
    else:
        signal_time = signal_time.astimezone(timezone.utc)

    delta = timedelta(minutes=1)
    candles: List[Candle] = []
    current_time = signal_time
    post_close_counter: Optional[int] = None
    close_time: Optional[datetime] = None
    result: Optional[Literal["success", "fail"]] = None

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

                if post_close_counter is not None:
                    post_close_counter -= 1
                    if post_close_counter <= 0:
                        return candles, close_time, result
                else:
                    if candle.low <= stop_loss:
                        result = "fail"
                        close_time = candle.time
                        post_close_counter = post_close_candles
                    elif any(candle.high >= tp for tp in take_profits):
                        result = "success"
                        close_time = candle.time
                        post_close_counter = post_close_candles

            last_candle_time = candles[-1].time
            current_time = last_candle_time + timedelta(milliseconds=1)

            now = datetime.now(timezone.utc)
            if current_time >= now:
                logger.info(
                    f"BREAK: current_time={current_time}, now={now}, candles={len(candles)}"
                )
                break

            await asyncio.sleep(0.05)

    return candles, close_time, result


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
                        c.time,
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


def update_closed_signal(
    signal_id: int, close_time: datetime, result: Literal["success", "fail"], pnl: float
):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE trading_signals SET close_time = %s, result = %s, pnl = %s WHERE id = %s",
                (close_time, result, pnl, signal_id),
            )
            logger.info(f"Updated signal {signal_id} to {close_time=} {result=} {pnl=}")


async def process_signal_row(
    sig: Signal, interval: str = "5m", post_close_intervals: int = 10
) -> None:
    if not sig.close_time:
        candles, close_time, result = await fetch_candles_until_close(
            sig.symbol,
            sig.signal_time,
            interval,
            sig.stop_loss,
            sig.take_profits,
            post_close_intervals,
        )
        save_candles(candles, interval)
        if close_time and result:
            pnl = count_pnl(sig, result)
            update_closed_signal(sig.id, close_time, result, pnl)
            logger.info(f"Signal {sig.id} closed at {close_time}")
        else:
            logger.info(f"Signal {sig.id} did not hit SL or TP")
    else:
        logger.info(f"🩷 Signal {sig.id} uses cached candles")


async def process_signals(sigs: List[Signal], interval="5m", post_close_intervals=7):
    for signal in sigs:
        await process_signal_row(
            signal, interval=interval, post_close_intervals=post_close_intervals
        )


def count_pnl(sig: Signal, result: Literal["success", "fail"]) -> float:
    if sig.action not in ("long", "short"):
        raise ValueError(f"Invalid signal: '{sig}'")

    if result == "success":
        target_price = sig.take_profits[0]
    else:
        target_price = sig.stop_loss

    if sig.action == "long":
        pnl = sig.leverage * (target_price / sig.entry_prices[0] - 1)
    else:
        pnl = sig.leverage * (1 - target_price / sig.entry_prices[0])

    return round(pnl * 100, 4)
