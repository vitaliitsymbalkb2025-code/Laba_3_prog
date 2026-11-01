# Лабораторна робота №3 — FastAPI + SQLite

**Варіант 9: облік часу опрацювання повідомлень.**
Студент: Цимбал Віталій Юрійович, група КБ-204.

## Предметна область

Сервіс обліку тривалості перевірки повідомлень про події безпеки.

| Поле | Значення |
|------|----------|
| `categories.name` | Джерело повідомлення: `siem`, `helpdesk`, `monitoring` |
| `records.code` | Унікальний код вимірювання, формат `V09-NN` |
| `records.title` | Назва: `Вимірювання опрацювання NN` |
| `records.value` | Тривалість опрацювання, **хвилини** (`minutes`), скінченне `float >= 0` |
| `records.status` | Стан перевірки вимірювання: `new`, `in_progress`, `done` |

Поріг реагування — **15.0 хв**. Вимірювання на рівні порогу або вище:
`GET /records?min_value=15`.

## Структура

```text
labs/lab03/
├── main.py           # FastAPI-застосунок, lifespan, /ping, /student, обробники помилок
├── database.py       # готовий код: з'єднання та виконання schema.sql
├── schema.sql        # готова схема (варіанти 7–9, хвилини)
├── repository.py     # параметризовані SQL-запити, транзакції, без залежності від FastAPI
├── schemas.py        # Pydantic-моделі запитів і відповідей
├── config.py         # одиниця вимірювання, поріг, обмеження варіанта
├── seed.py           # перевірка data/seed.json і початкове заповнення
├── routers/
│   ├── __init__.py   # перетворення помилок репозиторію на HTTP-коди
│   ├── categories.py
│   └── records.py
└── data/
    ├── seed.json     # навчальні дані варіанта 9 (у Git)
    └── lab3.sqlite3  # створюється програмою (не в Git)
```

## Встановлення

Команди виконуються з кореня репозиторію (Windows PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Створення та заповнення бази

```powershell
python -m labs.lab03.database   # лише створити таблиці
python -m labs.lab03.seed       # створити таблиці й додати 3 категорії та 8 записів
```

Повторний запуск `seed` не змінює непорожню базу. Щоб почати з нуля, видаліть
`labs/lab03/data/lab3.sqlite3`.

## Запуск API

```powershell
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Документація: <http://127.0.0.1:8000/docs>, схема: <http://127.0.0.1:8000/openapi.json>.

## Маршрути

| Метод і маршрут | Успіх | Помилки |
|-----------------|-------|---------|
| `GET /ping` | 200 | — |
| `GET /student` | 200 | — |
| `GET /categories` | 200 | — |
| `POST /categories` | 201 | 409, 422 |
| `DELETE /categories/{category_id}` | 204 | 404, 409, 422 |
| `GET /records` | 200 | 422 |
| `GET /records/{record_id}` | 200 | 404, 422 |
| `POST /records` | 201 | 404, 409, 422 |
| `PUT /records/{record_id}` | 200 | 404, 409, 422 |
| `DELETE /records/{record_id}` | 204 | 404, 422 |
| `POST /records/bulk` | 201 | 404, 409, 422 |

Параметри `GET /records`: `category_id`, `status`, `min_value`, `q`
(буквальний підрядок у `title`), `limit` (1–100, типово 20), `offset` (типово 0).

## Приклади запитів (Bash / Git Bash; у PowerShell — `curl.exe` або Swagger UI)

```bash
curl -i "http://127.0.0.1:8000/ping"
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"
curl -i "http://127.0.0.1:8000/records?min_value=15"

curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V09-TEST","title":"Вимірювання опрацювання тестове","category_id":1,"value":12.5,"status":"new"}'

# Скасування всього пакета: V09-01 уже є в базі -> 409, V09-ROLLBACK не збережено
curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V09-ROLLBACK","title":"Перший елемент","category_id":1,"value":4.0,"status":"new"},{"code":"V09-01","title":"Дублікат коду","category_id":2,"value":5.0,"status":"new"}]'
```

## Перевірка стилю

```powershell
ruff check .
ruff format --check .
```
