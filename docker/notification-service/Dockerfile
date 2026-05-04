FROM python:3.12-slim AS builder

WORKDIR /build
COPY shared /build/shared
COPY services/notification-service /build/service
RUN pip install --no-cache-dir --prefix=/install /build/shared \
    && pip install --no-cache-dir --prefix=/install -r /build/service/requirements.txt

FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY services/notification-service/app /app/app
USER appuser
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
