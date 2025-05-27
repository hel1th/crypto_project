from dotenv import load_dotenv
import gigachat
from gigachat.models import Chat, Messages, MessagesRole
import os
import sys
import io

load_dotenv()

API_KEY_LLM = os.getenv('API_KEY_LLM')



sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def analysis_of_all_data(message_of_time: str, coin_data: dict) -> str:

    prompt = f"Analyze data from the dict with predictions {message_of_time} (dictionary is collected from the message from telegram channel with trading \
    predictions) and compare them with data from DataFrame {coin_data} collected from Binance from the same time. Make conclusions about the accuracy of \
    the prediction and advice. Form your answer using five sentences"
                
    client = gigachat.GigaChat(credentials=API_KEY_LLM, verify_ssl_certs=False)
            
    messages = [
                Messages(role=MessagesRole.SYSTEM, content="You are a helpful trading signal analyzer. Return ONLY valid Python dictionary."),
                Messages(role=MessagesRole.USER, content=prompt),
            ]
    response = client.chat(Chat(messages=messages))
    response_content = response.choices[0].message.content


    return response_content #можно выводить на фронт