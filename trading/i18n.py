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
            "   → план с параметрами по умолчанию\n"
            "/plan ETH_USDT lev=10 risk=2 deposit=5000\n"
            "   → с кастомными параметрами\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>СКАНИРОВАНИЕ</b>\n"
            "/scan — скан топ-{top_n} монет (~2–4 мин)\n"
            "   → только сетапы выше порога уверенности\n\n"
            "📊 <b>ДАЙДЖЕСТ</b>\n"
            "/digest — полный обзор рынка прямо сейчас\n"
            "   → высокая / средняя уверенность + скип\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>ПАРАМЕТРЫ</b>\n"
            "<code>deposit</code> — депозит в USDT (сейчас: {deposit})\n"
            "<code>risk</code>    — % риска на сделку (сейчас: {risk}%)\n"
            "<code>lev</code>     — кредитное плечо (сейчас: {lev}x)\n"
            "<code>margin</code>  — тип маржи: cross / isolated\n\n"
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
            "   → plan with default parameters\n"
            "/plan ETH_USDT lev=10 risk=2 deposit=5000\n"
            "   → with custom parameters\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — scan top-{top_n} coins (~2–4 min)\n"
            "   → shows only setups above confidence threshold\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — full market overview right now\n"
            "   → high / medium confidence + skipped\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>PARAMETERS</b>\n"
            "<code>deposit</code> — deposit in USDT (now: {deposit})\n"
            "<code>risk</code>    — % risk per trade (now: {risk}%)\n"
            "<code>lev</code>     — leverage (now: {lev}x)\n"
            "<code>margin</code>  — margin type: cross / isolated\n\n"
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
        "plan_loading":    "⏳ Loading {symbol}...",
        "plan_error":      "❌ Error: {error}",
        "plan_usage":      "Usage: /plan BTC_USDT [lev=20 risk=1 deposit=3000]",
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
            "   → Plan mit Standardparametern\n"
            "/plan ETH_USDT lev=10 risk=2 deposit=5000\n"
            "   → mit eigenen Parametern\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — Top-{top_n} Coins scannen (~2–4 Min)\n"
            "   → nur Setups über dem Konfidenzschwellenwert\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — vollständige Marktübersicht jetzt\n"
            "   → hohe / mittlere Konfidenz + übersprungen\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>PARAMETER</b>\n"
            "<code>deposit</code> — Kapital in USDT (aktuell: {deposit})\n"
            "<code>risk</code>    — Risiko-% pro Trade (aktuell: {risk}%)\n"
            "<code>lev</code>     — Hebel (aktuell: {lev}x)\n"
            "<code>margin</code>  — Margin-Typ: cross / isolated\n\n"
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
        "plan_loading":    "⏳ Lade {symbol}...",
        "plan_error":      "❌ Fehler: {error}",
        "plan_usage":      "Verwendung: /plan BTC_USDT [lev=20 risk=1 deposit=3000]",
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
            "   → plan avec paramètres par défaut\n"
            "/plan ETH_USDT lev=10 risk=2 deposit=5000\n"
            "   → avec paramètres personnalisés\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>SCAN</b>\n"
            "/scan — scanner le top {top_n} (~2–4 min)\n"
            "   → uniquement les setups au-dessus du seuil\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — vue d'ensemble du marché maintenant\n"
            "   → haute / moyenne confiance + ignorés\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>PARAMÈTRES</b>\n"
            "<code>deposit</code> — dépôt en USDT (actuel : {deposit})\n"
            "<code>risk</code>    — % de risque par trade (actuel : {risk}%)\n"
            "<code>lev</code>     — levier (actuel : {lev}x)\n"
            "<code>margin</code>  — type de marge : cross / isolated\n\n"
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
        "plan_loading":    "⏳ Chargement de {symbol}...",
        "plan_error":      "❌ Erreur : {error}",
        "plan_usage":      "Utilisation : /plan BTC_USDT [lev=20 risk=1 deposit=3000]",
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
            "   → plan con parámetros por defecto\n"
            "/plan ETH_USDT lev=10 risk=2 deposit=5000\n"
            "   → con parámetros personalizados\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔍 <b>ESCANEO</b>\n"
            "/scan — escanear top {top_n} monedas (~2–4 min)\n"
            "   → solo setups sobre el umbral de confianza\n\n"
            "📊 <b>DIGEST</b>\n"
            "/digest — resumen completo del mercado ahora\n"
            "   → confianza alta / media + omitidos\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "⚙️ <b>PARÁMETROS</b>\n"
            "<code>deposit</code> — depósito en USDT (actual: {deposit})\n"
            "<code>risk</code>    — % de riesgo por trade (actual: {risk}%)\n"
            "<code>lev</code>     — apalancamiento (actual: {lev}x)\n"
            "<code>margin</code>  — tipo de margen: cross / isolated\n\n"
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
        "plan_loading":    "⏳ Cargando {symbol}...",
        "plan_error":      "❌ Error: {error}",
        "plan_usage":      "Uso: /plan BTC_USDT [lev=20 risk=1 deposit=3000]",
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
