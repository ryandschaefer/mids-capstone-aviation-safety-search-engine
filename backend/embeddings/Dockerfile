FROM python:3.11-slim AS build
ARG APP_DIR=/src

RUN apt-get update \
    && apt-get install -y \
         curl \
         build-essential \
         libffi-dev \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH=/root/.local/bin:$PATH

WORKDIR ${APP_DIR}
COPY pyproject.toml poetry.lock ./

RUN python -m venv --copies ${APP_DIR}/venv
RUN . ${APP_DIR}/venv/bin/activate && poetry install --no-root --only main

FROM python:3.11-slim AS run
ARG APP_DIR=/src

COPY --from=build ${APP_DIR}/venv ${APP_DIR}/venv/
ENV PATH=${APP_DIR}/venv/bin:$PATH

WORKDIR ${APP_DIR}
COPY . ./

EXPOSE 8002

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]