"""Отложенный контрольный набор. НЕ использовать эти фрагменты (и их почти-копии) в обучающих примерах."""

EVAL = [
    dict(id="e01", lang="python", question="Объясни, что делает этот код и почему он работает:",
         code="def f(xs):\n    seen = set()\n    return [x for x in xs if not (x in seen or seen.add(x))]"),
    dict(id="e02", lang="python", question="Почему этот код ведёт себя неожиданно при повторных вызовах?",
         code="def add(item, items=[]):\n    items.append(item)\n    return items"),
    dict(id="e03", lang="python", question="Объясни, что выведет код и почему:",
         code="funcs = [lambda: i for i in range(3)]\nprint([f() for f in funcs])"),
    dict(id="e04", lang="python", question="Объясни простыми словами, как работает этот декоратор:",
         code="import functools\ndef cache(fn):\n    memo = {}\n    @functools.wraps(fn)\n    def wrapper(*args):\n        if args not in memo:\n            memo[args] = fn(*args)\n        return memo[args]\n    return wrapper"),
    dict(id="e05", lang="python", question="Что выведет этот код? Объясни.",
         code="grid = [[0] * 3] * 3\ngrid[0][0] = 1\nprint(grid)"),
    dict(id="e06", lang="python", question="Почему тут ошибка, ведь x объявлен выше?",
         code="x = 10\ndef show():\n    print(x)\n    x = 5\nshow()"),
    dict(id="e07", lang="python", question="Почему второй print выводит 0?",
         code="squares = (n * n for n in range(4))\nprint(sum(squares))\nprint(sum(squares))"),
    dict(id="e08", lang="python", question="Почему результат False? Как правильно сравнивать?",
         code="print(0.1 + 0.2 == 0.3)"),
    dict(id="e09", lang="javascript", question="Что выведет этот код и почему? Как исправить?",
         code="for (var i = 0; i < 3; i++) {\n  setTimeout(() => console.log(i), 0);\n}"),
    dict(id="e10", lang="sql", question="Почему этот запрос ничего не возвращает, хотя клиенты без заказов есть?",
         code="CREATE TABLE clients(id INTEGER, name TEXT);\nCREATE TABLE orders(id INTEGER, client_id INTEGER);\nINSERT INTO clients VALUES (1,'Аня'),(2,'Боря'),(3,'Вика');\nINSERT INTO orders VALUES (10,1),(11,NULL);\nSELECT name FROM clients WHERE id NOT IN (SELECT client_id FROM orders);"),
    dict(id="e11", lang="python", question="Объясни, как работает эта функция и какая у неё сложность:",
         code="def find(arr, target):\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        if arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1"),
    dict(id="e12", lang="python", question="Объясни, как устроена и как работает эта программа целиком:",
         code=(
             "import json\n\n"
             "class Library:\n"
             "    def __init__(self, path):\n"
             "        self.path = path\n"
             "        self.books = self._load()\n\n"
             "    def _load(self):\n"
             "        try:\n"
             "            with open(self.path, encoding='utf-8') as f:\n"
             "                return json.load(f)\n"
             "        except FileNotFoundError:\n"
             "            return {}\n\n"
             "    def _save(self):\n"
             "        with open(self.path, 'w', encoding='utf-8') as f:\n"
             "            json.dump(self.books, f, ensure_ascii=False, indent=2)\n\n"
             "    def add(self, isbn, title):\n"
             "        self.books[isbn] = {'title': title, 'taken_by': None}\n"
             "        self._save()\n\n"
             "    def take(self, isbn, reader):\n"
             "        book = self.books.get(isbn)\n"
             "        if book is None or book['taken_by']:\n"
             "            return False\n"
             "        book['taken_by'] = reader\n"
             "        self._save()\n"
             "        return True\n\n"
             "    def give_back(self, isbn):\n"
             "        self.books[isbn]['taken_by'] = None\n"
             "        self._save()\n\n"
             "lib = Library('books.json')\n"
             "lib.add('111', 'Мастер и Маргарита')\n"
             "print(lib.take('111', 'Петя'), lib.take('111', 'Маша'))\n"
         )),
    dict(id="e13", lang="python", question="Почему выручка после merge получилась больше реальной? Объясни и исправь.",
         code=(
             "import pandas as pd\n"
             "orders = pd.DataFrame({'order_id': [1, 2, 3], 'client': ['A', 'B', 'A'], 'amount': [100, 250, 80]})\n"
             "contacts = pd.DataFrame({'client': ['A', 'A', 'B'], 'phone': ['111', '222', '333']})\n"
             "df = orders.merge(contacts, on='client')\n"
             "print(df['amount'].sum())"
         )),
    dict(id="e14", lang="none", question=(
             "Сделай дашборд на Streamlit для продаж интернет-магазина. Данные в sales.csv: date, region, category, "
             "revenue, orders. Нужны фильтры по региону и периоду, KPI (выручка, заказы, средний чек), график выручки "
             "по месяцам и топ-5 категорий. Объясни, как он устроен."), code=""),
    dict(id="e15", lang="none", question=(
             "Напиши SQL-запрос: выручка по месяцам и рост в процентах к прошлому месяцу. Таблица "
             "orders(id, user_id, created_at TEXT 'YYYY-MM-DD', amount). Объясни, как он работает."), code=""),
    dict(id="e16", lang="python", question="Почему модель почти не учится, хотя loss считается без ошибок?",
         code=(
             "import torch\nimport torch.nn as nn\n\n"
             "torch.manual_seed(0)\n"
             "model = nn.Sequential(nn.Linear(4, 3), nn.Softmax(dim=1))\n"
             "loss_fn = nn.CrossEntropyLoss()\n"
             "x = torch.randn(8, 4)\ny = torch.randint(0, 3, (8,))\n"
             "opt = torch.optim.SGD(model.parameters(), lr=0.5)\n"
             "for step in range(3):\n"
             "    loss = loss_fn(model(x), y)\n"
             "    loss.backward()\n"
             "    opt.step()\n"
             "    print(round(loss.item(), 4))"
         )),
    dict(id="e17", lang="none", question=(
             "Объясни простыми словами, что делает model.eval() и torch.no_grad() и почему на валидации "
             "нужны оба. Что будет, если забыть одно из них?"), code=""),
    dict(id="e18", lang="none", question=(
             "Я дообучил модель LoRA и смёрджил адаптер. Как понять, какие слои изменились сильнее всего? "
             "Напиши код, который сравнивает два state_dict (до и после) и выводит слои по убыванию изменения, "
             "и объясни, какие метрики тут осмысленны."), code=""),
]


