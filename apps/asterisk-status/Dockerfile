FROM python:3.12-alpine3.22
WORKDIR /app
COPY status.py /app/status.py
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python3", "/app/status.py"]
