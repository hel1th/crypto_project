import psycopg2
from ast import literal_eval
import gigachat
from gigachat.models import Chat, Messages, MessagesRole
from datetime import datetime
import logging
from ..config import DB_CONFIG, API_KEY_LLM
import json

logger = logging.getLogger(__name__)


def llm_parse_and_insert(message_id, channel_id, text, signal_time):
    client = gigachat.GigaChat(credentials=API_KEY_LLM, verify_ssl_certs=False)

    prompt = f"""Parse message '{text}', forming a dict message_parse = {{'coin': str without #, 'timeframe': str,
        'signal_type': str, 'entry_prices': list, 'take_profit_targets': list, 'stop_loss': float, 
        'leverage': int, 'margin_mode': str, 'channel': str}}. Return only dict as a variable message_parse. 
        stop_loss must be a single float value. Do not add extra symbols."""

    messages = [
        Messages(
            role=MessagesRole.SYSTEM,
            content="You are a helpful trading signal parser. Return ONLY a valid Python dictionary. If the message does not contain a trading signal, return an empty dictionary {}.",
        ),
        Messages(role=MessagesRole.USER, content=prompt),
    ]

    try:
        logger.debug(f"Попытка парсинга сообщения {message_id}: {text}")
        response = client.chat(Chat(messages=messages))
        content = response.choices[0].message.content

        dict_str = (
            content.split("message_parse =")[-1].strip()
            if "message_parse =" in content
            else content.strip()
        )
        dict_str = dict_str.replace("```python", "").replace("```", "").strip()

        parsed = literal_eval(dict_str)
        logger.debug(f"Сообщение {message_id} успешно распарсено: {parsed}")

        # Если сообщение не содержит сигнала, GigaChat должен вернуть пустой словарь
        if not parsed:
            logger.info(f"Сообщение {message_id} не содержит торгового сигнала: {text}")
            return

        # Проверка обязательных полей
        required_fields = [
            "coin",
            "signal_type",
            "stop_loss",
            "leverage",
            "margin_mode",
            "entry_prices",
            "take_profit_targets",
        ]
        missing_fields = [
            field
            for field in required_fields
            if field not in parsed or parsed[field] is None
        ]
        if missing_fields:
            logger.warning(
                f"Пропущено сообщение {message_id} из-за отсутствия полей {missing_fields}: {text}"
            )
            return

        # Проверка stop_loss
        if not isinstance(parsed["stop_loss"], (int, float)):
            logger.error(
                f"Некорректный формат stop_loss в сообщении {message_id}: {parsed['stop_loss']}"
            )
            return
        stop_loss_value = float(parsed["stop_loss"])  # Конвертируем в float

        # Проверка entry_prices и take_profit_targets
        if not isinstance(parsed["entry_prices"], list) or not parsed["entry_prices"]:
            logger.error(
                f"Некорректный формат entry_prices в сообщении {message_id}: {parsed['entry_prices']}"
            )
            return
        if (
            not isinstance(parsed["take_profit_targets"], list)
            or not parsed["take_profit_targets"]
        ):
            logger.error(
                f"Некорректный формат take_profit_targets в сообщении {message_id}: {parsed['take_profit_targets']}"
            )
            return

        # Конвертируем списки цен в JSON
        entry_prices_json = json.dumps(
            [float(price) for price in parsed["entry_prices"]]
        )
        take_profits_json = json.dumps(
            [float(price) for price in parsed["take_profit_targets"]]
        )

    except Exception as e:
        logger.error(f"Ошибка парсинга сообщения {message_id}: {e}")
        return

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Вставка в trading_signals с JSONB полями
                cur.execute(
                    """
                    INSERT INTO trading_signals (
                        message_id, channel_id, symbol, action,
                        stop_loss, leverage, margin_mode, signal_time,
                        entry_prices, take_profits
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        message_id,
                        channel_id,
                        parsed["coin"],
                        parsed["signal_type"],
                        stop_loss_value,
                        parsed["leverage"],
                        parsed["margin_mode"],
                        signal_time,
                        entry_prices_json,
                        take_profits_json,
                    ),
                )

                signal_id = cur.fetchone()[0]
                conn.commit()
                logger.info(
                    f"✅ Inserted signal {signal_id} for message {message_id} from channel {channel_id}"
                )

    except Exception as e:
        logger.error(
            f"Ошибка базы данных при вставке сигнала для сообщения {message_id}: {e}"
        )
