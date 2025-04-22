FROM python:3.11-slim
RUN pip install --upgrade pip
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock* README.md* /app/
RUN poetry config virtualenvs.create false && poetry install --only main --no-root --no-interaction --no-ansi
COPY . /app
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]