FROM python:3.11

RUN mkdir -p /root/.cloudvolume/secrets

WORKDIR /usr/src/app

COPY requirements.txt ./

COPY docker-entry.sh ./

RUN pip install --no-cache-dir -r requirements.txt

COPY nmcp nmcp

CMD ["./docker-entry.sh"]
