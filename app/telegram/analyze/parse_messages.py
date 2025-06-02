import psycopg2
from ast import literal_eval
import gigachat
from gigachat.models import Chat, Messages, MessagesRole
from datetime import datetime
from ..config import DB_CONFIG, API_KEY_LLM


def llm_parse_and_insert(message_id, channel_id, text, signal_time):
    client = gigachat.GigaChat(credentials=API_KEY_LLM, verify_ssl_certs=False)

    prompt = f"""Parse message {text}, forming a dict message_parse = 'coin': str without #, 'timeframe': str,
        'signal_type': str, 'entry_prices': list, 'take_profit_targets': list, 'stop_loss': (float, int), 'leverage': int,
        'margin_mode': str, channel: str. Return only dict as a variable message_parse. Do not add no spare symbols."""

    messages = [
        Messages(
            role=MessagesRole.SYSTEM,
            content="You are a helpful trading signal parser. Return ONLY valid Python dictionary.",
        ),
        Messages(role=MessagesRole.USER, content=prompt),
    ]

    try:
        response = client.chat(Chat(messages=messages))
        content = response.choices[0].message.content

        dict_str = (
            content.split("message_parse =")[-1].strip()
            if "message_parse =" in content
            else content.strip()
        )
        dict_str = dict_str.replace("```python", "").replace("```", "").strip()

        parsed = literal_eval(dict_str)

    except Exception as e:
        print(f"Parsing failed: {e}")

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # вставка в trading_signals
                cur.execute(
                    """
                    INSERT INTO trading_signals (
                        message_id, channel_id, symbol, action,
                        stop_loss, leverage, margin_mode, signal_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        message_id,
                        channel_id,
                        parsed["coin"],
                        parsed["signal_type"],
                        parsed["stop_loss"],
                        parsed["leverage"],
                        parsed["margin_mode"],
                        signal_time,
                    ),
                )

                signal_id = cur.fetchone()[0]

                for price in parsed.get("entry_prices", []):
                    cur.execute(
                        """
                        INSERT INTO signal_entry_prices (signal_id, price) VALUES (%s, %s)
                    """,
                        (signal_id, price),
                    )

                for price in parsed.get("take_profit_targets", []):
                    cur.execute(
                        """
                        INSERT INTO signal_take_profits (signal_id, price) VALUES (%s, %s)
                    """,
                        (signal_id, price),
                    )

                print(
                    f"✅ Inserted signal {signal_id} for message {message_id} from channel {channel_id}"
                )

    except Exception as e:
        print(f"❌ Database error: {e}")
