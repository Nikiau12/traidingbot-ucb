import json
import os
import time
from typing import Dict, Tuple


class AccessManager:
    def __init__(
        self,
        state_file: str,
        free_trial_signals: int,
        paid_access_hours: int,
        payment_address: str,
        payment_amount: str,
        payment_network: str,
    ):
        self.state_file = state_file
        self.free_trial_signals = free_trial_signals
        self.paid_access_seconds = paid_access_hours * 60 * 60
        self.payment_address = payment_address
        self.payment_amount = payment_amount
        self.payment_network = payment_network

    def ensure_user(self, chat_id: str):
        state = self._load()
        user = self._user(state, chat_id)
        user.setdefault("trial_used", 0)
        user.setdefault("paid_until", 0)
        user.setdefault("paywall_sent", False)
        self._save(state)

    def can_receive(self, chat_id: str) -> bool:
        user = self._user(self._load(), chat_id)
        return self._has_paid_access(user) or user.get("trial_used", 0) < self.free_trial_signals

    def consume_signal(self, chat_id: str) -> Tuple[bool, str]:
        state = self._load()
        user = self._user(state, chat_id)

        if self._has_paid_access(user):
            self._save(state)
            return True, "paid"

        trial_used = user.get("trial_used", 0)
        if trial_used < self.free_trial_signals:
            user["trial_used"] = trial_used + 1
            user["paywall_sent"] = False
            self._save(state)
            return True, "trial"

        self._save(state)
        return False, "paywall"

    def should_send_paywall(self, chat_id: str) -> bool:
        state = self._load()
        user = self._user(state, chat_id)
        if user.get("paywall_sent"):
            self._save(state)
            return False
        user["paywall_sent"] = True
        self._save(state)
        return True

    def find_payment_by_tx_hash(self, tx_hash: str, exclude_chat_id: str = None):
        normalized = str(tx_hash).lower()
        for chat_id, user in self._load().get("users", {}).items():
            claims = list(user.get("payment_claims") or [])
            legacy_claim = user.get("last_payment_claim") or {}
            if legacy_claim and not claims:
                claims.append(legacy_claim)
            for claim in claims:
                if str(claim.get("tx_hash", "")).lower() == normalized and str(chat_id) != str(exclude_chat_id):
                    return {"chat_id": str(chat_id), **claim}
        return None

    def record_payment_claim(self, chat_id: str, tx_hash: str, **details) -> dict:
        state = self._load()
        user = self._user(state, chat_id)
        claim = {
            "tx_hash": tx_hash,
            "status": "pending",
            "created_at": int(time.time()),
            **details,
        }
        user["last_payment_claim"] = claim
        user.setdefault("payment_claims", []).append(claim)
        user["paywall_sent"] = False
        self._save(state)
        return claim

    def grant_access(self, chat_id: str, hours: int = None) -> int:
        state = self._load()
        user = self._user(state, chat_id)
        duration = (hours * 60 * 60) if hours else self.paid_access_seconds
        paid_until = int(max(time.time(), user.get("paid_until", 0)) + duration)
        user["paid_until"] = paid_until
        user["paywall_sent"] = False
        if user.get("last_payment_claim"):
            user["last_payment_claim"]["status"] = "approved"
            user["last_payment_claim"]["approved_at"] = int(time.time())
            approved_hash = user["last_payment_claim"].get("tx_hash")
            for claim in user.get("payment_claims", []):
                if claim.get("tx_hash") == approved_hash:
                    claim["status"] = "approved"
                    claim["approved_at"] = user["last_payment_claim"]["approved_at"]
        self._save(state)
        return paid_until

    def revoke_access(self, chat_id: str):
        state = self._load()
        user = self._user(state, chat_id)
        user["paid_until"] = 0
        self._save(state)

    def status(self, chat_id: str) -> dict:
        user = self._user(self._load(), chat_id)
        paid_until = user.get("paid_until", 0)
        return {
            "trial_used": user.get("trial_used", 0),
            "trial_left": max(0, self.free_trial_signals - user.get("trial_used", 0)),
            "paid_until": paid_until,
            "has_paid_access": paid_until > time.time(),
            "payment_claim": user.get("last_payment_claim"),
        }

    def format_paywall(self) -> str:
        wallet = self.payment_address or "кошелек пока не настроен админом"
        return (
            "🔒 <b>Бесплатные сигналы закончились</b>\n\n"
            f"У тебя было {self.free_trial_signals} бесплатных сигналов. "
            f"Чтобы получить доступ на {self.paid_access_seconds // 86400} дней, "
            f"переведи <b>{self.payment_amount} USDT</b>.\n\n"
            f"Сеть: <b>{self.payment_network}</b>\n"
            f"Кошелек:\n<code>{wallet}</code>\n\n"
            "После оплаты отправь:\n"
            "<code>/paid TX_HASH</code>\n\n"
            "Админ проверит транзакцию и включит доступ."
        )

    def _load(self) -> Dict:
        if not os.path.exists(self.state_file):
            return {"users": {}}
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            data.setdefault("users", {})
            return data
        except Exception as e:
            print(f"[AccessManager] failed to read state: {e}")
            return {"users": {}}

    def _save(self, state: Dict):
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[AccessManager] failed to write state: {e}")

    def _user(self, state: Dict, chat_id: str) -> Dict:
        users = state.setdefault("users", {})
        return users.setdefault(str(chat_id), {})

    def _has_paid_access(self, user: Dict) -> bool:
        return user.get("paid_until", 0) > time.time()
