import gigachat
from gigachat.models import Chat, Messages, MessagesRole
from ast import literal_eval
import sys
import io
import json
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY_LLM = os.getenv('API_KEY_LLM')

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def llm_parse(dict_of_messages: dict) -> None:
    
    json_dict = {}
    
    client = gigachat.GigaChat(credentials=API_KEY_LLM, verify_ssl_certs=False)
    
    for time, text in dict_of_messages.items():    

        prompt = f"""Parse message {text}, forming a dict message_data = 'coin': str without #, 'timeframe': str, \
            'signal_type': str, 'entry_prices': list, 'take_profit_targets': list, 'stop_loss': (float, int), 'leverage': int,\
            'margin_mode': str, channel: str. Return only dict as a variable message_parse. Do not add no spare symbols\
            (brackets, emoji ect.) 
            """
            
        messages = [
            Messages(role=MessagesRole.SYSTEM, content="You are a helpful trading signal parser. Return ONLY valid Python dictionary."),
            Messages(role=MessagesRole.USER, content=prompt),
        ]
        
        try:
            response = client.chat(Chat(messages=messages))
            response_content = response.choices[0].message.content
            
            if "message_parse =" in response_content:
                dict_str = response_content.split("message_parse =")[1].strip()
            else:
                dict_str = response_content.strip()
            
            dict_str = dict_str.replace("```python", "").replace("```", "").strip()
            
            message_data = literal_eval(dict_str)
            json_dict[time] = message_data
            
        except SyntaxError:
            print(f"SyntaxError: LLM returned invalid dictionary format. Raw response: {response_content}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None
            
    with open("messages_data.json", "w", encoding='UTF-8') as json_file:
        json.dump(json_dict, json_file, ensure_ascii=True, indent=4)
        

dict_of_messages ={
    '23:15 12.05.25' : """📈 Long Signal

#UMAUSDT 30m | Mid-Term

Entry price : 

1) 1.271000
2) 1.23287

- ⏳ -  Signal details :

1) 1.278299
2) 1.304851
3) 1.331403
4) 1.357955

❌Stop-Loss : 1.190927

🧲Leverage : 10x [Isolated]

@USABitcoinArmy
___
💡After reaching the first target you can put the rest of the position to breakeven.""" ,

'23.30 12.05.25': """📉 Short Signal

#TRBUSDT 30m | Mid-Term

Entry price : 

1) 48.374
2) 49.825

- ⏳ -  Signal details :

1) 48.090
2) 47.069
3) 46.048
4) 45.027

❌Stop-Loss : 51.421

🧲Leverage : 10x [Isolated]

@USABitcoinArmy
___
💡After reaching the first target you can put the rest of the position to breakeven.""" 
}   

llm_parse(dict_of_messages)