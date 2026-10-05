FROM python:3.13-alpine

ARG BUILD_VERSION="0.5.0"
ARG BUILD_ARCH="amd64"

LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache libffi openssl && \
    pip install --no-cache-dir \
      'fastapi>=0.115,<1' \
      'uvicorn[standard]>=0.30,<1' \
      'pydantic>=2.9,<3' \
      'pydantic-settings>=2.5,<3' \
      'zeroconf>=0.135,<1' \
      'tinytuya>=1.16,<2' \
      'cryptography>=43,<47'

COPY rootfs/ /
ENV PYTHONPATH=/opt/casa-local-core \
    CASA_LOCAL_HOST=0.0.0.0 \
    CASA_LOCAL_PORT=8799 \
    CASA_LOCAL_DATA_DIR=/data

CMD ["python", "-m", "casalocal_core.main"]
