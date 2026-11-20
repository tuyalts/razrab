# Сборка зависимостей
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Запуск
FROM python:3.12-slim

# Создаем непривилегированного пользователя
RUN useradd -m appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Даем права новому пользователю
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH

# Запускаем gunicorn с 1 рабочим процессом (worker)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]