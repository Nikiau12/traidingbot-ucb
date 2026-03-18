#!/bin/bash
echo "🚀 [Railway Container] Запускаю MEXC Сигнального Бота..."
python -u bot.py &

echo "🚀 [Railway Container] Запускаю BingX Телеграм Автотрейдера..."
python -u bot_bingx.py &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
