import time
from datetime import datetime


class DemoApi:
    def ping(self) -> dict:
        return {
            "ok": True,
            "message": "pong",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def echo(self, text: str) -> dict:
        return {
            "input": text,
            "length": len(text or ""),
        }

    def fake_job(self, seconds: int = 2) -> dict:
        seconds = max(0, min(int(seconds), 10))
        time.sleep(seconds)
        return {
            "done": True,
            "waited_seconds": seconds,
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
