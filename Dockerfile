FROM python:3.9-slim

WORKDIR /app

# Устанавливаем системные зависимости, нужные для сборки некоторых пакетов (опционально)
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Команда для запуска бота
CMD ["python", "-u", "bot.py"]
