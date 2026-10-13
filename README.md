# Лабраторная работа №1 по информационной безопастности 

Выбраный стек: Python Flask, PostgreSQL, SQLAlchemy. Проверки: bandit, safety, а также OWASP Dependency-Check и Snyk

## Запуск

```bash
docker compose up --build
```

После запуска docker-compose API будет доступен на `http://localhost:8000`. PostgreSQL доступен на порту 5433. Liquibase создаёт таблицы `users` и `data`, включает `pgcrypto` и создаёт пользователя из переменных `DEFAULT_USER` и `DEFAULT_USER_PASSWORD`. Пароль пользователя сохраняется в виде bcrypt-хэша.

Чтобы полностью сбросить локальную базу и повторить миграции, выполните `docker compose down -v`. Команда удаляет том с данными PostgreSQL.

## API

### `POST /auth/login`

Принимает логин и пароль, возвращает JWT со сроком действия 15 минут.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"admin","password":"your-default-password"}'
```

Передайте полученное значение `access_token` в заголовке `Authorization: Bearer <token>` для защищённых методов.

### `GET /api/data`

Возвращает список записей. Требует действующий JWT.

```bash
curl http://localhost:8000/api/data \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### `POST /api/data`

Создаёт запись. Требует действующий JWT. Поля `name` и `description` обязательны, `extra_fields` необязателен и по умолчанию равен `{}`.

```bash
curl -X POST http://localhost:8000/api/data \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Example","description":"Example data","extra_fields":{"source":"demo"}}'
```

`GET /health` предназначен для проверки готовности контейнера.

## Меры защиты

- **SQL injection:** обращения к БД выполняются через SQLAlchemy ORM и связанные параметры. Пользовательские значения не добавляются к SQL-строкам конкатенацией.
- **XSS:** приложение сохраняет исходные строки в PostgreSQL, но экранирует HTML-спецсимволы в строковых значениях и ключах, которые возвращаются API, в том числе внутри `extra_fields`. JSON выдаётся с `Content-Type: application/json`. Клиентам всё равно следует использовать безопасные DOM API и контекстное кодирование при отображении данных.
- **Аутентификация:** пароль пользователя создаётся в Liquibase с помощью `pgcrypto` и `crypt(..., gen_salt('bf', 12))`. При входе пароль сравнивается с bcrypt-хэшем, открытый пароль не сохраняется. JWT подписывается HS256, проверяются алгоритм, издатель, аудитория, срок действия и обязательные claims. Ошибки входа не раскрывают, существует ли пользователь.
- **Секреты:** пароли БД, пароль пользователя по умолчанию и ключ подписи JWT задаются через `.env`, который исключён из Git.
- **HTTP-ответы:** выставляются `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy` и `Cache-Control`.
- **Контейнер:** backend запускается от непривилегированного пользователя; база данных доступна контейнерам Compose, но не публикуется наружу.

## GitHub Actions

Workflow `.github/workflows/ci.yml` запускается на `push`, `pull_request` и вручную. Он выполняет форматирование, Ruff, pytest, Bandit и OWASP Dependency-Check. Отчёты сохраняются как артефакт `security-reports`.

Чтобы запускались также Safety и Snyk, добавьте в `Settings → Secrets and variables → Actions` секреты `SAFETY_API_KEY` и `SNYK_TOKEN`. Для ускорения обновления базы уязвимостей Dependency-Check добавьте `NVD_API_KEY`. Safety и Snyk пропускаются, если соответствующий секрет не задан; это нужно учитывать при подготовке итогового скриншота CI.

В репозитории откройте `Actions`, выберите успешный запуск workflow и сохраните ссылку на него для сдачи. Скачайте артефакт `security-reports`, чтобы приложить результаты сканирования.
