<p align="center"><img src="assets/brand/banner.png" alt="local-code-tutor — Lo" width="100%"></p>

# Local Code Tutor — локальный 7B-наставник по коду, который не угадывает, а проверяет

[English](README.md)

<!-- EN: see README.md -->
**EN (short):** a local code tutor on a MacBook Air M2 / 8 GB. Qwen2.5-Coder-7B fine-tuned with QLoRA
on a free Kaggle T4 to explain code in Russian. Every training example is **verified by actually
running its code**: if the answer's output disagrees with the real one, the example is dropped.
The agent [loca](https://github.com/pnnnx/loca) runs the code before the model answers
"what will this print?", and asks clarifying questions instead of guessing. All claims below are measured.
`wtools/` adds weight analysis with charts (layer stats, checkpoint diff, LoRA spectrum, quantization error)
as MCP tools for the agent.

---

Студенческий проект: своя модель-помощник по коду, которая работает на ноутбуке и объясняет
по-русски — механизм, «почему так», подвохи, аналитику (pandas, SQL, дашборды) и веса нейросетей.

<table align="center">
<tr>
<td align="center" width="20%"><img src="assets/brand/lo_teach.png" width="110" alt=""><br><b>объясняет</b><br><sub>механизм, «почему», подвох</sub></td>
<td align="center" width="20%"><img src="assets/brand/lo_think.png" width="110" alt=""><br><b>думает вслух</b><br><sub>мысли видно сразу</sub></td>
<td align="center" width="20%"><img src="assets/brand/lo_grumpy.png" width="110" alt=""><br><b>ворчун</b><br><sub>только если включить</sub></td>
<td align="center" width="20%"><img src="assets/brand/lo_weights.png" width="110" alt=""><br><b>смотрит в веса</b><br><sub>графики LoRA</sub></td>
<td align="center" width="20%"><img src="assets/brand/lo_olymp.png" width="110" alt=""><br><b>олимпиады</b><br><sub>скоро</sub></td>
</tr>
</table>

Талисман проекта — Lo, маленький терминал в академической шапочке: наставник, который живёт у тебя на ноутбуке.

## Цель проекта

**Дать каждому студенту бесплатного и приватного наставника по коду, который работает на его
ноутбуке и никогда не утверждает о коде того, что не проверил.**

- **Объяснять, а не пересказывать:** механизм языка, «почему так» по шагам, подвох, исправление —
  на языке студента.
- **Проверять, а не угадывать:** вывод, ошибки и «готово ли» берутся из запуска кода.
- **Не только фрагменты:** программы целиком («как устроена система»), аналитика (pandas, SQL,
  дашборды) и разбор весов нейросетей с графиками.
- **Повторяемо за $0:** бесплатный GPU для обучения, локальный запуск, все решения и замеры записаны.

<img src="assets/brand/cards/goal_ru.png" alt="Критерии v1.0: факты 13/18 (цель 15/18); спрашивает, а не угадывает 4/4; вывод по запуску 2/2; большие задачи — замеряем; 1 581 из 2 000 примеров; офлайн на Mac 8 ГБ" width="100%">

<img src="assets/brand/cards/metrics_ru.png" alt="1 581 проверенный пример; факты 8 → 13 из 18; спрашивает 1/4 → 4/4; ответ по запуску 0/1 → 2/2; стоимость 0 ₽" width="100%">
Не цель: соревноваться с облачными моделями на больших рефакторингах и быть чат-ботом общего назначения.

## Главная идея

Маленькая модель (7B) не может выполнить код «в уме», поэтому в этом проекте модель вывод
не угадывает. Это касается всех трёх частей:

<img src="assets/brand/cards/rule_ru.png" alt="Модель не угадывает, что делает код, — его всегда кто-то запускает: в данных, в агенте и в проверке" width="100%">

<details><summary>Текстом</summary>

| Где | Как |
|---|---|
| **Данные** | каждый пример реально запускается (Python, JS, C/C++, Java, SQLite); ответ, не совпавший с настоящим выводом, отбрасывается; дубли ищутся по «скелету» кода (имена → ID) |
| **Агент** | на «что выведет / почему падает» loca сама показывает модели исходник и запускает код **до** её ответа |
| **Проверка** | 18 отложенных вопросов, которых нет в обучении, + автопроверка ключевых фактов |

</details>

<img src="assets/brand/cards/pipeline_ru.png" alt="Конвейер: LLM пишет примеры → запуск кода → дедуп → QLoRA на Kaggle T4 → GGUF → агент loca на Mac 8 ГБ; wtools подключены по MCP" width="100%">

<details><summary>Исходник схемы (Mermaid)</summary>

```mermaid
flowchart LR
  A[ChatGPT / Claude<br/>пишут примеры] --> B[ds: запуск кода,<br/>сверка вывода, дедуп]
  B --> C[датасет<br/>~900 примеров]
  C --> D[Kaggle T4:<br/>QLoRA, Unsloth]
  D --> E[GGUF Q4_K_M<br/>4,4 ГБ]
  E --> F[llama.cpp / Ollama<br/>на Mac 8 ГБ]
  F --> G[агент loca]
  H[wtools: веса<br/>и графики] -- MCP --> G
```

</details>

## Результаты (честно, включая то, что не получилось)

### Агент на настоящей 7B: узкие места маленькой модели

![до и после](assets/bottlenecks_7b.png)

- **№8 «додумывает вместо того, чтобы спросить».** На размытых просьбах («добавь промокоды») 7B
  придумывала цель. Задание перед работой + проверка задания в коде (пути сверяются с диском,
  размытая просьба без вопросов получает вопрос): **1/4 → 4/4**.
- **№4 «не может выполнить код в уме».** Напоминание «сначала запусти» модель **игнорировала** — на
  вопрос про файл ответила «файла не существует», не вызвав ни одного инструмента. Теперь агент
  запускает код сам (опасный — не запускает): **0/1 → 2/2**, объяснение по настоящим строкам исходника.

Прогоны: Qwen2.5-Coder-7B-Instruct Q4_K_M, llama-server, `bench/probe.py` в репозитории loca.

### Дообучение: v2 выучила форму, v3 начала попадать в факты

![контрольные вопросы](assets/eval_v3_en.png)

Автопроверка ключевых фактов на 18 отложенных вопросах: база с промптом — 8/18, v2 — 9/15, **v3 — 13/18**.
v2 отвечала как задумано, но уверенно выдумывала вывод (`[3, 3, 3]` вместо `[2, 2, 2]`). v3 (954 примера: pandas,
SQLite, PyTorch, веса) исправила позднее связывание, SQL на `STRFTIME` + `LAG` и вопросы по PyTorch. Считать в уме
всё ещё не умеет (e07, e13) — поэтому агент запускает код, а не верит модели. Сейчас учится **v4 на 1 581 примере**.
Подробности — [docs/RESULTS.md](docs/RESULTS.md).

### Анализ весов с графиками (`wtools`)

<img src="assets/brand/cards/wtools_ru.png" alt="Команды wtools: inspect, stats, diff, lora, quant" width="100%">

<details><summary>Текстом</summary>

| команда | что показывает |
|---|---|
| `inspect` | тензоры, формы, память fp32 / fp16 / int8 / int4 |
| `stats` | масштаб весов по слоям, выбросы > 6σ, «мёртвые» нейроны |
| `diff` | что изменилось после дообучения: ‖ΔW‖/‖W‖, косинус по слоям |
| `lora` | ΔW = B·A·α/r: норма по модулям, эффективный ранг, спектр (через QR — быстро и для 7B) |
| `quant` | ошибка int8/int4: масштаб на тензор / строку / блок 32 (как в GGUF) |

</details>

<p><img src="assets/wtools_demo_diff.png" width="49%"> <img src="assets/wtools_demo_lora.png" width="49%"></p>

*Графики на игрушечной модели из тестов.* Модель в loca картинки не видит, поэтому все числа с графика
дублируются в тексте — она объясняет их по числам.

## Дорожная карта

<img src="assets/brand/cards/roadmap_ru.png" alt="Дорожная карта: v0.1–v0.3 готово; v0.4 в работе (1 581 пример, модель v4, ворчун, write_tests, Lo); v0.5 дальше (/olymp); v0.6 в планах" width="100%">

## Что внутри

| Путь | Что это |
|---|---|
| `ds/` | сбор датасета: `./ds.sh` (ChatGPT/Claude через буфер обмена → запуск → проверки → git) |
| `ds/tools/runner.py`, `build.py`, `dedup.py` | запуск кода, проверки ответа, дубли по «скелету» |
| `ds/eval_set.py`, `ds/tools/score_eval.py` | отложенные вопросы и автопроверка фактов |
| `kaggle_qwen_coder_finetune_v2.ipynb` | обучение QLoRA на Kaggle → LoRA + GGUF + проверка |
| `loca_bench_kaggle_v2.ipynb` | бенчмарк агента и пробник узких мест на GPU |
| `wtools/` | анализ весов: CLI + MCP-сервер для loca |
| `docs/` | план, решения, узкие места, результаты, журнал каждого шага |

Сам датасет не публикуется: примеры сгенерированы ChatGPT и Claude, и условия их использования
для обучения моделей — серая зона. Опубликованы конвейер, проверки и результаты.

## Запуск

```bash
pip install torch safetensors matplotlib numpy pandas   # для проверки примеров и wtools
cd ds && ./ds.sh                                        # сбор: выбрать тему и идти по шагам
python3 wtools/weights.py lora path/to/lora_adapter     # разбор адаптера с графиками
python3 -m pytest -q wtools/test_weights.py
```

## Как сделано

<img src="assets/brand/cards/steps_ru.png" alt="Как собирается датасет: промпт → запуск → отбор → коммит" width="100%">

<img src="assets/brand/cards/lessons_ru.png" alt="Выводы: 7B игнорирует напоминания; стиль раньше фактов; проверять запуском; мерить на настоящей модели" width="100%">


Код писался вместе с ИИ-ассистентом (Claude) — это видно в коммитах. Решения, замеры и разбор
результатов — в `docs/`: [план](docs/PLAN.md), [решения](docs/DECISIONS.md),
[узкие места](docs/BOTTLENECKS.md), [журнал](docs/JOURNAL.md).

Лицензия — MIT. Базовая модель Qwen2.5-Coder-7B — Apache 2.0.
