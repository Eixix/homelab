FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir gunicorn==26.2.0
COPY server.py game.py engine.py ./
COPY public ./public
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 1003:1003
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "16", "--timeout", "60", "--worker-tmp-dir", "/tmp", "server:create_app()"]
