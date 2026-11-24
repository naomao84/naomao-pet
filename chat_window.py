"""Floating AI Chat Drawer combining Official Google Gemini Web & Local Pet AI.

Features:
- Default `✨ Gemini 웹` tab: embeds https://gemini.google.com/app using a persistent
  Chromium QWebEngineProfile (`gemini_web_profile`), preserving login/cookies across
  sessions, OAuth popup support, zoom controls, and a 1-click Chrome/Edge `--app=`
  standalone window launcher fallback if Google Sign-In blocks embedded WebViews.
- `🤖 로컬 AI` tab: preserves Minipet's local Ollama/OpenAI chat drawer, RPG/utility
  quick buttons, and persistent turn history (`chat_history.json`).
- Resizable frameless translucent drawer (560x740 <-> 760x820 toggle + QSizeGrip),
  always-on-top pin toggle (`📌`), and shared single-instance ownership across
  Ppong-ppong-i and Tree.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QPoint, QRect, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    WEBENGINE_CHAT_AVAILABLE = True
except Exception:
    WEBENGINE_CHAT_AVAILABLE = False
    QWebEnginePage = object  # type: ignore
    QWebEngineProfile = object  # type: ignore
    QWebEngineSettings = object  # type: ignore
    QWebEngineView = object  # type: ignore


GEMINI_APP_URL = "https://gemini.google.com/app"

QUICK_PROMPTS = [
    "오늘 일정과 메일 요약해줘",
    "바탕화면 전방위 모험 떠나기",
    "디펜스 웨이브 지금 출격!",
    "바탕화면 광맥 채굴하러 가자",
    "스파이더 뽕뽕이 출동!",
    "피곤한데 잠깐 쉴까? 슈퍼맨 비행!",
    "트리랑 같이 신나게 춤추기!",
    "컴퓨터 환경 깨끗이 청소해줘",
]

_SHARED_GEMINI_PROFILE: Optional[QWebEngineProfile] = None


def sanitize_gemini_user_agent(raw_ua: str) -> str:
    """Strip only `QtWebEngine/<ver>` token while retaining genuine Chromium build."""
    ua = re.sub(r"\s*QtWebEngine/\S+", "", raw_ua or "").strip()
    if not ua:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        )
    return ua


def resolve_default_data_dir(data_dir: Optional[Path] = None) -> Path:
    if data_dir is not None:
        base = Path(data_dir)
    else:
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            base = Path(local_app) / "Minipet"
        else:
            base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_shared_gemini_profile(
    data_dir: Optional[Path] = None,
    parent: Optional[QObject] = None,
) -> Optional[QWebEngineProfile]:
    """Return a singleton persistent QWebEngineProfile for Gemini Web."""
    global _SHARED_GEMINI_PROFILE
    if not WEBENGINE_CHAT_AVAILABLE:
        return None
    if _SHARED_GEMINI_PROFILE is not None:
        try:
            _SHARED_GEMINI_PROFILE.storageName()
            return _SHARED_GEMINI_PROFILE
        except RuntimeError:
            _SHARED_GEMINI_PROFILE = None

    base = resolve_default_data_dir(data_dir)
    profile_dir = base / "gemini_web_profile"
    storage_dir = profile_dir / "storage"
    cache_dir = profile_dir / "cache"
    storage_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    app_parent = parent if parent is not None else QApplication.instance()
    profile = QWebEngineProfile("MinipetGeminiWebProfile", app_parent)
    profile.setPersistentStoragePath(str(storage_dir))
    profile.setCachePath(str(cache_dir))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )

    try:
        default_ua = QWebEngineProfile.defaultProfile().httpUserAgent()
    except Exception:
        default_ua = ""
    profile.setHttpUserAgent(sanitize_gemini_user_agent(default_ua))

    try:
        s = profile.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
    except Exception:
        pass

    _SHARED_GEMINI_PROFILE = profile
    return _SHARED_GEMINI_PROFILE


def find_chrome_or_edge_exe() -> Optional[Path]:
    """Locate installed Google Chrome or Microsoft Edge binary on Windows."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(local_app) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(local_app) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for path in candidates:
        if path and path.exists():
            return path
    return None


