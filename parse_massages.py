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

def llm_parse(list_of_texts: list) -> None:
    
    json_list = []
    
    client = gigachat.GigaChat(credentials=API_KEY_LLM, verify_ssl_certs=False)
    
    for text in list_of_texts:     
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
            json_list.append(message_data)
            
        except SyntaxError:
            print(f"SyntaxError: LLM returned invalid dictionary format. Raw response: {response_content}")
            return None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return None
            
    with open("message_data.json", "w", encoding='UTF-8') as json_file:
        json.dump(json_list, json_file, ensure_ascii=True, indent=4)
            

list_of_texts = ["""📈 Long Signal

#HUMAUSDT 30m | Mid-Term

Entry price : 

1) 0.0730310
2) 0.0708400

- ⏳ -  Signal details :

1) 0.0734504
2) 0.0749760
3) 0.0765017
4) 0.0780274

❌Stop-Loss : 0.0684300

🧲Leverage : 10x [Isolated]

@USABitcoinArmy
___
💡After reaching the first target you can put the rest of the position to breakeven.""", """📈 Long Signal

#CETUSUSDT 30m | Mid-Term

Entry price : 

1) 0.1261300
2) 0.1223461

- ⏳ -  Signal details :

1) 0.1268543
2) 0.1294892
3) 0.1321242
4) 0.1347592

❌Stop-Loss : 0.1181838

🧲Leverage : 10x [Isolated]

@USABitcoinArmy
___
💡After reaching the first target you can put the rest of the position to breakeven.""", """📉 Short Signal

#RAREUSDT 30m | Mid-Term

Entry price : 

1) 0.0651800
2) 0.0671354

- ⏳ -  Signal details :

1) 0.0647982
2) 0.0634223
3) 0.0620464
4) 0.0606705

❌Stop-Loss : 0.0692863

🧲Leverage : 10x [Isolated]

@USABitcoinArmy
___
💡After reaching the first target you can put the rest of the position to breakeven."""]

llm_parse(list_of_texts)