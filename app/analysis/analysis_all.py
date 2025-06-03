import psycopg2
import json
from API_collection import fetch_crypto_data  # will have access after merge
from app.parse_llm.parse_messages import llm_parse
from analysis_llm import analysis_of_all_data
import pandas as pd


# need a query for datebase that returns a dict with key: time and value: text of message 


with psycopg2.connect(**DB_CONFIG) as conn:
    with conn.cursor() as cursor:
        data = cursor.execute("SELECT text, date FROM grfyhj")

            
llm_parse(data)

symbol_analysis = input()
time_to_find = input() 
symbol = input()



with open("messages_data.json", "r", encoding="UTF-8") as json_file:
    messages_with_time = json.load(json_file)
    

# file_name = f"{symbol}_{time_to_find}"
data_binance = fetch_crypto_data(symbol, time_to_find) # вопрос по аргументам



for time, message in messages_with_time:
    
    is_success = 'Unknown'
    entry_prices = message["entry_price"]
    profit = message["take_profit_targets"]
    stop_loss = message["stop_loss"]
    signal = message["signal_type"]
    
    filtered_data = data_binance.loc[data_binance['open_time'] > time, ['open', 'close']]
    for row in filtered_data.itertuples():
        if signal == 'Long':
            if row.close < stop_loss:
                is_success = 'fail'
                break
            if any([row.close > item for item in profit]):
                is_success = 'success'
                break
            
        if signal == 'Short':
            if row.close > stop_loss:
                is_success = 'fail'
            if any([row.close < item for item in profit]):
                is_success = 'success'
                break
    
        
    

