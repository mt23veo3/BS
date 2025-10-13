from __future__ import annotations
import os, re, sys
from typing import Any, Dict, Optional

try:
    from .discord_bot import send_text, send_action, send_signal
except Exception:
    from discord_bot import send_text, send_action, send_signal

NUM = r'[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?'

class Notifier:
    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}
        self.webhook_url = ((self.cfg.get("discord") or {}).get("webhook_url")
                            or os.getenv("DISCORD_WEBHOOK_URL") or "")
        self.enable_parse = (os.getenv("DISCORD_PARSE_ACTION_FROM_TEXT","1") == "1")

    def enabled(self): return bool(self.webhook_url)

    def signal(self, entry_signal: Dict[str, Any]) -> bool:
        if not self.enabled():
            print("[DISCORD] webhook rỗng", file=sys.stderr); return False
        try:
            ok = send_signal(self.webhook_url, entry_signal)
            if not ok: print("[DISCORD] send signal fail", file=sys.stderr)
            return ok
        except Exception as e:
            print(f"[DISCORD] Lỗi signal: {e}", file=sys.stderr); return False

    def _send_text(self, content: str) -> bool:
        if not self.enabled(): return False
        try:
            ok = send_text(self.webhook_url, content)
            if not ok: print("[DISCORD] send text fail", file=sys.stderr)
            return ok
        except Exception as e:
            print(f"[DISCORD] Lỗi text: {e}", file=sys.stderr); return False

    def send(self, content: str) -> bool: return self._send_text(str(content))
    def text(self, content: str) -> bool: return self._send_text(str(content))
    def info(self, content: str) -> bool: return self._send_text(f"[INFO] {content}")
    def warn(self, content: str) -> bool: return self._send_text(f"[WARN] {content}")
    def error(self, content: str) -> bool: return self._send_text(f"[ERROR] {content}")

    def send_file(self, file_path: str, content: str="Báo cáo cuối ngày"):
        if not self.enabled(): return False
        try:
            from utils import send_file_to_discord
            ok = send_file_to_discord(self.webhook_url, file_path, content)
            if not ok: print("[DISCORD] send file fail", file=sys.stderr)
            return ok
        except Exception as e:
            print(f"[DISCORD] Lỗi gửi file: {e}", file=sys.stderr)
            return False

__all__=["Notifier"]
