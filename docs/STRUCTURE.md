# Структура проекта

Сервис собирает черновик клинической рекомендации (КР) из научных статей. Путь данных:

1. Пользователь создаёт проект (тема, возраст, коды МКБ-10) и загружает PDF. `api/documents.py` сохраняет файл, считает хеш (точный дубликат не обрабатывается) и ставит задачу в таблицу `jobs`.
2. `worker.py` берёт задачу и запускает граф `pipeline/graph.py`:
   `ingest` → `relevance` → `extract` → `verify` → `dedupe` → `assign_sections` → `finalize`.
   Готовы: ingest, relevance, extract, verify (цитата и числа), finalize. Заглушки: dedupe, assign_sections.
3. Карточки доказательств и тезисы появляются в интерфейсе. Эксперт подтверждает и отклоняет, правит, добавляет экспертные тезисы.
4. Экспорт строго по схеме `backend/app/spec/kr_recommendation.schema.json`, проверка по схеме и отчёт о ресурсах.

## Дерево и назначение файлов

### Корень
| Файл | За что отвечает |
|---|---|
| `docker-compose.yml` | Пять сервисов: `mysql`, `backend` (FastAPI), `worker` (фоновая обработка PDF, тот же образ), `frontend` (Vite), `adminer` (просмотр базы на порту 8080, только с localhost). Тома для базы и загруженных PDF |
| `.env.example` | Шаблон переменных окружения: пароли MySQL, строка подключения, ключ и модель OpenRouter, каталог загрузок. Копируется в `.env` |
| `.gitignore` | Исключает `.env`, `__pycache__`, `node_modules` |
| `README.md` | Запуск, краткая структура, что сделано и что нет |
| `docs/STRUCTURE.md` | Этот файл |
| `scripts/git_commits.sh` | Делает по одному коммиту на файл, изменённый с первого архива |

### backend/
| Файл | За что отвечает |
|---|---|
| `Dockerfile` | Образ Python 3.12 с зависимостями; используется и для API, и для воркера |
| `requirements.txt` | Зависимости: FastAPI, SQLAlchemy, PyMuPDF, LangChain, LangGraph, jsonschema и др. |
| `app/config.py` | Настройки из переменных окружения (строка БД, ключ и модель OpenRouter, каталог загрузок) |
| `app/db.py` | Подключение к MySQL, фабрика сессий, `init_db` (создание таблиц), `to_dict` для ответов API |
| `app/models.py` | Все таблицы и словарь `SECTIONS` (18 разделов приказа 103н с официальными названиями) |
| `app/main.py` | Создаёт приложение FastAPI, подключает роутеры, отдаёт `/health` |
| `app/worker.py` | Бесконечный цикл: берёт задачи `queued` из `jobs`, запускает граф, записывает успех или ошибку и статус документа |

