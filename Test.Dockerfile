FROM python:3.10

WORKDIR /app

COPY docker-entry.sh ./

COPY pyproject.toml ./

COPY src ./src

RUN pip install --no-cache-dir .

CMD ["./docker-entry.sh"]
