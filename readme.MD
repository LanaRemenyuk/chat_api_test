## Проект: chat_api
### Описание: 
##### API чата, в котором пользователи могут общаться друг с другом в приватных каналах.

### Основные зависимости:

- Python 3.12
- FastAPI==0.115.5
- Uvicorn==0.32.0
- Pydantic==2.9.2
- SQLAlchemy==2.0.36
- Alembic==1.14.0
- SQLModel==0.0.22
- Asyncpg==0.30.0
- Aio-Pika==9.4.3
- Psycopg2-Binary==2.9.10

### Как запустить локально (с docker-compose):

Склонируйте репозиторий и перейдите в директорию проекта:
```sh
git clonegit@github.com:LanaRemenyuk/chat_api_test.git -> cd your_file_location/chat_api_test
```
Создайте в корне проекта файл .env и заполните его переменными окружения из тестового файла

Запустите скрипт docker-compose из корневой директории:
```sh
docker-compose up --build

```
Загрузите тестовые данные из скрипта в контейнере:
```sh
docker exec -it apps /bin/bash
poetry run python load_test_data.py
```
Создайте юзера и протестируйте роуты, перед тестом защищенных роутов необходимо пройти логин и ввести токен в заголовок авторизации. Документация доступна по адресу:
```sh
http://localhost:8000/chats/api/v1/docs
```
### Автор проекта:
- LanaRemenyuk
- Email: lan2828@yandex.ru
- Telegram: @Anr1494