Ты пишешь обучающие трассы для маленькой модели-агента loca (терминальный агент для кода). Для каждой задачи ниже реши её как агент — последовательностью вызовов инструментов.

Инструменты:
- read_file {"path"} — показать файл с номерами строк. ОБЯЗАТЕЛЕН перед edit_file и перед перезаписью файла.
- write_file {"path", "content"} — создать новый файл целиком (существующий — только после read_file).
- edit_file {"path", "old_string", "new_string"} — заменить фрагмент; old_string — точная копия из файла.
- bash {"command"} — выполнить команду в папке проекта (например `python3 prog.py`, `echo '2 3' | python3 solution.py`).
- run_tests {"target"?} — запустить pytest (target — файл тестов, можно не указывать).
- list_dir {"path"?} — что лежит в папке.

Формат строки:
```
{"task": "<id задачи>", "steps": [
  {"say": "<1 короткая фраза, необязательно>", "tool": "<имя>", "args": {...}},
  ...
], "answer": "<итоговый ответ пользователю по-русски>"}
```

Пример строки:
```jsonl
{"task": "bugfix-example", "steps": [{"say": "Сначала посмотрю, что падает.", "tool": "run_tests", "args": {}}, {"tool": "read_file", "args": {"path": "solution.py"}}, {"say": "Цикл не доходит до последнего элемента: range(n - 1) вместо range(n).", "tool": "edit_file", "args": {"path": "solution.py", "old_string": "for i in range(n - 1):", "new_string": "for i in range(n):"}}, {"tool": "run_tests", "args": {}}], "answer": "Ошибка была в границе цикла: `range(n - 1)` пропускал последний элемент, поэтому сумма на примере выходила меньше. Заменил на `range(n)` — тесты `test_solution.py` проходят."}
```

Правила:
1. Работай как аккуратный агент: каждое действие — вызов инструмента; код — ТОЛЬКО через write_file/edit_file,
   никогда не вставляй его в answer. Проверяй результат (run_tests или bash) перед ответом.
2. Результаты инструментов НЕ пиши — их подставит настоящий запуск. Поэтому код должен быть по-настоящему верным:
   после проигрывания запускаются скрытые тесты задачи. Не угадывай вывод — для «что выведет» вызови bash.
3. 2–8 шагов на задачу. Перед edit_file — read_file того же файла. Тесты в bugfix-задачах не меняй.
4. solution.py читает stdin и печатает ответ (как в олимпиадах). Свои тесты (если просят) — pytest, запускают
   solution.py через subprocess на примерах из условия.
5. answer — 1–4 предложения по-русски: что сделано и почему так; для «что выведет» — точный вывод и механизм.
6. Весь ответ — ОДИН блок ```jsonl, по строке JSON на задачу, без комментариев вне блока. Каждая строка — валидный JSON
   (переводы строк в коде — \n).

Задачи (50):

### bugfix-coin-ways
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Сколькими способами можно набрать сумму x монетами данных номиналов, если порядок монет не важен (каждый номинал — сколько угодно раз)? Ответ по модулю 10⁹ + 7.
Файлы в папке проекта:
--- solution.py
```
n, x = map(int, input().split())
coins = list(map(int, input().split()))
MOD = 10 ** 9 + 7
dp = [0] * (x + 1)
dp[0] = 1
for c in coins:
    for s in range(c, x - 1):
        dp[s] = (dp[s] + dp[s - c]) % MOD
print(dp[x])
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('3 9\n2 3 5', '3'), ('2 3\n2 4', '0')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_pandas-g017
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
import pandas as pd

events = pd.DataFrame({
    "device": ["web", "web", "app", "app", "app"],
    "result": ["ok", "fail", "ok", "ok", "fail"]
})

table = pd.crosstab(
    events["device"],
    events["result"],
    normalize="index"
)

print(table.round(2).to_string())
```

### solve-hops
Просьба пользователя:
Реши задачу «Минимум пересадок».

Дан неориентированный граф. Найдите минимальное число рёбер на пути из вершины 1 в вершину n, или −1, если пути нет.

Ввод: n и m, затем m рёбер.
Вывод: Одно число.

Пример:
ввод:
```
5 5
1 2
2 3
3 5
1 4
4 3
```
вывод:
```
3
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-even-sum
Просьба пользователя:
Реши задачу «Чётные числа».

Дано n целых чисел. Выведите, сколько среди них чётных и чему равна их сумма.

