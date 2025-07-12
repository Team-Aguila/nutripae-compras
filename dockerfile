FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --with dev

COPY . .

# Agregar PYTHONPATH para que Python encuentre los módulos en src/
ENV PYTHONPATH=/app/src

CMD ["poetry", "run", "poe", "dev"]