from __future__ import annotations
from typing import Any

LANG_BUTTONS = [
    ("🇷🇺 Русский",  "lang_ru"),
    ("🇬🇧 English",  "lang_en"),
    ("🇩🇪 Deutsch",  "lang_de"),
    ("🇫🇷 Français", "lang_fr"),
    ("🇪🇸 Español",  "lang_es"),
]

STRINGS: dict[str, dict[str, Any]] = {

    # ─────────────────────────── RUSSIAN ───────────────────────────
    "ru": {
        "welcome": (
            "👋 Привет! Я <b>UCB_TRADING_BOT</b>\n\n"
            "Твой торговый ассистент для MEXC Futures.\n"
            "Анализирую рынок по 4h и 1d свечам, нахожу сетапы\n"
            "и строю планы: вход, стоп, два TP и размер позиции.\n\n"
            "🌐 Выбери язык:"
        ),
        "lang_set": "✅ Язык установлен: <b>Русский</b>\n\nПечатай /help — покажу все команды.",
        "choose_lang": "🌐 Выбери язык:",
        "help": (
            "📋 <b>UCB_TRADING_BOT — Справочник</b>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 <b>ПЛАНЫ</b>\n"
            "/plan BTC_USDT\n"
            "   → план с твоими сохранёнными параметрами\n"
            "/plan ETH_USDT lev=10 risk=2\n"
            "   → переопределить параметры для одного запроса\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>СКАНИРОВАНИЕ</b>\n"
            "/scan — скан топ-{top_n} монет (~2–4 мин)\n"
            "   → только сетапы выше порога уверенности\n\n"
            "📊 <b>ДАЙДЖЕСТ</b>\n"
            "/digest — полный обзор рынка прямо сейчас\n"
            "   → высокая / средняя уверенность + скип\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>ТВОИ ПАРАМЕТРЫ</b>\n"
            "/settings — посмотреть текущие параметры\n\n"
            "/set deposit=5000    — твой депозит (обязательно)\n"
            "/set risk=1          — % риска на сделку (по умолч. 1%)\n"
            "/set lev=20          — кредитное плечо (по умолч. 10x)\n"
            "/set margin=isolated — тип маржи (по умолч. cross)\n\n"
            "Можно сразу несколько:\n"
            "<code>/set deposit=5000 risk=1.5 lev=15</code>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <b>ЧТО ЗНАЧИТ ПЛАН</b>\n"
            "<code>entry</code>   — цена входа (лимитный ордер)\n"
            "<code>stop</code>    — стоп-лосс\n"
            "<code>tp1/tp2</code> — тейк-профиты (по 50% позиции)\n"
            "<code>conf</code>    — уверенность алгоритма (0.0–1.0)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🕐 <b>РАСПИСАНИЕ (UTC)</b>\n"
            "Автосканирование: 00:05 / 04:05 / 08:05\n"
            "                  12:05 / 16:05 / 20:05\n"
            "Дайджест: {digest_hour}:00 ежедневно\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>ВАЖНО</b>\n"
            "Бот предоставляет аналитику, а не торговые сигналы.\n"
            "Решение о входе в сделку всегда остаётся за тобой.\n\n"
            "🌐 Сменить язык → /start"
        ),
        "no_deposit": (
            "⚠️ Депозит не установлен.\n\n"
            "Укажи свой депозит один раз:\n"
            "<code>/set deposit=5000</code>\n\n"
            "Бот запомнит — больше вводить не нужно."
        ),
        "set_usage": (
            "Использование:\n"
            "<code>/set deposit=5000</code>\n"
            "<code>/set risk=1.5</code>\n"
            "<code>/set lev=20</code>\n"
            "<code>/set deposit=5000 risk=1 lev=20</code>"
        ),
        "set_saved":       "✅ Сохранено: {params}",
        "set_unknown":     "❌ Неизвестный параметр: {key}. Доступны: deposit, risk, lev, margin",
        "settings_title":  "⚙️ <b>Твои параметры</b>\n\n",
        "settings_deposit":"💰 deposit: {val}\n",
        "settings_deposit_missing": "💰 deposit: <b>⚠️ не установлен</b> → <code>/set deposit=XXXX</code>\n",
        "settings_risk":   "🎯 risk: <b>{val}%</b>\n",
        "settings_lev":    "🧰 lev: <b>{val}x</b>\n",
        "settings_margin": "📐 margin: <b>{val}</b>\n\n",
        "settings_change": "Изменить: <code>/set deposit=X risk=X lev=X</code>",
        "deposit_not_set": "⚠️ не установлен → /set deposit=XXXX",
        "plan_loading":    "⏳ Загружаю {symbol}...",
        "plan_error":      "❌ Ошибка: {error}",
        "plan_usage":      "Использование: /plan BTC_USDT [lev=20 risk=1 deposit=3000]",
        "scan_starting":   "🔍 Сканирую топ-{top_n} монет (~2–4 мин)...",
        "scan_done":       "✅ Найдено {count} сетап(ов). Топ-5:",
        "scan_none":       "🧊 Нет сетапов выше порога уверенности",
        "scan_more":       "...и ещё {count}. Используй /digest для полного обзора.",
        "scan_error":      "❌ Ошибка сканирования: {error}",
        "digest_preparing":"📊 Готовлю дайджест...",
        "digest_title":    "📊 <b>Дайджест {time} UTC</b>\nПроверено: <b>{total}</b> монет",
        "digest_high":     "🟢 <b>Высокая уверенность ≥0.65 — {count} шт.</b>",
        "digest_medium":   "🟡 <b>Средняя уверенность 0.50–0.65 — {count} шт.</b>",
        "digest_skipped":  "🧊 Нет сетапа: <b>{count}</b> монет",
        "digest_error":    "❌ Ошибка дайджеста: {error}",
        "autoscan_error":  "⚠️ Ошибка автосканирования: {error}",
        # plan render labels
        "r_context":       "🧠 Контекст",
        "r_plan":          "план",
        "r_price":         "💵 Цена",
        "r_profile":       "🧷 Профиль",
        "r_deposit":       "💰 депозит",
        "r_risk":          "🎯 риск",
        "r_lev":           "🧰 плечо",
        "r_regime":        "🧭 Режим рынка",
        "r_trend_1d":      "trend 1D",
        "r_trend_4h":      "4H",
        "r_struct":        "структура 4H",
        "r_bos":           "BOS/CHOCH",
        "r_regime_label":  "режим",
        "r_mid":           "midrange",
        "r_scenario":      "Сценарий",
        "r_entry":         "🎯 entry",
        "r_stop":          "🛑 stop",
        "r_tp1":           "🥅 tp1",
        "r_tp2":           "🥅 tp2",
        "r_size":          "📦 Размер",
        "r_qty":           "кол-во",
        "r_margin_need":   "маржа",
        "r_levels":        "🧱 Уровни",
        "r_support":       "🟩 поддержка",
        "r_resistance":    "🟥 сопротивление",
        "r_why":           "🔍 Почему",
        "r_risk_rule":     "🚨 Риск-правило",
        "r_risk_text":     "<b>CROSS + плечо — без стопа нельзя.</b> Стоп обязателен.",
        "r_skip_conf":     "🧊 Уверенность",
        "r_skip_reason":   "🔍 Причины",
        "r_cache_warn":    "⚠️<i>кэш</i>",
    },

    # ─────────────────────────── ENGLISH ───────────────────────────
    "en": {
        "welcome": (
            "👋 Hello! I'm <b>UCB_TRADING_BOT</b>\n\n"
            "Your trading assistant for MEXC Futures.\n"
            "I analyse the market on 4h and 1d candles, find setups\n"
            "and build plans: entry, stop-loss, two TPs and position size.\n\n"
            "🌐 Choose your language:"
        ),
        "lang_set": "✅ Language set: <b>English</b>\n\nType /help to see all commands.",
        "choose_lang": "🌐 Choose your language:",
        "help": (
            "📋 <b>UCB_TRADING_BOT — Commands</b>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 <b>PLANS</b>\n"
            "/plan BTC_USDT\n"
            "   → plan with your saved parameters\n"
            "/plan ETH_USDT lev=10 risk=2\n"
            "   → override parameters for one request\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — scan top-{top_n} coins (~2–4 min)\n"
            "   → shows only setups above confidence threshold\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — full market overview right now\n"
            "   → high / medium confidence + skipped\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>YOUR PARAMETERS</b>\n"
            "/settings — view your current parameters\n\n"
            "/set deposit=5000    — your deposit (required)\n"
            "/set risk=1          — % risk per trade (default 1%)\n"
            "/set lev=20          — leverage (default 10x)\n"
            "/set margin=isolated — margin type (default cross)\n\n"
            "Multiple at once:\n"
            "<code>/set deposit=5000 risk=1.5 lev=15</code>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <b>WHAT THE PLAN MEANS</b>\n"
            "<code>entry</code>   — entry price (limit order)\n"
            "<code>stop</code>    — stop-loss\n"
            "<code>tp1/tp2</code> — take-profits (50% of position each)\n"
            "<code>conf</code>    — algorithm confidence (0.0–1.0)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🕐 <b>SCHEDULE (UTC)</b>\n"
            "Auto-scan: 00:05 / 04:05 / 08:05\n"
            "           12:05 / 16:05 / 20:05\n"
            "Digest: {digest_hour}:00 daily\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>DISCLAIMER</b>\n"
            "The bot provides analytics, not trading signals.\n"
            "The decision to enter a trade is always yours.\n\n"
            "🌐 Change language → /start"
        ),
        "no_deposit": (
            "⚠️ Deposit not set.\n\n"
            "Set your deposit once:\n"
            "<code>/set deposit=5000</code>\n\n"
            "The bot will remember it — no need to enter it again."
        ),
        "set_usage": (
            "Usage:\n"
            "<code>/set deposit=5000</code>\n"
            "<code>/set risk=1.5</code>\n"
            "<code>/set lev=20</code>\n"
            "<code>/set deposit=5000 risk=1 lev=20</code>"
        ),
        "set_saved":       "✅ Saved: {params}",
        "set_unknown":     "❌ Unknown parameter: {key}. Allowed: deposit, risk, lev, margin",
        "settings_title":  "⚙️ <b>Your settings</b>\n\n",
        "settings_deposit":"💰 deposit: {val}\n",
        "settings_deposit_missing": "💰 deposit: <b>⚠️ not set</b> → <code>/set deposit=XXXX</code>\n",
        "settings_risk":   "🎯 risk: <b>{val}%</b>\n",
        "settings_lev":    "🧰 lev: <b>{val}x</b>\n",
        "settings_margin": "📐 margin: <b>{val}</b>\n\n",
        "settings_change": "Change: <code>/set deposit=X risk=X lev=X</code>",
        "deposit_not_set": "⚠️ not set → /set deposit=XXXX",
        "plan_loading":    "⏳ Loading {symbol}...",
        "plan_error":      "❌ Error: {error}",
        "plan_usage":      "Usage: /plan BTC_USDT [lev=20 risk=1]",
        "scan_starting":   "🔍 Scanning top-{top_n} coins (~2–4 min)...",
        "scan_done":       "✅ Found {count} setup(s). Top 5:",
        "scan_none":       "🧊 No setups above confidence threshold",
        "scan_more":       "...and {count} more. Use /digest for a full overview.",
        "scan_error":      "❌ Scan error: {error}",
        "digest_preparing":"📊 Preparing digest...",
        "digest_title":    "📊 <b>Digest {time} UTC</b>\nChecked: <b>{total}</b> coins",
        "digest_high":     "🟢 <b>High confidence ≥0.65 — {count} setup(s)</b>",
        "digest_medium":   "🟡 <b>Medium confidence 0.50–0.65 — {count} setup(s)</b>",
        "digest_skipped":  "🧊 No setup: <b>{count}</b> coins",
        "digest_error":    "❌ Digest error: {error}",
        "autoscan_error":  "⚠️ Auto-scan error: {error}",
        "r_context":       "🧠 Context",
        "r_plan":          "plan",
        "r_price":         "💵 Price",
        "r_profile":       "🧷 Profile",
        "r_deposit":       "💰 deposit",
        "r_risk":          "🎯 risk",
        "r_lev":           "🧰 leverage",
        "r_regime":        "🧭 Market regime",
        "r_trend_1d":      "trend 1D",
        "r_trend_4h":      "4H",
        "r_struct":        "structure 4H",
        "r_bos":           "BOS/CHOCH",
        "r_regime_label":  "regime",
        "r_mid":           "midrange",
        "r_scenario":      "Scenario",
        "r_entry":         "🎯 entry",
        "r_stop":          "🛑 stop",
        "r_tp1":           "🥅 tp1",
        "r_tp2":           "🥅 tp2",
        "r_size":          "📦 Size",
        "r_qty":           "qty",
        "r_margin_need":   "margin",
        "r_levels":        "🧱 Levels",
        "r_support":       "🟩 support",
        "r_resistance":    "🟥 resistance",
        "r_why":           "🔍 Why",
        "r_risk_rule":     "🚨 Risk rule",
        "r_risk_text":     "<b>CROSS + leverage — stop-loss is mandatory.</b>",
        "r_skip_conf":     "🧊 Confidence",
        "r_skip_reason":   "🔍 Reasons",
        "r_cache_warn":    "⚠️<i>cache</i>",
    },

    # ─────────────────────────── GERMAN ───────────────────────────
    "de": {
        "welcome": (
            "👋 Hallo! Ich bin <b>UCB_TRADING_BOT</b>\n\n"
            "Dein Trading-Assistent für MEXC Futures.\n"
            "Ich analysiere den Markt auf 4h- und 1d-Kerzen, finde Setups\n"
            "und erstelle Pläne: Einstieg, Stop-Loss, zwei TPs und Positionsgröße.\n\n"
            "🌐 Wähle deine Sprache:"
        ),
        "lang_set": "✅ Sprache gesetzt: <b>Deutsch</b>\n\nTippe /help für alle Befehle.",
        "choose_lang": "🌐 Wähle deine Sprache:",
        "help": (
            "📋 <b>UCB_TRADING_BOT — Befehle</b>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 <b>PLÄNE</b>\n"
            "/plan BTC_USDT\n"
            "   → Plan mit deinen gespeicherten Parametern\n"
            "/plan ETH_USDT lev=10 risk=2\n"
            "   → Parameter für eine Anfrage überschreiben\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — Top-{top_n} Coins scannen (~2–4 Min)\n"
            "   → nur Setups über dem Konfidenzschwellenwert\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — vollständige Marktübersicht jetzt\n"
            "   → hohe / mittlere Konfidenz + übersprungen\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>DEINE PARAMETER</b>\n"
            "/settings — aktuelle Parameter anzeigen\n\n"
            "/set deposit=5000    — dein Kapital (erforderlich)\n"
            "/set risk=1          — Risiko-% pro Trade (Standard 1%)\n"
            "/set lev=20          — Hebel (Standard 10x)\n"
            "/set margin=isolated — Margin-Typ (Standard cross)\n\n"
            "Mehrere gleichzeitig:\n"
            "<code>/set deposit=5000 risk=1.5 lev=15</code>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <b>WAS DER PLAN BEDEUTET</b>\n"
            "<code>entry</code>   — Einstiegskurs (Limit-Order)\n"
            "<code>stop</code>    — Stop-Loss\n"
            "<code>tp1/tp2</code> — Take-Profits (je 50 % der Position)\n"
            "<code>conf</code>    — Algorithmus-Konfidenz (0.0–1.0)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🕐 <b>ZEITPLAN (UTC)</b>\n"
            "Auto-Scan: 00:05 / 04:05 / 08:05\n"
            "           12:05 / 16:05 / 20:05\n"
            "Digest: {digest_hour}:00 täglich\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>HINWEIS</b>\n"
            "Der Bot liefert Analysen, keine Handelssignale.\n"
            "Die Entscheidung zum Handeln liegt immer bei dir.\n\n"
            "🌐 Sprache ändern → /start"
        ),
        "no_deposit": (
            "⚠️ Kapital nicht festgelegt.\n\n"
            "Lege dein Kapital einmalig fest:\n"
            "<code>/set deposit=5000</code>\n\n"
            "Der Bot merkt es sich — du musst es nicht erneut eingeben."
        ),
        "set_usage": (
            "Verwendung:\n"
            "<code>/set deposit=5000</code>\n"
            "<code>/set risk=1.5</code>\n"
            "<code>/set lev=20</code>\n"
            "<code>/set deposit=5000 risk=1 lev=20</code>"
        ),
        "set_saved":       "✅ Gespeichert: {params}",
        "set_unknown":     "❌ Unbekannter Parameter: {key}. Erlaubt: deposit, risk, lev, margin",
        "settings_title":  "⚙️ <b>Deine Parameter</b>\n\n",
        "settings_deposit":"💰 deposit: {val}\n",
        "settings_deposit_missing": "💰 deposit: <b>⚠️ nicht festgelegt</b> → <code>/set deposit=XXXX</code>\n",
        "settings_risk":   "🎯 risk: <b>{val}%</b>\n",
        "settings_lev":    "🧰 lev: <b>{val}x</b>\n",
        "settings_margin": "📐 margin: <b>{val}</b>\n\n",
        "settings_change": "Ändern: <code>/set deposit=X risk=X lev=X</code>",
        "deposit_not_set": "⚠️ nicht festgelegt → /set deposit=XXXX",
        "plan_loading":    "⏳ Lade {symbol}...",
        "plan_error":      "❌ Fehler: {error}",
        "plan_usage":      "Verwendung: /plan BTC_USDT [lev=20 risk=1]",
        "scan_starting":   "🔍 Scanne Top-{top_n} Coins (~2–4 Min)...",
        "scan_done":       "✅ {count} Setup(s) gefunden. Top 5:",
        "scan_none":       "🧊 Keine Setups über dem Schwellenwert",
        "scan_more":       "...und {count} weitere. Nutze /digest für eine vollständige Übersicht.",
        "scan_error":      "❌ Scan-Fehler: {error}",
        "digest_preparing":"📊 Digest wird vorbereitet...",
        "digest_title":    "📊 <b>Digest {time} UTC</b>\nGeprüft: <b>{total}</b> Coins",
        "digest_high":     "🟢 <b>Hohe Konfidenz ≥0.65 — {count} Setup(s)</b>",
        "digest_medium":   "🟡 <b>Mittlere Konfidenz 0.50–0.65 — {count} Setup(s)</b>",
        "digest_skipped":  "🧊 Kein Setup: <b>{count}</b> Coins",
        "digest_error":    "❌ Digest-Fehler: {error}",
        "autoscan_error":  "⚠️ Auto-Scan-Fehler: {error}",
        "r_context":       "🧠 Kontext",
        "r_plan":          "Plan",
        "r_price":         "💵 Kurs",
        "r_profile":       "🧷 Profil",
        "r_deposit":       "💰 Kapital",
        "r_risk":          "🎯 Risiko",
        "r_lev":           "🧰 Hebel",
        "r_regime":        "🧭 Marktlage",
        "r_trend_1d":      "Trend 1D",
        "r_trend_4h":      "4H",
        "r_struct":        "Struktur 4H",
        "r_bos":           "BOS/CHOCH",
        "r_regime_label":  "Regime",
        "r_mid":           "Midrange",
        "r_scenario":      "Szenario",
        "r_entry":         "🎯 Einstieg",
        "r_stop":          "🛑 Stop",
        "r_tp1":           "🥅 TP1",
        "r_tp2":           "🥅 TP2",
        "r_size":          "📦 Größe",
        "r_qty":           "Menge",
        "r_margin_need":   "Margin",
        "r_levels":        "🧱 Levels",
        "r_support":       "🟩 Unterstützung",
        "r_resistance":    "🟥 Widerstand",
        "r_why":           "🔍 Begründung",
        "r_risk_rule":     "🚨 Risikoregel",
        "r_risk_text":     "<b>CROSS + Hebel — Stop-Loss ist Pflicht.</b>",
        "r_skip_conf":     "🧊 Konfidenz",
        "r_skip_reason":   "🔍 Gründe",
        "r_cache_warn":    "⚠️<i>Cache</i>",
    },

    # ─────────────────────────── FRENCH ───────────────────────────
    "fr": {
        "welcome": (
            "👋 Bonjour ! Je suis <b>UCB_TRADING_BOT</b>\n\n"
            "Ton assistant de trading pour MEXC Futures.\n"
            "J'analyse le marché sur les bougies 4h et 1d, trouve des setups\n"
            "et crée des plans : entrée, stop-loss, deux TP et taille de position.\n\n"
            "🌐 Choisis ta langue :"
        ),
        "lang_set": "✅ Langue définie : <b>Français</b>\n\nTape /help pour voir toutes les commandes.",
        "choose_lang": "🌐 Choisis ta langue :",
        "help": (
            "📋 <b>UCB_TRADING_BOT — Commandes</b>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 <b>PLANS</b>\n"
            "/plan BTC_USDT\n"
            "   → plan avec tes paramètres sauvegardés\n"
            "/plan ETH_USDT lev=10 risk=2\n"
            "   → remplacer les paramètres pour une requête\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — scanner le top {top_n} (~2–4 min)\n"
            "   → uniquement les setups au-dessus du seuil\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — vue d'ensemble du marché maintenant\n"
            "   → haute / moyenne confiance + ignorés\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>TES PARAMÈTRES</b>\n"
            "/settings — voir tes paramètres actuels\n\n"
            "/set deposit=5000    — ton dépôt (obligatoire)\n"
            "/set risk=1          — % de risque par trade (défaut 1%)\n"
            "/set lev=20          — levier (défaut 10x)\n"
            "/set margin=isolated — type de marge (défaut cross)\n\n"
            "Plusieurs à la fois :\n"
            "<code>/set deposit=5000 risk=1.5 lev=15</code>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <b>CE QUE SIGNIFIE LE PLAN</b>\n"
            "<code>entry</code>   — prix d'entrée (ordre limite)\n"
            "<code>stop</code>    — stop-loss\n"
            "<code>tp1/tp2</code> — take-profits (50 % de la position chacun)\n"
            "<code>conf</code>    — confiance de l'algorithme (0.0–1.0)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🕐 <b>PLANNING (UTC)</b>\n"
            "Scan auto : 00:05 / 04:05 / 08:05\n"
            "            12:05 / 16:05 / 20:05\n"
            "Digest : {digest_hour}:00 quotidiennement\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>AVERTISSEMENT</b>\n"
            "Le bot fournit des analyses, pas des signaux de trading.\n"
            "La décision d'entrer en position reste toujours la tienne.\n\n"
            "🌐 Changer de langue → /start"
        ),
        "no_deposit": (
            "⚠️ Dépôt non défini.\n\n"
            "Définis ton dépôt une seule fois :\n"
            "<code>/set deposit=5000</code>\n\n"
            "Le bot s'en souviendra — pas besoin de le ressaisir."
        ),
        "set_usage": (
            "Utilisation :\n"
            "<code>/set deposit=5000</code>\n"
            "<code>/set risk=1.5</code>\n"
            "<code>/set lev=20</code>\n"
            "<code>/set deposit=5000 risk=1 lev=20</code>"
        ),
        "set_saved":       "✅ Sauvegardé : {params}",
        "set_unknown":     "❌ Paramètre inconnu : {key}. Autorisés : deposit, risk, lev, margin",
        "settings_title":  "⚙️ <b>Tes paramètres</b>\n\n",
        "settings_deposit":"💰 deposit : {val}\n",
        "settings_deposit_missing": "💰 deposit : <b>⚠️ non défini</b> → <code>/set deposit=XXXX</code>\n",
        "settings_risk":   "🎯 risk : <b>{val}%</b>\n",
        "settings_lev":    "🧰 lev : <b>{val}x</b>\n",
        "settings_margin": "📐 margin : <b>{val}</b>\n\n",
        "settings_change": "Modifier : <code>/set deposit=X risk=X lev=X</code>",
        "deposit_not_set": "⚠️ non défini → /set deposit=XXXX",
        "plan_loading":    "⏳ Chargement de {symbol}...",
        "plan_error":      "❌ Erreur : {error}",
        "plan_usage":      "Utilisation : /plan BTC_USDT [lev=20 risk=1]",
        "scan_starting":   "🔍 Scan du top {top_n} en cours (~2–4 min)...",
        "scan_done":       "✅ {count} setup(s) trouvé(s). Top 5 :",
        "scan_none":       "🧊 Aucun setup au-dessus du seuil de confiance",
        "scan_more":       "...et {count} de plus. Utilise /digest pour une vue complète.",
        "scan_error":      "❌ Erreur de scan : {error}",
        "digest_preparing":"📊 Préparation du digest...",
        "digest_title":    "📊 <b>Digest {time} UTC</b>\nVérifié : <b>{total}</b> coins",
        "digest_high":     "🟢 <b>Haute confiance ≥0.65 — {count} setup(s)</b>",
        "digest_medium":   "🟡 <b>Confiance moyenne 0.50–0.65 — {count} setup(s)</b>",
        "digest_skipped":  "🧊 Pas de setup : <b>{count}</b> coins",
        "digest_error":    "❌ Erreur digest : {error}",
        "autoscan_error":  "⚠️ Erreur scan auto : {error}",
        "r_context":       "🧠 Contexte",
        "r_plan":          "plan",
        "r_price":         "💵 Prix",
        "r_profile":       "🧷 Profil",
        "r_deposit":       "💰 dépôt",
        "r_risk":          "🎯 risque",
        "r_lev":           "🧰 levier",
        "r_regime":        "🧭 Régime de marché",
        "r_trend_1d":      "tendance 1D",
        "r_trend_4h":      "4H",
        "r_struct":        "structure 4H",
        "r_bos":           "BOS/CHOCH",
        "r_regime_label":  "régime",
        "r_mid":           "midrange",
        "r_scenario":      "Scénario",
        "r_entry":         "🎯 entrée",
        "r_stop":          "🛑 stop",
        "r_tp1":           "🥅 tp1",
        "r_tp2":           "🥅 tp2",
        "r_size":          "📦 Taille",
        "r_qty":           "qté",
        "r_margin_need":   "marge",
        "r_levels":        "🧱 Niveaux",
        "r_support":       "🟩 support",
        "r_resistance":    "🟥 résistance",
        "r_why":           "🔍 Pourquoi",
        "r_risk_rule":     "🚨 Règle de risque",
        "r_risk_text":     "<b>CROSS + levier — le stop-loss est obligatoire.</b>",
        "r_skip_conf":     "🧊 Confiance",
        "r_skip_reason":   "🔍 Raisons",
        "r_cache_warn":    "⚠️<i>cache</i>",
    },

    # ─────────────────────────── SPANISH ───────────────────────────
    "es": {
        "welcome": (
            "👋 ¡Hola! Soy <b>UCB_TRADING_BOT</b>\n\n"
            "Tu asistente de trading para MEXC Futures.\n"
            "Analizo el mercado en velas de 4h y 1d, encuentro setups\n"
            "y creo planes: entrada, stop-loss, dos TP y tamaño de posición.\n\n"
            "🌐 Elige tu idioma:"
        ),
        "lang_set": "✅ Idioma establecido: <b>Español</b>\n\nEscribe /help para ver todos los comandos.",
        "choose_lang": "🌐 Elige tu idioma:",
        "help": (
            "📋 <b>UCB_TRADING_BOT — Comandos</b>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📌 <b>PLANES</b>\n"
            "/plan BTC_USDT\n"
            "   → plan con tus parámetros guardados\n"
            "/plan ETH_USDT lev=10 risk=2\n"
            "   → reemplazar parámetros para una sola consulta\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>ESCANEO</b>\n"
            "/scan — escanear top {top_n} monedas (~2–4 min)\n"
            "   → solo setups sobre el umbral de confianza\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — resumen completo del mercado ahora\n"
            "   → confianza alta / media + omitidos\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>TUS PARÁMETROS</b>\n"
            "/settings — ver tus parámetros actuales\n\n"
            "/set deposit=5000    — tu depósito (obligatorio)\n"
            "/set risk=1          — % de riesgo por trade (defecto 1%)\n"
            "/set lev=20          — apalancamiento (defecto 10x)\n"
            "/set margin=isolated — tipo de margen (defecto cross)\n\n"
            "Varios a la vez:\n"
            "<code>/set deposit=5000 risk=1.5 lev=15</code>\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📖 <b>QUÉ SIGNIFICA EL PLAN</b>\n"
            "<code>entry</code>   — precio de entrada (orden límite)\n"
            "<code>stop</code>    — stop-loss\n"
            "<code>tp1/tp2</code> — take-profits (50% de la posición c/u)\n"
            "<code>conf</code>    — confianza del algoritmo (0.0–1.0)\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🕐 <b>HORARIO (UTC)</b>\n"
            "Escaneo auto: 00:05 / 04:05 / 08:05\n"
            "              12:05 / 16:05 / 20:05\n"
            "Digest: {digest_hour}:00 diariamente\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>AVISO</b>\n"
            "El bot proporciona análisis, no señales de trading.\n"
            "La decisión de entrar en una operación es siempre tuya.\n\n"
            "🌐 Cambiar idioma → /start"
        ),
        "no_deposit": (
            "⚠️ Depósito no establecido.\n\n"
            "Establece tu depósito una sola vez:\n"
            "<code>/set deposit=5000</code>\n\n"
            "El bot lo recordará — no necesitas ingresarlo de nuevo."
        ),
        "set_usage": (
            "Uso:\n"
            "<code>/set deposit=5000</code>\n"
            "<code>/set risk=1.5</code>\n"
            "<code>/set lev=20</code>\n"
            "<code>/set deposit=5000 risk=1 lev=20</code>"
        ),
        "set_saved":       "✅ Guardado: {params}",
        "set_unknown":     "❌ Parámetro desconocido: {key}. Permitidos: deposit, risk, lev, margin",
        "settings_title":  "⚙️ <b>Tus parámetros</b>\n\n",
        "settings_deposit":"💰 deposit: {val}\n",
        "settings_deposit_missing": "💰 deposit: <b>⚠️ no establecido</b> → <code>/set deposit=XXXX</code>\n",
        "settings_risk":   "🎯 risk: <b>{val}%</b>\n",
        "settings_lev":    "🧰 lev: <b>{val}x</b>\n",
        "settings_margin": "📐 margin: <b>{val}</b>\n\n",
        "settings_change": "Cambiar: <code>/set deposit=X risk=X lev=X</code>",
        "deposit_not_set": "⚠️ no establecido → /set deposit=XXXX",
        "plan_loading":    "⏳ Cargando {symbol}...",
        "plan_error":      "❌ Error: {error}",
        "plan_usage":      "Uso: /plan BTC_USDT [lev=20 risk=1]",
        "scan_starting":   "🔍 Escaneando top {top_n} monedas (~2–4 min)...",
        "scan_done":       "✅ {count} setup(s) encontrado(s). Top 5:",
        "scan_none":       "🧊 Sin setups sobre el umbral de confianza",
        "scan_more":       "...y {count} más. Usa /digest para una vista completa.",
        "scan_error":      "❌ Error de escaneo: {error}",
        "digest_preparing":"📊 Preparando digest...",
        "digest_title":    "📊 <b>Digest {time} UTC</b>\nVerificado: <b>{total}</b> monedas",
        "digest_high":     "🟢 <b>Alta confianza ≥0.65 — {count} setup(s)</b>",
        "digest_medium":   "🟡 <b>Confianza media 0.50–0.65 — {count} setup(s)</b>",
        "digest_skipped":  "🧊 Sin setup: <b>{count}</b> monedas",
        "digest_error":    "❌ Error en digest: {error}",
        "autoscan_error":  "⚠️ Error en escaneo automático: {error}",
        "r_context":       "🧠 Contexto",
        "r_plan":          "plan",
        "r_price":         "💵 Precio",
        "r_profile":       "🧷 Perfil",
        "r_deposit":       "💰 depósito",
        "r_risk":          "🎯 riesgo",
        "r_lev":           "🧰 apalancamiento",
        "r_regime":        "🧭 Régimen de mercado",
        "r_trend_1d":      "tendencia 1D",
        "r_trend_4h":      "4H",
        "r_struct":        "estructura 4H",
        "r_bos":           "BOS/CHOCH",
        "r_regime_label":  "régimen",
        "r_mid":           "midrange",
        "r_scenario":      "Escenario",
        "r_entry":         "🎯 entrada",
        "r_stop":          "🛑 stop",
        "r_tp1":           "🥅 tp1",
        "r_tp2":           "🥅 tp2",
        "r_size":          "📦 Tamaño",
        "r_qty":           "cant.",
        "r_margin_need":   "margen",
        "r_levels":        "🧱 Niveles",
        "r_support":       "🟩 soporte",
        "r_resistance":    "🟥 resistencia",
        "r_why":           "🔍 Por qué",
        "r_risk_rule":     "🚨 Regla de riesgo",
        "r_risk_text":     "<b>CROSS + apalancamiento — el stop-loss es obligatorio.</b>",
        "r_skip_conf":     "🧊 Confianza",
        "r_skip_reason":   "🔍 Razones",
        "r_cache_warn":    "⚠️<i>caché</i>",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    lang_strings = STRINGS.get(lang, STRINGS["en"])
    text = lang_strings.get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