def launch_gemini_app_window(url: str = GEMINI_APP_URL) -> bool:
    """Launch official Gemini Web inside a standalone frameless Chrome/Edge `--app` window."""
    exe = find_chrome_or_edge_exe()
    if exe is not None:
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = (
                    getattr(subprocess, "DETACHED_PROCESS", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                )
            subprocess.Popen(
                [
                    str(exe),
                    f"--app={url}",
                    "--window-size=680,820",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            return True
        except Exception:
            pass
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


class ChatHistoryManager:
    """Persistent JSON storage for Local AI chat turns."""

    def __init__(
        self,
        max_turns: int = 30,
        data_dir: Optional[Path] = None,
    ) -> None:
        self._max_turns = max_turns
        self._path = resolve_default_data_dir(data_dir) / "chat_history.json"
        self.turns: list[dict[str, str]] = []
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.turns = data[-self._max_turns :]
            except Exception:
                self.turns = []

    def append(self, role: str, text: str, tag: str = "") -> None:
        self.turns.append(
            {
                "role": role,
                "text": text,
                "tag": tag,
                "ts": datetime.now().strftime("%H:%M"),
            }
        )
        if len(self.turns) > self._max_turns:
            self.turns = self.turns[-self._max_turns :]
        try:
            self._path.write_text(
                json.dumps(self.turns, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def clear(self) -> None:
        self.turns = []
        try:
            if self._path.exists():
                self._path.unlink()
        except Exception:
            pass


class ChatBubbleWidget(QFrame):
    """Single chat message bubble widget for the Local AI tab."""

    def __init__(
        self,
        role: str,
        text: str,
        ts: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        is_user = role == "user"
        outer = QHBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)

        bubble = QFrame()
        bubble.setObjectName("msgBubble")
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(11, 8, 11, 7)
        b_layout.setSpacing(3)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setStyleSheet(
            f"color: {'#ffffff' if is_user else '#f1f5f9'}; "
            "font-size: 12.5px; line-height: 1.42; background: transparent; border: none;"
        )
        b_layout.addWidget(lbl)

        if ts:
            t_lbl = QLabel(ts)
            t_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
            )
            t_lbl.setStyleSheet(
                "color: rgba(203, 213, 225, 0.72); font-size: 10px; "
                "background: transparent; border: none;"
            )
            b_layout.addWidget(t_lbl)

        bg = (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(79,70,229,0.92),stop:1 rgba(124,58,237,0.92))"
            if is_user
            else "rgba(30, 41, 59, 0.88)"
        )
        border = (
            "rgba(167, 139, 250, 0.45)"
            if is_user
            else "rgba(148, 163, 184, 0.25)"
        )
        bubble.setStyleSheet(
            f"QFrame#msgBubble {{ background: {bg}; border: 1px solid {border}; border-radius: 13px; }}"
        )
        bubble.setMaximumWidth(370)

        if is_user:
            outer.addStretch(1)
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addStretch(1)


if WEBENGINE_CHAT_AVAILABLE:

    class _GeminiPopupDialog(QDialog):
        """Popup WebEngine window for Google OAuth sign-in or target=_blank links."""

        def __init__(
            self,
            profile: QWebEngineProfile,
            parent: Optional[QWidget] = None,
        ) -> None:
            super().__init__(parent)
            self.setWindowTitle("Google 로그인 · Gemini 인증")
            self.resize(520, 680)
            self.setStyleSheet("background: #0f172a; color: #f8fafc;")

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            self._view = QWebEngineView(self)
            self._page = QWebEnginePage(profile, self._view)
            self._view.setPage(self._page)
            self._page.windowCloseRequested.connect(self.close)
            self._page.titleChanged.connect(
                lambda title: self.setWindowTitle(title or "Google 로그인")
            )
            layout.addWidget(self._view, 1)

        def page(self) -> QWebEnginePage:
            return self._page

        def release_page(self) -> None:
            if getattr(self, "_page", None) is not None:
                try:
                    self._view.setPage(None)  # type: ignore
                except Exception:
                    pass
                try:
                    self._page.deleteLater()
                except Exception:
                    pass
                self._page = None  # type: ignore

        def closeEvent(self, event) -> None:  # type: ignore
            self.release_page()
            super().closeEvent(event)

    class _GeminiWebPage(QWebEnginePage):
        """Custom QWebEnginePage routing OAuth popups cleanly."""

        def __init__(
            self,
            profile: QWebEngineProfile,
            popup_factory,
            parent: Optional[QObject] = None,
        ) -> None:
            super().__init__(profile, parent)
            self._popup_factory = popup_factory

        def createWindow(self, win_type):  # type: ignore
            if callable(self._popup_factory):
                dlg = self._popup_factory()
                if dlg is not None:
                    return dlg.page()
            return None


class FloatingChatWindow(QWidget):
    """Floating executive AI drawer housing Official Gemini Web & Local Pet AI."""

    message_submitted = pyqtSignal(str)
    mail_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    alarm_requested = pyqtSignal()
    cleanup_requested = pyqtSignal()
    rpg_hub_requested = pyqtSignal()
    bag_requested = pyqtSignal()

    DEFAULT_SIZE = (560, 740)
    WIDE_SIZE = (760, 820)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(parent)
        self._data_dir = resolve_default_data_dir(data_dir)
        self._owner_pet: Optional[object] = None
        self._drag_pos = QPoint()
        self._busy = False
        self._is_wide = False
        self._pinned_on_top = True
        self._gemini_loaded = False
        self._active_tab = "gemini"
        self._popup_dialogs: list = []
        self._gemini_profile: Optional[QWebEngineProfile] = None
        self._gemini_view: Optional[QWebEngineView] = None
        self._gemini_page: Optional[QWebEnginePage] = None
        self._auth_hint_dismissed = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(460, 560)
        self.resize(*self.DEFAULT_SIZE)

        self.history_mgr = ChatHistoryManager(max_turns=30, data_dir=self._data_dir)
        self._build_ui()
        self._restore_history()

        esc = QShortcut(QKeySequence("Escape"), self)
        esc.activated.connect(self.hide)

    @property
    def owner_pet(self) -> Optional[object]:
        return self._owner_pet

    def set_owner_pet(self, owner_pet: Optional[object]) -> None:
        self._owner_pet = owner_pet
        if owner_pet is not None and hasattr(self, "_owner_badge"):
            name = getattr(owner_pet, "char_display_name", "") or "미니펫"
            icon = "🎄" if getattr(owner_pet, "char_id", "") == "tree" else "🦄"
            self._owner_badge.setText(f"{icon} {name}")

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # 1. Header Bar + Mode Switcher + Window Controls
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        header.setSpacing(6)

        self._owner_badge = QLabel("🦄 뽕뽕이")
        self._owner_badge.setStyleSheet(
            "color: #e2e8f0; font-size: 12px; font-weight: 700; "
            "background: rgba(51, 65, 85, 0.72); border: 1px solid rgba(148, 163, 184, 0.28); "
            "border-radius: 10px; padding: 3px 9px;"
        )
        header.addWidget(self._owner_badge)

        self._tab_gemini_btn = QPushButton("✨ Gemini 웹")
        self._tab_local_btn = QPushButton("🤖 로컬 AI")
        for btn in (self._tab_gemini_btn, self._tab_local_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
        self._tab_gemini_btn.clicked.connect(lambda: self._switch_tab("gemini"))
        self._tab_local_btn.clicked.connect(lambda: self._switch_tab("local"))
        header.addWidget(self._tab_gemini_btn)
        header.addWidget(self._tab_local_btn)

        header.addStretch(1)

        self._ext_header_btn = QPushButton("🌐 앱 창")
        self._ext_header_btn.setToolTip("Chrome/Edge 공식 Gemini 독립 창으로 열기")
        self._ext_header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ext_header_btn.setFixedHeight(27)
        self._ext_header_btn.setStyleSheet(
            "QPushButton { background: rgba(56, 189, 248, 0.22); color: #bae6fd; "
            "border: 1px solid rgba(56, 189, 248, 0.45); border-radius: 9px; "
            "font-size: 11px; font-weight: 700; padding: 2px 9px; }"
            "QPushButton:hover { background: rgba(56, 189, 248, 0.38); color: #ffffff; }"
        )
        self._ext_header_btn.clicked.connect(self._on_launch_external_app)
        header.addWidget(self._ext_header_btn)

        btn_css = (
            "QPushButton { background: rgba(51, 65, 85, 0.65); color: #cbd5e1; "
            "border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 9px; "
            "font-size: 12px; font-weight: 700; }"
            "QPushButton:hover { background: rgba(99, 102, 241, 0.55); color: #ffffff; }"
            "QPushButton:checked { background: rgba(79, 70, 229, 0.72); color: #ffffff; "
            "border-color: rgba(165, 180, 252, 0.65); }"
        )

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setChecked(True)
        self._pin_btn.setFixedSize(27, 27)
        self._pin_btn.setToolTip("항상 위 고정 토글")
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.setStyleSheet(btn_css)
        self._pin_btn.clicked.connect(self._toggle_pin_on_top)
        header.addWidget(self._pin_btn)

        self._wide_btn = QPushButton("⤢")
        self._wide_btn.setCheckable(True)
        self._wide_btn.setFixedSize(27, 27)
        self._wide_btn.setToolTip("넓은 보기 / 기본 보기 전환 (560x740 ↔ 760x820)")
        self._wide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wide_btn.setStyleSheet(btn_css)
        self._wide_btn.clicked.connect(self._toggle_wide_size)
        header.addWidget(self._wide_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(27, 27)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(239, 68, 68, 0.28); color: #fecaca; "
            "border: 1px solid rgba(248, 113, 113, 0.35); border-radius: 9px; font-weight: 700; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.78); color: #ffffff; }"
        )
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        root.addLayout(header)

        # 2. Dual-Mode Body Stack
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_gemini_web_page())
        self._stack.addWidget(self._build_local_ai_page())
        root.addWidget(self._stack, 1)

        # 3. Bottom Resize Grip Row
        footer = QHBoxLayout()
        footer.setContentsMargins(6, 0, 2, 0)
        footer.setSpacing(6)
        self._footer_hint = QLabel("드래그 이동 · 모서리 크기 조절 · Ctrl+G 빠른 토글")
        self._footer_hint.setStyleSheet(
            "color: rgba(148, 163, 184, 0.78); font-size: 10.5px; background: transparent;"
        )
        footer.addWidget(self._footer_hint)
        footer.addStretch(1)
        grip = QSizeGrip(self)
        grip.setFixedSize(16, 16)
        grip.setToolTip("창 크기 조절")
        footer.addWidget(grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(footer)

        self._switch_tab("gemini", load_now=False)

    def _build_gemini_web_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Compact Web Toolbar
        nav = QHBoxLayout()
        nav.setContentsMargins(2, 0, 2, 0)
        nav.setSpacing(4)

        nav_btn_css = (
            "QPushButton { background: rgba(30, 41, 59, 0.78); color: #e2e8f0; "
            "border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 8px; "
            "font-size: 11px; font-weight: 600; padding: 3px 8px; }"
            "QPushButton:hover { background: rgba(56, 189, 248, 0.30); border-color: rgba(56, 189, 248, 0.55); }"
        )

        self._web_back_btn = QPushButton("◀")
        self._web_back_btn.setFixedSize(26, 25)
        self._web_back_btn.setStyleSheet(nav_btn_css)
        self._web_back_btn.clicked.connect(
            lambda: self._gemini_view.back() if self._gemini_view is not None else None
        )
        nav.addWidget(self._web_back_btn)

        self._web_reload_btn = QPushButton("⟳")
        self._web_reload_btn.setFixedSize(26, 25)
        self._web_reload_btn.setStyleSheet(nav_btn_css)
        self._web_reload_btn.clicked.connect(self._reload_gemini_web)
        nav.addWidget(self._web_reload_btn)

        self._web_home_btn = QPushButton("✨ Gemini 홈")
        self._web_home_btn.setFixedHeight(25)
        self._web_home_btn.setStyleSheet(nav_btn_css)
        self._web_home_btn.clicked.connect(
            lambda: self.load_gemini_url(GEMINI_APP_URL)
        )
        nav.addWidget(self._web_home_btn)

        self._web_status_lbl = QLabel("대기 중")
        self._web_status_lbl.setStyleSheet(
            "color: #93c5fd; font-size: 11px; padding: 0 6px; background: transparent;"
        )
        nav.addWidget(self._web_status_lbl, 1)

        zoom_out_btn = QPushButton("A-")
        zoom_out_btn.setFixedSize(28, 25)
        zoom_out_btn.setStyleSheet(nav_btn_css)
        zoom_out_btn.clicked.connect(lambda: self._adjust_web_zoom(-0.1))
        nav.addWidget(zoom_out_btn)

        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.setFixedSize(28, 25)
        zoom_in_btn.setStyleSheet(nav_btn_css)
        zoom_in_btn.clicked.connect(lambda: self._adjust_web_zoom(+0.1))
        nav.addWidget(zoom_in_btn)

        launch_btn = QPushButton("🌐 앱 창으로 열기")
        launch_btn.setFixedHeight(25)
        launch_btn.setStyleSheet(
            "QPushButton { background: rgba(79, 70, 229, 0.72); color: #ffffff; "
            "border: 1px solid rgba(165, 180, 252, 0.55); border-radius: 8px; "
            "font-size: 11px; font-weight: 700; padding: 3px 9px; }"
            "QPushButton:hover { background: rgba(99, 102, 241, 0.92); }"
        )
        launch_btn.clicked.connect(self._on_launch_external_app)
        nav.addWidget(launch_btn)
        layout.addLayout(nav)

        # Optional Non-Blocking Auth Tip Banner (shown if redirected to accounts.google.com)
        self._auth_banner = QFrame()
        self._auth_banner.setObjectName("authTipBanner")
        self._auth_banner.setVisible(False)
        self._auth_banner.setStyleSheet(
            "QFrame#authTipBanner { background: rgba(120, 53, 15, 0.85); "
            "border: 1px solid rgba(251, 191, 36, 0.50); border-radius: 9px; }"
        )
        ab_lay = QHBoxLayout(self._auth_banner)
        ab_lay.setContentsMargins(9, 5, 7, 5)
        ab_lay.setSpacing(6)
        ab_lbl = QLabel(
            "Google 로그인 창이 제한될 경우 우측 [🌐 앱 창으로 열기]로 Chrome/Edge 공식 창에서 바로 이용하세요."
        )
        ab_lbl.setWordWrap(True)
        ab_lbl.setStyleSheet("color: #fef3c7; font-size: 11px; background: transparent;")
        ab_lay.addWidget(ab_lbl, 1)
        ab_open = QPushButton("열기")
        ab_open.setFixedHeight(22)
        ab_open.setStyleSheet(
            "QPushButton { background: #f59e0b; color: #0f172a; border-radius: 6px; "
            "font-size: 11px; font-weight: 700; padding: 2px 8px; }"
        )
        ab_open.clicked.connect(self._on_launch_external_app)
        ab_lay.addWidget(ab_open)
        ab_dismiss = QPushButton("✕")
        ab_dismiss.setFixedSize(20, 20)
        ab_dismiss.setStyleSheet(
            "QPushButton { background: transparent; color: #fde68a; border: none; font-weight: 700; }"
        )
        ab_dismiss.clicked.connect(self._dismiss_auth_banner)
        ab_lay.addWidget(ab_dismiss)
        layout.addWidget(self._auth_banner)

        # Embedded WebView Container
        self._web_container = QFrame()
        self._web_container.setObjectName("geminiWebFrame")
        self._web_container.setStyleSheet(
            "QFrame#geminiWebFrame { background: rgba(15, 23, 42, 0.92); "
            "border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 12px; }"
        )
        wc_lay = QVBoxLayout(self._web_container)
        wc_lay.setContentsMargins(4, 4, 4, 4)
        wc_lay.setSpacing(0)

        if WEBENGINE_CHAT_AVAILABLE:
            self._gemini_profile = get_shared_gemini_profile(self._data_dir, QApplication.instance())
            view = QWebEngineView(self._web_container)
            page_obj = _GeminiWebPage(
                self._gemini_profile,
                popup_factory=self._create_oauth_popup,
                parent=view,
            )
            view.setPage(page_obj)
            view.setZoomFactor(0.95)
            view.loadStarted.connect(self._on_web_load_started)
            view.loadFinished.connect(self._on_web_load_finished)
            view.urlChanged.connect(self._on_web_url_changed)
            self._gemini_view = view
            self._gemini_page = page_obj
            wc_lay.addWidget(view, 1)
        else:
            fallback_lbl = QLabel(
                "PyQt6-WebEngine이 비활성화되어 있어요.\n"
                "상단의 [🌐 앱 창으로 열기] 버튼으로 Google Gemini를 바로 열 수 있어요!"
            )
            fallback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback_lbl.setWordWrap(True)
            fallback_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px; padding: 24px;")
            wc_lay.addWidget(fallback_lbl, 1)

        layout.addWidget(self._web_container, 1)
        return page

    def _build_local_ai_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Quick Utility Header Bar
        qbar = QHBoxLayout()
        qbar.setContentsMargins(2, 0, 2, 0)
        qbar.setSpacing(4)

        btn_specs = [
            ("🏰 사령부", self.rpg_hub_requested.emit),
            ("🎒 가방", self.bag_requested.emit),
            ("📧 메일", self.mail_requested.emit),
            ("⏰ 알람", self.alarm_requested.emit),
            ("🧹 청소", self.cleanup_requested.emit),
            ("⚙️ 설정", self.settings_requested.emit),
        ]
        for label, cb in btn_specs:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(25)
            b.setStyleSheet(
                "QPushButton { background: rgba(30, 41, 59, 0.72); color: #e2e8f0; "
                "border: 1px solid rgba(148, 163, 184, 0.22); border-radius: 8px; "
                "font-size: 11px; font-weight: 600; padding: 2px 7px; }"
                "QPushButton:hover { background: rgba(99, 102, 241, 0.45); }"
            )
            b.clicked.connect(cb)
            qbar.addWidget(b)

        qbar.addStretch(1)
        clear_btn = QPushButton("🗑️")
        clear_btn.setFixedSize(26, 25)
        clear_btn.setToolTip("로컬 대화 기록 비우기")
        clear_btn.setStyleSheet(
            "QPushButton { background: rgba(30, 41, 59, 0.72); color: #cbd5e1; "
            "border: 1px solid rgba(148, 163, 184, 0.22); border-radius: 8px; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.45); color: #fff; }"
        )
        clear_btn.clicked.connect(self._clear_history)
        qbar.addWidget(clear_btn)
        layout.addLayout(qbar)

        # Scrollable History Area
        self.history_area = QScrollArea()
        self.history_area.setWidgetResizable(True)
        self.history_area.setFrameShape(QFrame.Shape.NoFrame)
        self.history_area.setStyleSheet(
            "QScrollArea { background: rgba(15, 23, 42, 0.58); border-radius: 12px; "
            "border: 1px solid rgba(148, 163, 184, 0.16); }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(148, 163, 184, 0.35); border-radius: 3px; }"
        )
        self.history_container = QWidget()
        self.history_container.setStyleSheet("background: transparent;")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(8, 8, 8, 8)
        self.history_layout.setSpacing(6)
        self.history_layout.addStretch(1)
        self.history_area.setWidget(self.history_container)
        layout.addWidget(self.history_area, 1)

        # Typing Indicator & Prompt Bar
        self.typing_lbl = QLabel("")
        self.typing_lbl.setVisible(False)
        self.typing_lbl.setStyleSheet("color: #93c5fd; font-size: 11.5px; padding-left: 6px;")
        layout.addWidget(self.typing_lbl)

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItem("✨ 빠른 명령어 / 추천 질문 선택...")
        for p in QUICK_PROMPTS:
            self.prompt_combo.addItem(p)
        self.prompt_combo.setStyleSheet(
            "QComboBox { background: rgba(30, 41, 59, 0.72); color: #cbd5e1; "
            "border: 1px solid rgba(148, 163, 184, 0.22); border-radius: 9px; "
            "padding: 4px 10px; font-size: 11.5px; }"
        )
        self.prompt_combo.currentIndexChanged.connect(self._on_quick_prompt_picked)
        layout.addWidget(self.prompt_combo)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("로컬 AI에게 말 걸기 또는 액션 명령...")
        self.input_edit.setFixedHeight(36)
        self.input_edit.setStyleSheet(
            "QLineEdit { background: rgba(30, 41, 59, 0.88); color: #f8fafc; "
            "border: 1px solid rgba(148, 163, 184, 0.32); border-radius: 11px; "
            "padding: 0 12px; font-size: 12.5px; }"
            "QLineEdit:focus { border-color: #818cf8; }"
        )
        self.input_edit.returnPressed.connect(self._submit)
        input_row.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("전송 ✦")
        self.send_btn.setFixedSize(72, 36)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6366f1,stop:1 #8b5cf6); "
            "color: #ffffff; border: none; border-radius: 11px; font-size: 12.5px; font-weight: 700; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #818cf8,stop:1 #a78bfa); }"
            "QPushButton:disabled { background: rgba(71, 85, 105, 0.55); color: #94a3b8; }"
        )
        self.send_btn.clicked.connect(self._submit)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)
        return page

    # ------------------------------------------------------------------
    # Tab, Gemini Web & OAuth Popup Handling
    # ------------------------------------------------------------------
    def _switch_tab(self, tab_key: str, load_now: bool = True) -> None:
        self._active_tab = "local" if tab_key == "local" else "gemini"
        is_gem = self._active_tab == "gemini"
        self._stack.setCurrentIndex(0 if is_gem else 1)

        active_css = (
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4f46e5,stop:1 #0ea5e9); "
            "color: #ffffff; border: 1px solid rgba(186, 230, 253, 0.55); border-radius: 10px; "
            "font-size: 12px; font-weight: 700; padding: 3px 11px; }"
        )
        idle_css = (
            "QPushButton { background: rgba(30, 41, 59, 0.72); color: #cbd5e1; "
            "border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 10px; "
            "font-size: 12px; font-weight: 600; padding: 3px 11px; }"
            "QPushButton:hover { background: rgba(51, 65, 85, 0.90); color: #ffffff; }"
        )
        self._tab_gemini_btn.setChecked(is_gem)
        self._tab_local_btn.setChecked(not is_gem)
        self._tab_gemini_btn.setStyleSheet(active_css if is_gem else idle_css)
        self._tab_local_btn.setStyleSheet(idle_css if is_gem else active_css)

        if is_gem and load_now:
            self.ensure_gemini_loaded()
        elif not is_gem:
            self.input_edit.setFocus()

    def ensure_gemini_loaded(self) -> None:
        if not WEBENGINE_CHAT_AVAILABLE or self._gemini_view is None:
            return
        if not self._gemini_loaded:
            self._gemini_loaded = True
            self.load_gemini_url(GEMINI_APP_URL)

    def load_gemini_url(self, url: str = GEMINI_APP_URL) -> None:
        if self._gemini_view is not None:
            self._gemini_loaded = True
            self._gemini_view.setUrl(QUrl(url))

    def _reload_gemini_web(self) -> None:
        if self._gemini_view is not None:
            if not self._gemini_loaded:
                self.ensure_gemini_loaded()
            else:
                self._gemini_view.reload()

    def _adjust_web_zoom(self, delta: float) -> None:
        if self._gemini_view is not None:
            cur = self._gemini_view.zoomFactor()
            self._gemini_view.setZoomFactor(max(0.65, min(1.6, round(cur + delta, 2))))

    def _on_web_load_started(self) -> None:
        if hasattr(self, "_web_status_lbl"):
            self._web_status_lbl.setText("불러오는 중...")

    def _on_web_load_finished(self, ok: bool) -> None:
        if hasattr(self, "_web_status_lbl"):
            if ok:
                cur = self._gemini_view.url().toString() if self._gemini_view is not None else ""
                if "accounts.google.com" in cur:
                    self._web_status_lbl.setText("Google 로그인 진행 중")
                elif "gemini.google.com" in cur:
                    self._web_status_lbl.setText("Gemini 웹 연결됨")
                else:
                    self._web_status_lbl.setText("연결됨")
            else:
                self._web_status_lbl.setText("연결 확인 · [앱 창으로 열기] 가능")

    def _on_web_url_changed(self, url: QUrl) -> None:
        s = url.toString() if url is not None else ""
        if not self._auth_hint_dismissed and "accounts.google.com" in s:
            self._auth_banner.setVisible(True)
        elif "gemini.google.com" in s:
            self._auth_banner.setVisible(False)

    def _dismiss_auth_banner(self) -> None:
        self._auth_hint_dismissed = True
        self._auth_banner.setVisible(False)

    def _create_oauth_popup(self):
        if not WEBENGINE_CHAT_AVAILABLE or self._gemini_profile is None:
            return None
        dlg = _GeminiPopupDialog(self._gemini_profile, self)
        self._popup_dialogs.append(dlg)
        dlg.finished.connect(lambda _res, d=dlg: self._remove_popup_dialog(d))
        dlg.show()
        return dlg

    def _remove_popup_dialog(self, dlg) -> None:
        if dlg in self._popup_dialogs:
            self._popup_dialogs.remove(dlg)
        try:
            dlg.release_page()
            dlg.deleteLater()
        except Exception:
            pass

    def _on_launch_external_app(self) -> None:
        url = GEMINI_APP_URL
        if self._gemini_view is not None:
            cur = self._gemini_view.url().toString()
            if cur.startswith("https://gemini.google.com"):
                url = cur
        launch_gemini_app_window(url)

    # ------------------------------------------------------------------
    # Window Toggles, Sizing & Smart Clamped Placement
    # ------------------------------------------------------------------
    def _toggle_pin_on_top(self) -> None:
        self._pinned_on_top = bool(self._pin_btn.isChecked())
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._pinned_on_top)
        if was_visible:
            self.show()
            self.raise_()

    def _toggle_wide_size(self) -> None:
        self._is_wide = bool(self._wide_btn.isChecked())
        target = self.WIDE_SIZE if self._is_wide else self.DEFAULT_SIZE
        geo = self.geometry()
        geo.setWidth(target[0])
        geo.setHeight(target[1])
        screen = QApplication.screenAt(geo.center()) or QApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            x = max(avail.left() + 8, min(geo.x(), avail.right() - target[0] - 8))
            y = max(avail.top() + 8, min(geo.y(), avail.bottom() - target[1] - 8))
            self.setGeometry(x, y, target[0], target[1])
        else:
            self.resize(*target)

    def _position_beside_pet(self, pet_geo: QRect) -> None:
        screen = QApplication.screenAt(pet_geo.center()) or QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1040)
        w, h = self.width(), self.height()

        right_x = pet_geo.right() + 14
        left_x = pet_geo.left() - w - 14
        if right_x + w <= avail.right() - 8:
            x = right_x
        elif left_x >= avail.left() + 8:
            x = left_x
        else:
            x = max(avail.left() + 8, min(pet_geo.center().x() - w // 2, avail.right() - w - 8))

        y = pet_geo.bottom() - h + 20
        y = max(avail.top() + 8, min(y, avail.bottom() - h - 8))
        self.move(x, y)

    def show_beside_pet(
        self,
        pet_geo: QRect,
        owner_pet: Optional[object] = None,
    ) -> None:
        if owner_pet is not None:
            self.set_owner_pet(owner_pet)
        self._position_beside_pet(pet_geo)
        self.show()
        self.raise_()
        self.activateWindow()
        if self._active_tab == "gemini":
            self.ensure_gemini_loaded()
        else:
            self.input_edit.setFocus()

    def open_gemini_web(
        self,
        pet_geo: Optional[QRect] = None,
        owner_pet: Optional[object] = None,
    ) -> None:
        if owner_pet is not None:
            self.set_owner_pet(owner_pet)
        self._switch_tab("gemini", load_now=True)
        if pet_geo is not None:
            self._position_beside_pet(pet_geo)
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_visibility_beside(
        self,
        pet_geo: QRect,
        owner_pet: Optional[object] = None,
    ) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_beside_pet(pet_geo, owner_pet=owner_pet)

    # ------------------------------------------------------------------
    # Local AI Tab Methods (Preserved Backward Compatibility)
    # ------------------------------------------------------------------
    def _restore_history(self) -> None:
        for turn in self.history_mgr.turns:
            self._append_bubble_widget(
                turn.get("role", "pet"),
                turn.get("text", ""),
                turn.get("ts", ""),
            )
        if not self.history_mgr.turns:
            self._append_bubble_widget(
                "pet",
                "안녕! 나는 뽕뽕이 로컬 AI 비서야. '✨ Gemini 웹' 탭에서는 Google Gemini와 직접 대화할 수 있어요!",
                datetime.now().strftime("%H:%M"),
            )

    def _clear_history(self) -> None:
        self.history_mgr.clear()
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._append_bubble_widget(
            "pet",
            "로컬 대화 기록을 깨끗하게 정리했어요!",
            datetime.now().strftime("%H:%M"),
        )

    def _append_bubble_widget(self, role: str, text: str, ts: str = "") -> None:
        w = ChatBubbleWidget(role, text, ts, self.history_container)
        self.history_layout.insertWidget(max(0, self.history_layout.count() - 1), w)
        QApplication.processEvents()
        sb = self.history_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def add_message(self, role: str, text: str, tag: str = "") -> None:
        ts = datetime.now().strftime("%H:%M")
        self.history_mgr.append(role, text, tag)
        self._append_bubble_widget(role, text, ts)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_btn.setEnabled(not busy)
        self.input_edit.setEnabled(not busy)
        self.typing_lbl.setText("생각 중... 💭" if busy else "")
        self.typing_lbl.setVisible(busy)
        if not busy and self.isVisible() and self._active_tab == "local":
            self.input_edit.setFocus()

    def populate_prompt(self, text: str) -> None:
        self._switch_tab("local", load_now=False)
        self.input_edit.setText(text)
        self.input_edit.setFocus()

    def _on_quick_prompt_picked(self, index: int) -> None:
        if index <= 0:
            return
        text = self.prompt_combo.currentText()
        self.prompt_combo.setCurrentIndex(0)
        self.input_edit.setText(text)
        self._submit()

    def _submit(self) -> None:
        if self._busy:
            return
        text = self.input_edit.text().strip()
        if not text:
            return
        self.input_edit.clear()
        self.add_message("user", text)
        self.message_submitted.emit(text)

    # ------------------------------------------------------------------
    # Clean Shutdown & Rounded Translucent Backdrop
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        for dlg in list(self._popup_dialogs):
            self._remove_popup_dialog(dlg)
        if self._gemini_page is not None:
            try:
                if self._gemini_view is not None:
                    self._gemini_view.setPage(None)  # type: ignore
                self._gemini_page.deleteLater()
            except Exception:
                pass
            self._gemini_page = None
        if self._gemini_view is not None:
            try:
                self._gemini_view.deleteLater()
            except Exception:
                pass
            self._gemini_view = None

    def paintEvent(self, event) -> None:  # type: ignore
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), 18.0, 18.0)
        p.fillPath(path, QColor(15, 23, 42, 236))
        p.setPen(QPen(QColor(148, 163, 184, 72), 1.4))
        p.drawPath(path)
        p.end()

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
