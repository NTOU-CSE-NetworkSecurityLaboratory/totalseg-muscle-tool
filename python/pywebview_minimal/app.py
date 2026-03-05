from pathlib import Path

import webview

from backend.api import DemoApi


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    frontend_path = base_dir / "frontend" / "index.html"

    api = DemoApi()
    webview.create_window(
        title="PyWebView Minimal Demo",
        url=frontend_path.as_uri(),
        js_api=api,
        width=1000,
        height=700,
    )
    webview.start()


if __name__ == "__main__":
    main()
