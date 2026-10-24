FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md AGENTS.md CLAUDE.md wireframe_de_olho_no_brasil.html ./
COPY .agents ./.agents
COPY docs ./docs
COPY src ./src
COPY tests ./tests

RUN useradd --create-home --shell /bin/bash donb && chown -R donb:donb /app
USER donb

CMD ["python3", "-m", "deolhonobrasil.harness.runner", "--checkpoint", "4", "--trials", "3"]
