FROM python:3.10

WORKDIR /app

COPY docker-entry.sh ./

RUN pip install --no-cache-dir nmcp-precomputed==3.0.6

CMD ["./docker-entry.sh"]
