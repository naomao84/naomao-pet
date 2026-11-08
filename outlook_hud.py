#!/usr/bin/env python3
"""
Executive Outlook AI Mail Hub for Ppong-ppong-i
==============================================
A world-class, Microsoft 365 / Superhuman-inspired executive email client & AI briefing drawer:
  - Dynamic sender monogram avatars with color-hashed initials
  - Segmented dual-view: [⚡ AI 스마트 분석 & 실행 과제] vs [📄 이메일 원문 보기]
  - Real-time Outlook search & segmented filtering (전체, 읽지 않음, 긴급, 회의)
  - Action items / to-do checklist extraction with interactive checks
  - Detected meeting scheduler with one-click Outlook Calendar registration
  - 3-tone AI response draft generator (수락, 일정 조율, 세부 문의)
  - Direct Outlook interop: Open in Outlook desktop (item.Display()), Reply, Mark Read/Unread
  - Screen-safe magnetic docking to the 3D pet & draggable header bar
"""

from __future__ import annotations

import hashlib
from typing import Any, List, Optional

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from outlook_service import OutlookAIAssistantService, OutlookEmailItem

# Executive Midnight Palette
COLOR_BG_DEEP = "#080c14"       # Deep executive obsidian
COLOR_SURFACE = "#0f172a"       # Slate 900
COLOR_SURFACE_HOVER = "#1e293b" # Slate 800
COLOR_BORDER = "rgba(148, 163, 184, 0.16)"
COLOR_ACCENT = "#38bdf8"        # Sky 400
COLOR_ACCENT_BLUE = "#2563eb"   # Royal Blue 600
COLOR_TEXT_MAIN = "#f8fafc"     # Slate 50
COLOR_TEXT_MUTED = "#94a3b8"    # Slate 400
COLOR_TEXT_SUBTLE = "#64748b"   # Slate 500
COLOR_URGENT = "#ef4444"        # Red 500
COLOR_MEETING = "#10b981"       # Emerald 500

AVATAR_PALETTES = [
    ("#1e3a8a", "#93c5fd"), # Blue
    ("#4c1d95", "#c4b5fd"), # Purple
    ("#064e3b", "#a7f3d0"), # Emerald
    ("#831843", "#fbcfe8"), # Pink
    ("#7c2d12", "#fed7aa"), # Amber/Orange
    ("#164e63", "#a5f3fc"), # Cyan
]


def get_sender_avatar_colors(sender_name: str) -> tuple[str, str]:
    h = int(hashlib.md5(sender_name.encode("utf-8")).hexdigest(), 16)
    return AVATAR_PALETTES[h % len(AVATAR_PALETTES)]


def get_sender_initials(sender_name: str) -> str:
    cleaned = sender_name.strip()
    if not cleaned:
        return "M"
    parts = cleaned.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return cleaned[:2].upper()


