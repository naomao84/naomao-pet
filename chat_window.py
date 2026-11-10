#!/usr/bin/env python3
"""
Floating Executive AI Chat & History Drawer for Ppong-ppong-i
============================================================
A top-level, glassmorphic dark-slate floating window that:
  - Floats independently on top (NEVER occluded behind the 3D character)
  - Records full chat history with timestamps and persistent storage (chat_history.json)
  - Allows one-click "이어서 작업하기" (Reuse / Continue Prompt) from past messages
  - Provides instant quick-action recommendation chips (낚시, 캠핑, 커피, 집짓기, Outlook, PC 정리 등)
  - Docks smoothly beside the 3D pet window with screen boundary safety
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

if getattr(sys, "frozen", False):
    _DATA_DIR = Path(sys.executable).resolve().parent
else:
    _DATA_DIR = Path(__file__).resolve().parent
CHAT_HISTORY_FILE = _DATA_DIR / "chat_history.json"

# Premium Slate Palette
COLOR_BG_DEEP = "#030712"       # Slate 950 deep obsidian
COLOR_SURFACE = "#0f172a"       # Slate 900
COLOR_SURFACE_LIGHT = "#1e293b" # Slate 800
COLOR_BORDER = "rgba(148, 163, 184, 0.16)"
COLOR_ACCENT = "#38bdf8"        # Sky 400
COLOR_ACCENT_HOVER = "#0284c7"  # Sky 600
COLOR_TEXT_MAIN = "#f8fafc"     # Slate 50
COLOR_TEXT_MUTED = "#94a3b8"    # Slate 400


class ChatHistoryManager:
    """Handles thread-safe persistence and querying of chat history."""

    def __init__(self, file_path: Path = CHAT_HISTORY_FILE) -> None:
        self.file_path = file_path
        self._history: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._history[-120:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_message(self, role: str, text: str, action: str = "") -> dict[str, Any]:
        entry = {
            "id": f"msg_{int(time.time() * 1000)}",
            "role": role,  # "user" or "pet"
            "text": text.strip(),
            "action": action,
            "time": datetime.now().strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후"),
        }
        self._history.append(entry)
        self.save()
        return entry

    def get_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def clear(self) -> None:
        self._history.clear()
        self.save()


class ChatBubbleWidget(QFrame):
    """Clean bubble card representing a single message in the history timeline."""

    reuse_clicked = pyqtSignal(str)

    def __init__(self, data: dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.data = data
        self._init_ui()

    def _init_ui(self) -> None:
        is_user = self.data.get("role") == "user"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header: Role Badge + Time
        header = QHBoxLayout()
        header.setSpacing(6)

        badge_txt = "👤 나" if is_user else "🦄 뽕뽕이"
        badge_color = "#38bdf8" if is_user else "#a855f7"
        lbl_badge = QLabel(badge_txt, self)
        lbl_badge.setStyleSheet(f"color: {badge_color}; font-weight: bold; font-size: 11px;")
        header.addWidget(lbl_badge)

        lbl_time = QLabel(self.data.get("time", ""), self)
        lbl_time.setStyleSheet("color: #64748b; font-size: 10px;")
        header.addWidget(lbl_time, stretch=1)

        if is_user:
            btn_reuse = QPushButton("이어서 작업 ↵", self)
            btn_reuse.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_reuse.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(56, 189, 248, 0.12);
                    color: #38bdf8;
                    border: 1px solid rgba(56, 189, 248, 0.28);
                    border-radius: 6px;
                    padding: 2px 7px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #38bdf8;
                    color: #020617;
                }
                """
            )
            btn_reuse.clicked.connect(lambda: self.reuse_clicked.emit(self.data.get("text", "")))
            header.addWidget(btn_reuse)

        layout.addLayout(header)

        # Message Text
        lbl_text = QLabel(self.data.get("text", ""), self)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet(
            f"color: {COLOR_TEXT_MAIN}; font-size: 12px; line-height: 140%;"
            if is_user else
            "color: #e2e8f0; font-size: 12px; line-height: 140%;"
        )
        layout.addWidget(lbl_text)

        bg = "#1e293b" if is_user else "#0f172a"
        border = "rgba(56, 189, 248, 0.35)" if is_user else "rgba(148, 163, 184, 0.14)"
        self.setStyleSheet(
            f"""
            ChatBubbleWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            """
        )


