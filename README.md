# PUP UMIS Backend

Purnea University - University Management Information System Backend

## Requirements

- Python 3.12+
- Poetry

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Activate the virtual environment:
   ```bash
   poetry shell
   ```

3. Run migrations:
   ```bash
   poetry run python manage.py migrate
   ```

4. Run the development server:
   ```bash
   poetry run python manage.py runserver
   ```

## Development Commands

- **Run server**: `poetry run python manage.py runserver`
- **Make migrations**: `poetry run python manage.py makemigrations`
- **Apply migrations**: `poetry run python manage.py migrate`
- **Create superuser**: `poetry run python manage.py createsuperuser`
- **Shell**: `poetry run python manage.py shell`
