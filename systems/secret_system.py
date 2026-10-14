"""Registro global de secretos.

Los secretos son globales (no por mapa) para que en el futuro puedan
guardarse y para que un secreto de una zona afecte a otra.

    secrets.register("arken_shrine", name="Santuario oculto")
    secrets.is_unlocked("arken_shrine")   -> False
    secrets.unlock("arken_shrine")        -> True la primera vez
"""


class SecretSystem:
    def __init__(self):
        self._secrets = {}      # id -> {"name", "unlock_message", "unlocked"}
        self._listeners = []

    def register(self, secret_id, name="", unlock_message=None):
        entry = self._secrets.setdefault(secret_id, {"unlocked": False})
        entry["name"] = name or secret_id
        entry["unlock_message"] = unlock_message

    def add_listener(self, callback):
        """callback(secret_id, info) al desbloquearse un secreto."""
        self._listeners.append(callback)

    def is_unlocked(self, secret_id):
        return self._secrets.get(secret_id, {}).get("unlocked", False)

    def unlock(self, secret_id):
        entry = self._secrets.setdefault(secret_id, {"name": secret_id, "unlock_message": None,
                                                     "unlocked": False})
        if entry["unlocked"]:
            return False
        entry["unlocked"] = True
        for cb in self._listeners:
            cb(secret_id, entry)
        return True

    def status(self):
        return {sid: e["unlocked"] for sid, e in self._secrets.items()}

    # --- Guardado futuro ----------------------------------------------------
    def get_state(self):
        return [sid for sid, e in self._secrets.items() if e["unlocked"]]

    def set_state(self, unlocked_ids):
        for sid in unlocked_ids:
            self._secrets.setdefault(sid, {"name": sid, "unlock_message": None})["unlocked"] = True
