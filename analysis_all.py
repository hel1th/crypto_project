import psycopg2
import json
from API_collection import fetch_crypto_data  # will have access after merge
from parse_massages import llm_parse
from analysis_llm import analysis_of_all_data


# need a query for datebase that returns a dict with key: time and value: text of message 

with psycopg2.connect(**DB_CONFIG) as conn:
    with conn.cursor() as cursor:
        data = cursor.execute("SELECT text, date FROM grfyhj")

            
llm_parse(data)

symbol_analysis = input() # get data from frontend  
time_to_find = input() #get time from frontend


with open("messages_data.json", "r", encoding="UTF-8") as json_file:
    messages_with_time = json.load(json_file)
    
    
message_of_time = messages_with_time[time_to_find]
coin_data = fetch_crypto_data(symbol_analysis, time_to_find) # надо добавить определение начального куска промежутка времени 

print(analysis_of_all_data(message_of_time, coin_data))
