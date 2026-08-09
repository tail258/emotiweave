from __future__ import annotations

import json
import threading
from datetime import datetime
from typing import Any

from sentientbot.config import PrivacyConfig
from sentientbot.models import AffectState


class SessionLogger:
    def __init__(self, config: PrivacyConfig) -> None:
        self.config = config
        self._lock = threading.Lock()

    def write(
        self,
        event: str,
        state: AffectState,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not self.config.log_events:
            return
        now = datetime.now().astimezone()
        record = {
            "time": now.isoformat(timespec="milliseconds"),
            "event": event,
            "affect": state.as_dict(),
            "payload": payload or {},
        }
        self.config.log_directory.mkdir(parents=True, exist_ok=True)
        path = self.config.log_directory / f"{now:%Y-%m-%d}.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