class AvatarWidget(QFrame):
    """Circular monogram avatar for an executive email sender."""

    def __init__(self, sender_name: str, size: int = 36, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.sender_name = sender_name
        self.avatar_size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg_hex, fg_hex = get_sender_avatar_colors(self.sender_name)
        p.setBrush(QColor(bg_hex))
        p.setPen(QPen(QColor(fg_hex), 1.2))
        p.drawEllipse(1, 1, self.avatar_size - 2, self.avatar_size - 2)

        p.setPen(QColor(fg_hex))
        font_sz = max(9, int(self.avatar_size * 0.36))
        p.setFont(QFont("Malgun Gothic", font_sz, QFont.Weight.Bold))
        initials = get_sender_initials(self.sender_name)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        p.end()


class EmailCardWidget(QFrame):
    """Executive email preview card in the master list."""

    clicked = pyqtSignal(OutlookEmailItem)

    def __init__(self, item: OutlookEmailItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.item = item
        self._is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left Avatar
        self.avatar = AvatarWidget(self.item.sender_name, size=38, parent=self)
        main_layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignTop)

        # Middle Content
        content_vbox = QVBoxLayout()
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(3)

        # Row 1: Sender Name + Badges + Time
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_sender = QLabel(self.item.sender_name, self)
        f_sender = QFont("Malgun Gothic", 10, QFont.Weight.Bold if self.item.is_unread else QFont.Weight.DemiBold)
        self.lbl_sender.setFont(f_sender)
        self.lbl_sender.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; background: transparent;")
        top_row.addWidget(self.lbl_sender, stretch=1)

        if self.item.urgency_level == "urgent":
            lbl_urg = QLabel("긴급", self)
            lbl_urg.setStyleSheet("background-color: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;")
            top_row.addWidget(lbl_urg)

        if self.item.extracted_meeting:
            lbl_meet = QLabel("회의", self)
            lbl_meet.setStyleSheet("background-color: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;")
            top_row.addWidget(lbl_meet)

        # Time
        time_part = self.item.received_time.split(" ")[-1] if " " in self.item.received_time else self.item.received_time
        self.lbl_time = QLabel(time_part, self)
        self.lbl_time.setStyleSheet(f"color: {COLOR_TEXT_SUBTLE}; font-size: 10px; background: transparent;")
        top_row.addWidget(self.lbl_time)

        # Unread dot
        if self.item.is_unread:
            dot = QLabel("●", self)
            dot.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 8px; margin-left: 2px;")
            top_row.addWidget(dot)

        content_vbox.addLayout(top_row)

        # Row 2: Subject Line
        self.lbl_subject = QLabel(self.item.subject, self)
        f_sub = QFont("Malgun Gothic", 9, QFont.Weight.Medium if self.item.is_unread else QFont.Weight.Normal)
        self.lbl_subject.setFont(f_sub)
        self.lbl_subject.setWordWrap(False)
        self.lbl_subject.setStyleSheet(f"color: {COLOR_TEXT_MAIN if self.item.is_unread else COLOR_TEXT_MUTED}; background: transparent;")
        content_vbox.addWidget(self.lbl_subject)

        # Row 3: Preview Snippet
        snippet = self.item.body.strip().replace("\n", " ")[:60] + ("..." if len(self.item.body) > 60 else "")
        self.lbl_preview = QLabel(snippet, self)
        self.lbl_preview.setStyleSheet(f"color: {COLOR_TEXT_SUBTLE}; font-size: 10px; background: transparent;")
        content_vbox.addWidget(self.lbl_preview)

        main_layout.addLayout(content_vbox, stretch=1)
        self._update_style()

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_style()

    def _update_style(self) -> None:
        if self._is_selected:
            bg = "#1e293b"
            border = f"border-left: 3.5px solid {COLOR_ACCENT}; border-top: 1px solid rgba(56, 189, 248, 0.4); border-right: 1px solid rgba(56, 189, 248, 0.4); border-bottom: 1px solid rgba(56, 189, 248, 0.4);"
        else:
            bg = COLOR_SURFACE
            border = f"border: 1px solid {COLOR_BORDER};"

        self.setStyleSheet(
            f"""
            EmailCardWidget {{
                background-color: {bg};
                {border}
                border-radius: 10px;
            }}
            EmailCardWidget:hover {{
                background-color: {COLOR_SURFACE_HOVER};
                border-color: {COLOR_ACCENT};
            }}
            """
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item)
        super().mousePressEvent(event)


class OutlookHUDDrawer(QWidget):
    """
    Executive Windows 11 Fluent Outlook AI Mail Hub Drawer.
    """

    drawer_closed = pyqtSignal()
    calendar_action_triggered = pyqtSignal(str)

    def __init__(
        self,
        service: OutlookAIAssistantService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self._current_items: List[OutlookEmailItem] = []
        self._filtered_items: List[OutlookEmailItem] = []
        self._selected_item: Optional[OutlookEmailItem] = None
        self._filter_tab = "all"
        self._cards: list[EmailCardWidget] = []
        self._drag_pos = QPoint()

        self._init_window()
        self._init_ui()
        self._connect_signals()

        if hasattr(self.service, "cached_items") and self.service.cached_items:
            self._current_items = list(self.service.cached_items)
            self._apply_filters()

        self.service.refresh_inbox()

    def _init_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(840, 620)
        self.setWindowTitle("Outlook AI Mail Hub - Executive Edition")

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.main_container = QFrame(self)
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet(
            f"""
            QFrame#MainContainer {{
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
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 7px 11px;
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

        c_layout = QVBoxLayout(self.main_container)
        c_layout.setContentsMargins(14, 12, 14, 14)
        c_layout.setSpacing(10)

        # 1. Header Bar (Draggable)
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl_logo = QLabel("📬 Microsoft Outlook AI Executive Hub", self.main_container)
        lbl_logo.setFont(QFont("Malgun Gothic", 12, QFont.Weight.Bold))
        header.addWidget(lbl_logo)

        self.lbl_status = QLabel("● 동기화 완료", self.main_container)
        self.lbl_status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
        header.addWidget(self.lbl_status, stretch=1)

        btn_sync = QPushButton("🔄 메일함 새로고침", self.main_container)
        btn_sync.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sync.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #1e293b;
                border-color: {COLOR_ACCENT};
            }}
            """
        )
        btn_sync.clicked.connect(self._on_refresh_clicked)
        header.addWidget(btn_sync)

        btn_close = QPushButton("✕", self.main_container)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ef4444;
            }
            """
        )
        btn_close.clicked.connect(self.hide_drawer)
        header.addWidget(btn_close)

        c_layout.addLayout(header)

        # 2. Main Splitter (Left: Mail List, Right: Executive Detail Hub)
        splitter = QSplitter(Qt.Orientation.Horizontal, self.main_container)
        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background-color: rgba(148, 163, 184, 0.12);
                width: 1px;
            }
            """
        )

        # =========================================================
        # Left Pane: Search + Segmented Filter Pills + Mail List
        # =========================================================
        left_pane = QWidget(splitter)
        left_pane.setMinimumWidth(300)
        left_vbox = QVBoxLayout(left_pane)
        left_vbox.setContentsMargins(0, 0, 8, 0)
        left_vbox.setSpacing(8)

        # Search bar
        self.search_edit = QLineEdit(left_pane)
        self.search_edit.setPlaceholderText("🔍 보낸사람, 제목, 본문 검색...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        left_vbox.addWidget(self.search_edit)

        # Filter Pills Row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)

        self.btn_tab_all = self._create_filter_pill("전체", "all", True)
        self.btn_tab_unread = self._create_filter_pill("안 읽음", "unread", False)
        self.btn_tab_urgent = self._create_filter_pill("긴급 🔴", "urgent", False)
        self.btn_tab_meeting = self._create_filter_pill("회의 📅", "meeting", False)

        for b in [self.btn_tab_all, self.btn_tab_unread, self.btn_tab_urgent, self.btn_tab_meeting]:
            filter_row.addWidget(b)

        left_vbox.addLayout(filter_row)

        # Mail Cards Scroll Area
        self.scroll_area = QScrollArea(left_pane)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
            }
            """
        )

        self.card_list_container = QWidget()
        self.card_list_container.setStyleSheet("background: transparent;")
        self.card_list_layout = QVBoxLayout(self.card_list_container)
        self.card_list_layout.setContentsMargins(0, 2, 4, 2)
        self.card_list_layout.setSpacing(6)
        self.card_list_layout.addStretch()
        self.scroll_area.setWidget(self.card_list_container)

        left_vbox.addWidget(self.scroll_area, stretch=1)
        splitter.addWidget(left_pane)

        # =========================================================
        # Right Pane: Executive Detail View & AI Hub
        # =========================================================
        right_pane = QWidget(splitter)
        right_pane.setMinimumWidth(480)
        right_vbox = QVBoxLayout(right_pane)
        right_vbox.setContentsMargins(8, 0, 0, 0)
        right_vbox.setSpacing(8)

        # Header Profile & Actions
        self.detail_header_frame = QFrame(right_pane)
        self.detail_header_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
                padding: 8px;
            }}
            """
        )
        d_head_layout = QHBoxLayout(self.detail_header_frame)
        d_head_layout.setContentsMargins(8, 8, 8, 8)
        d_head_layout.setSpacing(10)

        # Sender Avatar Large
        self.detail_avatar = AvatarWidget("메일", size=44, parent=self.detail_header_frame)
        d_head_layout.addWidget(self.detail_avatar)

        # Sender & Subject Info
        meta_vbox = QVBoxLayout()
        meta_vbox.setSpacing(2)

        self.lbl_detail_sender = QLabel("메일을 선택해주세요", self.detail_header_frame)
        self.lbl_detail_sender.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        meta_vbox.addWidget(self.lbl_detail_sender)

        self.lbl_detail_subject = QLabel("선택된 메일의 제목이 여기에 표시됩니다.", self.detail_header_frame)
        self.lbl_detail_subject.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Medium))
        self.lbl_detail_subject.setWordWrap(True)
        self.lbl_detail_subject.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        meta_vbox.addWidget(self.lbl_detail_subject)

        d_head_layout.addLayout(meta_vbox, stretch=1)

        # Executive Action Toolbar
        action_vbox = QVBoxLayout()
        action_vbox.setSpacing(4)

        self.btn_open_outlook = QPushButton("✉ Outlook 앱에서 열기", self.detail_header_frame)
        self.btn_open_outlook.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_outlook.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_ACCENT_BLUE};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #1d4ed8;
            }}
            """
        )
        self.btn_open_outlook.clicked.connect(self._on_open_in_outlook_clicked)
        action_vbox.addWidget(self.btn_open_outlook)

        btn_toggle_read = QPushButton("🔄 읽음/안읽음 전환", self.detail_header_frame)
        btn_toggle_read.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_toggle_read.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_HOVER};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {COLOR_ACCENT};
            }}
            """
        )
        btn_toggle_read.clicked.connect(self._on_toggle_unread_clicked)
        action_vbox.addWidget(btn_toggle_read)

        d_head_layout.addLayout(action_vbox)
        right_vbox.addWidget(self.detail_header_frame)

        # Segmented View Switcher: [⚡ AI 스마트 분석] vs [📄 이메일 원문 보기]
        view_tabs_layout = QHBoxLayout()
        view_tabs_layout.setSpacing(6)

        self.btn_view_ai = QPushButton("⚡ AI 스마트 브리핑 & 실행 과제", right_pane)
        self.btn_view_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_body = QPushButton("📄 이메일 원문 보기", right_pane)
        self.btn_view_body.setCursor(Qt.CursorShape.PointingHandCursor)

        self._style_tab_btn(self.btn_view_ai, True)
        self._style_tab_btn(self.btn_view_body, False)

        self.btn_view_ai.clicked.connect(lambda: self._switch_detail_tab(0))
        self.btn_view_body.clicked.connect(lambda: self._switch_detail_tab(1))

        view_tabs_layout.addWidget(self.btn_view_ai)
        view_tabs_layout.addWidget(self.btn_view_body)
        view_tabs_layout.addStretch()
        right_vbox.addLayout(view_tabs_layout)

        # Stacked Widget for Detail Panes
        self.detail_stack = QStackedWidget(right_pane)

        # --- Sub-Pane 0: AI Smart Briefing & Actions ---
        pane_ai = QWidget()
        pane_ai_vbox = QVBoxLayout(pane_ai)
        pane_ai_vbox.setContentsMargins(0, 0, 0, 0)
        pane_ai_vbox.setSpacing(8)

        # 1. Executive Briefing Card
        self.card_briefing = QFrame(pane_ai)
        self.card_briefing.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-left: 3.5px solid {COLOR_ACCENT};
                border-radius: 10px;
                padding: 10px;
            }}
            """
        )
        briefing_vbox = QVBoxLayout(self.card_briefing)
        briefing_vbox.setContentsMargins(6, 6, 6, 6)
        briefing_vbox.setSpacing(6)

        lbl_b_title = QLabel("⚡ 핵심 브리핑 요약 (Executive Summary)", self.card_briefing)
        lbl_b_title.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        lbl_b_title.setStyleSheet(f"color: {COLOR_ACCENT};")
        briefing_vbox.addWidget(lbl_b_title)

        self.lbl_briefing_body = QLabel("좌측 목록에서 메일을 선택하면 AI가 핵심 요점과 조치 사항을 정리합니다.", self.card_briefing)
        self.lbl_briefing_body.setWordWrap(True)
        self.lbl_briefing_body.setStyleSheet("color: #e2e8f0; font-size: 11px; line-height: 150%;")
        briefing_vbox.addWidget(self.lbl_briefing_body)

        # Action Items Checklist
        self.lbl_actions_title = QLabel("📌 실행 과제 (Action Items Checklist)", self.card_briefing)
        self.lbl_actions_title.setFont(QFont("Malgun Gothic", 9, QFont.Weight.Bold))
        self.lbl_actions_title.setStyleSheet("color: #cbd5e1; margin-top: 4px;")
        briefing_vbox.addWidget(self.lbl_actions_title)

        self.actions_container = QWidget(self.card_briefing)
        self.actions_layout = QVBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(4)
        briefing_vbox.addWidget(self.actions_container)

        pane_ai_vbox.addWidget(self.card_briefing)

        # 2. Detected Meeting Schedule Box
        self.box_meeting = QFrame(pane_ai)
        self.box_meeting.setStyleSheet(
            """
            QFrame {
                background-color: rgba(6, 78, 59, 0.4);
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 10px;
                padding: 8px;
            }
            """
        )
        meet_layout = QHBoxLayout(self.box_meeting)
        meet_layout.setContentsMargins(8, 6, 8, 6)
        meet_layout.setSpacing(10)

        self.lbl_meet_info = QLabel("📅 감지된 회의 일정 정보", self.box_meeting)
        self.lbl_meet_info.setStyleSheet("color: #a7f3d0; font-size: 11px; font-weight: bold;")
        meet_layout.addWidget(self.lbl_meet_info, stretch=1)

        self.btn_calendar_reg = QPushButton("📅 Outlook 캘린더 자동 등록", self.box_meeting)
        self.btn_calendar_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calendar_reg.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_MEETING};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #059669;
            }}
            """
        )
        self.btn_calendar_reg.clicked.connect(self._on_add_calendar_clicked)
        meet_layout.addWidget(self.btn_calendar_reg)

        self.box_meeting.hide()
        pane_ai_vbox.addWidget(self.box_meeting)

        # 3. AI Quick Reply Generator Box
        box_reply = QFrame(pane_ai)
        box_reply.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 8px;
            }}
            """
        )
        reply_vbox = QVBoxLayout(box_reply)
        reply_vbox.setContentsMargins(6, 6, 6, 6)
        reply_vbox.setSpacing(6)

        lbl_r_title = QLabel("✍️ AI 스마트 회신 초안 생성 (Quick Response)", box_reply)
        lbl_r_title.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
        lbl_r_title.setStyleSheet("color: #cbd5e1;")
        reply_vbox.addWidget(lbl_r_title)

        tone_row = QHBoxLayout()
        tone_row.setSpacing(6)
        for tone_key, tone_label in [("accept", "수락 및 확인"), ("reschedule", "일정 조율 요청"), ("inquire", "세부 문의")]:
            btn_t = QPushButton(tone_label, box_reply)
            btn_t.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_t.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(30, 41, 59, 0.8);
                    color: #cbd5e1;
                    border: 1px solid rgba(148, 163, 184, 0.2);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                    color: #ffffff;
                    border-color: #38bdf8;
                }
                """
            )
            btn_t.clicked.connect(lambda _c, t=tone_key: self._generate_reply_draft(t))
            tone_row.addWidget(btn_t)

        reply_vbox.addLayout(tone_row)

        self.edit_reply_draft = QTextEdit(box_reply)
        self.edit_reply_draft.setPlaceholderText("상단 톤 버튼을 클릭하면 AI 회신 초안이 생성됩니다.")
        self.edit_reply_draft.setFixedHeight(80)
        self.edit_reply_draft.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: #0b1120;
                color: #e2e8f0;
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
            """
        )
        reply_vbox.addWidget(self.edit_reply_draft)

        draft_btn_row = QHBoxLayout()
        draft_btn_row.addStretch()

        btn_copy_draft = QPushButton("📋 초안 복사", box_reply)
        btn_copy_draft.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_draft.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_HOVER};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_ACCENT};
            }}
            """
        )
        btn_copy_draft.clicked.connect(self._on_copy_draft_clicked)
        draft_btn_row.addWidget(btn_copy_draft)

        btn_create_outlook_reply = QPushButton("✉ Outlook 회신창 열기", box_reply)
        btn_create_outlook_reply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create_outlook_reply.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_ACCENT_BLUE};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #1d4ed8;
            }}
            """
        )
        btn_create_outlook_reply.clicked.connect(self._on_open_outlook_reply_clicked)
        draft_btn_row.addWidget(btn_create_outlook_reply)

        reply_vbox.addLayout(draft_btn_row)
        pane_ai_vbox.addWidget(box_reply)

        self.detail_stack.addWidget(pane_ai)

        # --- Sub-Pane 1: Original Email Full Body View ---
        pane_body = QWidget()
        pane_body_vbox = QVBoxLayout(pane_body)
        pane_body_vbox.setContentsMargins(0, 0, 0, 0)

        self.edit_original_body = QTextEdit(pane_body)
        self.edit_original_body.setReadOnly(True)
        self.edit_original_body.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: {COLOR_SURFACE};
                color: #f1f5f9;
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 14px;
                font-size: 12px;
                line-height: 160%;
                font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            }}
            """
        )
        pane_body_vbox.addWidget(self.edit_original_body)
        self.detail_stack.addWidget(pane_body)

        right_vbox.addWidget(self.detail_stack, stretch=1)
        splitter.addWidget(right_pane)

        # Set splitter proportions (35% left, 65% right)
        splitter.setSizes([290, 510])
        c_layout.addWidget(splitter, stretch=1)
        outer_layout.addWidget(self.main_container)

    def _create_filter_pill(self, label: str, tab_id: str, is_active: bool) -> QPushButton:
        btn = QPushButton(label, self.main_container)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_pill_btn(btn, is_active)
        btn.clicked.connect(lambda: self._set_filter_tab(tab_id))
        return btn

    def _style_pill_btn(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLOR_ACCENT_BLUE};
                    color: #ffffff;
                    border: 1px solid {COLOR_ACCENT};
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                """
            )
        else:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(30, 41, 59, 0.6);
                    color: #94a3b8;
                    border: 1px solid rgba(148, 163, 184, 0.18);
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: #1e293b;
                    color: #f8fafc;
                }}
                """
            )

    def _style_tab_btn(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(56, 189, 248, 0.16);
                    color: {COLOR_ACCENT};
                    border: 1px solid rgba(56, 189, 248, 0.35);
                    border-radius: 8px;
                    padding: 5px 12px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                """
            )
        else:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    color: #94a3b8;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding: 5px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(30, 41, 59, 0.5);
                    color: #e2e8f0;
                }
                """
            )

    def _switch_detail_tab(self, index: int) -> None:
        self.detail_stack.setCurrentIndex(index)
        self._style_tab_btn(self.btn_view_ai, index == 0)
        self._style_tab_btn(self.btn_view_body, index == 1)

    def _connect_signals(self) -> None:
        self.service.emails_updated.connect(self._on_emails_updated)
        self.service.calendar_registered.connect(self._on_calendar_registered)

    def _on_emails_updated(self, items: List[OutlookEmailItem], is_live: bool, msg: str) -> None:
        self._current_items = items
        live_tag = "실시간 Outlook 연동" if is_live else "보안 캐시 모드"
        self.lbl_status.setText(f"● {live_tag} ({len(items)}건)")
        self._apply_filters()

    def _on_calendar_registered(self, item_id: str, message: str) -> None:
        self.btn_calendar_reg.setText("✓ 등록 완료!")
        self.btn_calendar_reg.setEnabled(False)
        self.btn_calendar_reg.setStyleSheet("background-color: #047857; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-size: 11px;")

    def _set_filter_tab(self, tab_id: str) -> None:
        self._filter_tab = tab_id
        self._style_pill_btn(self.btn_tab_all, tab_id == "all")
        self._style_pill_btn(self.btn_tab_unread, tab_id == "unread")
        self._style_pill_btn(self.btn_tab_urgent, tab_id == "urgent")
        self._style_pill_btn(self.btn_tab_meeting, tab_id == "meeting")
        self._apply_filters()

    def _on_search_changed(self) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = self.search_edit.text().strip().lower()
        res = self._current_items

        if self._filter_tab == "unread":
            res = [it for it in res if it.is_unread]
        elif self._filter_tab == "urgent":
            res = [it for it in res if it.urgency_level == "urgent"]
        elif self._filter_tab == "meeting":
            res = [it for it in res if it.extracted_meeting]

        if query:
            res = [
                it for it in res
                if query in it.sender_name.lower() or query in it.subject.lower() or query in it.body.lower()
            ]

        self._filtered_items = res
        self._rebuild_card_list()

    def _rebuild_card_list(self) -> None:
        for card in self._cards:
            self.card_list_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        for item in self._filtered_items:
            card = EmailCardWidget(item, self.card_list_container)
            card.clicked.connect(self._on_card_clicked)
            if self._selected_item and item.id == self._selected_item.id:
                card.set_selected(True)
            self._cards.append(card)
            self.card_list_layout.insertWidget(self.card_list_layout.count() - 1, card)

        if not self._selected_item and self._filtered_items:
            self._on_card_clicked(self._filtered_items[0])

    def _on_card_clicked(self, item: OutlookEmailItem) -> None:
        self._selected_item = item
        for c in self._cards:
            c.set_selected(c.item.id == item.id)

        # Update Detail View
        self.detail_avatar.sender_name = item.sender_name
        self.detail_avatar.update()

        self.lbl_detail_sender.setText(f"{item.sender_name} <{item.sender_email}>")
        self.lbl_detail_subject.setText(item.subject)

        # AI Briefing
        summary_txt = item.ai_summary or "AI 요약 생성 중..."
        self.lbl_briefing_body.setText(summary_txt)

        # Clear and populate action items
        for i in reversed(range(self.actions_layout.count())):
            w = self.actions_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if item.ai_action_items:
            self.lbl_actions_title.show()
            for act in item.ai_action_items:
                chk = QCheckBox(act, self.actions_container)
                chk.setStyleSheet("QCheckBox { color: #cbd5e1; font-size: 11px; } QCheckBox::indicator:checked { background: #38bdf8; }")
                self.actions_layout.addWidget(chk)
        else:
            self.lbl_actions_title.hide()

        # Meeting Box
        if item.extracted_meeting:
            m = item.extracted_meeting
            desc = f"📅 {m.get('date', '')} {m.get('time', '')} - {m.get('topic', '미팅')}"
            self.lbl_meet_info.setText(desc)
            self.box_meeting.show()
        else:
            self.box_meeting.hide()

        # Original Body Text
        self.edit_original_body.setPlainText(
            f"보낸 사람: {item.sender_name} <{item.sender_email}>\n"
            f"받은 날짜: {item.received_time}\n"
            f"메일 제목: {item.subject}\n"
            f"중요도: {'높음' if item.importance == 2 else '보통'}\n"
            f"{'-' * 60}\n\n"
            f"{item.body}"
        )

        # Reset reply draft
        self.edit_reply_draft.clear()

    def _on_refresh_clicked(self) -> None:
        self.lbl_status.setText("● 동기화 진행 중...")
        self.service.refresh_inbox()

    def _on_open_in_outlook_clicked(self) -> None:
        if self._selected_item:
            self.service.display_email_item(self._selected_item.id)

    def _on_toggle_unread_clicked(self) -> None:
        if self._selected_item:
            self.service.toggle_unread_status(self._selected_item.id)
            self._selected_item.is_unread = not self._selected_item.is_unread
            self._apply_filters()

    def _on_add_calendar_clicked(self) -> None:
        if self._selected_item:
            self.service.add_meeting_to_calendar(self._selected_item.id)

    def _on_calendar_added(self, item_id: str, success: bool) -> None:
        if success:
            self.btn_calendar_reg.setText("✓ 등록 완료!")
            self.btn_calendar_reg.setEnabled(False)
            self.btn_calendar_reg.setStyleSheet("background-color: #047857; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-size: 11px;")

    def _generate_reply_draft(self, tone: str) -> None:
        if not self._selected_item:
            return
        draft = self.service.generate_reply_draft(self._selected_item.id, tone)
        self.edit_reply_draft.setPlainText(draft)

    def _on_copy_draft_clicked(self) -> None:
        txt = self.edit_reply_draft.toPlainText().strip()
        if txt:
            QApplication.clipboard().setText(txt)
            self.lbl_status.setText("✓ 클립보드에 초안 복사 완료!")

    def _on_open_outlook_reply_clicked(self) -> None:
        if self._selected_item:
            txt = self.edit_reply_draft.toPlainText().strip()
            self.service.create_outlook_reply(self._selected_item.id, txt)

    def show_beside_pet(self, pet_geo: QRect) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()

        target_x = pet_geo.right() + 16
        if target_x + w > screen.right():
            target_x = pet_geo.left() - w - 16

        target_y = pet_geo.bottom() - h + 40
        target_y = max(screen.top() + 10, min(screen.bottom() - h - 10, target_y))
        target_x = max(screen.left() + 10, min(screen.right() - w - 10, target_x))

        self.move(int(target_x), int(target_y))
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_drawer(self) -> None:
        self.hide()
        self.drawer_closed.emit()

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
