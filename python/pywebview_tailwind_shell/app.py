from pathlib import Path

import webview

from pywebview_tailwind_shell.backend.api import AppApi


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    entry = base_dir / "frontend" / "index.html"
    api = AppApi()

    window = webview.create_window(
        title="TotalSeg AI - WebView Shell",
        url=entry.as_uri(),
        js_api=api,
        maximized=True,
        min_size=(1280, 780),
    )

    def _on_closed(*_args):
        api.shutdown()

    window.events.closed += _on_closed
    webview.start()


if __name__ == "__main__":
    main()
