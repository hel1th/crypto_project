### Анализ криптовалютных сигналов из Telegram
### Порт из GitLab https://gitlab.mai.ru/antygin/crypto_project

---

## Описание  
Веб-приложение для анализа трейдинговых сигналов из Telegram-каналов. Пользователи могут выбрать канал и сигнал, после чего получат график изменения цены криптовалюты с отметками точек Stop Loss (SL) и Take Profit (TP).  

**Пример канала**: [@USABitcoinArmy](https://t.me/USABitcoinArmy)

---

## Функционал  
1. **Выбор Telegram-канала**  
   - Выпадающий список доступных каналов (данные хранятся в PostgreSQL)  
2. **Выбор сигнала**  
   - Показ 5 последних сигналов выбранного канала  
3. **Визуализация аналитики**  
   - Интерактивный график цены (Plotly)  
   - Отметки точек входа, SL и TP  
---

## Технологии  
| Компонент        | Технология                         |
|------------------|------------------------------------|
| Бэкенд          | Python 3.10+                       |
| Веб-интерфейс   | Streamlit                          |
| База данных     | PostgreSQL                         |
| Визуализация    | Plotly, Matplotlib                 |
| AI-парсинг    | GigaChat API                       |
| Парсинг сигналов | `telethon`, `python-telegram-bot`  |

---

## Установка  
1. **Клонирование репозитория**:  
   ```bash
   git clone https://gitlab.mai.ru/antygin/crypto_project.git
   cd crypto_project
2. **Установка зависимостей**   
    ```bash
    pip install -r requirements.txt
3. **Настройка вирутального окружения**
     - cоздать файл .env по шаблону в .env.example
     - добавить свои credentials в проект

4. **Запуск приложения**
   - Запуск парсера сообщений  
    ```bash
    python.exe -B -m app.telegram.main
    ```
   - Запуск сайта  
    ```bash
    python.exe -B -m app.frontend.website
    ```  
