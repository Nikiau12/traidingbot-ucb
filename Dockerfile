FROM python:3.9-slim

WORKDIR /app

# Устанавливаем системные зависимости, нужные для сборки некоторых пакетов (опционально)
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Копируем скрипт запуска и даем права
COPY start.sh .
RUN chmod +x start.sh

# Команда для запуска контейнера (2 бота параллельно)
CMD ["./start.sh"]
