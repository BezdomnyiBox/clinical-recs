# Клинические рекомендации из научных статей (каркас)

Путь данных: PDF → страницы → карточки доказательств → тезисы по разделам → редактор → JSON / текст / Word.

## Запуск
    cp .env.example .env      # впишите OPENROUTER_API_KEY и смените пароли
    docker compose up --build
Интерфейс: http://localhost:5173, API и документация: http://localhost:8000/docs

## Структура
- `backend/app/models.py` - модель данных (auto_data / user_edits / pending_version защищают правки пользователя)
- `backend/app/pipeline/` - граф LangGraph: ingest → extract → verify → dedupe → assign_sections → finalize
- `backend/app/worker.py` - фоновая обработка задач из таблицы `jobs`
- `backend/app/api/` - REST API (проекты, документы, карточки, тезисы, экспорт)
- `frontend/src/features/` - вкладки проекта: документы, карточки, тезисы, отчёт

## Что ещё не сделано (TODO в коде)
1. `pipeline.extract`: извлечение карточек LLM (сейчас намеренно падает с понятной ошибкой)
2. Проверка смысла и отрицаний, дедупликация, противоречия, разделы, УДД/УУР, критерии качества
3. Повторная обработка с сохранением правок (сопоставление по `content_hash`, `pending_version`)
4. Выгрузка текста и Word, схема JSON по выданному описанию
5. Просмотрщик PDF рядом с карточкой (пока ссылка на страницу), редактирование текста карточки
6. Модуль оценки Precision/Recall/F1, Alembic, справочник МКБ-10
