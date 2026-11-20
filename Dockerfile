# Сборка зависимостей
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Используем зеркало PyPI, чтобы обойти блокировку SSL в Codespaces
RUN pip install --user --no-cache-dir --default-timeout=1000 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# Запуск
FROM python:3.11-slim

# Устанавливаем curl для healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя
RUN useradd -m appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Даем права новому пользователю
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

# Запускаем gunicorn с 1 рабочим процессом
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]