**backend/app/api/** (REST)
| Файл | За что отвечает |
|---|---|
| `projects.py` | Создание и чтение проектов; возрастная группа: `adults`, `children`, `mixed` |
| `documents.py` | Загрузка PDF, поиск дубликатов по хешу, список документов, страницы и покрытие, выдача PDF, повторная обработка (`?force=true` запускает нерелевантный источник) |
| `review.py` | Карточки и тезисы: чтение, правка с записью в журнал, экспертные тезисы, автопроверка тезиса, противоречия |
| `export.py` | Выгрузка по схеме (`/export/json`), проверка по схеме (`/export/validate`), расширенная выгрузка (`/export/full`), отчёт о покрытии и ресурсах (`/report`). Текст и Word отдают 501 |
| `glossary.py` | Отдаёт глоссарий из `spec/glossary.json` |

**backend/app/pipeline/** (обработка документа)
| Файл | За что отвечает |
|---|---|
| `graph.py` | Граф LangGraph: порядок шагов, ветвление (нерелевантный источник пропускает извлечение), итоговый статус документа |
| `ingest.py` | Текст по страницам (PyMuPDF), проверка наличия текстового слоя |
| `extract.py` | Узлы `relevance` (библиография, дизайн источника, релевантность теме) и `extract` (нарезка на фрагменты, вызов модели, сохранение карточек, исправление страницы цитаты, защита правок при повторном запуске) |
| `verify.py` | Детерминированные проверки: нормализация текста, поиск дословной цитаты на странице, сверка чисел, хеш карточки |
| `grading.py` | Правила УДД/УУР по приказу 103н: дизайн → УДД по двум шкалам, лучший УДД, формулировка по УУР, проверка тезиса (раздел, фраза, ссылки, УУР при УДД 4–5) |
| `llm.py` | Клиент OpenRouter через LangChain; запись каждого вызова (токены, стоимость, время) в `llm_calls` |

**backend/app/spec/** (данные и схемы)
| Файл | За что отвечает |
|---|---|
| `kr_recommendation.schema.json` | Основная двухуровневая схема: `evidence_units` и `recommendation_theses`. Доработана: в доказательстве обязательны `quote`, `page`, `document_id` |
| `kr_flat.schema.json` | Плоская схема знаний, вариант упрощённого экспорта |
| `glossary.json` | Глоссарий: 96 терминов в пяти разделах |

**backend/tests/**
| Файл | За что отвечает |
|---|---|
| `__init__.py` | Делает каталог пакетом |
| `test_extract_offline.py` | Прогон relevance → extract → verify на подменённой модели без обращения к OpenRouter. Проверяет поиск цитат, исправление страницы, УДД и сохранение правок |

### frontend/
| Файл | За что отвечает |
|---|---|
| `Dockerfile`, `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html` | Сборка и запуск Vite; алиас `@` на `src`; прокси `/api` на бэкенд |
| `components.json` | Настройки shadcn/ui для команды `npx shadcn add` |
| `src/main.tsx` | Точка входа: React Query и роутер |
| `src/App.tsx` | Шапка и маршруты (`/`, `/projects/:id`, `/glossary`) |
| `src/index.css` | Тема Tailwind и общий стиль (ваш вариант в стиле Яндекса) |
| `src/lib/utils.ts` | Функция `cn` для объединения классов |
| `src/lib/labels.ts` | Разделы КР, разделы для тезисов (2–5), подписи статусов документов, цитат и проверки |
| `src/lib/api.ts` | Типы данных и вызовы API |
| `src/components/ui/` | `button`, `badge`, `card` в стиле shadcn |
| `src/pages/ProjectsPage.tsx` | Список проектов и форма создания |
| `src/pages/ProjectPage.tsx` | Страница проекта с вкладками |
| `src/pages/GlossaryPage.tsx` | Глоссарий с поиском и фильтром по разделу |
| `src/features/DocumentsTab.tsx` | Загрузка PDF, статусы документов, повторная обработка |
| `src/features/CardsTab.tsx` | Карточки: цитата, ссылка на страницу PDF, статус проверки, подтвердить или отклонить |
| `src/features/ThesesTab.tsx` | Тезисы по разделам 2–5, пометка «Недостаточно материалов», добавление экспертного тезиса |
| `src/features/ReportTab.tsx` | Ресурсы (токены, стоимость, время), покрытие страниц, ссылки на выгрузку и проверку по схеме |

## API
| Метод и путь | Назначение |
|---|---|
| `GET, POST /api/projects`, `GET /api/projects/{id}` | Проекты |
| `GET, POST /api/projects/{id}/documents` | Список и загрузка PDF |
| `GET /api/documents/{id}/pages`, `/file` | Страницы со статусами; сам PDF |
| `POST /api/documents/{id}/reprocess[?force=true]` | Повторная обработка |
| `GET /api/projects/{id}/cards`, `PATCH /api/cards/{id}` | Карточки |
| `GET, POST /api/projects/{id}/theses`, `PATCH /api/theses/{id}` | Тезисы |
| `GET /api/projects/{id}/conflicts` | Противоречия |
| `GET /api/projects/{id}/export/json`, `/validate`, `/full`, `/report` | Выгрузка, проверка по схеме, расширенная выгрузка, отчёт |
| `GET /api/glossary`, `GET /health` | Глоссарий; проверка работоспособности |

## Таблицы БД
`projects`, `documents`, `pages` (текст страниц для проверки цитат), `evidence_cards`, `theses`, `thesis_cards` (связь тезисов и карточек), `conflicts`, `quality_criteria` (пока не используется: критерии лежат в поле `quality_criterion` тезиса), `expert_edits` (журнал правок), `jobs` (очередь), `llm_calls` (учёт токенов и стоимости).

## Статусы документа
`queued`, `processing`, `done`, `done_empty` (утверждений нет), `done_partial` (часть страниц с ошибкой), `failed`, `unsupported` (нет текстового слоя), `duplicate`, `irrelevant`.