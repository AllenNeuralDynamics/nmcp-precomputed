FROM python:3.10

# Supplied by the Taskfile from pyproject.toml; selects the wheel `uv build` wrote for this version.
ARG VERSION

WORKDIR /app

COPY --chmod=755 docker-entry.sh ./

COPY dist/nmcp_precomputed-${VERSION}-py3-none-any.whl ./

RUN pip install --no-cache-dir "./nmcp_precomputed-${VERSION}-py3-none-any.whl[numerics,api]"

CMD ["./docker-entry.sh"]
