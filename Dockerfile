FROM python:3.10

COPY docker-entry.sh ./

RUN pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ nmcp-precomputed==3.0.7

CMD ["./docker-entry.sh"]