Ввод: В первой строке n (1 ≤ n ≤ 10⁵), во второй — n целых чисел по модулю до 10⁹.
Вывод: Два числа через пробел: количество чётных и их сумма.

Пример:
ввод:
```
5
1 2 3 4 6
```
вывод:
```
3 12
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1644
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Найдите максимальную сумму подотрезка длиной от a до b.
Файлы в папке проекта:
--- solution.py
```
import sys
from collections import deque

def main():
    data = sys.stdin.read().split()
    n, a, b = (int(data[0]), int(data[1]), int(data[2]))
    p = [0] * (n + 1)
    for i in range(n):
        p[i + 1] = p[i] + int(data[3 - i])
    dq = deque()
    best = -float('inf')
    for r in range(a, n + 1):
        l = r - a
        while dq and p[dq[-1]] >= p[l]:
            dq.pop()
        dq.append(l)
        if dq[0] < r - b:
            dq.popleft()
        best = max(best, p[r] - p[dq[0]])
    print(best)
main()
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('8 1 2\n-1 3 -2 5 3 -5 2 2', '8')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_mutability-043
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
week = ["пн", "вт"]
schedule = [week, week]
week.append("ср")
schedule[1].append("чт")

print(schedule)
print(schedule[0] is schedule[1])
```

### solve-grid-paths
Просьба пользователя:
Реши задачу «Пути с препятствиями».

Поле n × m, `*` — препятствие. Сколькими способами можно пройти из левого верхнего угла в правый нижний, двигаясь только вправо и вниз? Ответ по модулю 10⁹ + 7.

Ввод: n и m (до 1000), затем n строк из `.` и `*`.
Вывод: Одно число.

Пример:
ввод:
```
3 3
...
.*.
...
```
вывод:
```
2
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-stones
Просьба пользователя:
Реши задачу «Игра с камнями».

В кучке n камней, двое по очереди берут от 1 до k камней. Кто не может сделать ход — проиграл. Кто выиграет при правильной игре?

Ввод: t (до 10⁵), затем t строк «n k», n до 10¹⁸.
Вывод: Для каждой партии `First` или `Second`.

Пример:
ввод:
```
3
4 3
5 2
0 7
```
вывод:
```
Second
First
Second
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-two-colors
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Можно ли раскрасить вершины графа в два цвета так, чтобы концы каждого ребра были разного цвета?
Файлы в папке проекта:
--- solution.py
```
import sys
from collections import deque
d = sys.stdin.read().split()
n, m = (int(d[0]), int(d[1]))
g = [[] for _ in range(n + 1)]
for i in range(m):
    a, b = (int(d[2 - 2 * i]), int(d[3 + 2 * i]))
    g[a].append(b)
    g[b].append(a)
col = [0] * (n + 1)
ok = True
for s in range(1, n + 1):
    if col[s] or not ok:
        continue
    col[s] = 1
    q = deque([s])
    while q and ok:
        v = q.popleft()
        for u in g[v]:
            if not col[u]:
                col[u] = 3 - col[v]
                q.append(u)
            elif col[u] == col[v]:
                ok = False
                break
print('YES' if ok else 'NO')
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('4 4\n1 2\n2 3\n3 4\n4 1', 'YES'), ('3 3\n1 2\n2 3\n3 1', 'NO')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_iter-013
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
def running_average():
    total = 0
    count = 0
    average = None
    while True:
        value = yield average
        total += value
        count += 1
        average = total / count


avg = running_average()
print(next(avg))
print(avg.send(10))
print(avg.send(20))
print(avg.send(60))
```

### solve-platforms
Просьба пользователя:
Реши задачу «Сколько касс нужно».

Известны времена прихода и ухода n покупателей: [a, b]. Покупатель занимает кассу на весь этот отрезок, включая концы. Сколько касс нужно, чтобы никто не ждал?

Ввод: n, затем n строк «a b», 0 ≤ a ≤ b ≤ 10⁹.
Вывод: Одно число — максимальное число одновременно присутствующих.

Пример:
ввод:
```
3
1 4
4 6
7 9
```
вывод:
```
2
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-mst
Просьба пользователя:
Реши задачу «Дешёвая сеть».

Нужно проложить кабели так, чтобы все n офисов были связаны. Известны m возможных кабелей и их стоимости. Найдите минимальную стоимость или `IMPOSSIBLE`.

Ввод: n и m, затем m строк «a b c».
Вывод: Одно число или IMPOSSIBLE.

