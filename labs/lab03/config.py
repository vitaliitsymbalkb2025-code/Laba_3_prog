"""Параметри варіанта 9: облік часу опрацювання повідомлень."""

import sys

VARIANT_NUMBER = 9
APP_TITLE = "Облік часу опрацювання повідомлень (ЛР №3, варіант 9)"
SUBJECT_AREA = (
    "Сервіс обліку тривалості перевірки повідомлень про події безпеки. "
    "Категорія визначає джерело повідомлення (siem, helpdesk, monitoring), "
    "value — тривалість опрацювання у хвилинах, status — стан перевірки "
    "вимірювання."
)

VALUE_UNIT = "minutes"
VALUE_THRESHOLD = 15.0
VALUE_MIN = 0.0
VALUE_MAX = sys.float_info.max

CATEGORY_NAMES = ("siem", "helpdesk", "monitoring")
RECORD_TITLE = "Вимірювання опрацювання"
STATUSES = ("new", "in_progress", "done")

SQLITE_INT_MAX = 2**63 - 1

BULK_MIN_ITEMS = 1
BULK_MAX_ITEMS = 100
PAGE_DEFAULT_LIMIT = 20
PAGE_MAX_LIMIT = 100
