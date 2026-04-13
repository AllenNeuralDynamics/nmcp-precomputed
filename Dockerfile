FROM python:3.10

WORKDIR /app

COPY docker-entry.sh ./

RUN pip install --no-cache-dir "nmcp-precomputed[numerics]==3.0.7"

CMD ["./docker-entry.sh"]