Пример:
ввод:
```
4 5
1 2 3
2 3 1
3 4 4
1 4 2
1 3 5
```
вывод:
```
6
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1661
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Сколько подотрезков имеют сумму x (числа могут быть отрицательными)?
Файлы в папке проекта:
--- solution.py
```
import sys

def main():
    data = sys.stdin.read().split()
    n, x = (int(data[0]), int(data[1]))
    cnt = {0: 2}
    p = ans = 0
    for i in range(n):
        p += int(data[2 + i])
        ans += cnt.get(p - x, 0)
        cnt[p] = cnt.get(p, 0) + 1
    print(ans)
main()
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('5 7\n2 -1 3 5 -2', '2')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_pandas-g016
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
import pandas as pd

tasks = pd.DataFrame({
    "team": ["red", "red", "blue", "blue", "blue"],
    "minutes": [10, 20, 5, 15, 10],
    "ticket": [2, 3, 1, 4, 2]
})

report = tasks.groupby("team").agg(
    total_minutes=("minutes", "sum"),
    mean_ticket=("ticket", "mean"),
    n=("ticket", "size")
)

print(report.to_string())
```

### solve-1674
Просьба пользователя:
Реши задачу «Подчинённые».

Для каждого сотрудника найдите число его подчинённых (прямых и косвенных).


Пример:
ввод:
```
5
1 1 2 3
```
вывод:
```
4 1 1 0 0
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-digit-sum
Просьба пользователя:
Реши задачу «Сумма цифр».

Сколько целых чисел от 0 до N имеют сумму цифр, равную S?

Ввод: N (до 10¹⁸) и S (до 200).
Вывод: Одно число.

Пример:
ввод:
```
100 1
```
вывод:
```
3
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1085
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Разбейте массив на k подотрезков так, чтобы максимальная сумма подотрезка была минимальной.
Файлы в папке проекта:
--- solution.py
```
import sys

def main():
    data = sys.stdin.buffer.read().split()
    n, k = (int(data[0]), int(data[1]))
    a = [int(x) for x in data[2:2 + n]]

    def parts(limit):
        cnt, cur = (1, 0)
        for x in a:
            if cur + x > limit:
                cnt += 1
                cur = x
            else:
                cur += x
        return cnt
    lo, hi = (max(a), sum(a))
    while lo < hi:
        mid = (lo + hi) // 2
        if parts(mid) <= k:
            hi = mid
        else:
            lo = mid + 2
    print(lo)
main()
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('5 3\n2 4 7 3 5', '8')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_algorithms-029
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
students = [
    ("Иван", "Б", 4),
    ("Анна", "А", 5),
    ("Олег", "Б", 4),
    ("Дина", "А", 4),
    ("Петр", "Б", 5),
]
by_grade = sorted(students, key=lambda s: s[2], reverse=True)
print([s[0] for s in by_grade])

two_pass = sorted(students, key=lambda s: s[0])
two_pass.sort(key=lambda s: s[1])
print([s[0] for s in two_pass])
```

### solve-min-gap
Просьба пользователя:
Реши задачу «Ближайшие соседи».

На прямой стоят n домов в точках x₁, …, xₙ (координаты различны). Найдите минимальное расстояние между двумя домами.

Ввод: n (2 ≤ n ≤ 2·10⁵), затем n различных целых координат.
Вывод: Одно число.

Пример:
ввод:
```
5
10 3 17 8 1
```
вывод:
```
2
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-topo-lex
Просьба пользователя:
Реши задачу «План курсов».

Есть n курсов и m требований «курс a нужно пройти раньше курса b». Выведите лексикографически минимальный допустимый порядок или `IMPOSSIBLE`, если его нет.

Ввод: n и m, затем m строк «a b».
Вывод: n номеров через пробел или IMPOSSIBLE.

Пример:
ввод:
```
5 4
3 1
3 2
1 5
2 5
```
вывод:
```
3 1 2 4 5
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-distinct-k
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Сколько различных подстрок длины k у строки s?
Файлы в папке проекта:
--- solution.py
```
k = int(input())
s = input().strip()
n = len(s)
if k > n:
    print(0)