class FloatingChatWindow(QWidget):
    """
    Top-Level Glassmorphic Chat & History Drawer.
    Floats completely above the 3D pet window with zero occlusion.
    """

    message_submitted = pyqtSignal(str)
    mail_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    alarm_requested = pyqtSignal()
    cleanup_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.history_mgr = ChatHistoryManager()
        self._drag_pos = QPoint()
        self._history_visible = True

        self._init_window()
        self._init_ui()
        self._load_recent_history()

    def _init_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(420, 560)
        self.setWindowTitle("Ppong-ppong-i AI Assistant")

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame(self)
        self.container.setObjectName("MainFrame")
        self.container.setStyleSheet(
            f"""
            QFrame#MainFrame {{
                background-color: {COLOR_BG_DEEP};
                border: 1.5px solid rgba(148, 163, 184, 0.22);
                border-radius: 16px;
            }}
            QLabel {{
                color: {COLOR_TEXT_MAIN};
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
            QLineEdit {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 12px;
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {COLOR_ACCENT};
                background-color: #0b1120;
            }}
            QPushButton {{
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
            """
        )

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.setSpacing(10)

        # 1. Header Toolbar (Draggable)
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl_title = QLabel("💬 뽕뽕이 AI 어시스턴트", self.container)
        lbl_title.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        header.addWidget(lbl_title)

        lbl_status = QLabel("● 온라인", self.container)
        lbl_status.setStyleSheet("color: #34d399; font-size: 10px; font-weight: bold;")
        header.addWidget(lbl_status, stretch=1)

        # Toolbar Actions
        btn_hist = self._create_icon_btn("📜", "대화 기록 토글", self._toggle_history)
        btn_mail = self._create_icon_btn("📬", "Outlook 메일 허브", self.mail_requested.emit)
        btn_alarm = self._create_icon_btn("⏰", "스마트 알람 관리", self.alarm_requested.emit)
        btn_clean = self._create_icon_btn("🧹", "PC 환경 정리", self.cleanup_requested.emit)
        btn_close = self._create_icon_btn("✕", "닫기", self.hide)
        btn_close.setStyleSheet("QPushButton { color: #ef4444; font-weight: bold; font-size: 13px; }")

        for b in [btn_hist, btn_mail, btn_alarm, btn_clean, btn_close]:
            header.addWidget(b)

        c_layout.addLayout(header)

        # 2. Quick Suggestion Action Chips Bar
        chips_scroll = QScrollArea(self.container)
        chips_scroll.setFixedHeight(38)
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        chips_widget = QWidget()
        chips_widget.setStyleSheet("background: transparent;")
        chips_layout = QHBoxLayout(chips_widget)
        chips_layout.setContentsMargins(0, 2, 0, 2)
        chips_layout.setSpacing(6)

        quick_actions = [
            ("🎣 낚시", "낚시해줘"),
            ("🏕️ 캠핑", "캠핑 가자"),
            ("☕ 커피 드립", "커피 내려줘"),
            ("🏠 집짓기", "집 지어줘"),
            ("🎸 기타 연주", "기타 쳐봐"),
            ("📬 메일 확인", "메일 확인해줘"),
            ("⏰ 알람 목록", "알람 목록 보여줘"),
            ("🧹 PC 청소", "컴퓨터 청소해줘"),
        ]

        for label, cmd in quick_actions:
            chip_btn = QPushButton(label, chips_widget)
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(30, 41, 59, 0.7);
                    color: #cbd5e1;
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(56, 189, 248, 0.2);
                    color: #38bdf8;
                    border-color: #38bdf8;
                }
                """
            )
            chip_btn.clicked.connect(lambda _c, c=cmd: self._send_command_direct(c))
            chips_layout.addWidget(chip_btn)

        chips_scroll.setWidget(chips_widget)
        c_layout.addWidget(chips_scroll)

        # 3. Chat History & Conversation Feed
        self.history_area = QScrollArea(self.container)
        self.history_area.setWidgetResizable(True)
        self.history_area.setStyleSheet(
            """
            QScrollArea {
                background-color: #0b1120;
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 12px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
            """
        )

        self.history_container = QWidget()
        self.history_container.setStyleSheet("background: transparent;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(8, 8, 8, 8)
        self.history_layout.setSpacing(8)
        self.history_layout.addStretch()

        self.history_area.setWidget(self.history_container)
        c_layout.addWidget(self.history_area, stretch=1)

        # 4. Input Area (Pill Input + Send Button)
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_edit = QLineEdit(self.container)
        self.input_edit.setPlaceholderText("💬 뽕뽕이에게 질문이나 작업을 입력하세요... (Enter)")
        self.input_edit.returnPressed.connect(self._on_submit)
        input_row.addWidget(self.input_edit, stretch=1)

        self.send_btn = QPushButton("전송 ↵", self.container)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                color: #020617;
                border: none;
                border-radius: 10px;
                padding: 9px 15px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7dd3fc;
            }}
            QPushButton:disabled {{
                background-color: #1e293b;
                color: #64748b;
            }}
            """
        )
        self.send_btn.clicked.connect(self._on_submit)
        input_row.addWidget(self.send_btn)

        c_layout.addLayout(input_row)
        outer.addWidget(self.container)

    def _create_icon_btn(self, text: str, tip: str, callback) -> QPushButton:
        btn = QPushButton(text, self.container)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(30, 41, 59, 0.6);
                color: #94a3b8;
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #f8fafc;
                border-color: #38bdf8;
            }
            """
        )
        btn.clicked.connect(callback)
        return btn

    def _load_recent_history(self) -> None:
        messages = self.history_mgr.get_messages(30)
        for msg in messages:
            self._append_bubble(msg)

    def _append_bubble(self, data: dict[str, Any]) -> None:
        bubble = ChatBubbleWidget(data, self.history_container)
        bubble.reuse_clicked.connect(self.populate_prompt)
        # Insert before stretch
        self.history_layout.insertWidget(self.history_layout.count() - 1, bubble)
        # Auto scroll to bottom
        QGuiApplication.processEvents()
        self.history_area.verticalScrollBar().setValue(self.history_area.verticalScrollBar().maximum())

    def populate_prompt(self, text: str) -> None:
        """Populates the input bar with selected past prompt and focuses for immediate continuation."""
        self.input_edit.setText(text)
        self.input_edit.setFocus()
        self.input_edit.selectAll()

    def add_message(self, role: str, text: str, action: str = "") -> None:
        entry = self.history_mgr.add_message(role, text, action)
        self._append_bubble(entry)

    def _on_submit(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        self.input_edit.clear()
        self.add_message("user", text)
        self.message_submitted.emit(text)

    def _send_command_direct(self, cmd: str) -> None:
        self.add_message("user", cmd)
        self.message_submitted.emit(cmd)

    def _toggle_history(self) -> None:
        self._history_visible = not self._history_visible
        self.history_area.setVisible(self._history_visible)

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.input_edit.setEnabled(not busy)
        if not busy:
            self.input_edit.setFocus()

    def show_beside_pet(self, pet_geo: QRect) -> None:
        """Docks gracefully adjacent to the pet without any occlusion."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()

        # Try right side first
        target_x = pet_geo.right() + 14
        if target_x + w > screen.right():
            # Place on left side
            target_x = pet_geo.left() - w - 14

        # Vertically align with pet bottom
        target_y = pet_geo.bottom() - h + 30
        target_y = max(screen.top() + 10, min(screen.bottom() - h - 10, target_y))
        target_x = max(screen.left() + 10, min(screen.right() - w - 10, target_x))

        self.move(int(target_x), int(target_y))
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus()

    def toggle_visibility_beside(self, pet_geo: QRect) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_beside_pet(pet_geo)

    # Window Dragging
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = QPoint()

