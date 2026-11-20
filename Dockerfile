FROM python:3.11-slim

WORKDIR /app

# Сначала зависимости — для кэша слоёв
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код (секреты и локальная база исключены через .dockerignore)
COPY . .

# Боту не нужен порт (long polling). Переменные задаются через env_file/ENV.
CMD ["python", "bot.py"]
