#!/bin/sh
# Датасет «объяснение кода»: одна точка входа. Подробно — README.md.
cd "$(dirname "$0")" || exit 1
cmd="$1"; [ $# -gt 0 ] && shift
case "$cmd" in
  "")      python3 tools/gpt.py menu ;;
  status)  python3 tools/coverage.py ;;
  go|new|more|paste|add) python3 tools/gpt.py "$cmd" "$@" ;;
  setup)   python3 -m pip install --user numpy pandas matplotlib seaborn plotly streamlit scikit-learn safetensors torch ;;
  persona) python3 tools/persona.py "$@" ;;
  java-prompt) python3 tools/prompt.py java_claude "$@" ;;
  claude)  python3 tools/claude_prompt.py "$@" ;;
  build)   python3 tools/merge.py && echo "Готово: $(pwd)/explain_ru_train.jsonl — его и загружайте в Kaggle" ;;
  traces)  sub="$1"; [ $# -gt 0 ] && shift
           case "$sub" in
             build) python3 ../traces/build_tasks.py "$@" ;;
             kit)   python3 ../traces/kit.py ;;
             add|status) python3 ../traces/review.py "$sub" "$@" ;;
             *) echo "./ds.sh traces build | kit | add results.zip [--yes] | status" ;;
           esac ;;
  *) cat <<'HELP'
./ds.sh                     ПРОЩЕ ВСЕГО: выбрать тему и идти по шагам
./ds.sh setup               установить всё, что нужно для проверки примеров (один раз)
./ds.sh status              сколько примеров есть и сколько не хватает по темам
./ds.sh new <категория>     промпт для НОВОГО чата ChatGPT → в буфер обмена
./ds.sh more <категория>    «ещё порцию» для того же чата → в буфер
./ds.sh paste <категория>   ответ ChatGPT из буфера → проверка запуском → в датасет
./ds.sh add <файл>          то же для сохранённого файла
./ds.sh claude [N]          промпт «добери датасет одним файлом» для чата Claude (N примеров, по умолч. 60)
./ds.sh java-prompt         промпт для Java-датасета по своим практикам (другой чат Claude) → в буфер
./ds.sh persona             режим «ворчун»: реакции с матом поверх готовых примеров
./ds.sh build               собрать explain_ru_train.jsonl для обучения
./ds.sh traces build        задачи для трасс с инструментами (algo-cli, мутации, «что выведет»)
./ds.sh traces kit          traces_kit.zip для Kaggle (loca + скрипты + задачи)
./ds.sh traces add <zip>    результаты Kaggle → просмотр спорных → ds/traces/traces.jsonl → коммит
./ds.sh traces status       сколько трасс собрано
HELP
  ;;
esac
