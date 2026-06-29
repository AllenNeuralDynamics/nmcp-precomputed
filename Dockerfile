FROM python:3.10

# Supplied by the Taskfile from pyproject.toml; selects the wheel `uv build` wrote for this version.
ARG VERSION

WORKDIR /app

COPY --chmod=755 docker-entry.sh ./

COPY dist/requirements.txt dist/nmcp_precomputed-${VERSION}-py3-none-any.whl ./

# requirements.txt is exported from uv.lock by the Taskfile; used as constraints so the image gets the locked
# versions rather than whatever is newest on PyPI at build time.
RUN pip install --no-cache-dir -c requirements.txt "./nmcp_precomputed-${VERSION}-py3-none-any.whl[numerics,api]"

CMD ["./docker-entry.sh"]
