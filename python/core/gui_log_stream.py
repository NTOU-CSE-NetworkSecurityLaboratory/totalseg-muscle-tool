from __future__ import annotations

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import QApplication


class GuiLogStreamController:
    def __init__(self, window):
        self.window = window

    def append_stream_log(self, text: str) -> None:
        clean = self.window.ansi_escape_re.sub("", text)
        if not clean:
            return
        self.window._append_case_excerpt(clean)
        self._consume_stream_text(clean)

    def _consume_stream_text(self, text: str) -> None:
        for ch in text:
            if ch == "\r":
                if self.window._stream_line_buffer:
                    self._render_ephemeral_line(self.window._stream_line_buffer)
                    self.window._stream_line_buffer = ""
                continue
            if ch == "\n":
                self._commit_stream_line(self.window._stream_line_buffer)
                self.window._stream_line_buffer = ""
                continue
            self.window._stream_line_buffer += ch

    def _replace_last_line(self, text: str) -> None:
        content = self.window.log_area.toPlainText()
        if not content:
            new_content = text
        elif content.endswith("\n"):
            new_content = content + text
        else:
            parts = content.rsplit("\n", 1)
            prefix = parts[0] + "\n" if len(parts) == 2 else ""
            new_content = prefix + text
        self.window.log_area.setPlainText(new_content)
        self.window.log_area.moveCursor(self.window.text_cursor_end)
        self.window._trim_log_area_if_needed()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def _render_ephemeral_line(self, text: str) -> None:
        if not text:
            return
        if self.window._ephemeral_active:
            self._replace_last_line(text)
            return

        existing = self.window.log_area.toPlainText()
        if existing and not existing.endswith("\n"):
            self.window.log_area.moveCursor(self.window.text_cursor_end)
            self.window.log_area.insertPlainText("\n")
        self.window.log_area.moveCursor(self.window.text_cursor_end)
        self.window.log_area.insertPlainText(text)
        self.window.log_area.moveCursor(self.window.text_cursor_end)
        self.window._ephemeral_active = True
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def _commit_stream_line(self, text: str) -> None:
        if self.window._ephemeral_active:
            if text:
                self._replace_last_line(text)
            self.window.log_area.moveCursor(self.window.text_cursor_end)
            self.window.log_area.insertPlainText("\n")
            self.window.log_area.moveCursor(self.window.text_cursor_end)
            self.window._ephemeral_active = False
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)
            return
        self.window.log_area.moveCursor(self.window.text_cursor_end)
        if text:
            self.window.log_area.insertPlainText(text)
        self.window.log_area.insertPlainText("\n")
        self.window.log_area.moveCursor(self.window.text_cursor_end)
        self.window._trim_log_area_if_needed()
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 5)

    def drain_process_output(self) -> None:
        if not hasattr(self.window.process, "readAll"):
            return
        chunk = bytes(self.window.process.readAll()).decode("utf8", errors="replace")
        if not chunk:
            return
        self.window._stream_buffer += chunk
        self.append_stream_log(self.window._stream_buffer)
        self.window._stream_buffer = ""

    def flush_pending(self) -> None:
        self.drain_process_output()
        if self.window._stream_buffer:
            self.append_stream_log(self.window._stream_buffer)
            self.window._stream_buffer = ""
        if self.window._stream_line_buffer:
            self._commit_stream_line(self.window._stream_line_buffer)
            self.window._stream_line_buffer = ""
        self.window._ephemeral_active = False