# Ключевые факты для автопроверки ответов (tools/score_eval.py).
# must — все регексы должны найтись; must_not — ни один (типичная ошибка модели).
# Правильные значения проверены запуском кода.
CHECKS = {
    "e01": dict(must=[r"порядок"], must_not=[r"O\(n²\)", r"O\(n\^2\)"]),
    "e02": dict(must=[r"\[1, 2\]", r"(один раз|при определении)"]),
    "e03": dict(must=[r"(\[2, 2, 2\]|равн\w* 2\b)"], must_not=[r"\[3, 3, 3\]"]),
    "e04": dict(must=[r"(memo|кэш)", r"wraps"]),
    "e05": dict(must=[r"\[\[1, 0, 0\], \[1, 0, 0\], \[1, 0, 0\]\]"]),
    "e06": dict(must=[r"UnboundLocalError"]),
    "e07": dict(must=[r"\b14\b"], must_not=[r"`6`", r"выводит 6", r"печатает 6"]),
    "e08": dict(must=[r"False", r"(isclose|погрешн|epsilon|эпсилон)"]),
    "e09": dict(must=[r"3\D{1,6}3\D{1,6}3|три раза", r"\blet\b"]),
    "e10": dict(must=[r"(пуст|ничего не (вернёт|возвращает|выв)|ни одной строки|0 строк)",
                      r"(NOT EXISTS|IS NOT NULL)"],
                must_not=[r"только `?Аня"]),
    "e11": dict(must=[r"O\(log ?n\)", r"отсортир"]),
    "e12": dict(must=[r"True\W{1,4}False"]),
    "e13": dict(must=[r"\b610\b", r"\b430\b"]),
    "e14": dict(must=[r"sidebar", r"metric", r"cache_data"]),
    "e15": dict(must=[r"(strftime|substr)", r"\bLAG\b"],
                must_not=[r"DATE_TRUNC", r"::date", r"GROUP BY created_at\s*\n"]),
    "e16": dict(must=[r"[Ss]oftmax", r"(логит|logits)", r"zero_grad"]),
    "e17": dict(must=[r"[Dd]ropout", r"(BatchNorm|батч-?норм)", r"градиент"]),
    "e18": dict(must=[r"state_dict", r"(norm|норм)"]),
}
