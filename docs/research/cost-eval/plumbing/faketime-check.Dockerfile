FROM python:3.12-slim
RUN apt-get update -qq && apt-get install -y -qq faketime >/dev/null && rm -rf /var/lib/apt/lists/*
RUN pip install -q fastapi uvicorn
WORKDIR /app
COPY faketime-check-app.py app.py
ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/faketime/libfaketime.so.1 FAKETIME_DONT_FAKE_MONOTONIC=1 FAKETIME_NO_CACHE=1 FAKETIME_TIMESTAMP_FILE=/clock/faketime
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
