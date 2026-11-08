"""
Visual 3D Alarm Dialog for Ppong-ppong-i Desktop Pet:
- Opens a frameless, high-fidelity 3D metallic alarm clock in the exact center of the screen.
- Features vibrating bells, sonic shockwave rings, stardust confetti, and audio chimes.
- Seamlessly communicates click actions via navigation interception ('alarm://dismiss', 'alarm://snooze').
- Provides instant text display via URL parameters and keyboard shortcuts (Esc/Enter/Space).
"""

from __future__ import annotations
import os
import sys
from urllib.parse import quote
from typing import Optional
from PyQt6.QtCore import QEventLoop, QObject, QPoint, QRect, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QKeyEvent, QPainter
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QDialog, QGraphicsDropShadowEffect, QPushButton, QWidget


class AlarmWebEnginePage(QWebEnginePage):
    """Intercepts custom 'alarm://' navigation requests for 100% reliable click feedback."""

    def __init__(self, dialog: "Visual3DAlarmDialog", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._dialog = dialog

    def acceptNavigationRequest(
        self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool
    ) -> bool:
        if url.scheme() == "alarm":
            action = url.host() or url.path().lstrip("/")
            if "dismiss" in action or "ok" in action:
                self._dialog.dismiss()
            elif "snooze" in action:
                self._dialog.snooze()
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class Visual3DAlarmDialog(QDialog):
    snooze_clicked = pyqtSignal(str)  # label

    def __init__(
        self,
        asset_server_port: int,
        label: str = "알람 시간이에요!",
        time_str: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.label = label
        self.time_str = time_str
        self.asset_server_port = asset_server_port

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setFixedSize(540, 480)

        # Center on primary desktop screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            cx = avail.left() + (avail.width() - self.width()) // 2
            cy = avail.top() + (avail.height() - self.height()) // 2
            self.move(cx, cy)

        # WebEngine setup with dedicated AlarmWebEnginePage
        self.web_view = QWebEngineView(self)
        self.web_view.setGeometry(0, 0, self.width(), self.height())
        self.web_view.setStyleSheet("background: transparent;")

        page = AlarmWebEnginePage(self, self.web_view)
        page.setBackgroundColor(QColor(0, 0, 0, 0))
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        self.web_view.setPage(page)

        self.web_view.page().loadFinished.connect(self._on_loaded)

        # Pass label and time directly in URL query params for instantaneous zero-latency display
        encoded_label = quote(self.label)
        encoded_time = quote(self.time_str)
        url = f"http://127.0.0.1:{self.asset_server_port}/alarm_3d.html?label={encoded_label}&time={encoded_time}"
        self.web_view.setUrl(QUrl(url))

        # Sleek Native Fallback Close Button in top-right corner
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setGeometry(self.width() - 48, 22, 28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.75);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 14px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 1.0);
                transform: scale(1.08);
            }
        """)
        self.close_btn.clicked.connect(self.dismiss)
        self.close_btn.raise_()

    def _on_loaded(self, ok: bool) -> None:
        # Also run secondary JavaScript update in case page was cached
        safe_label = self.label.replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
        safe_time = self.time_str.replace('"', '\\"').replace("'", "\\'")
        js = f"window.setAlarmDetails && window.setAlarmDetails('{safe_label}', '{safe_time}');"
        self.web_view.page().runJavaScript(js)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.dismiss()
        else:
            super().keyPressEvent(event)

    def dismiss(self) -> None:
        self.close()

    def snooze(self) -> None:
        self.snooze_clicked.emit(self.label)
        self.close()
