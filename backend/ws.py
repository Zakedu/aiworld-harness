"""WebSocket 매니저 — Screen 2 실시간 이벤트 브로드캐스트."""
from __future__ import annotations
from collections import defaultdict
from fastapi import WebSocket
import json


class WSManager:
    def __init__(self):
        self._by_run: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, run_id: str, ws: WebSocket):
        await ws.accept()
        self._by_run[run_id].append(ws)

    def disconnect(self, run_id: str, ws: WebSocket):
        try:
            self._by_run[run_id].remove(ws)
        except ValueError:
            pass

    async def push(self, run_id: str, event_type: str, payload: dict):
        message = json.dumps({"event": event_type, "run_id": run_id, "payload": payload}, ensure_ascii=False)
        stale: list[WebSocket] = []
        for ws in list(self._by_run.get(run_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for s in stale:
            self.disconnect(run_id, s)


ws_manager = WSManager()