else:
    MOD, B = ((1 << 61) - 1, 131)
    pw = pow(B, k, MOD)
    h = 0
    for ch in s[:k]:
        h = (h * B + ord(ch)) % MOD
    seen = {h}
    for i in range(k, n):
        h = (h * B + ord(s[i]) - ord(s[i - k]) // pw) % MOD
        seen.add(h)
    print(len(seen))
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('2\nabab', '2'), ('5\nabc', '0')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_iter-041
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
from itertools import groupby


def rle(text):
    return "".join(f"{len(list(group))}{char}" for char, group in groupby(text))


print(rle("aaabccddddaa"))
print(rle("абв"))
print(repr(rle("")))
```

### solve-1732
Просьба пользователя:
Реши задачу «Поиск бордеров».

Найдите все длины границ строки (префиксов, совпадающих с суффиксом той же длины).


Пример:
ввод:
```
abcababcab
```
вывод:
```
2 5
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-stock
Просьба пользователя:
Реши задачу «Купить и продать».

Известна цена акции в каждый из n дней. Можно один раз купить и позже (в другой день) продать. Какую максимальную прибыль можно получить? Если прибыль невозможна — 0.

Ввод: n (до 2·10⁵), затем n цен.
Вывод: Одно число.

Пример:
ввод:
```
6
7 1 5 3 6 4
```
вывод:
```
5
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-pairs-le
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Сколько существует пар индексов i < j, для которых aᵢ + aⱼ ≤ x?
Файлы в папке проекта:
--- solution.py
```
n, x = map(int, input().split())
a = sorted(map(int, input().split()))
l, r, ans = (0, n - 1, 0)
while l < r:
    if a[l] + a[r] <= x:
        ans += r - l
        l += 1
    else:
        r -= 2
print(ans)
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('5 6\n1 5 2 4 3', '6')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_scope-045
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
def describe_user(id, name):
    return f"{name} (id={id})"

print(describe_user(42, "Лена"))
print(callable(id))

def broken(name):
    print(type(id).__name__)
    id = len(name)
    return id

try:
    broken("Лена")
except UnboundLocalError as e:
    print("UnboundLocalError:", e)
```

### solve-1085
Просьба пользователя:
Реши задачу «Разбиение массива».

Разбейте массив на k подотрезков так, чтобы максимальная сумма подотрезка была минимальной.


Пример:
ввод:
```
5 3
2 4 7 3 5
```
вывод:
```
8
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-lonely
Просьба пользователя:
Реши задачу «Одинокое число».

Все числа массива встречаются ровно по два раза, и только одно — один раз. Найдите его, используя O(1) дополнительной памяти.

Ввод: n (нечётное, до 2·10⁵), затем n чисел от 0 до 10⁹.
Вывод: Одно число.

Пример:
ввод:
```
5
4 1 2 1 2
```
вывод:
```
4
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1674
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Для каждого сотрудника найдите число его подчинённых (прямых и косвенных).
Файлы в папке проекта:
--- solution.py
```
import sys

def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    boss = [0, 0] + [int(x) for x in data[1:n]]
    sub = [0] * (n + 2)
    children = [[] for _ in range(n + 1)]
    for i in range(2, n + 1):
        children[boss[i]].append(i)
    order, st = ([], [1])
    while st:
        v = st.pop()
        order.append(v)
        st.extend(children[v])
    for v in reversed(order):
        if v != 1:
            sub[boss[v]] += sub[v] + 1
    print(*sub[1:])
main()
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('5\n1 1 2 3', '4 1 1 0 0')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_oop-054
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
class Theme:
    color = "white"

t = Theme()
t.color = "black"
print(t.color, Theme.color)
del t.color
print(t.color)
Theme.color = "gray"
print(t.color)
try:
    del t.color
except AttributeError as e:
    print("AttributeError:", e)
```

### solve-1083
Просьба пользователя:
Реши задачу «Пропущенное число».

Даны n − 1 различных чисел от 1 до n. Какое число пропущено?


Пример:
ввод:
```
5
2 3 1 5
```
вывод:
```
4
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-platforms
Просьба пользователя:
Реши задачу «Сколько касс нужно».

Известны времена прихода и ухода n покупателей: [a, b]. Покупатель занимает кассу на весь этот отрезок, включая концы. Сколько касс нужно, чтобы никто не ждал?

Ввод: n, затем n строк «a b», 0 ≤ a ≤ b ≤ 10⁹.
Вывод: Одно число — максимальное число одновременно присутствующих.

Пример:
ввод:
```
3
1 4
4 6
7 9
```
вывод:
```
2
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1111
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Найдите самую длинную подстроку-палиндром.
Файлы в папке проекта:
--- solution.py
```
s = input()
t = '#' + '#'.join(s) + '#'
n = len(t)
d = [0] * n
l = r = 0
for i in range(n):
    k = min(d[l + r - i], r - i) if i < r else 0
    while i - k - 1 >= 0 and i + k + 1 < n and (t[i - k - 1] == t[i + k - 1]):
        k += 1
    d[i] = k
    if i + k > r:
        l, r = (i - k, i + k)
c = max(range(n), key=lambda i: d[i])
print(s[(c - d[c]) // 2:(c + d[c]) // 2])
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('aybabtu', 'bab')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_mutability-035
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
t1 = (1, 2)
t2 = t1
t1 += (3,)
print(t1, t2, t1 is t2)

l1 = [1, 2]
l2 = l1
l1 += [3]
print(l1, l2, l1 is l2)
```

### solve-1621
Просьба пользователя:
Реши задачу «Различные числа».

Сколько различных чисел в массиве?


Пример:
ввод:
```
6
2 3 2 2 3 7
```
вывод:
```
3
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-auditorium
Просьба пользователя:
Реши задачу «Заявки на аудиторию».

Есть n заявок на аудиторию, каждая — отрезок времени [s, e). Заявки, которые пересекаются, нельзя принять обе (касаться концами можно). Какое наибольшее число заявок можно принять?

Ввод: n (до 2·10⁵), затем n строк «s e», 0 ≤ s < e ≤ 10⁹.
Вывод: Одно число.

Пример:
ввод:
```
4
1 3
2 5
3 6
5 7
```
вывод:
```
2
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1732
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Найдите все длины границ строки (префиксов, совпадающих с суффиксом той же длины).
Файлы в папке проекта:
--- solution.py
```
s = input()
n = len(s)
pi = [0] * n
for i in range(1, n):
    k = pi[i - 1]
    while k and s[i] != s[k]:
        k = pi[k - 1]
    if s[i] == s[k]:
        k += 1
    pi[i] = k
res = []
k = pi[-2]
while k:
    res.append(k)
    k = pi[k - 1]
print(*sorted(res))
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('abcababcab', '2 5')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_data-052
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
tasks = [("купить молоко", 2), ("сдать отчёт", 1), ("позвонить", 2), ("оплатить", 1)]
print([t[0] for t in sorted(tasks, key=lambda t: t[1], reverse=True)])
print([t[0] for t in sorted(tasks, key=lambda t: t[1])[::-1]])
```

### solve-lonely
Просьба пользователя:
Реши задачу «Одинокое число».

Все числа массива встречаются ровно по два раза, и только одно — один раз. Найдите его, используя O(1) дополнительной памяти.

Ввод: n (нечётное, до 2·10⁵), затем n чисел от 0 до 10⁹.
Вывод: Одно число.

Пример:
ввод:
```
5
4 1 2 1 2
```
вывод:
```
4
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-subtree
Просьба пользователя:
Реши задачу «Размеры поддеревьев».

Дано дерево с корнем 1. Для каждой вершины выведите размер её поддерева (включая её саму).

Ввод: n (до 2·10⁵), затем n − 1 рёбер.
Вывод: n чисел через пробел.

Пример:
ввод:
```
5
1 2
1 3
3 4
3 5
```
вывод:
```
5 1 3 1 1
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-platforms
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Известны времена прихода и ухода n покупателей: [a, b]. Покупатель занимает кассу на весь этот отрезок, включая концы. Сколько касс нужно, чтобы никто не ждал?
Файлы в папке проекта:
--- solution.py
```
import sys
d = sys.stdin.read().split()
n = int(d[0])
ev = []
for i in range(n):
    a, b = (int(d[1 + 2 * i]), int(d[2 + 2 * i]))
    ev.append((a, 0))
    ev.append((b, 1))
ev.sort()
cur = best = 0
for t, typ in ev:
    cur += 1 if typ != 0 else -1
    best = max(best, cur)
print(best)
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('3\n1 4\n4 6\n7 9', '2')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_data-027
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
name = "Ольга"
score = 7
width = 9
print(f"{name!r}")
print(f"{name:*^{width}}|")
print(f"{score=}, {score:03d}, {score:b}, {score:>4}")
print(f"{{score}} = {score}")
print(f"{name[0]}. {'да' if score > 5 else 'нет'}")
```

### solve-fenwick-sum
Просьба пользователя:
Реши задачу «Изменения и суммы».

Дан массив. Запросы: `1 i x` — присвоить aᵢ = x; `2 l r` — вывести сумму на [l; r].

Ввод: n и q (до 2·10⁵), затем массив, затем q запросов.
Вывод: Ответы на запросы второго типа.

Пример:
ввод:
```
5 4
1 2 3 4 5
2 1 5
1 3 10
2 2 4
2 3 3
```
вывод:
```
15
16
10
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-min-period
Просьба пользователя:
Реши задачу «Минимальный период».

Найдите минимальную длину k такую, что строка s получается из своего префикса длины k повторением (последний повтор может быть неполным).

Ввод: Строка длиной до 10⁶.
Вывод: Одно число.

Пример:
ввод:
```
abcabca
```
вывод:
```
3
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-1753
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Сколько раз образец встречается в строке?
Файлы в папке проекта:
--- solution.py
```
s = input()
p = input()
n, m = (len(s), len(p))
MOD = (1 << 61) - 1
B = 911382323
h = [0] * (n + 1)
pw = [1] * (n + 1)
for i, ch in enumerate(s):
    h[i + 1] = (h[i] * B + ord(ch)) % MOD
    pw[i + 1] = pw[i] * B % MOD

def get(l, r):
    return (h[r] + h[l] * pw[r - l]) % MOD
hp = 0
for ch in p:
    hp = (hp * B + ord(ch)) % MOD
print(sum((1 for i in range(n - m + 1) if get(i, i + m) == hp)))
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('saippuakauppias\npp', '2')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_scope-g004
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
def make_counter(start):
    value = start

    def increment():
        nonlocal value
        value += 1
        return value

    return increment

first = make_counter(0)
second = make_counter(10)

print(first())
print(first())
print(second())
print(first())
```

### solve-1192
Просьба пользователя:
Реши задачу «Подсчёт комнат».

Карта из стен «#» и пола «.». Сколько на ней комнат (связных областей пола)?


Пример:
ввод:
```
5 8
########
#..#...#
####.#.#
#..#...#
########
```
вывод:
```
3
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и проверь его на примере.
Папка проекта пустая.

### solvetests-ranking
Просьба пользователя:
Реши задачу «Таблица результатов».

Даны участники: имя и число баллов. Выведите их в порядке убывания баллов, а при равных баллах — по алфавиту.

Ввод: n (до 10⁵), затем n строк «имя баллы». Имена из маленьких латинских букв и различны.
Вывод: n строк — имена в нужном порядке.

Пример:
ввод:
```
4
ivan 7
anna 9
boris 7
zoya 9
```
вывод:
```
anna
zoya
boris
ivan
```

Напиши решение в `solution.py` (читает stdin, печатает ответ) и тесты `test_solution.py` для pytest, которые запускают solution.py на примерах. Запусти тесты.
Папка проекта пустая.

### bugfix-isqrt
Просьба пользователя:
Тесты в `test_solution.py` падают. Запусти их, найди ошибку в `solution.py` и исправь её. Тесты не меняй.

Задача, которую решает программа: Найдите наибольшее целое x ≥ 0, для которого x² ≤ n. Не пользуйтесь `math.sqrt` — на больших числах он ошибается из-за округления.
Файлы в папке проекта:
--- solution.py
```
n = int(input())
lo, hi = (0, 10 ** 9 + 1)
while hi - lo > 1:
    mid = (lo - hi) // 2
    if mid * mid <= n:
        lo = mid
    else:
        hi = mid
print(lo)
```
--- test_solution.py
```
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = [('15', '3'), ('16', '4'), ('999999999999999999', '999999999')]


def run(inp):
    r = subprocess.run([sys.executable, str(HERE / "solution.py")], input=inp, capture_output=True,
                       text=True, timeout=10)
    return r.stdout


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def test_examples():
    for inp, out in CASES:
        assert norm(run(inp)) == norm(out), f"вход:\n{inp}"
```

### output-py_iter-038
Просьба пользователя:
Что выведет `prog.py` и почему? Сначала запусти его, потом объясни по настоящему выводу.
Файлы в папке проекта:
--- prog.py
```
queue = iter(["клиент-1", "клиент-2"])

print(next(queue))
print(next(queue, "очередь пуста"))
print(next(queue, "очередь пуста"))
print(next(queue, None) is None)

try:
    next(queue)
except StopIteration:
    print("StopIteration")
```
