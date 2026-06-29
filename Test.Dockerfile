FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/

WORKDIR /app

COPY docker-entry.sh ./

COPY pyproject.toml uv.lock ./

# Constrain to the uv.lock versions rather than whatever is newest on PyPI at build time; --locked fails the build
# if uv.lock is out of date with pyproject.toml.
RUN uv export --locked --no-hashes --no-emit-project --extra numerics --extra api -o requirements.txt

COPY src ./src

RUN pip install --no-cache-dir -c requirements.txt ".[numerics,api]"

CMD ["./docker-entry.sh"]
