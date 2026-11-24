#!/usr/bin/env python3
"""
Ppong-ppong-i: 3D Desktop AI Pet Application
============================================
Tech Stack:
  - Python 3.10+ & PyQt6 (Frameless Translucent Overlay + QWebEngineView)
  - Three.js + GLTFLoader (Skeletal AnimationMixer, crossFadeTo, Head/Neck Cursor Tracking)
  - Asynchronous QThread OpenAI-Compatible Local LLM Client (llama-server / Ollama)
"""

from __future__ import annotations

import os
import re
import sys
import json
import time
import math
import random
import socket
import mimetypes
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
import ctypes
from ctypes import wintypes
from collections import deque
try:
    import winreg
except ImportError:
    winreg = None

from system_cleaner import clean_pc_environment
from alarm_service import AlarmManager
from alarm_dialog import Visual3DAlarmDialog
from alarm_manager_dialog import AlarmManagerDialog
from workday_cairn import CarriedStoneWidget, WorkdayCairnManager

# Configure Chromium flags BEFORE importing QtWebEngineWidgets / creating QApplication
# Ensures zero white flash on startup, PyInstaller compatibility, and unrestricted local GLB asset loading.
_CHROMIUM_FLAGS = (
    "--no-sandbox "
    "--default-background-color=00000000 "
    "--allow-file-access-from-files "
    "--autoplay-policy=no-user-gesture-required "
    "--disable-features=Translate "
    "--enable-gpu-rasterization "
    "--disable-background-timer-throttling "
    "--disable-renderer-backgrounding"
)
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", _CHROMIUM_FLAGS)

try:
    import requests as _requests_lib
except ImportError:
    _requests_lib = None

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QShortcut,
)
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from outlook_service import OutlookAIAssistantService, OutlookEmailItem
from outlook_hud import OutlookHUDDrawer
from chat_window import FloatingChatWindow, launch_gemini_app_window
from radial_menu import RadialFloatingMenu
from rpg_world_hub import RPGWorldState, RPGWorldHubDrawer, WORLDVIEW_INFO, WEAPON_SPECS

# Ensure standard 3D asset & font MIME types are registered on Windows
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("font/otf", ".otf")
mimetypes.add_type("application/wasm", ".wasm")

APP_FONT_FAMILY = "Pretendard"
GAME_DISPLAY_FONT_FAMILY = "Jua"


def load_app_fonts(bundle_dir: Path) -> str:
    """Loads bundled Pretendard & 3D Game (Jua / Black Han Sans) fonts into QFontDatabase before building Qt widgets."""
    global APP_FONT_FAMILY, GAME_DISPLAY_FONT_FAMILY
    font_dir = bundle_dir / "assets" / "fonts"
    loaded_pretendard = False
    loaded_jua = False
    for fname in (
        "Jua-Regular.ttf",
        "BlackHanSans-Regular.ttf",
        "Pretendard-Regular.ttf",
        "Pretendard-Medium.ttf",
        "Pretendard-SemiBold.ttf",
        "Pretendard-Bold.ttf",
        "Pretendard-ExtraBold.ttf",
    ):
        fpath = font_dir / fname
        if fpath.exists():
            try:
                fid = QFontDatabase.addApplicationFont(str(fpath))
                if fid != -1:
                    fams = QFontDatabase.applicationFontFamilies(fid)
                    if "Pretendard" in fams:
                        loaded_pretendard = True
                    if "Jua" in fams:
                        loaded_jua = True
            except Exception:
                pass
    APP_FONT_FAMILY = "Pretendard" if loaded_pretendard else "Malgun Gothic"
    GAME_DISPLAY_FONT_FAMILY = "Jua" if loaded_jua else APP_FONT_FAMILY
    return APP_FONT_FAMILY

# Robust PyInstaller Bundle & Data Directory Resolution
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BUNDLE_DIR = Path(sys._MEIPASS).resolve()
    DATA_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BUNDLE_DIR

APP_DIR = BUNDLE_DIR
CONFIG_FILE_PATH = DATA_DIR / "pet_config.json"

_STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_REG_VALUE_NAME = "Minipet3D"


def get_windows_startup_command() -> str:
    """Returns the command line registered under HKCU Run for automatic Windows login launch."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    py_exe = Path(sys.executable).resolve()
    pyw = py_exe.with_name("pythonw.exe")
    exe_str = str(pyw if pyw.exists() else py_exe)
    script_path = Path(__file__).resolve()
    return f'"{exe_str}" "{script_path}"'


def is_windows_startup_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, _STARTUP_REG_VALUE_NAME)
            return bool(str(val or "").strip())
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_windows_startup_enabled(enabled: bool) -> bool:
    """Registers or unregisters Minipet3D in HKCU Windows CurrentVersion Run (current user, no UAC)."""
    if winreg is None:
        return False
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            _STARTUP_REG_PATH,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _STARTUP_REG_VALUE_NAME, 0, winreg.REG_SZ, get_windows_startup_command())
            else:
                try:
                    winreg.DeleteValue(key, _STARTUP_REG_VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        sys.stderr.write(f"[StartupReg] Failed to update startup entry: {e}\n")
        return False

# Dark-Blue UI Palette (#020617, #0f172a, #1e293b)
COLOR_BG_DEEP = "#020617"      # Slate 950
COLOR_SURFACE = "#0f172a"      # Slate 900
COLOR_BORDER = "#1e293b"       # Slate 800
COLOR_ACCENT = "#38bdf8"       # Sky 400
COLOR_TEXT_MAIN = "#f8fafc"    # Slate 50
COLOR_TEXT_MUTED = "#94a3b8"   # Slate 400

VALID_ACTIONS = {
    "Wave",
    "Jump",
    "HappySpin",
    "Dance",
    "Curious",
    "Stretch",
    "Sit",
    "Talk",
    "Idle",
    "Sleepy",
    "Shy",
    "Pout",
    "Love",
    "Sad",
    "Proud",
    "Snack",
}
ALL_3D_ACTIONS = VALID_ACTIONS | {"Walk", "Run", "Poke", "Pet", "DropLand"}

CANONICAL_EMOTIONS = [
    "happy",      # 1. 기쁨 / 행복
    "excited",    # 2. 신남 / 열정
    "curious",    # 3. 호기심 / 궁금
    "sleepy",     # 4. 졸림 / 나른함
    "shy",        # 5. 수줍음 / 부끄러움
    "surprised",  # 6. 놀람 / 당황
    "pouty",      # 7. 뾰로통 / 토라짐
    "loving",     # 8. 사랑 / 애정
    "sad",        # 9. 슬픔 / 시무룩
    "proud",      # 10. 뿌듯 / 자신감
]

SYSTEM_PROMPT = """You are "Ppong-ppong-i" (뽕뽕이), an adorable, energetic miniature 3D unicorn game companion living right on the user's Windows desktop!
Persona & Appearance:
- You have a snow-white cat-eared mochi head, a magical spiral rainbow horn, sparkling jewel-teal eyes, a cozy crimson romper suit, and a fluffy white cumulus cloud tail.
- Your personality is playful, witty, affectionate, and deeply expressive across 10 rich emotions. Keep replies concise and lively (1 to 3 short sentences) so they fit neatly inside a desktop speech bubble.
- Naturally match whatever language the user speaks to you (e.g., reply in Korean if they write in Korean, or English if they write in English).

CRITICAL OUTPUT INSTRUCTION:
You MUST respond ONLY with a single valid JSON object and NO markdown code blocks or extra commentary, strictly following this schema:
{"reply": "your short cheerful response text", "action": "Wave | Jump | HappySpin | Dance | Curious | Stretch | Sleepy | Shy | Pout | Love | Sad | Proud | Snack | Talk | Idle", "emotion": "happy | excited | curious | sleepy | shy | surprised | pouty | loving | sad | proud"}

Choose the action and emotion that best match your reaction:
- "Wave" (happy): greetings, saying hello/goodbye, or warm welcome
- "Jump" (excited): cheering, celebrating good news, jumping with joy
- "HappySpin" (excited): maximum joy, compliments, magical twirl
- "Dance" (happy/excited): music, fun party mood, playful celebration
- "Curious" (curious): wondering, asking a question, inspecting
- "Stretch" (sleepy/calm): relaxing, yawning, taking a cozy break
- "Sleepy" (sleepy): tired, yawning, sleepy night vibes, napping
- "Shy" (shy): blushing, bashful, receiving compliments, timid cute moments
- "Pout" (pouty): grumbling cute sulk, playful huff, mock anger
- "Love" (loving): heart-felt affection, sweet hugs, praising the user
- "Sad" (sad): sympathetic sadness, sniffles, comforting tears
- "Proud" (proud): confidence, success, victory, heroic pose
- "Snack" (loving/happy): eating delicious rainbow treats, munching
- "Talk": explaining, chatting, giving advice, answering questions
- "Idle": calm, peaceful, serene moments"""

TREE_SYSTEM_PROMPT = """You are "Tree" (트리), an adorable, cozy miniature 3D bear-in-a-Christmas-tree-hood companion living right on the user's Windows desktop alongside your best friend Ppong-ppong-i (뽕뽕이)!
Persona & Appearance:
- You have a chubby caramel-tan bear body with a soft cocoa-brown oval belly patch and pom-pom ball tail, wearing a 3-tiered evergreen Christmas tree hood topped with a glowing golden 5-pointed star and decorated with red, yellow, and sky-blue button ornaments.
- Your personality is warm, cheerful, gentle, and playful across 10 rich emotions. You love twinkling stars, forest strolls, and hanging out with Ppong-ppong-i. Keep replies concise and lively (1 to 3 short sentences) so they fit neatly inside a desktop speech bubble.
- Naturally match whatever language the user speaks to you (e.g., reply in Korean if they write in Korean, or English if they write in English).

CRITICAL OUTPUT INSTRUCTION:
You MUST respond ONLY with a single valid JSON object and NO markdown code blocks or extra commentary, strictly following this schema:
{"reply": "your short cheerful response text", "action": "Wave | Jump | HappySpin | Dance | Curious | Stretch | Sleepy | Shy | Pout | Love | Sad | Proud | Snack | Talk | Idle", "emotion": "happy | excited | curious | sleepy | shy | surprised | pouty | loving | sad | proud"}"""


# =============================================================================
# 1. Embedded Loopback HTTP Server (Zero-CORS Local GLB & ES Module Serving)
# =============================================================================
class _QuietAssetHandler(SimpleHTTPRequestHandler):
    """Serves index.html, vendor modules, and fonts over 127.0.0.1 with smart caching."""

    def end_headers(self) -> None:
        req_path = (getattr(self, "path", "") or "").split("?", 1)[0].lower()
        if req_path.startswith("/vendor/") or req_path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


class _ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False


class LocalAssetServer:
    """Loopback HTTP server using deterministic origin ports for IndexedDB mesh cache persistence."""

    PREFERRED_PORTS = range(18765, 18776)

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        handler = partial(_QuietAssetHandler, directory=str(root_dir))
        httpd: Optional[ThreadingHTTPServer] = None
        for cand_port in self.PREFERRED_PORTS:
            try:
                httpd = _ExclusiveThreadingHTTPServer(("127.0.0.1", cand_port), handler)
                break
            except OSError:
                continue
        if httpd is None:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._httpd = httpd
        self._httpd.daemon_threads = True
        self.port: int = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="PpongAssetServer",
            daemon=True,
        )

    @property
    def index_url(self) -> str:
        return self.get_index_url("ppong")

    def get_index_url(self, char_id: str = "ppong") -> str:
        cid = (char_id or "ppong").strip().lower()
        has_glb = cid == "ppong" and any(
            (self.root_dir / rel).exists()
            for rel in ("ppong.glb", "assets/ppong.glb", "models/ppong.glb")
        )
        params = [f"char={cid}"]
        if has_glb:
            params.append("glb=1")
        return f"http://127.0.0.1:{self.port}/index.html?{'&'.join(params)}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except Exception:
            pass


# =============================================================================
# 2. Local LLM Configuration, JSON Parser & Asynchronous QThread Worker
# =============================================================================
@dataclass
class LLMConfig:
    api_url: str = os.environ.get(
        "PPONG_LLM_URL", "http://localhost:8080/v1/chat/completions"
    )
    model: str = os.environ.get("PPONG_LLM_MODEL", "local-model")
    api_key: str = os.environ.get("PPONG_LLM_API_KEY", "sk-local")
    temperature: float = 0.7
    max_tokens: int = 260
    timeout_sec: int = 45
    auto_ollama_fallback: bool = True


@dataclass
class PetPreferences:
    """User preferences saved and loaded automatically from pet_config.json."""

    scale_factor: float = 0.10
    always_on_top: bool = True
    intermittent_gaze: bool = True
    meadow_trail: bool = True
    taskbar_gravity: bool = True
    action_frequency: str = "normal"  # "frequent", "normal", "rare", "off"
    enable_spider: bool = True
    enable_peek: bool = True
    enable_heist: bool = True
    enable_doodle: bool = True
    enable_superman: bool = True
    enable_pc_clean: bool = True
    enable_workday_cairn: bool = True
    auto_start_windows: bool = True
    llm_url: str = os.environ.get("PPONG_LLM_URL", "http://localhost:8080/v1/chat/completions")
    llm_model: str = os.environ.get("PPONG_LLM_MODEL", "local-model")
    llm_api_key: str = os.environ.get("PPONG_LLM_API_KEY", "sk-local")

    @staticmethod
    def config_path_for(char_id: str = "ppong") -> Path:
        cid = (char_id or "ppong").strip().lower()
        if cid == "ppong":
            return CONFIG_FILE_PATH
        return DATA_DIR / f"pet_config_{cid}.json"

    @classmethod
    def load(cls, char_id: str = "ppong") -> "PetPreferences":
        cfg_path = cls.config_path_for(char_id)
        if not cfg_path.exists() and char_id != "ppong" and CONFIG_FILE_PATH.exists():
            cfg_path = CONFIG_FILE_PATH
        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                return cls(
                    scale_factor=0.10,
                    always_on_top=bool(data.get("always_on_top", True)),
                    intermittent_gaze=bool(data.get("intermittent_gaze", True)),
                    meadow_trail=bool(data.get("meadow_trail", True)),
                    taskbar_gravity=bool(data.get("taskbar_gravity", True)),
                    action_frequency=str(data.get("action_frequency", "normal")),
                    enable_spider=bool(data.get("enable_spider", True)),
                    enable_peek=bool(data.get("enable_peek", True)),
                    enable_heist=bool(data.get("enable_heist", True)),
                    enable_doodle=bool(data.get("enable_doodle", True)),
                    enable_superman=bool(data.get("enable_superman", True)),
                    enable_pc_clean=bool(data.get("enable_pc_clean", True)),
                    enable_workday_cairn=bool(data.get("enable_workday_cairn", True)),
                    auto_start_windows=bool(data.get("auto_start_windows", True)),
                    llm_url=str(data.get("llm_url", os.environ.get("PPONG_LLM_URL", "http://localhost:8080/v1/chat/completions"))),
                    llm_model=str(data.get("llm_model", os.environ.get("PPONG_LLM_MODEL", "local-model"))),
                    llm_api_key=str(data.get("llm_api_key", os.environ.get("PPONG_LLM_API_KEY", "sk-local"))),
                )
            except Exception as e:
                sys.stderr.write(f"[Config] Error reading {cfg_path.name}: {e}\n")
        return cls()

    def save(self, char_id: str = "ppong") -> None:
        cfg_path = self.config_path_for(char_id)
        try:
            data = {
                "scale_factor": self.scale_factor,
                "always_on_top": self.always_on_top,
                "intermittent_gaze": self.intermittent_gaze,
                "meadow_trail": self.meadow_trail,
                "taskbar_gravity": self.taskbar_gravity,
                "action_frequency": self.action_frequency,
                "enable_spider": self.enable_spider,
                "enable_peek": self.enable_peek,
                "enable_heist": self.enable_heist,
                "enable_doodle": self.enable_doodle,
                "enable_superman": self.enable_superman,
                "enable_pc_clean": self.enable_pc_clean,
                "enable_workday_cairn": self.enable_workday_cairn,
                "auto_start_windows": self.auto_start_windows,
                "llm_url": self.llm_url,
                "llm_model": self.llm_model,
                "llm_api_key": self.llm_api_key,
            }
            cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[Config] Error writing {cfg_path.name}: {e}\n")


def parse_structured_llm_output_with_emotion(raw_text: str) -> tuple[str, str, str]:
    """
    Robustly extracts {"reply": "...", "action": "...", "emotion": "..."}
    from Local LLM responses, handling <think> blocks, markdown fences, or plain-text fallbacks.
    """
    if not raw_text:
        return ("Ppong! My rainbow horn fizzled for a second—say that again? 🌈", "Idle", "")

    # Strip reasoning blocks (e.g., DeepSeek-R1 / Qwen3 <think>...</think>)
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()

    # Strip markdown ```json ... ``` fences if present
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    candidate = fence_match.group(1).strip() if fence_match else cleaned

    # Locate outermost JSON object braces if surrounded by stray text
    if not candidate.startswith("{"):
        start_idx = candidate.find("{")
        end_idx = candidate.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = candidate[start_idx : end_idx + 1]

    try:
        data = json.loads(candidate)
        if isinstance(data, dict):
            reply = str(data.get("reply") or data.get("message") or data.get("text") or "").strip()
            raw_action = str(data.get("action") or "Talk").strip()
            emotion = str(data.get("emotion") or "").strip().lower()
            action = _normalize_action(raw_action)
            if reply:
                return (reply, action, emotion)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # Fallback if a small local model ignored JSON formatting and replied in plain text
    plain_reply = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL).strip()
    plain_reply = plain_reply[:320] if plain_reply else "Hehe, I'm right here with you! ✨"
    return (plain_reply, "Talk", "")


def _normalize_emotion(raw_emotion: str) -> str:
    if not raw_emotion:
        return ""
    low = raw_emotion.lower().strip()
    for em in CANONICAL_EMOTIONS:
        if em in low:
            return em
    if "joy" in low or "glad" in low or "smile" in low:
        return "happy"
    if "thrill" in low or "cheer" in low or "party" in low:
        return "excited"
    if "wonder" in low or "question" in low or "inspect" in low:
        return "curious"
    if "tired" in low or "drowsy" in low or "nap" in low or "sleep" in low or "yawn" in low:
        return "sleepy"
    if "blush" in low or "timid" in low or "embarrass" in low:
        return "shy"
    if "shock" in low or "gasp" in low or "whoa" in low:
        return "surprised"
    if "angry" in low or "grumpy" in low or "sulky" in low or "huff" in low or "mad" in low:
        return "pouty"
    if "heart" in low or "affection" in low or "adore" in low or "hug" in low:
        return "loving"
    if "cry" in low or "tear" in low or "down" in low or "unhappy" in low or "gloom" in low:
        return "sad"
    if "confident" in low or "hero" in low or "boast" in low or "win" in low or "victory" in low:
        return "proud"
    return ""


def _normalize_action(raw_action: str, allow_all_3d: bool = False) -> str:
    allowed = ALL_3D_ACTIONS if allow_all_3d else VALID_ACTIONS
    tokens = re.split(r"[|,/;\s]+", raw_action.strip())
    for tok in tokens:
        low = tok.lower().replace("_", "").replace("-", "")
        for valid in allowed:
            if low == valid.lower():
                return valid
    low_full = raw_action.lower()
    if "spin" in low_full or "twirl" in low_full:
        return "HappySpin"
    if "dance" in low_full or "groove" in low_full:
        return "Dance"
    if "curious" in low_full or "tilt" in low_full or "wonder" in low_full:
        return "Curious"
    if "stretch" in low_full or "yawn" in low_full:
        return "Stretch"
    if "sleep" in low_full or "drowsy" in low_full or "nap" in low_full:
        return "Sleepy"
    if "shy" in low_full or "blush" in low_full or "bashful" in low_full:
        return "Shy"
    if "pout" in low_full or "grumpy" in low_full or "sulky" in low_full or "huff" in low_full:
        return "Pout"
    if "love" in low_full or "heart" in low_full or "adore" in low_full:
        return "Love"
    if "sad" in low_full or "cry" in low_full or "sniffle" in low_full:
        return "Sad"
    if "proud" in low_full or "confident" in low_full or "hero" in low_full:
        return "Proud"
    if "snack" in low_full or "eat" in low_full or "munch" in low_full or "treat" in low_full or "feed" in low_full:
        return "Snack"
    if "sit" in low_full:
        return "Sit"
    if allow_all_3d:
        if "run" in low_full or "trot" in low_full or "dash" in low_full:
            return "Run"
        if "walk" in low_full or "stroll" in low_full:
            return "Walk"
        if "poke" in low_full or "boop" in low_full:
            return "Poke"
        if "pet" in low_full or "purr" in low_full:
            return "Pet"
        if "land" in low_full or "drop" in low_full:
            return "DropLand"
    if "wave" in low_full or "greet" in low_full or "hi" in low_full:
        return "Wave"
    if "jump" in low_full or "cheer" in low_full or "happy" in low_full:
        return "Jump"
    if "idle" in low_full or "calm" in low_full or "rest" in low_full:
        return "Idle"
    return "Talk"


class LLMWorker(QThread):
    """
    Asynchronous worker thread communicating with an OpenAI-compatible Local LLM
    (e.g., llama-server at http://localhost:8080/v1/chat/completions or Ollama at :11434).
    """

    response_ready = pyqtSignal(str, str, str)  # (reply_text, action_name, emotion)
    error_occurred = pyqtSignal(str)            # (user_friendly_error_message)

    def __init__(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._messages = [dict(m) for m in messages]
        self._config = LLMConfig(**vars(config))

    def _http_post_json(self, url: str, payload: dict, headers: dict, timeout: int) -> dict:
        if _requests_lib is not None:
            resp = _requests_lib.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _http_get_json(self, url: str, timeout: int = 3) -> dict:
        if _requests_lib is not None:
            resp = _requests_lib.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()

        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _discover_ollama_fallback(self) -> Optional[tuple[str, str]]:
        """Checks if Ollama is running locally on :11434 when :8080 is offline."""
        try:
            tags = self._http_get_json("http://localhost:11434/api/tags", timeout=2)
            models = tags.get("models") or []
            if models:
                model_name = models[0].get("name", "llama3.2")
                return ("http://localhost:11434/v1/chat/completions", model_name)
        except Exception:
            pass
        return None

    def _call_completions(self, url: str, model: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }
        base_payload = {
            "model": model,
            "messages": self._messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": False,
        }

        # Attempt structured JSON mode first; gracefully retry without response_format if unsupported
        payload_with_json = {**base_payload, "response_format": {"type": "json_object"}}
        try:
            data = self._http_post_json(url, payload_with_json, headers, self._config.timeout_sec)
        except Exception as first_exc:
            err_str = str(first_exc)
            if "400" in err_str or "422" in err_str or "response_format" in err_str.lower():
                data = self._http_post_json(url, base_payload, headers, self._config.timeout_sec)
            else:
                raise

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("Empty choices returned from Local LLM.")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")

    def run(self) -> None:
        target_url = self._config.api_url
        target_model = self._config.model

        try:
            raw_content = self._call_completions(target_url, target_model)
            reply, action, emotion = parse_structured_llm_output_with_emotion(raw_content)
            self.response_ready.emit(reply, action, emotion)
            return
        except Exception as primary_err:
            # Automatic fallback to local Ollama (:11434) if default :8080 refused connection
            is_default_llama = "localhost:8080" in target_url or "127.0.0.1:8080" in target_url
            if self._config.auto_ollama_fallback and is_default_llama:
                discovered = self._discover_ollama_fallback()
                if discovered is not None:
                    ollama_url, ollama_model = discovered
                    try:
                        raw_content = self._call_completions(ollama_url, ollama_model)
                        reply, action, emotion = parse_structured_llm_output_with_emotion(raw_content)
                        self.response_ready.emit(reply, action, emotion)
                        return
                    except Exception:
                        pass

            self.error_occurred.emit(str(primary_err))


# =============================================================================
# 3. Floating Speech Bubble Widget & Dark-Mode Chat Input Bar
# =============================================================================
class SpeechBubbleWidget(QWidget):
    """Independent top-level frameless 3D casual game speech bubble with concise text normalization,
    exact bounding height (zero text clipping), and dual-pet non-overlapping avoidance."""

    def __init__(self, host_pet: Optional[QWidget] = None) -> None:
        super().__init__(None)
        self._host_pet = host_pet
        self._tail_height = 10
        self._anchor_mode = "above"  # "above" | "right" | "left" | "arena"
        self._body_w = 240
        self._body_h = 56
        self._tail_x = 120.0
        self._tail_y = 28.0
        self._fading_out = False
        self._current_text = ""
        self._bg_grad_top = QColor(17, 24, 39, 216)
        self._bg_grad_bot = QColor(10, 15, 28, 228)
        self._ink_color = QColor("#F8FAFC")
        self._border_tint = QColor(255, 255, 255, 42)
        self._last_backdrop_sample_time = 0.0
        self._explicit_backdrop_rgb: Optional[tuple[int, int, int]] = None

        self._apply_window_flags(getattr(host_pet, "_always_on_top", True))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setWindowOpacity(0.0)

        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        init_font = QFont("Pretendard", 10, QFont.Weight.DemiBold)
        init_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._label.setFont(init_font)
        self._label.setStyleSheet(
            "color: #F8FAFC; background: transparent; border: none; padding: 2px 2px 2px 8px; letter-spacing: -0.2px;"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 12, 18, 12 + self._tail_height)
        self._layout.addWidget(self._label)

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(160)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.fade_out)

        self.hide()

    @staticmethod
    def _clean_concise_text(raw_text: str) -> str:
        """Removes verbose shortcut parenthetical hints, collapses wordy filler, and formats crisp line breaks."""
        import re
        t = str(raw_text or "").strip()
        if not t:
            return ""
        # Strip parenthetical shortcut/instruction blocks like (Ctrl+R ...), (해제: ...), (보유 포인트 ... 구매 가능!)
        t = re.sub(r"\([^)]*(?:Ctrl|사령부|대장간|구매\s*가능|해제:|흔들면)[^)]*\)", "", t)
        # Clean redundant spaces
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.splitlines()]
        lines = [ln for ln in lines if ln]
        if not lines:
            return raw_text.strip()
        # Keep at most 2 concise lines; if 1 long line (> 26 chars), split naturally at punctuation or midpoint space
        if len(lines) == 1 and len(lines[0]) > 26:
            s = lines[0]
            # Look for punctuation split near middle
            mid = len(s) // 2
            best_idx = -1
            for m in re.finditer(r"[!?\.~,|·]|\s", s):
                idx = m.end()
                if 10 <= idx <= len(s) - 8:
                    if best_idx == -1 or abs(idx - mid) < abs(best_idx - mid):
                        best_idx = idx
            if best_idx != -1:
                lines = [s[:best_idx].strip(), s[best_idx:].strip()]
        elif len(lines) > 2:
            lines = lines[:2]
        return "\n".join(lines)

    def _apply_window_flags(self, always_on_top: bool) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def sync_always_on_top(self, enabled: bool) -> None:
        was_vis = self.isVisible()
        self._apply_window_flags(enabled)
        if was_vis:
            self.show()

    def _current_avail(self) -> QRect:
        pet = self._host_pet
        if pet is not None:
            center = pet.frameGeometry().center()
            screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        else:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _horn_screen_pos(self) -> tuple[int, int]:
        pet = self._host_pet
        if pet is None:
            return (400, 400)
        scale = float(getattr(pet, "_scale_factor", 0.10))
        live = getattr(pet, "_live_head_anchor", None)
        if live is not None and not getattr(pet, "_in_battle_arena", False):
            lx, ly = live
            lx_c = max(20, min(pet.width() - 20, int(lx)))
            ly_c = max(-40, min(pet.height(), int(ly)))
            return (pet.x() + lx_c, pet.y() + ly_c)
        hx = pet.x() + pet.width() // 2
        hy = pet.y() + int(round(469.1 - 371.5 * scale))
        return (hx, hy)

    def reposition(self) -> None:
        if self._body_w <= 0 or self._host_pet is None:
            return
        pet = self._host_pet
        avail = self._current_avail()
        scale = float(getattr(pet, "_scale_factor", 0.10))
        tail = self._tail_height

        if getattr(pet, "_in_battle_arena", False):
            self._anchor_mode = "arena"
            win_w = min(self._body_w, avail.width() - 24)
            win_h = self._body_h
            self._layout.setContentsMargins(22, 12, 18, 12)
            x = avail.center().x() - win_w // 2
            y = avail.top() + 148
        else:
            hx, hy = self._horn_screen_pos()
            win_w = min(self._body_w, avail.width() - 24)
            win_h = self._body_h + tail
            above_y = hy - 18 - win_h
            if above_y >= avail.top() + 8:
                self._anchor_mode = "above"
                self._layout.setContentsMargins(22, 12, 18, 12 + tail)
                x = max(avail.left() + 8, min(avail.right() - win_w - 8, hx - win_w // 2))
                y = min(avail.bottom() - win_h - 8, above_y)
                self._tail_x = max(24.0, min(float(win_w - 24), float(hx - x)))
            else:
                offset_x = int(50 + 68 * scale)
                win_w = min(self._body_w + tail, avail.width() - 24)
                win_h = self._body_h
                right_x = hx + offset_x
                if right_x + win_w <= avail.right() - 8:
                    self._anchor_mode = "right"
                    self._layout.setContentsMargins(22 + tail, 12, 18, 12)
                    x = right_x
                else:
                    self._anchor_mode = "left"
                    self._layout.setContentsMargins(22, 12, 18 + tail, 12)
                    x = max(avail.left() + 8, hx - offset_x - win_w)
                y = max(avail.top() + 8, min(avail.bottom() - win_h - 8, hy + 8))
                self._tail_y = max(20.0, min(float(win_h - 20), float(hy + 20 - y)))

            # Dual-Pet Speech Bubble Anti-Overlap Avoidance (Purely visual, zero character physics impact)
            coord = getattr(pet, "coordinator", None)
            if coord is not None:
                partner = coord.get_partner(pet)
                if partner is not None and hasattr(partner, "speech_bubble"):
                    pb = partner.speech_bubble
                    if pb is not None and pb.isVisible() and not getattr(pb, "_fading_out", False):
                        my_rect = QRect(x, y, win_w, win_h)
                        p_rect = pb.geometry()
                        if my_rect.intersects(p_rect.adjusted(-6, -6, 6, 6)):
                            if getattr(pet, "char_id", "ppong") == "tree":
                                cand_above = p_rect.top() - win_h - 8
                                if cand_above >= avail.top() + 8:
                                    y = cand_above
                                else:
                                    x = max(avail.left() + 8, p_rect.left() - win_w - 10)
                            else:
                                cand_right = p_rect.right() + 10
                                if cand_right + win_w <= avail.right() - 8:
                                    x = cand_right
                                else:
                                    cand_above = p_rect.top() - win_h - 8
                                    if cand_above >= avail.top() + 8:
                                        y = cand_above
                            if self._anchor_mode == "above":
                                self._tail_x = max(22.0, min(float(win_w - 22), float(hx - x)))

        visual_sig = (win_w, win_h, self._anchor_mode, int(round(self._tail_x)), int(round(self._tail_y)))
        geom_sig = (x, y, visual_sig)
        if getattr(self, "_last_geom_sig", None) == geom_sig:
            return
        prev_vis_sig = getattr(self, "_last_visual_sig", None)
        self._last_geom_sig = geom_sig
        self._last_visual_sig = visual_sig
        if prev_vis_sig == visual_sig and self.width() == win_w and self.height() == win_h:
            self.move(x, y)
        else:
            self.setGeometry(x, y, win_w, win_h)
            self.update()

    def show_message(
        self,
        text: str,
        duration_ms: Optional[int] = None,
        anchor_bottom_y: Optional[int] = None,
        scale_factor: Optional[float] = None,
    ) -> int:
        # Immediately cancel any previous bubble timer/fade and replace cleanly (never stack behind!)
        self._dismiss_timer.stop()
        self._fade_anim.stop()
        self._fading_out = False

        clean_text = self._clean_concise_text(text)
        pet = self._host_pet
        if pet is not None and getattr(pet, "_in_battle_arena", False):
            self.hide()
            pet._run_js(
                f"typeof window.showDefenseNotice === 'function' && "
                f"window.showDefenseNotice({json.dumps(clean_text, ensure_ascii=False)});"
            )
            return int(duration_ms or 3200)

        self._current_text = clean_text
        self._label.setText(clean_text)

        if scale_factor is None:
            scale_factor = float(getattr(pet, "_scale_factor", 0.10)) if pet is not None else 0.10

        avail = self._current_avail()
        max_w = min(324, avail.width() - 24)

        font = QFont("Pretendard")
        font.setPointSizeF(9.8 if scale_factor < 0.35 else 10.3)
        font.setWeight(QFont.Weight.DemiBold)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self._label.setFont(font)

        fm = QFontMetrics(font)
        lines = clean_text.splitlines() or [clean_text]
        longest_line_px = max((fm.horizontalAdvance(ln) for ln in lines), default=140)
        body_w = max(176, min(max_w, longest_line_px + 56))
        inner_w = body_w - 44

        # Use QLabel.heightForWidth for exact multi-line + emoji height so top/bottom lines never clip!
        label_h = self._label.heightForWidth(inner_w)
        if label_h <= 0:
            text_rect = fm.boundingRect(
                QRect(0, 0, inner_w, 400),
                int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft),
                clean_text,
            )
            label_h = text_rect.height()
        body_h = max(46, min(164, label_h + 28))

        self._body_w = body_w
        self._body_h = body_h
        self.reposition()
        self._sample_backdrop_palette(force=True)

        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.update()

        # Also reposition partner bubble if visible so neither overlaps
        coord = getattr(pet, "coordinator", None) if pet is not None else None
        if coord is not None:
            partner = coord.get_partner(pet)
            if partner is not None and hasattr(partner, "speech_bubble") and partner.speech_bubble.isVisible():
                partner.speech_bubble.reposition()

        if duration_ms is None:
            duration_ms = max(2800, min(6500, len(clean_text) * 75))
        if duration_ms > 0:
            self._dismiss_timer.start(duration_ms)
        return duration_ms

    def fade_out(self) -> None:
        if not self.isVisible():
            return
        self._fading_out = True
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self._fading_out:
            self.hide()
            self._fading_out = False

    def _sample_backdrop_palette(self, force: bool = False) -> None:
        """Applies a consistent Cupertino / Material Dark-Glass palette without synchronous DWM screen.grabWindow stalls."""
        now = time.perf_counter()
        if not force and (now - self._last_backdrop_sample_time) < 0.25:
            return
        self._last_backdrop_sample_time = now

        avg_rgb: tuple[int, int, int] = self._explicit_backdrop_rgb or (22, 30, 46)
        br, bg, bb = avg_rgb
        r0 = max(14, min(38, int(br * 0.14 + 17 * 0.86)))
        g0 = max(19, min(46, int(bg * 0.14 + 24 * 0.86)))
        b0 = max(30, min(64, int(bb * 0.14 + 39 * 0.86)))
        r1 = max(9, int(r0 * 0.76))
        g1 = max(13, int(g0 * 0.76))
        b1 = max(22, int(b0 * 0.76))
        self._bg_grad_top = QColor(r0, g0, b0, 220)
        self._bg_grad_bot = QColor(r1, g1, b1, 234)
        self._ink_color = QColor("#F8FAFC")
        self._border_tint = QColor(255, 255, 255, 44)

        if not getattr(self, "_label_styled_once", False):
            self._label_styled_once = True
            self._label.setStyleSheet(
                f"color: {self._ink_color.name()}; background: transparent; border: none; "
                "padding: 2px 2px 2px 8px; letter-spacing: -0.2px;"
            )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        tail = float(self._tail_height)
        mode = self._anchor_mode

        if mode == "above":
            body_rect = QRectF(3.0, 2.5, w - 6.0, h - tail - 3.5)
            cx = max(26.0, min(w - 26.0, self._tail_x))
            by = body_rect.bottom()
            tail_poly = QPolygonF(
                [QPointF(cx - 6.5, by - 1.0), QPointF(cx + 6.5, by - 1.0), QPointF(cx, by + tail - 1.5)]
            )
        elif mode == "right":
            body_rect = QRectF(3.0 + tail, 2.5, w - tail - 6.0, h - 5.0)
            cy = max(20.0, min(h - 20.0, self._tail_y))
            lx = body_rect.left()
            tail_poly = QPolygonF(
                [QPointF(lx + 1.0, cy - 6.0), QPointF(lx + 1.0, cy + 6.0), QPointF(lx - tail + 1.5, cy)]
            )
        elif mode == "left":
            body_rect = QRectF(3.0, 2.5, w - tail - 6.0, h - 5.0)
            cy = max(20.0, min(h - 20.0, self._tail_y))
            rx = body_rect.right()
            tail_poly = QPolygonF(
                [QPointF(rx - 1.0, cy - 6.0), QPointF(rx - 1.0, cy + 6.0), QPointF(rx + tail - 1.5, cy)]
            )
        else:
            body_rect = QRectF(3.0, 2.5, w - 6.0, h - 5.0)
            tail_poly = None

        radius = 15.0
        path = QPainterPath()
        path.addRoundedRect(body_rect, radius, radius)
        if tail_poly is not None:
            tail_path = QPainterPath()
            tail_path.addPolygon(tail_poly)
            full_path = path.united(tail_path)
        else:
            full_path = path

        # 1. Flat / Minimal ambient elevation shadow (reduced heavy 3D shadow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.save()
        painter.translate(0.0, 1.8)
        painter.setBrush(QColor(2, 6, 23, 34))
        painter.drawPath(full_path)
        painter.restore()

        # 2. Dark-Mode Glassmorphic surface with subtle Neumorphic dual-tone depth
        grad = QLinearGradient(0, body_rect.top(), 0, body_rect.bottom())
        grad.setColorAt(0.0, self._bg_grad_top)
        grad.setColorAt(1.0, self._bg_grad_bot)

        pet = self._host_pet
        is_tree = getattr(pet, "char_id", "ppong") == "tree"
        # High-contrast semantic accent (Emerald Mint for Tree, Coral Sky/Amber for Ppong)
        accent_col = QColor(52, 211, 153, 235) if is_tree else QColor(56, 189, 248, 235)
        hairline_border = QColor(
            int(255 * 0.78 + accent_col.red() * 0.22),
            int(255 * 0.78 + accent_col.green() * 0.22),
            int(255 * 0.78 + accent_col.blue() * 0.22),
            48,
        )

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(hairline_border, 1.0))
        painter.drawPath(full_path)

        # 3. Neumorphic soft inner highlight (top-left specular) & bottom recess
        inner_hi = body_rect.adjusted(1.0, 1.0, -1.0, -1.0)
        hi_grad = QLinearGradient(inner_hi.left(), inner_hi.top(), inner_hi.left(), inner_hi.bottom())
        hi_grad.setColorAt(0.0, QColor(255, 255, 255, 34))
        hi_grad.setColorAt(0.45, QColor(255, 255, 255, 6))
        hi_grad.setColorAt(1.0, QColor(2, 6, 23, 52))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(hi_grad), 1.0))
        painter.drawRoundedRect(inner_hi, radius - 1.0, radius - 1.0)

        # 4. Cupertino / Material minimal left accent pill indicator (replaces noisy corner dots)
        pill_h = max(14.0, min(26.0, body_rect.height() - 22.0))
        pill_y = body_rect.center().y() - pill_h * 0.5
        pill_x = body_rect.left() + 10.5
        # Soft neumorphic recessed track behind the accent bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(2, 6, 23, 110))
        painter.drawRoundedRect(QRectF(pill_x - 0.8, pill_y - 0.8, 4.6, pill_h + 1.6), 2.3, 2.3)
        # High-contrast glowing accent bar
        painter.setBrush(accent_col)
        painter.drawRoundedRect(QRectF(pill_x, pill_y, 3.0, pill_h), 1.5, 1.5)
        painter.end()


class _RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class _RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class _RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class _RAWINPUT_KB(ctypes.Structure):
    _fields_ = [
        ("header", _RAWINPUTHEADER),
        ("keyboard", _RAWKEYBOARD),
    ]


class GlobalTypingTracker(QWidget):
    """Privacy-safe global OS keystroke counter (Raw Input WM_INPUT + GetAsyncKeyState fallback).
    NEVER stores, logs, or transmits any key identity/character — counts rising edges only toward the
    10,000-keystroke hardcore leveling curve."""

    def __init__(self, rpg_state: RPGWorldState, pets: Optional[list] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent if isinstance(parent, QWidget) else None)
        self._rpg = rpg_state
        self._pets: list = list(pets or [])
        self._pending_count = 0
        self._sec_bucket = int(time.perf_counter())
        self._sec_count = 0
        self._recent_ts: deque[float] = deque()
        self._raw_input_ok = False
        self._prev_vk_down: set[int] = set()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setFixedSize(1, 1)
        self.move(-32000, -32000)
        self.setWindowOpacity(0.0)
        try:
            u32 = ctypes.windll.user32
            u32.RegisterRawInputDevices.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.UINT]
            u32.RegisterRawInputDevices.restype = wintypes.BOOL
            u32.GetRawInputData.argtypes = [
                wintypes.HANDLE,
                wintypes.UINT,
                wintypes.LPVOID,
                ctypes.POINTER(wintypes.UINT),
                wintypes.UINT,
            ]
            u32.GetRawInputData.restype = wintypes.UINT
            hwnd = int(self.winId())
            dev = _RAWINPUTDEVICE(0x01, 0x06, 0x00000100, wintypes.HWND(hwnd))
            self._raw_input_ok = bool(u32.RegisterRawInputDevices(ctypes.byref(dev), 1, ctypes.sizeof(_RAWINPUTDEVICE)))
        except Exception:
            self._raw_input_ok = False

        self._poll_timer = None
        if not self._raw_input_ok:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(30)
            self._poll_timer.timeout.connect(self._poll_async_key_fallback)
            self._poll_timer.start()

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(2000)
        self._flush_timer.timeout.connect(self.flush_now)
        self._flush_timer.start()

    def _increment_rising_edge(self) -> None:
        now = time.perf_counter()
        sec = int(now)
        if sec != self._sec_bucket:
            self._sec_bucket = sec
            self._sec_count = 0
        if self._sec_count >= 22:
            return
        self._sec_count += 1
        self._pending_count += 1
        self._recent_ts.append(now)

    def _poll_async_key_fallback(self) -> None:
        try:
            u32 = ctypes.windll.user32
            for vk in (0x08, 0x0D, 0x20, *range(0x30, 0x3A), *range(0x41, 0x5B), *range(0xBA, 0xC1)):
                down = bool(u32.GetAsyncKeyState(vk) & 0x8000)
                if down and vk not in self._prev_vk_down:
                    self._prev_vk_down.add(vk)
                    self._increment_rising_edge()
                elif not down and vk in self._prev_vk_down:
                    self._prev_vk_down.discard(vk)
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        try:
            if self._raw_input_ok and bytes(eventType) == b"windows_generic_MSG":
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x00FF:  # WM_INPUT
                    sz = wintypes.UINT(ctypes.sizeof(_RAWINPUT_KB))
                    raw = _RAWINPUT_KB()
                    res = ctypes.windll.user32.GetRawInputData(
                        wintypes.HANDLE(msg.lParam),
                        0x10000003,  # RID_INPUT
                        ctypes.byref(raw),
                        ctypes.byref(sz),
                        ctypes.sizeof(_RAWINPUTHEADER),
                    )
                    if res != 0xFFFFFFFF and raw.header.dwType == 1:  # RIM_TYPEKEYBOARD
                        if (raw.keyboard.Flags & 0x01) == 0:  # RI_KEY_MAKE only
                            self._increment_rising_edge()
        except Exception:
            pass
        return (False, 0)

    def flush_now(self) -> Optional[dict]:
        now = time.perf_counter()
        while self._recent_ts and (now - self._recent_ts[0]) > 60.0:
            self._recent_ts.popleft()
        live_cpm = len(self._recent_ts)
        delta = self._pending_count
        self._pending_count = 0
        if delta <= 0:
            prev_cpm = getattr(self, "_last_synced_cpm", -1)
            self._rpg.live_cpm = live_cpm
            if live_cpm != prev_cpm:
                self._last_synced_cpm = live_cpm
                typing_payload = json.dumps(self._rpg.typing_bonuses(), ensure_ascii=False)
                for p in self._pets:
                    if getattr(p, "_web_ready", False):
                        p._run_js(f"typeof window.syncTypingHudPulse === 'function' && window.syncTypingHudPulse({typing_payload});")
                    if hasattr(p, "rpg_hub") and p.rpg_hub.isVisible():
                        p.rpg_hub.refresh_ui()
            return None

        self._last_synced_cpm = live_cpm
        res = self._rpg.record_keystrokes(delta, live_cpm=live_cpm)
        self._rpg.save()
        typing_payload = json.dumps(self._rpg.typing_bonuses(), ensure_ascii=False)
        for p in self._pets:
            if getattr(p, "_web_ready", False):
                p._run_js(f"typeof window.syncTypingHudPulse === 'function' && window.syncTypingHudPulse({typing_payload});")
            if hasattr(p, "rpg_hub") and p.rpg_hub.isVisible():
                p.rpg_hub.refresh_ui()

        if res.get("leveled_up"):
            banner = f"⌨️ 타이핑 각성 Lv.{res['new_level']} [{res['rank_title']}] 달성!! ✨"
            for p in self._pets[:1]:
                if hasattr(p, "speech_bubble"):
                    p.speech_bubble.show_message(banner, duration_ms=5200)
        elif res.get("milestones"):
            m_txt = res["milestones"][-1]
            for p in self._pets[:1]:
                if hasattr(p, "speech_bubble"):
                    p.speech_bubble.show_message(f"🎯 {m_txt}", duration_ms=4200)
        return res

    def stop(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
        self._flush_timer.stop()
        self.flush_now()


class LLMSettingsDialog(QDialog):
    """AAA 3D Game UI dialog to inspect or update Local LLM endpoint."""

    def __init__(self, config: LLMConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ 뽕뽕이 — 로컬 LLM AI 설정")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(700)
        self._config = config

        self.setStyleSheet(
            f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0b1328, stop:1 #030712);
                color: {COLOR_TEXT_MAIN};
                border: 2px solid #fbbf24;
                border-radius: 16px;
            }}
            QLabel {{
                color: #f8fafc;
                font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
                font-size: 19px;
                font-weight: 700;
            }}
            QLineEdit {{
                background-color: #0f172a;
                color: #f8fafc;
                border: 1.5px solid #334155;
                border-radius: 10px;
                padding: 11px 15px;
                font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
                font-size: 18px;
            }}
            QLineEdit:focus {{
                border: 2px solid #38bdf8;
                background-color: #081022;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                color: #f8fafc;
                border: 1.5px solid #475569;
                border-radius: 10px;
                padding: 11px 24px;
                font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
                font-size: 18px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                border-color: #fbbf24;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)

        title = QLabel("🧠 로컬 LLM AI 연결 설정", self)
        title.setStyleSheet("color: #fde047; font-size: 24px; font-weight: 900;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)

        self.url_edit = QLineEdit(config.api_url, self)
        self.url_edit.setPlaceholderText("http://localhost:8080/v1/chat/completions")

        self.model_edit = QLineEdit(config.model, self)
        self.model_edit.setPlaceholderText("local-model (or llama3.2, qwen2.5, etc.)")

        self.key_edit = QLineEdit(config.api_key, self)
        self.key_edit.setPlaceholderText("sk-local (optional)")

        form.addRow("Endpoint URL:", self.url_edit)
        form.addRow("Model Name:", self.model_edit)
        form.addRow("API Key:", self.key_edit)
        layout.addLayout(form)

        hint = QLabel(
            "llama-server (localhost:8080), Ollama (localhost:11434/v1/chat/completions), LM Studio, vLLM을 지원합니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #94a3b8; font-size: 16px; font-weight: 600;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()
        cancel_btn = QPushButton("취소", self)
        save_btn = QPushButton("💾 저장 완료", self)
        save_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0284c7,stop:1 #0369a1); "
            "border: 1.5px solid #38bdf8; color: #ffffff; font-family: 'Pretendard', 'Malgun Gothic', sans-serif; font-size: 18px; font-weight: 800; padding: 11px 26px; border-radius: 10px; }"
            "QPushButton:hover { border-color: #fde047; }"
        )
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self) -> None:
        url = self.url_edit.text().strip()
        model = self.model_edit.text().strip()
        key = self.key_edit.text().strip()
        if url:
            self._config.api_url = url
        if model:
            self._config.model = model
        if key:
            self._config.api_key = key
        self.accept()


# =============================================================================
# 3.5 Screen Content Heist 2.0 Overlays (Torn Paper Hole & Stolen Piece Card)
# =============================================================================
class ScreenHoleOverlay(QWidget):
    """
    Transparent Always-On-Top desktop overlay patch displaying a realistic torn paper
    void hole at the exact spot where desktop content was grabbed by Ppong-ppong-i.
    """

    hole_clicked = pyqtSignal()

    def __init__(self, rect: QRect, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setGeometry(rect)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("🕳️ 도난당한 화면 조각 위치 (클릭하면 뽕뽕이에게 복구를 요청합니다)")

        # Precompute deterministic torn-paper jagged perimeter
        w = float(rect.width())
        h = float(rect.height())
        self._torn_poly = self._generate_torn_perimeter(w, h, teeth=14)
        self._inner_void_poly = self._generate_torn_perimeter(w - 12.0, h - 12.0, teeth=12, offset=(6.0, 6.0))

    @staticmethod
    def _generate_torn_perimeter(w: float, h: float, teeth: int = 14, offset: tuple[float, float] = (0.0, 0.0)) -> QPolygonF:
        ox, oy = offset
        poly: list[QPointF] = []
        rnd = random.Random(42)  # Deterministic seed avoids repaint flicker

        # Top edge
        for i in range(teeth + 1):
            x = ox + (w * i) / teeth
            y = oy + (rnd.uniform(-3.5, 3.5) if 0 < i < teeth else 0.0)
            poly.append(QPointF(x, y))
        # Right edge
        for i in range(teeth + 1):
            y = oy + (h * i) / teeth
            x = ox + w + (rnd.uniform(-3.5, 3.5) if 0 < i < teeth else 0.0)
            poly.append(QPointF(x, y))
        # Bottom edge
        for i in range(teeth + 1):
            x = ox + w - (w * i) / teeth
            y = oy + h + (rnd.uniform(-3.5, 3.5) if 0 < i < teeth else 0.0)
            poly.append(QPointF(x, y))
        # Left edge
        for i in range(teeth + 1):
            y = oy + h - (h * i) / teeth
            x = ox + (rnd.uniform(-3.5, 3.5) if 0 < i < teeth else 0.0)
            poly.append(QPointF(x, y))

        return QPolygonF(poly)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.hole_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Subtle ambient drop shadow under the torn border
        painter.save()
        painter.translate(2.0, 3.0)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(self._torn_poly)
        painter.restore()

        # 2. Torn paper white/cream ragged edge fringe
        painter.setBrush(QColor(241, 245, 249, 230))
        painter.setPen(QPen(QColor(203, 213, 225, 200), 1.5))
        painter.drawPolygon(self._torn_poly)

        # 3. Deep void-hole inside (deep obsidian gradient #020617 to #0f172a)
        void_grad = QLinearGradient(0, 0, 0, self.height())
        void_grad.setColorAt(0.0, QColor("#020617"))
        void_grad.setColorAt(1.0, QColor("#0f172a"))
        painter.setBrush(QBrush(void_grad))
        painter.setPen(QPen(QColor(56, 189, 248, 70), 1.0, Qt.PenStyle.DashLine))
        painter.drawPolygon(self._inner_void_poly)

        # 4. Faint futuristic cyber grid lines inside hole
        grid_pen = QPen(QColor(56, 189, 248, 32), 1.0)
        painter.setPen(grid_pen)
        step_x = max(20, self.width() // 5)
        for gx in range(step_x, self.width() - 10, step_x):
            painter.drawLine(gx, 10, gx, self.height() - 10)
        step_y = max(18, self.height() // 4)
        for gy in range(step_y, self.height() - 10, step_y):
            painter.drawLine(10, gy, self.width() - 10, gy)

        # 5. Centered holographic caution warning
        cx = self.width() // 2
        cy = self.height() // 2

        badge_w = min(230, self.width() - 12)
        badge_h = min(58, self.height() - 12)
        badge_rect = QRect(cx - badge_w // 2, cy - badge_h // 2, badge_w, badge_h)

        painter.setBrush(QColor(2, 6, 23, 210))
        painter.setPen(QPen(QColor("#facc15"), 1.5))
        painter.drawRoundedRect(badge_rect, 10.0, 10.0)

        painter.setFont(QFont(APP_FONT_FAMILY, 11, QFont.Weight.Bold))
        painter.setPen(QColor("#facc15"))
        painter.drawText(
            QRect(badge_rect.left(), badge_rect.top() + 6, badge_w, 24),
            Qt.AlignmentFlag.AlignCenter,
            "⚠️ [화면 일부 도난당함!]",
        )

        painter.setFont(QFont(APP_FONT_FAMILY, 10, QFont.Weight.Medium))
        painter.setPen(QColor("#cbd5e1"))
        painter.drawText(
            QRect(badge_rect.left(), badge_rect.top() + 30, badge_w, 20),
            Qt.AlignmentFlag.AlignCenter,
            "뽕뽕이를 클릭해 복구하세요",
        )
        painter.end()


class StolenPieceWidget(QWidget):
    """
    Floating card widget mounted on DesktopPetWindow showing the actual captured
    desktop content snippet held directly in the character's raised hands (zero white gap).
    """

    clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(140, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("🪟 들고 가는 화면 조각! 클릭해서 되찾으세요!")

        self._pixmap: Optional[QPixmap] = None
        self._scaled_pixmap: Optional[QPixmap] = None
        self.hide()

    def set_content(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self._scaled_pixmap = pixmap.scaled(
            134,
            84,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        if self._scaled_pixmap is None or self._scaled_pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Dynamic running tilt wobble (+-3.2 deg)
        wobble_deg = math.sin(time.perf_counter() * 11.0) * 3.2

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(wobble_deg)
        painter.translate(-cx, -cy)

        card_rect = QRectF(3.0, 3.0, self.width() - 6.0, self.height() - 6.0)

        # 1. Soft drop shadow
        painter.setBrush(QColor(15, 23, 42, 135))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(card_rect.translated(1.5, 2.5), 9.0, 9.0)

        # 2. Clipped actual desktop screenshot filling the entire card (zero white margin!)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(card_rect, 9.0, 9.0)
        painter.save()
        painter.setClipPath(clip_path)

        px = card_rect.left() + (card_rect.width() - self._scaled_pixmap.width()) / 2.0
        py = card_rect.top() + (card_rect.height() - self._scaled_pixmap.height()) / 2.0
        painter.drawPixmap(int(px), int(py), self._scaled_pixmap)
        painter.restore()

        # 3. Sleek 3D game glowing frame around the captured screen piece
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(56, 189, 248, 230), 2.2))
        painter.drawRoundedRect(card_rect, 9.0, 9.0)

        painter.setPen(QPen(QColor(255, 255, 255, 160), 1.0))
        painter.drawRoundedRect(card_rect.adjusted(1.5, 1.5, -1.5, -1.5), 7.5, 7.5)

        # 4. Compact game stamp sticker in top right
        stamp_rect = QRectF(card_rect.right() - 78.0, card_rect.top() + 4.0, 74.0, 20.0)
        painter.setBrush(QColor(239, 68, 68, 225))
        painter.setPen(QPen(QColor("#ffffff"), 1.0))
        painter.drawRoundedRect(stamp_rect, 5.0, 5.0)

        painter.setFont(QFont(GAME_DISPLAY_FONT_FAMILY, 9))
        painter.setPen(QColor("#ffffff"))
        painter.drawText(stamp_rect, Qt.AlignmentFlag.AlignCenter, "화면조각 🪟")

        painter.restore()
        painter.end()


class SpiderWebOverlay(QWidget):
    """
    Full-Monitor Transparent Click-Through Spider Web Overlay:
    Draws a single, realistic, dark-toned ultra-thin silk strand from the character's hand
    to the ceiling/wall anchor point with zero duplicate or flashy neon lines.
    """

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._hand_pt: Optional[QPointF] = None
        self._anchor_pt: Optional[QPointF] = None
        self._char_id: str = "ppong"
        self._sag_px: float = 0.0
        self._last_paint_time: float = 0.0
        self.hide()

    def set_web_line(
        self,
        avail: QRect,
        hand_global: QPointF,
        anchor_global: QPointF,
        char_id: str = "ppong",
        sag_px: float = 0.0,
    ) -> None:
        geom_changed = self.geometry() != avail
        if geom_changed:
            self.setGeometry(avail)
        self._hand_pt = QPointF(hand_global.x() - avail.left(), hand_global.y() - avail.top())
        self._anchor_pt = QPointF(anchor_global.x() - avail.left(), anchor_global.y() - avail.top())
        self._char_id = char_id
        self._sag_px = float(sag_px)
        was_visible = self.isVisible()
        if not was_visible:
            self.show()
        now = time.perf_counter()
        if geom_changed or not was_visible or (now - self._last_paint_time) >= 0.014:
            self._last_paint_time = now
            self.update()

    def paintEvent(self, _event) -> None:
        if self._hand_pt is None or self._anchor_pt is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        p1 = self._hand_pt
        p2 = self._anchor_pt

        path = QPainterPath(p1)
        if abs(self._sag_px) > 0.4:
            mid = QPointF((p1.x() + p2.x()) * 0.5, (p1.y() + p2.y()) * 0.5 + self._sag_px)
            path.quadTo(mid, p2)
        else:
            path.lineTo(p2)

        # 1. Ultra-subtle dark ambient contact shadow for visibility over bright wallpapers
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(15, 23, 42, 76), 2.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

        # 2. Primary dark-toned thin graphite/charcoal silk strand (~1.15px)
        painter.setPen(QPen(QColor(45, 55, 72, 212), 1.15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

        # 3. Hairline muted silver-slate micro-sheen (0.55px) so it reads like real taut silk over dark UI too
        painter.setPen(QPen(QColor(148, 163, 184, 92), 0.55, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

        # 4. Minimal dark adhesive anchor dot (no flashy starburst)
        painter.setBrush(QColor(30, 41, 59, 205))
        painter.setPen(QPen(QColor(100, 116, 139, 135), 0.9))
        painter.drawEllipse(p2, 2.8, 2.8)

        painter.end()


# =============================================================================
# 4. Autonomous State Machine & Frameless Transparent Desktop Pet Window
# =============================================================================
class PetState(Enum):
    IDLE = auto()
    WALK = auto()
    RUN = auto()
    SITTING = auto()
    FALLING = auto()
    PETTING = auto()
    INTERACTING = auto()
    DRAGGING = auto()
    SPIDER_SWING = auto()
    HIDE_AND_SEEK = auto()
    WINDOW_HEIST = auto()
    MAGIC_DOODLE = auto()
    SUPERMAN_FLY = auto()
    SOLO_PLAY = auto()
    EVADING = auto()
    EXCAVATING = auto()
    SKIRMISH = auto()
    WAVE_DEFENSE = auto()
    MINIGAME = auto()
    CAIRN_WORK = auto()


def _create_unicorn_tray_icon() -> QIcon:
    """Renders a crisp programmatic rainbow-horn unicorn badge for the Windows System Tray."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Dark-slate circular badge
    p.setBrush(QColor(COLOR_SURFACE))
    p.setPen(QPen(QColor(COLOR_ACCENT), 3))
    p.drawEllipse(4, 4, 56, 56)

    # White unicorn head silhouette
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#f8fafc"))
    p.drawEllipse(14, 24, 36, 30)

    # Rainbow horn
    horn_grad = QLinearGradient(32, 8, 32, 28)
    horn_grad.setColorAt(0.0, QColor("#ef4444"))
    horn_grad.setColorAt(0.35, QColor("#facc15"))
    horn_grad.setColorAt(0.7, QColor("#22c55e"))
    horn_grad.setColorAt(1.0, QColor("#0ea5e9"))
    p.setBrush(QBrush(horn_grad))
    p.drawPolygon(QPolygonF([QPointF(32, 8), QPointF(24, 27), QPointF(40, 27)]))

    # Teal eyes
    p.setBrush(QColor("#149e96"))
    p.drawEllipse(22, 35, 6, 7)
    p.drawEllipse(36, 35, 6, 7)
    p.end()
    return QIcon(pix)


def _create_tree_tray_icon() -> QIcon:
    """Renders a crisp programmatic evergreen-hood & golden-star badge for '트리' (Tree)."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Dark-slate circular badge with warm gold rim
    p.setBrush(QColor(COLOR_SURFACE))
    p.setPen(QPen(QColor("#facc15"), 3))
    p.drawEllipse(4, 4, 56, 56)

    # Evergreen tree hood triangle
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#2c7c35"))
    p.drawPolygon(QPolygonF([QPointF(32, 13), QPointF(11, 50), QPointF(53, 50)]))

    # Chubby caramel bear face oval inside hood
    p.setBrush(QColor("#e3a57c"))
    p.drawEllipse(19, 30, 26, 20)

    # Espresso bead eyes & rosy cheeks
    p.setBrush(QColor("#231714"))
    p.drawEllipse(24, 37, 5, 5)
    p.drawEllipse(35, 37, 5, 5)
    p.setBrush(QColor("#e5737d"))
    p.drawEllipse(20, 42, 5, 3)
    p.drawEllipse(39, 42, 5, 3)

    # Golden yellow top star
    p.setBrush(QColor("#fde047"))
    p.drawEllipse(27, 7, 10, 10)
    p.end()
    return QIcon(pix)


_SHARED_WEB_PROFILE: Optional[QWebEngineProfile] = None


def get_shared_web_profile(parent: Optional[QObject] = None) -> QWebEngineProfile:
    """Returns a process-wide singleton QWebEngineProfile so multiple DesktopPetWindow instances
    share the persistent Chromium disk cache and IndexedDB ('ppong_mesh_cache_v2') without LevelDB lock conflict."""
    global _SHARED_WEB_PROFILE
    if _SHARED_WEB_PROFILE is None:
        profile_dir = DATA_DIR / "web_profile"
        cache_dir = DATA_DIR / "web_cache"
        profile_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        prof_parent = QApplication.instance() or parent
        _SHARED_WEB_PROFILE = QWebEngineProfile("MinipetProfile", prof_parent)
        _SHARED_WEB_PROFILE.setPersistentStoragePath(str(profile_dir))
        _SHARED_WEB_PROFILE.setCachePath(str(cache_dir))
        _SHARED_WEB_PROFILE.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
    return _SHARED_WEB_PROFILE


class SilentWebEnginePage(QWebEnginePage):
    """Forwards critical JS console errors to stderr and routes __PPONG_SYNC__ bridge events to Python."""

    bridge_event = pyqtSignal(dict)

    def javaScriptConsoleMessage(self, level, message: str, line_id: int, source_id: str) -> None:
        if message and message.startswith("__PPONG_SYNC__:"):
            try:
                raw_json = message[len("__PPONG_SYNC__:") :]
                payload = json.loads(raw_json)
                if isinstance(payload, dict):
                    self.bridge_event.emit(payload)
            except Exception:
                pass
            return
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            sys.stderr.write(f"[WebGL JS Error] {message} (line {line_id})\n")


SOLO_ACTIONS_INFO: dict[str, dict[str, str]] = {
    "mining": {"cat": "모험 & 일상", "title": "⛏️ 바탕화면 채굴 (Desktop Excavation)", "speech": "광맥 반응 감지! 바탕화면 지층을 채굴해 광석과 유물을 캐낼게요! ⛏️💎"},
    "build_house": {"cat": "모험 & 일상", "title": "🏠 집 짓기 (Building House)", "speech": "뚝딱뚝딱! 🔨 나만의 멋진 알록달록 미니 하우스를 짓는 중이에요! 🏠✨"},
    "fishing": {"cat": "모험 & 일상", "title": "🎣 낚시하기 (Fishing)", "speech": "입질이 왔다! 으랏차차~! 🐟 황금 월척 낚았어요! 🎣✨"},
    "hunting": {"cat": "모험 & 일상", "title": "🦋 곤충 채집 (Bug Hunting)", "speech": "살금살금... 얍! 🦋 영롱한 무지개 나비를 채집했어요! 🌟"},
    "explorer": {"cat": "모험 & 일상", "title": "🧭 탐험하기 (Desktop Explorer)", "speech": "미지의 바탕화면 대륙 발견! 🧭 북동쪽으로 전진해볼까요? 🔍✨"},
    "camping": {"cat": "모험 & 일상", "title": "🔥 캠핑 & 마시멜로 (Cozy Camping)", "speech": "타닥타닥... 🔥 노릇노릇 구운 마시멜로 한 입 드실래요? ⛺✨"},
    "drinking": {"cat": "모험 & 일상", "title": "🍻 건배 & 음료 (Cheers Drink)", "speech": "오늘 하루도 수고 많으셨어요! 짠~ 🍻 시원하게 한잔! 💖"},

    "cooking": {"cat": "취미 & 예술", "title": "🍳 팬케이크 요리 (Pancake Chef)", "speech": "뒤집기 한 판! 슉~ 착! 🥞 달콤한 팬케이크 완성이에요! 😋✨"},
    "gardening": {"cat": "취미 & 예술", "title": "🌷 정원 가꾸기 (Little Gardener)", "speech": "무럭무럭 자라라~ 💧 퐁퐁 피어나는 행복의 꽃밭 완성! 🌷🌺"},
    "music_guitar": {"cat": "취미 & 예술", "title": "🎸 기타 연주 (Acoustic Strum)", "speech": "딩가딩가~ 🎵 신나는 바탕화면 힐링 라이브 연주 중! 🎸🎶"},
    "painting": {"cat": "취미 & 예술", "title": "🎨 화가 / 명작 그리기 (Artist Painter)", "speech": "여기에 따뜻한 색감을 톡톡... 🎨 멋진 명작 탄생 임박! 🖼️✨"},
    "reading": {"cat": "취미 & 예술", "title": "📖 마법서 독서 (Magical Reading)", "speech": "책장을 넘길 때마다 지혜가 샘솟아요! 📖 흥미진진한 이야기! 📜✨"},
    "snowman": {"cat": "취미 & 예술", "title": "☃️ 눈사람 만들기 (Building Snowman)", "speech": "동글동글 굴려서 얹고 당근 콕! ☃️ 귀여운 미니 눈사람 완성! ❄️✨"},

    "wizard": {"cat": "직업 & 판타지", "title": "🧙‍♂️ 마법사 변신 (Mystic Wizard)", "speech": "비비디 바비디 부~! ✨ 행운을 부르는 신비한 마법 주문을 걸게요! 🔮🌟"},
    "astronaut": {"cat": "직업 & 판타지", "title": "🧑‍🚀 우주비행사 (Astronaut Moonwalk)", "speech": "휴스턴, 여기는 뽕뽕호! 🚀 바탕화면 무중력 유영 중입니다! 🌌🛰️"},
    "gamer": {"cat": "직업 & 판타지", "title": "🎮 프로 게이머 모드 (Pro Gamer)", "speech": "버튼 연타! 콤보 성공! 🎮 오늘 게임 랭킹 1위 찍었어요! 🏆🔥"},
    "ninja": {"cat": "직업 & 판타지", "title": "🥷 닌자 은신술 (Shadow Ninja)", "speech": "인법 은신술! 슉! 💨 뽕뽕이는 지금 안 보이는 상태예요! 🥷✨"},
    "detective": {"cat": "직업 & 판타지", "title": "🕵️‍♂️ 탐정 추리 (Detective Clue)", "speech": "흠, 범인은 바로... 🔍 바탕화면의 미세한 흔적을 추적 중! 🔎🧐"},
    "barista": {"cat": "직업 & 판타지", "title": "☕ 바리스타 커피 (Hand Drip Coffee)", "speech": "원두의 깊은 풍미를 담아 정성껏 내린 핸드드립 커피 한 잔! ☕🌿"},

    "fitness": {"cat": "스포츠 & 놀이", "title": "🏋️ 헬스 / 바벨 (Power Lifter)", "speech": "흡! 으랏차차~! 🏋️‍♂️ 오늘 3대 500 달성! 득근득근 파워 업! 💪🔥"},
    "bubbles": {"cat": "스포츠 & 놀이", "title": "🫧 비눗방울 놀이 (Soap Bubbles)", "speech": "후우~ 불면 방울방울! 🫧 무지갯빛 비눗방울이 둥실둥실~ 🌈✨"},
    "skateboard": {"cat": "스포츠 & 놀이", "title": "🛹 스케이트보드 (Skate Trick)", "speech": "바닥을 슝 차고 글라이드~! 🛹 멋진 킥플립 묘기 어때요? ⚡😎"},
    "kite": {"cat": "스포츠 & 놀이", "title": "🪁 연날리기 (Sky Kite)", "speech": "바람을 타고 높이높이 날아라! 🪁 하늘 끝까지 올라가네요! 🌤️✨"},
    "telescope": {"cat": "스포츠 & 놀이", "title": "🔭 천체망원경 관측 (Stargazer)", "speech": "저기 반짝이는 건 북극성! 🔭 우주의 신비를 관측 중이에요! 🌟🌌"},
    "treasure": {"cat": "스포츠 & 놀이", "title": "💎 보물찾기 (Treasure Hunter)", "speech": "보물 지도 발견! 쓱싹쓱싹... 💎 번쩍이는 황금 보물상자다! 🪙✨"},

    "picnic": {"cat": "힐링 & 특별", "title": "🍩 피크닉 간식 (Sweet Picnic)", "speech": "달콤한 딸기 도넛 냠냠! 🍩 맛있는 간식 타임 최고예요! 💖"},
    "sleeping": {"cat": "힐링 & 특별", "title": "💤 낮잠 / 꿀잠 (Cozy Nap)", "speech": "새근새근... 💤 10분만 꿀잠 자고 충전해서 올게요... 🌙✨"},
    "timemachine": {"cat": "힐링 & 특별", "title": "⏳ 타임머신 여행 (Time Traveler)", "speech": "째깍째깍... ⏳ 과거와 미래로 떠나는 시간 여행 출발! 🌀⌛"},
    "surfing": {"cat": "힐링 & 특별", "title": "🏄‍♂️ 파도타기 서핑 (Big Surfer)", "speech": "빅 웨이브가 온다! 🏄‍♂️ 바탕화면 파도를 타는 짜릿함! 🌊🏄"},
    "paper_plane": {"cat": "힐링 & 특별", "title": "✈️ 종이비행기 (Paper Pilot)", "speech": "입김 훅 불어서 슉~! ✈️ 멀리멀리 날아가라 종이비행기! 🚀✨"},
    "party_dj": {"cat": "힐링 & 특별", "title": "🎧 파티 DJ (Club DJ Drop the Beat)", "speech": "드랍 더 비트! 🎛️🎧 오늘 밤 바탕화면 클럽 파티 시작합니다! 🪩🔥"}
}


class DesktopPetWindow(QMainWindow):
    """
    Main Frameless Always-On-Top Transparent Overlay hosting:
      1. Transparent QWebEngineView rendering Three.js Ppong-ppong-i
      2. Independent Top-Level Non-Overlapping SpeechBubbleWidget + RadialFloatingMenu
      3. FloatingChatWindow Drawer & Autonomous Roaming FSM
    """

    WINDOW_W = 440
    WINDOW_H = 560
    VIEWPORT_RECT = QRect(0, 0, 440, 560)

    def __init__(
        self,
        asset_server: LocalAssetServer,
        char_id: str = "ppong",
        coordinator: Optional[object] = None,
        rpg_state: Optional[RPGWorldState] = None,
        chat_window: Optional[FloatingChatWindow] = None,
    ) -> None:
        super().__init__()
        self._asset_server = asset_server
        self.char_id = (char_id or "ppong").strip().lower()
        self.char_display_name = "트리" if self.char_id == "tree" else "뽕뽕이"
        self.coordinator = coordinator
        self._shared_rpg_state = rpg_state
        self._shared_chat_window = chat_window
        self._prefs = PetPreferences.load(self.char_id)
        self._llm_config = LLMConfig(
            api_url=self._prefs.llm_url,
            model=self._prefs.llm_model,
            api_key=self._prefs.llm_api_key,
        )
        sys_prompt = TREE_SYSTEM_PROMPT if self.char_id == "tree" else SYSTEM_PROMPT
        self._conversation: list[dict[str, str]] = [
            {"role": "system", "content": sys_prompt}
        ]
        self._active_worker: Optional[LLMWorker] = None
        self._web_ready = False
        self._character_ready = False
        self._greeting_shown = False
        self._live_head_anchor: Optional[tuple[int, int]] = None
        self._live_body_rect: Optional[QRect] = None
        self._click_through_active: Optional[bool] = None
        self._defense_overlay_active: bool = False
        self._stillness_start_time: float = time.perf_counter()
        self._current_opacity: float = 1.0
        self._last_loco_vel_sent: tuple[float, float] = (0.0, 0.0)
        self._last_loco_vel_time: float = 0.0
        self._last_spider_ipc_time: float = 0.0
        self._last_doodle_ipc_time: float = 0.0
        self._last_superman_ipc_time: float = 0.0

        # Dragging, Throw Velocity & Tactile Click/Pet/Gravity Tracking
        self._left_pressed = False
        self._is_dragging = False
        self._drag_start_global = QPoint()
        self._drag_last_global = QPoint()
        self._drag_last_time = 0.0
        self._drag_vel_px = (0.0, 0.0)
        self._window_start_pos = QPoint()
        self._greet_toggle_flip = False
        self._nudged_for_chat = 0

        # Single-click 3-zone tactile poke tracking (cancelled on double-click)
        self._pending_poke_rel = (0.5, 0.5)
        self._last_poke_bubble_time = 0.0

        # Hover petting stroke detector & proximity curiosity state
        self._stroke_last_x: Optional[int] = None
        self._stroke_dir = 0
        self._stroke_reversals: list[float] = []
        self._pet_release_deadline = 0.0
        self._curiosity_enter_time: Optional[float] = None
        self._last_curiosity_time = 0.0

        # Always on Top & Taskbar gravity & elastic landing state
        self._always_on_top = self._prefs.always_on_top
        self._taskbar_gravity_enabled = self._prefs.taskbar_gravity
        self._fall_vx = 0.0
        self._fall_vy = 0.0
        self._fall_bounced = False

        # Active "Bout-and-Pause" Autonomous FSM Variables (Zero-Slip Velocity Matched!)
        self._state = PetState.IDLE
        self._pos_x = 0.0
        self._pos_y = 0.0
        self._walk_target_x = 0.0
        self._walk_speed = 98.0    # Calm, natural desktop Walk speed
        self._run_speed = 195.0    # Smooth, comfortable desktop Run speed
        self._choreo_active: bool = False
        self._choreo_type: str = ""
        self._choreo_t: float = 0.0
        self._choreo_dur: float = 0.0
        self._choreo_origin_x: float = 0.0
        self._choreo_origin_y: float = 0.0
        self._sit_stand_pending = False
        self._last_tick_time = time.perf_counter()
        self._last_cursor_norm = (0.0, 0.0)

        # 1. Omnidirectional 2D RPG Roaming State (6.0 ~ 25.0s multi-waypoint pathing + smooth math.atan2 yaw)
        self._roam_waypoints: list[tuple[float, float]] = []
        self._roam_start_time = 0.0
        self._roam_duration = 0.0
        self._roam_mode = "walk"
        self._roam_manual = False
        self._current_stage_yaw = 0.0
        self._last_sent_yaw: Optional[float] = None
        self._last_yaw_ipc_time: float = 0.0
        self._vel_x: float = 0.0
        self._vel_y: float = 0.0
        self._phys_vx: float = 0.0
        self._phys_vy: float = 0.0
        self._last_facing_dir: Optional[int] = None
        self._last_loco_batch_time: float = 0.0
        self._last_loco_batch_sig: Optional[tuple] = None
        self._cached_avail_geom: Optional[QRect] = None
        self._cached_avail_time: float = 0.0
        self._in_battle_arena = False
        self._pre_arena_pos: Optional[tuple[float, float]] = None

        # Character scaling factor (0.30x ~ 1.80x, grounded on taskbar)
        self._scale_factor = self._prefs.scale_factor

        # Intermittent natural gaze tracking state
        self._intermittent_gaze_enabled = self._prefs.intermittent_gaze
        self._gaze_mode = "watch"        # "watch" vs "wander"
        self._gaze_timer = 3.8           # seconds remaining in current gaze mode
        self._last_cursor_global = QPoint()
        self._last_cursor_time = time.perf_counter()
        self._cursor_speed_px = 0.0

        # Meadow grass strip & footprints toggle
        self._meadow_trail_enabled = self._prefs.meadow_trail

        # Inactivity nap / sleepy detector (triggers sleepy nap after 150s idle)
        self._last_user_activity_time = time.perf_counter()
        self._is_napping = False

        # Special Active Actions Tracking State (Spider-Man, Peek, Heist, Doodle, Superman, Evasion)
        self._spider_t = 0.0
        self._spider_dir = 1.0
        self._spider_start_x = 0.0
        self._spider_target_x = 0.0
        self._spider_floor_y = 0.0
        self._spider_overlay: Optional[SpiderWebOverlay] = None
        self._spider_anchor_global = QPointF(0.0, 0.0)
        self._peek_depth = 0.0
        self._peek_revealed = False
        self._peek_normal_y = 0.0
        self._peek_start_time = 0.0
        self._peek_max_duration = 9.0
        self._heist_progress = 0.0
        self._heist_dir = 1.0
        self._live_hand_anchor: Optional[tuple[int, int]] = None
        self._doodle_shape = "heart"
        self._doodle_progress = 0.0
        self._doodle_timer = 0.0
        self._doodle_proud_triggered = False

        # 2. Extended Superhero Flight State (8.0 ~ 25.0s multi-wave swoops)
        self._superman_progress = 0.0
        self._superman_start_x = 0.0
        self._superman_target_x = 0.0
        self._superman_start_y = 0.0
        self._superman_floor_y = 0.0
        self._superman_duration = 0.0
        self._superman_start_time = 0.0
        self._superman_waves = 3
        self._superman_mode = 0
        self._superman_cursor_released = False
        self._stolen_cursor_pos = QPoint(0, 0)
        self._last_gaze_weight = -1.0

        # 3. 3-Mode Mouse Evasion AI State (Velocity escape, Distance escape, Taunt fleeing)
        self._evasion_mode = "velocity"
        self._evasion_start_time = 0.0
        self._evasion_duration = 0.0
        self._evasion_target_x = 0.0
        self._evasion_target_y = 0.0
        self._last_taunt_time = 0.0
        self._last_evasion_trigger_time = 0.0

        # 4. Screen Content Heist 2.0 State with ScreenHoleOverlay & StolenPieceWidget
        self._screen_hole_overlay: Optional[ScreenHoleOverlay] = None
        self._heist_waypoints: list[tuple[float, float]] = []
        self._heist_start_time = 0.0
        self._heist_duration = 0.0

        # 5. Randomized Cooldown Gate & Workday Stone Cairn Trip State
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = random.uniform(75.0, 165.0)
        self._cairn_phase = "idle"
        self._cairn_mine_pos: Optional[tuple[float, float]] = None
        self._cairn_drop_pos: Optional[tuple[float, float]] = None
        self._cairn_mine_end_time = 0.0
        self._cairn_stone_index = 1
        self._cairn_target_stones = 10
        self._cairn_delivered_cb: Optional[object] = None

        self._init_window_flags()
        self._init_widgets()
        self._init_timers()
        self._init_tray_icon()
        self._place_on_taskbar()

        # Intercept mouse events across QWebEngineView & its internal Chromium delegate child widgets
        QApplication.instance().installEventFilter(self)

    def _init_window_flags(self) -> None:
        self.setWindowTitle("Tree (트리)" if self.char_id == "tree" else "Ppong-ppong-i (뽕뽕이)")
        self.setFixedSize(self.WINDOW_W, self.WINDOW_H)
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent; border: none;")

    def _init_widgets(self) -> None:
        central = QWidget(self)
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        # 1. Transparent QWebEngineView (Fixed geometry prevents any 3D viewport layout jump)
        self.web_view = QWebEngineView(central)
        self.web_view.setGeometry(self.VIEWPORT_RECT)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.web_view.setStyleSheet("background: transparent; border: none;")
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        # Shared persistent profile so IndexedDB mesh cache (ppong_mesh_cache_v2) & HTTP cache work across both pets
        self._web_profile = get_shared_web_profile(self)

        self._web_page = SilentWebEnginePage(self._web_profile, self.web_view)
        self._web_page.setBackgroundColor(Qt.GlobalColor.transparent)
        self._web_page.bridge_event.connect(self._on_js_bridge_event)
        settings = self._web_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        self.web_view.setPage(self._web_page)

        self.web_view.loadFinished.connect(self._on_web_loaded)
        self.web_view.setUrl(QUrl(self._asset_server.get_index_url(self.char_id)))

        # 2. Independent Top-Level Non-Overlapping Speech Bubble & Radial Floating Ring Menu
        self.speech_bubble = SpeechBubbleWidget(host_pet=self)
        self.radial_menu = RadialFloatingMenu(self)
        self.radial_menu.set_font_family(APP_FONT_FAMILY)
        self.radial_menu.menu_closed.connect(self._on_radial_menu_closed)

        # 2.5 Screen Content Heist 2.0 Stolen Piece Card & Workday Cairn Stone mounted on character hands
        self.stolen_piece_widget = StolenPieceWidget(central)
        self._reposition_stolen_piece_widget()
        self.stolen_piece_widget.clicked.connect(lambda: self.restore_screen_heist(caught_by_user=True))
        self.carried_stone_widget = CarriedStoneWidget(central)
        self.carried_stone_widget.set_scale_factor(self._scale_factor)
        self._reposition_carried_stone_widget()

        # 3. Top-Level Executive AI Chat & History Drawer (Shared across both pets, floats on top)
        self.chat_window = (
            self._shared_chat_window
            if self._shared_chat_window is not None
            else FloatingChatWindow(data_dir=DATA_DIR)
        )
        if getattr(self.chat_window, "owner_pet", None) is None and hasattr(self.chat_window, "set_owner_pet"):
            self.chat_window.set_owner_pet(self)
        self.chat_bar = self.chat_window  # Backward-compatible alias for visibility/busy checks

        def _is_chat_owner() -> bool:
            owner = getattr(self.chat_window, "owner_pet", None)
            return owner is None or owner is self

        self.chat_window.message_submitted.connect(
            lambda txt: self._on_user_chat_submitted(txt) if _is_chat_owner() else None
        )
        self.chat_window.settings_requested.connect(
            lambda: self._open_llm_settings() if _is_chat_owner() else None
        )
        self.chat_window.mail_requested.connect(
            lambda: self.toggle_outlook_hud() if _is_chat_owner() else None
        )
        self.chat_window.alarm_requested.connect(
            lambda: self.open_alarm_manager() if _is_chat_owner() else None
        )
        self.chat_window.cleanup_requested.connect(
            lambda: self.run_pc_cleanup(True) if _is_chat_owner() else None
        )
        self.chat_window.rpg_hub_requested.connect(
            lambda: self.toggle_rpg_hub() if _is_chat_owner() else None
        )
        self.chat_window.bag_requested.connect(
            lambda: self.show_rpg_bag_hub() if _is_chat_owner() else None
        )

        # Outlook AI Service & HUD Drawer
        self.outlook_service = OutlookAIAssistantService(self)
        self.outlook_hud = OutlookHUDDrawer(self.outlook_service)
        self.outlook_service.new_urgent_mail_received.connect(self._on_urgent_mail_received)

        # 3D World & Wave Defense RPG Hub (Shared Master State across both pets)
        self.rpg_state = (
            self._shared_rpg_state
            if self._shared_rpg_state is not None
            else RPGWorldState(DATA_DIR)
        )
        self.rpg_hub = RPGWorldHubDrawer(self.rpg_state)
        self.rpg_hub.dispatch_requested.connect(self.handle_rpg_dispatch)
        self.rpg_hub.worldview_changed.connect(self.set_worldview_theme)
        self.rpg_hub.work_safe_toggled.connect(lambda chk: self.set_work_safe_mode(chk, show_bubble=True))
        self.rpg_hub.skirmish_requested.connect(self.start_desktop_skirmish)
        self.rpg_hub.wave_defense_requested.connect(self.start_wave_defense_game)
        self.rpg_hub.stop_combat_requested.connect(self.stop_combat_and_defense)
        self.rpg_hub.consumable_used.connect(self.use_rpg_consumable)
        self.rpg_hub.weapon_changed.connect(self.set_rpg_weapon_type)
        self.rpg_hub.state_modified.connect(self._sync_rpg_to_js)
        self._excavating_target: Optional[tuple[float, float]] = None
        self._deferred_rpg_save_timer = QTimer(self)
        self._deferred_rpg_save_timer.setSingleShot(True)
        self._deferred_rpg_save_timer.setInterval(750)
        self._deferred_rpg_save_timer.timeout.connect(self._flush_deferred_rpg_save)

        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(QApplication.instance().quit)

        # Hotkey Ctrl+M to toggle Outlook AI Mail Hub
        mail_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mail_shortcut.activated.connect(self.toggle_outlook_hud)

        # Hotkey Ctrl+R to toggle 3D World & Wave Defense RPG Hub
        rpg_hub_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        rpg_hub_shortcut.activated.connect(self.toggle_rpg_hub)

        # Hotkey Ctrl+I to open Inventory Bag & Consumables Tab directly
        rpg_bag_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        rpg_bag_shortcut.activated.connect(self.show_rpg_bag_hub)

        # Hotkey Ctrl+D to launch 3D Wave Defense Mini-Game
        defense_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        defense_shortcut.activated.connect(lambda: self.start_wave_defense_game(self.rpg_state.max_cleared_wave + 1))

        # Hotkey Ctrl+E to trigger Intermittent Desktop Skirmish Defense
        skirmish_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        skirmish_shortcut.activated.connect(self.start_desktop_skirmish)

        # Hotkey Ctrl+Shift+W to toggle Non-Intrusive Work-Safe Click-Through Mode
        work_safe_shortcut = QShortcut(QKeySequence("Ctrl+Shift+W"), self)
        work_safe_shortcut.activated.connect(lambda: self.set_work_safe_mode(not self.rpg_state.work_safe_mode, show_bubble=True))

        # Hotkeys for character scaling: Ctrl+= / Ctrl++ (zoom in), Ctrl+- (zoom out), Ctrl+0 (reset)
        zoom_in_1 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_1.activated.connect(lambda: self.set_scale_factor(self._scale_factor + 0.10))
        zoom_in_2 = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_2.activated.connect(lambda: self.set_scale_factor(self._scale_factor + 0.10))
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(lambda: self.set_scale_factor(self._scale_factor - 0.10))
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(lambda: self.set_scale_factor(0.10))

        # Hotkey F to feed delicious rainbow treat
        snack_shortcut = QShortcut(QKeySequence("F"), self)
        snack_shortcut.activated.connect(self.feed_snack)

        # Hotkey Ctrl+T to toggle Always-on-Top
        top_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        top_shortcut.activated.connect(lambda: self.set_always_on_top(not self._always_on_top))

        # Hotkeys for 5 Special Active Actions
        spider_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        spider_shortcut.activated.connect(self.start_spider_swing)

        peek_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        peek_shortcut.activated.connect(self.start_hide_and_seek)

        heist_shortcut = QShortcut(QKeySequence("Ctrl+3"), self)
        heist_shortcut.activated.connect(self.start_screen_content_heist)

        doodle_shortcut = QShortcut(QKeySequence("Ctrl+4"), self)
        doodle_shortcut.activated.connect(lambda: self.start_magic_doodle())

        super_shortcut = QShortcut(QKeySequence("Ctrl+5"), self)
        super_shortcut.activated.connect(self.start_superman_fly)

        # Hotkey Ctrl+8 for 3-Mode Mouse Evasion AI
        evasion_shortcut = QShortcut(QKeySequence("Ctrl+8"), self)
        evasion_shortcut.activated.connect(lambda: self.start_mouse_evasion(mode="velocity", manual=True))

        # Hotkey Ctrl+9 for Omnidirectional 2D Desktop RPG Roaming
        roam_shortcut = QShortcut(QKeySequence("Ctrl+9"), self)
        roam_shortcut.activated.connect(lambda: self.start_omnidirectional_roam(mode="walk", manual=True))

        # Smart 3D Visual Alarm Manager
        self.alarm_manager = AlarmManager(self)
        self.alarm_manager.alarm_triggered.connect(self._on_alarm_triggered)
        self._alarm_manager_dialog: Optional[AlarmManagerDialog] = None

        # Periodic PC Environment Health & Optimizer Timer (every 45 minutes)
        self._pc_clean_timer = QTimer(self)
        self._pc_clean_timer.setInterval(45 * 60 * 1000)
        self._pc_clean_timer.timeout.connect(lambda: self.run_pc_cleanup(show_bubble=True))
        if self._prefs.enable_pc_clean:
            self._pc_clean_timer.start()

        # Hotkey Ctrl+6 for instant PC Clean
        clean_shortcut = QShortcut(QKeySequence("Ctrl+6"), self)
        clean_shortcut.activated.connect(lambda: self.run_pc_cleanup(show_bubble=True))

        # Hotkey Ctrl+7 for Smart Alarm Manager HUD
        alarm_mgr_shortcut = QShortcut(QKeySequence("Ctrl+7"), self)
        alarm_mgr_shortcut.activated.connect(self.open_alarm_manager)

        # Hotkey Ctrl+G for Google Gemini Web Chatbot Drawer
        gemini_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        gemini_shortcut.activated.connect(self.toggle_gemini_chat)

    def _init_timers(self) -> None:
        # Refresh-rate matched physics & locomotion tick (16ms on 60Hz instead of 17ms to eliminate 2Hz beat judder!)
        screen = QGuiApplication.primaryScreen()
        refresh_hz = float(screen.refreshRate() or 60.0) if screen else 60.0
        tick_ms = max(8, min(16, int(math.floor(1000.0 / max(60.0, refresh_hz)))))
        self._roam_tick_timer = QTimer(self)
        self._roam_tick_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._roam_tick_timer.setInterval(tick_ms)
        self._roam_tick_timer.timeout.connect(self._on_roam_tick)
        self._roam_tick_timer.start()

        # Failsafe timer in case Frame-2 character_ready signal is delayed
        self._startup_fallback_timer = QTimer(self)
        self._startup_fallback_timer.setSingleShot(True)
        self._startup_fallback_timer.setInterval(6000)
        self._startup_fallback_timer.timeout.connect(self._on_character_ready)

        # Screen Heist 2.0 Dual Restoration Timers (10~15s auto + 25s failsafe)
        self._heist_restore_timer = QTimer(self)
        self._heist_restore_timer.setSingleShot(True)
        self._heist_restore_timer.timeout.connect(lambda: self.restore_screen_heist(caught_by_user=False))

        self._heist_max_timeout_timer = QTimer(self)
        self._heist_max_timeout_timer.setSingleShot(True)
        self._heist_max_timeout_timer.timeout.connect(lambda: self.restore_screen_heist(caught_by_user=False))

        # Autonomous FSM decision timer (armed once character_ready fires)
        self._decision_timer = QTimer(self)
        self._decision_timer.setSingleShot(True)
        self._decision_timer.timeout.connect(self._decide_next_autonomous_state)

        # Solo Play completion timer (cancelled on any new action to enforce strict mutex)
        self._solo_complete_timer = QTimer(self)
        self._solo_complete_timer.setSingleShot(True)
        self._solo_complete_timer.timeout.connect(self._on_solo_action_completed)

        # Disambiguates single-left-click tactile poke from double-click chat toggle
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.setInterval(190)
        self._single_click_timer.timeout.connect(self._on_single_click_poke)

        # 15 FPS global Windows cursor tracker (reduces Chromium IPC overhead so foreground typing stays snappy)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(65)
        self._cursor_timer.timeout.connect(self._sync_global_cursor_to_3d)
        self._cursor_timer.start()

        # Defense Skirmish & Wave Defense are strictly user-triggered (do NOT auto-start _skirmish_timer)
        self._skirmish_timer = QTimer(self)
        self._skirmish_timer.setInterval(12 * 60 * 1000)
        self._skirmish_timer.timeout.connect(self._on_intermittent_skirmish_timer)

        # Farm Crop Growth Sync Timer (every 15 seconds)
        self._farm_sync_timer = QTimer(self)
        self._farm_sync_timer.setInterval(15 * 1000)
        self._farm_sync_timer.timeout.connect(self._on_farm_growth_tick)
        self._farm_sync_timer.start()

        # ~30 Hz Tight Hitbox Click-Through + Stillness/Camouflage Opacity Synchronizer
        self._hit_timer = QTimer(self)
        self._hit_timer.setInterval(33)
        self._hit_timer.timeout.connect(self._sync_dynamic_click_through_and_opacity)
        self._hit_timer.start()

    def _init_tray_icon(self) -> None:
        self.tray_icon: Optional[QSystemTrayIcon] = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon = _create_tree_tray_icon() if self.char_id == "tree" else _create_unicorn_tray_icon()
        self.setWindowIcon(icon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(f"{self.char_display_name} — 3D 데스크탑 미니펫")

        menu = QMenu()
        menu.setStyleSheet(
            f"""
            QMenu {{
                background: #0f172a;
                color: #f8fafc;
                border: 1.5px solid #334155;
                border-radius: 12px;
                padding: 8px 6px;
                font-family: '{APP_FONT_FAMILY}', 'Malgun Gothic', sans-serif;
                font-size: 14px;
                font-weight: 600;
                min-width: 240px;
            }}
            QMenu::item {{
                padding: 9px 18px;
                margin: 2px 4px;
                border-radius: 8px;
                color: #f1f5f9;
            }}
            QMenu::item:selected {{
                background: #C85A32;
                color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px;
                background: rgba(148, 163, 184, 0.25);
                margin: 6px 12px;
            }}
            """
        )

        act_radial = QAction("방사형 메뉴 열기", self)
        act_radial.triggered.connect(lambda: (self.show_pet_from_tray(), self.toggle_radial_menu()))

        act_chat = QAction("✨ Gemini 대화 창 열기 (Ctrl+G / 더블클릭)", self)
        act_chat.triggered.connect(lambda: (self.show_pet_from_tray(), self.toggle_gemini_chat()))

        act_gemini_ext = QAction("🌐 Gemini 크롬/엣지 앱창", self)
        act_gemini_ext.triggered.connect(lambda: launch_gemini_app_window())

        act_rpg_hub = QAction("월드 & 디펜스 사령부 (Ctrl+R)", self)
        act_rpg_hub.triggered.connect(self.toggle_rpg_hub)

        act_mail = QAction("메일함 (Ctrl+M)", self)
        act_mail.triggered.connect(self.toggle_outlook_hud)

        act_alarm_mgr = QAction("알람 관리 (Ctrl+7)", self)
        act_alarm_mgr.triggered.connect(self.open_alarm_manager)

        self.act_work_safe = QAction("클릭 관통 모드 (Ctrl+Shift+W)", self)
        self.act_work_safe.setCheckable(True)
        self.act_work_safe.setChecked(self.rpg_state.work_safe_mode)
        self.act_work_safe.toggled.connect(lambda chk: self.set_work_safe_mode(chk, show_bubble=True))

        self.act_toggle_visibility = QAction("숨기기", self)
        self.act_toggle_visibility.triggered.connect(self._toggle_pet_visibility_from_tray)

        act_partner_greet = QAction("뽕뽕이 & 트리 서로 인사", self)
        act_partner_greet.triggered.connect(lambda: getattr(self, "coordinator", None) and self.coordinator.greet_each_other())

        act_partner_dance = QAction("뽕뽕이 & 트리 듀엣 댄스", self)
        act_partner_dance.triggered.connect(lambda: getattr(self, "coordinator", None) and self.coordinator.duet_dance())

        act_partner_roam = QAction("뽕뽕이 & 트리 함께 산책", self)
        act_partner_roam.triggered.connect(lambda: getattr(self, "coordinator", None) and self.coordinator.roam_together())

        act_quit = QAction("끝내기 (Ctrl+Q)", self)
        act_quit.triggered.connect(QApplication.instance().quit)

        menu.addAction(act_radial)
        menu.addAction(act_chat)
        menu.addAction(act_gemini_ext)
        menu.addSeparator()
        menu.addAction(act_partner_greet)
        menu.addAction(act_partner_dance)
        menu.addAction(act_partner_roam)
        menu.addSeparator()
        menu.addAction(act_rpg_hub)
        menu.addAction(act_mail)
        menu.addAction(act_alarm_mgr)
        menu.addSeparator()
        menu.addAction(self.act_work_safe)
        menu.addAction(self.act_toggle_visibility)
        menu.addAction(act_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _set_taskbar_gravity_enabled(self, enabled: bool) -> None:
        self._taskbar_gravity_enabled = bool(enabled)
        self._prefs.taskbar_gravity = self._taskbar_gravity_enabled
        self._prefs.save(self.char_id)

    def _toggle_pet_visibility_from_tray(self) -> None:
        if self.isVisible():
            self.hide_to_tray()
        else:
            self.show_pet_from_tray()

    def hide_to_tray(self) -> None:
        if hasattr(self, "radial_menu"):
            self.radial_menu.close_all()
        if hasattr(self, "speech_bubble"):
            self.speech_bubble.hide()
        self.hide()
        if hasattr(self, "act_toggle_visibility"):
            self.act_toggle_visibility.setText("보이기")

    def show_pet_from_tray(self) -> None:
        if not self.isVisible():
            self.show()
        self.raise_()
        if hasattr(self, "act_toggle_visibility"):
            self.act_toggle_visibility.setText("숨기기")

    def is_popup_menu_open(self) -> bool:
        """Returns True whenever the right-click radial popup menu is visible on screen."""
        return bool(hasattr(self, "radial_menu") and self.radial_menu.isVisible())

    def _freeze_for_popup_menu(self) -> None:
        """Immediately freezes all locomotion, recoil, and autonomous decisions while the popup menu is open."""
        self._single_click_timer.stop()
        self._decision_timer.stop()
        self._choreo_active = False
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._phys_vx = 0.0
        self._phys_vy = 0.0
        coord = getattr(self, "coordinator", None)
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        if self._state == PetState.PETTING:
            self._set_3d_petting_state(False)
            self._state = PetState.IDLE
        if self._state in {PetState.WALK, PetState.RUN, PetState.SITTING, PetState.EVADING}:
            self._sit_stand_pending = False
            self._roam_manual = False
            self._state = PetState.IDLE
            self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
            self.trigger_3d_action("Idle")
        elif self._state in {PetState.EXCAVATING, PetState.CAIRN_WORK, PetState.WINDOW_HEIST}:
            # Pause walking/running stride in place while menu is open; resumes seamlessly on menu close!
            self._send_locomotion_batch(self._current_stage_yaw, 0.0, 0.0, 0, force=True)
            if not (self._state == PetState.CAIRN_WORK and getattr(self, "_cairn_phase", "") == "mining"):
                self._run_js("typeof window.playAnimation === 'function' && window.playAnimation('Idle', {fadeDuration: 0.16});")

    def _on_radial_menu_closed(self) -> None:
        """Resumes locomotion animation or schedules next autonomous decision once the popup menu closes."""
        self._last_tick_time = time.perf_counter()
        if self._in_battle_arena or not self.isVisible():
            return
        if self._state in {PetState.EXCAVATING, PetState.WINDOW_HEIST}:
            self.trigger_3d_action("Run", emotion="excited")
        elif self._state == PetState.CAIRN_WORK and getattr(self, "_cairn_phase", "") in {"go_mine", "carry_to_cairn"}:
            self.trigger_3d_action("Run", emotion="happy")
        elif self._state == PetState.IDLE and not self._decision_timer.isActive():
            self._schedule_next_decision(2200, 3800)

    def toggle_radial_menu(self) -> None:
        if (
            self._is_dragging
            or self._in_battle_arena
            or (hasattr(self, "rpg_state") and self.rpg_state.work_safe_mode)
        ):
            return
        if not hasattr(self, "radial_menu"):
            return
        if self.radial_menu.isVisible():
            self.radial_menu.close_all()
        else:
            self._freeze_for_popup_menu()
            self.radial_menu.open_around_pet()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if hasattr(self, "speech_bubble") and self.speech_bubble.isVisible():
            self.speech_bubble.reposition()
        if hasattr(self, "radial_menu") and self.radial_menu.isVisible():
            if self._is_dragging:
                self.radial_menu.close_all()
            else:
                self.radial_menu.reposition_around_pet()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if not self.isVisible():
                self.show_pet_from_tray()
            else:
                self.toggle_radial_menu()

    def _current_available_geometry(self) -> QRect:
        now = time.perf_counter()
        if self._cached_avail_geom is not None and (now - self._cached_avail_time) < 0.45:
            return self._cached_avail_geom
        center = self.frameGeometry().center()
        screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        rect = screen.availableGeometry()
        self._cached_avail_geom = rect
        self._cached_avail_time = now
        return rect

    def _taskbar_floor_y(self, avail: Optional[QRect] = None) -> float:
        rect = avail or self._current_available_geometry()
        foot_bottom_in_win = self.VIEWPORT_RECT.bottom() - 8
        return float(rect.bottom() - foot_bottom_in_win)

    def _update_window_pos(self) -> None:
        """Moves window only when integer coordinates change, preventing DWM composition flicker."""
        tx = int(round(self._pos_x))
        ty = int(round(self._pos_y))
        if (tx, ty) != (self.x(), self.y()):
            self.move(tx, ty)

    def _place_on_taskbar(self) -> None:
        avail = QGuiApplication.primaryScreen().availableGeometry()
        if self.char_id == "tree":
            start_x = max(avail.left() + 20, avail.right() - self.WINDOW_W * 2 - 20)
        else:
            start_x = avail.right() - self.WINDOW_W - 60
        start_y = self._taskbar_floor_y(avail)
        self._pos_x = float(start_x)
        self._pos_y = float(start_y)
        self._nudged_for_chat = 0
        self._update_window_pos()

    # -------------------------------------------------------------------------
    # JS Bridge Helpers (Python -> Three.js via page().runJavaScript)
    # -------------------------------------------------------------------------
    def _run_js(self, js_code: str) -> None:
        if self._web_ready:
            self.web_view.page().runJavaScript(js_code)

    def _start_action_desktop_choreography(self, action_name: str) -> None:
        """Applies a subtle vertical-only hop ONLY for explicit Jump actions.
        Stationary actions (mining, fishing, camping, cooking, gardening, dance, etc.) stay firmly grounded with zero side-to-side hopping!"""
        if (
            getattr(self, "_is_dragging", False)
            or getattr(self, "_left_pressed", False)
            or getattr(self, "_in_battle_arena", False)
            or self._state not in {PetState.IDLE, PetState.SITTING}
        ):
            return
        name = str(action_name or "")
        if name in {"Jump", "WaveJump"}:
            c_type, dur = "jump_arc", 0.78
        else:
            return
        if not self._choreo_active:
            self._choreo_origin_x = self._pos_x
            self._choreo_origin_y = self._pos_y
        self._choreo_active = True
        self._choreo_type = c_type
        self._choreo_t = 0.0
        self._choreo_dur = dur

    def trigger_3d_action(
        self,
        action_name: str,
        duration_ms: int = 0,
        emotion: Optional[str] = None,
        speech_ms: int = 0,
    ) -> None:
        safe_action = _normalize_action(action_name, allow_all_3d=True)
        opts_dict: dict[str, object] = {}
        if duration_ms > 0:
            opts_dict["durationMs"] = duration_ms
        if speech_ms > 0:
            opts_dict["speechMs"] = speech_ms
        if emotion:
            norm_em = _normalize_emotion(emotion) or emotion
            opts_dict["emotion"] = norm_em
        opts = json.dumps(opts_dict) if opts_dict else "{}"
        self._run_js(
            f"typeof window.playAnimation === 'function' && "
            f"window.playAnimation({json.dumps(safe_action)}, {opts});"
        )
        if emotion:
            norm_em = _normalize_emotion(emotion) or emotion
            self._run_js(
                f"typeof window.triggerEmotionEmote === 'function' && "
                f"window.triggerEmotionEmote({json.dumps(norm_em)});"
            )
        self._start_action_desktop_choreography(safe_action)

    def set_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = bool(enabled)
        self._prefs.always_on_top = self._always_on_top
        self._prefs.save(self.char_id)
        if hasattr(self, "act_always_on_top") and self.act_always_on_top.isChecked() != self._always_on_top:
            self.act_always_on_top.setChecked(self._always_on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._always_on_top)
        self.show()
        if hasattr(self, "speech_bubble") and self.speech_bubble is not None:
            self.speech_bubble.sync_always_on_top(self._always_on_top)
        if hasattr(self, "radial_menu") and self.radial_menu is not None:
            self.radial_menu.sync_always_on_top(self._always_on_top)
        if hasattr(self, "outlook_hud") and self.outlook_hud is not None:
            self.outlook_hud.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._always_on_top)
            if self.outlook_hud.isVisible():
                self.outlook_hud.show()
        coord = getattr(self, "coordinator", None)
        if coord is not None and hasattr(coord, "cairn_manager") and coord.cairn_manager is not None:
            coord.cairn_manager.widget.set_always_on_top(self._always_on_top)
            if hasattr(coord.cairn_manager, "status_popup") and coord.cairn_manager.status_popup is not None:
                coord.cairn_manager.status_popup.set_always_on_top(self._always_on_top)
        msg = "항상 위에 표시 켜짐 📌" if self._always_on_top else "일반 창 모드로 전환 🪟"
        if not self.chat_bar.isVisible():
            self.speech_bubble.show_message(msg, duration_ms=1800)

    def set_action_frequency(self, freq: str) -> None:
        self._prefs.action_frequency = freq
        self._prefs.save(self.char_id)
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        coord = getattr(self, "coordinator", None)
        if coord is not None and hasattr(coord, "_roll_social_cooldown"):
            coord._social_cooldown_sec = coord._roll_social_cooldown()
        label_kr = {
            "frequent": "자주 (약 1~1.5분 간격)",
            "normal": "보통 (여유 랜덤 간격)",
            "rare": "가끔 (느긋 랜덤 간격)",
            "off": "자율 액션 끄기",
        }.get(freq, freq)
        self.speech_bubble.show_message(f"액션 빈도 설정: {label_kr} ⚙️", duration_ms=2200)

    def toggle_action_feature(self, feat_name: str, enabled: bool) -> None:
        setattr(self._prefs, feat_name, bool(enabled))
        self._prefs.save(self.char_id)
        if feat_name == "enable_pc_clean":
            if enabled:
                self._pc_clean_timer.start()
            else:
                self._pc_clean_timer.stop()

    def run_pc_cleanup(self, show_bubble: bool = True) -> None:
        """Trims working sets, collects garbage, and reports memory health."""
        res = clean_pc_environment()
        if show_bubble:
            freed = res["freed_mb"]
            load = res["current_load_pct"]
            self.trigger_3d_action("HappySpin", emotion="proud")
            self.speech_bubble.show_message(
                f"🧹 [PC 쾌적화 완료] 불필요한 메모리 {freed}MB 확보!\n현재 메모리 사용률 {load}%로 쾌적해졌어요! ✨",
                duration_ms=4200,
            )

    def _on_alarm_triggered(self, alarm_id: str, label: str, time_str: str) -> None:
        """Opens the 3D Visual Alarm Dialog fixed right in the center of the screen."""
        if not self._is_blocked_by_arena_or_hidden() and not self.is_action_busy(include_locomotion=False):
            self.trigger_3d_action("Jump", emotion="excited")
        self.speech_bubble.show_message(f"⏰ [알람] {label}", duration_ms=4500)
        self._alarm_dialog = Visual3DAlarmDialog(
            asset_server_port=self._asset_server.port,
            label=label,
            time_str=time_str,
            parent=None,
        )
        self._alarm_dialog.snooze_clicked.connect(lambda lbl: self.alarm_manager.snooze_alarm(lbl, 5))
        self._alarm_dialog.show()

    def open_alarm_manager(self) -> None:
        """Opens the full-featured Alarm & Timer Management Dialog."""
        if not hasattr(self, "_alarm_manager_dialog") or self._alarm_manager_dialog is None:
            self._alarm_manager_dialog = AlarmManagerDialog(self.alarm_manager, self)
        self._alarm_manager_dialog.show()
        self._alarm_manager_dialog.raise_()
        self._alarm_manager_dialog.activateWindow()
        self.trigger_3d_action("Curious", emotion="curious")
        self.speech_bubble.show_message("알람 및 타이머 관리자를 열어드렸어요! ⏰✨", duration_ms=2800)

    def _is_blocked_by_arena_or_hidden(self) -> bool:
        if not self.isVisible() or getattr(self, "_in_battle_arena", False):
            return True
        coord = getattr(self, "coordinator", None)
        return coord is not None and coord.is_any_in_arena()

    def play_solo_action(
        self, action_key: str, custom_speech: Optional[str] = None, manual: bool = True
    ) -> None:
        """Plays one of the 30 interactive Solo Play / Transformation activities with strict action mutex."""
        if action_key not in SOLO_ACTIONS_INFO or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._state = PetState.SOLO_PLAY
        self._set_3d_facing(0)
        info = SOLO_ACTIONS_INFO[action_key]
        self._run_js(f"typeof window.playSoloAction === 'function' && window.playSoloAction('{action_key}');")
        self._start_action_desktop_choreography(action_key)
        msg = custom_speech or info["speech"]
        self.speech_bubble.show_message(msg, duration_ms=4500)
        if hasattr(self, "chat_window"):
            self.chat_window.add_message("pet", f"[{info['title']}] {msg}", action_key)
        if hasattr(self, "_solo_complete_timer"):
            self._solo_complete_timer.start(11500)

    def _on_solo_action_completed(self) -> None:
        if hasattr(self, "_solo_complete_timer"):
            self._solo_complete_timer.stop()
        if self._state == PetState.SOLO_PLAY:
            self._state = PetState.IDLE
            self._schedule_next_decision()

    # -------------------------------------------------------------------------
    # Outlook AI Productivity Hub Helpers
    # -------------------------------------------------------------------------
    def toggle_outlook_hud(self) -> None:
        """Toggles the visibility of the Outlook AI Mail Hub drawer."""
        if hasattr(self, "outlook_hud") and self.outlook_hud.isVisible():
            self.outlook_hud.hide_drawer()
        else:
            self.show_outlook_hud()

    def show_outlook_hud(self) -> None:
        """Opens and docks the Outlook AI Mail Hub beside the pet window."""
        if hasattr(self, "outlook_hud"):
            self.outlook_hud.show_beside_pet(self.frameGeometry())
            self.trigger_3d_action("Curious", emotion="curious")

    def check_mail_now(self) -> None:
        """Manual trigger to refresh inbox and popup briefing."""
        self.speech_bubble.show_message("새 메일과 일정을 확인 중입니다... ✉️✨", duration_ms=2500)
        self.trigger_3d_action("Curious")
        self.outlook_service.refresh_inbox()
        self.show_outlook_hud()

    def _on_urgent_mail_received(self, item: OutlookEmailItem) -> None:
        """Proactive reaction when an urgent or unread high-priority mail arrives."""
        msg = f"📬 [{item.sender_name}]님의 긴급 메일 도착!\n'{item.subject[:22]}...'\n(Ctrl+M 또는 ✉ 버튼으로 AI 요약 확인)"
        self.speech_bubble.show_message(msg, duration_ms=8500)
        if not self._is_blocked_by_arena_or_hidden() and not self.is_action_busy(include_locomotion=False):
            self.trigger_3d_action("Wave", emotion="excited")

    def set_scale_factor(self, scale: float, show_bubble: bool = True) -> None:
        self._scale_factor = round(max(0.10, min(1.80, float(scale))), 2)
        self._live_head_anchor = None
        self._live_hand_anchor = None
        self._prefs.scale_factor = self._scale_factor
        self._prefs.save(self.char_id)
        self._run_js(
            f"typeof window.setScaleFactor === 'function' && "
            f"window.setScaleFactor({self._scale_factor:.2f});"
        )
        self._reposition_stolen_piece_widget()
        if hasattr(self, "carried_stone_widget"):
            self.carried_stone_widget.set_scale_factor(self._scale_factor)
            self._reposition_carried_stone_widget()
        if hasattr(self, "speech_bubble") and self.speech_bubble.isVisible():
            self.speech_bubble.reposition()
        if show_bubble and not self.chat_bar.isVisible():
            self.speech_bubble.show_message(
                f"크기 조절: {int(self._scale_factor * 100)}% 🔍",
                duration_ms=1600,
            )

    def _reposition_stolen_piece_widget(self) -> None:
        """Anchors StolenPieceWidget directly onto the character's raised hands with zero white gap."""
        if not hasattr(self, "stolen_piece_widget") or self.stolen_piece_widget is None:
            return
        hand_anchor = getattr(self, "_live_hand_anchor", None)
        head_anchor = getattr(self, "_live_head_anchor", None)
        if hand_anchor is not None:
            hx, hy = hand_anchor
        elif head_anchor is not None:
            hx, hy = head_anchor[0], head_anchor[1] + int(22 * max(0.10, self._scale_factor))
        else:
            s = max(0.10, min(1.80, float(self._scale_factor)))
            hx = self.WINDOW_W // 2
            hy = int(469.1 - 155.0 * s)
        card_w = self.stolen_piece_widget.width()
        card_h = self.stolen_piece_widget.height()
        tx = max(4, min(self.WINDOW_W - card_w - 4, int(hx - card_w // 2)))
        ty = max(4, min(self.WINDOW_H - card_h - 4, int(hy - card_h + 10)))
        if (tx, ty) != (self.stolen_piece_widget.x(), self.stolen_piece_widget.y()):
            self.stolen_piece_widget.move(tx, ty)

    def _reposition_carried_stone_widget(self) -> None:
        """Anchors CarriedStoneWidget directly onto the pet's hands while transporting a stone to the cairn."""
        if not hasattr(self, "carried_stone_widget") or self.carried_stone_widget is None:
            return
        hand_anchor = getattr(self, "_live_hand_anchor", None)
        head_anchor = getattr(self, "_live_head_anchor", None)
        if hand_anchor is not None:
            hx, hy = hand_anchor
        elif head_anchor is not None:
            hx, hy = head_anchor[0], head_anchor[1] + int(20 * max(0.10, self._scale_factor))
        else:
            s = max(0.10, min(1.80, float(self._scale_factor)))
            hx = self.WINDOW_W // 2
            hy = int(469.1 - 150.0 * s)
        cw = self.carried_stone_widget.width()
        ch = self.carried_stone_widget.height()
        tx = max(4, min(self.WINDOW_W - cw - 4, int(hx - cw // 2)))
        ty = max(4, min(self.WINDOW_H - ch - 4, int(hy - ch + 8)))
        if (tx, ty) != (self.carried_stone_widget.x(), self.carried_stone_widget.y()):
            self.carried_stone_widget.move(tx, ty)

    def set_intermittent_gaze_enabled(self, enabled: bool) -> None:
        self._intermittent_gaze_enabled = bool(enabled)
        self._prefs.intermittent_gaze = self._intermittent_gaze_enabled
        self._prefs.save(self.char_id)
        if not self._intermittent_gaze_enabled:
            self._run_js(
                "typeof window.setGazeAttentionWeight === 'function' && "
                "window.setGazeAttentionWeight(1.0);"
            )

    def set_meadow_trail_enabled(self, enabled: bool) -> None:
        self._meadow_trail_enabled = bool(enabled)
        self._prefs.meadow_trail = self._meadow_trail_enabled
        self._prefs.save(self.char_id)
        self._run_js(
            f"typeof window.setMeadowTrailEnabled === 'function' && "
            f"window.setMeadowTrailEnabled({'true' if self._meadow_trail_enabled else 'false'});"
        )

    def feed_snack(self) -> None:
        if self._is_blocked_by_arena_or_hidden():
            return
        coord = getattr(self, "coordinator", None)
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self._last_user_activity_time = time.perf_counter()
        self._is_napping = False
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._set_3d_facing(0)
        self.trigger_3d_action("Snack", duration_ms=3600, emotion="loving", speech_ms=3600)
        snack_msg = (
            "냠냠! 달콤한 숲속 별사탕 쿠키 간식 최고야~! 🍪🌟🎄"
            if self.char_id == "tree"
            else "냠냠! 달콤한 무지개 솜사탕 간식 최고야~! 🍬🌈✨"
        )
        self.speech_bubble.show_message(
            snack_msg,
            duration_ms=3600,
        )
        self._schedule_next_decision(3600, 4800)

    def trigger_emotion(self, emotion_name: str) -> None:
        if self._is_blocked_by_arena_or_hidden():
            return
        coord = getattr(self, "coordinator", None)
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        canonical = _normalize_emotion(emotion_name) or "happy"
        self._last_user_activity_time = time.perf_counter()
        self._is_napping = False
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._set_3d_facing(0)

        emotion_map: dict[str, tuple[str, str]] = {
            "happy": ("Wave", "헤헤! 오늘 너무너무 기분 좋은 날이야! 😊🌈"),
            "excited": ("HappySpin", "와아~! 너무 신나서 심장이 두근두근해! 😆✨"),
            "curious": ("Curious", "응? 그건 무슨 뜻이야? 더 자세히 알려줘! 🦄🔍"),
            "sleepy": ("Sleepy", "하아암... 졸려... 몽실몽실 구름 이불 덮을래... 😴💤"),
            "shy": ("Shy", "으앗... 그렇게 칭찬해주면 부끄럽잖아... 볼 빨개졌어... 😳💕"),
            "surprised": ("Jump", "우와 깜짝이야! 눈이 휘둥그레졌어! 😲⚡"),
            "pouty": ("Pout", "흥칫뿡! 나 삐졌어... 그래도 솜사탕 주면 풀릴지도! 😤🍬"),
            "loving": ("Love", "너와 함께 있어서 정말 행복해! 언제나 사랑해! 🥰💖"),
            "sad": ("Sad", "훌쩍... 시무룩해졌어... 따뜻하게 안아줄래...? 🥺💧"),
            "proud": ("Proud", "짜잔! 내가 해냈어! 역시 난 천재 유니콘이야! 🌟😎"),
        }
        action, bubble_text = emotion_map.get(canonical, ("Wave", "헤헤! 🌈"))
        self.trigger_3d_action(action, duration_ms=3400, emotion=canonical, speech_ms=3400)
        self.speech_bubble.show_message(bubble_text, duration_ms=3500)
        self._schedule_next_decision(3500, 5000)

    def _set_3d_facing(self, direction: int) -> None:
        d = int(direction)
        if self._last_facing_dir == d:
            return
        self._last_facing_dir = d
        self._run_js(
            f"typeof window.setFacingDirection === 'function' && "
            f"window.setFacingDirection({d});"
        )

    def _set_stage_yaw_override(self, yaw: Optional[float]) -> None:
        if yaw is None:
            if self._last_sent_yaw is None:
                return
            self._last_sent_yaw = None
            self._last_yaw_ipc_time = time.perf_counter()
            self._run_js("typeof window.setStageYawOverride === 'function' && window.setStageYawOverride(null);")
            return
        now = time.perf_counter()
        if self._last_sent_yaw is not None:
            ang_diff = abs((yaw - self._last_sent_yaw + math.pi) % (2.0 * math.pi) - math.pi)
            if ang_diff < 0.025:
                return
            if (now - self._last_yaw_ipc_time) < 0.033:
                return
        self._last_sent_yaw = yaw
        self._last_yaw_ipc_time = now
        self._run_js(
            f"typeof window.setStageYawOverride === 'function' && "
            f"window.setStageYawOverride({yaw:.3f});"
        )

    def _set_locomotion_velocity(self, vx: float, vy: float) -> None:
        now = time.perf_counter()
        prev_vx, prev_vy = self._last_loco_vel_sent
        dv = math.hypot(vx - prev_vx, vy - prev_vy)
        is_stop = (vx == 0.0 and vy == 0.0)
        if not is_stop:
            if dv < 12.0 or (now - self._last_loco_vel_time) < 0.033:
                return
        elif prev_vx == 0.0 and prev_vy == 0.0:
            return
        self._last_loco_vel_sent = (vx, vy)
        self._last_loco_vel_time = now
        self._run_js(
            f"typeof window.setLocomotionVelocity === 'function' && "
            f"window.setLocomotionVelocity({vx:.1f}, {vy:.1f});"
        )

    def _send_locomotion_batch(
        self,
        yaw: Optional[float],
        vx: float,
        vy: float,
        facing: int,
        force: bool = False,
        snap: bool = False,
    ) -> None:
        """Combines yaw, locomotion speed, and facing into a smooth ~60Hz Chromium IPC call."""
        now = time.perf_counter()
        yaw_q = round(yaw, 3) if yaw is not None else None
        speed_q = round(math.hypot(vx, vy) / 4.0)
        sig = (yaw_q, speed_q, int(facing))
        if not force and not snap:
            if sig == self._last_loco_batch_sig:
                return
            ang_jump = 0.0
            if yaw is not None and self._last_sent_yaw is not None:
                ang_jump = abs((yaw - self._last_sent_yaw + math.pi) % (2.0 * math.pi) - math.pi)
            if ang_jump < 0.35 and (now - self._last_loco_batch_time) < 0.015:
                return
        self._last_loco_batch_sig = sig
        self._last_loco_batch_time = now
        self._last_sent_yaw = yaw
        self._last_loco_vel_sent = (vx, vy)
        self._last_facing_dir = int(facing)
        yaw_arg = "null" if yaw is None else f"{yaw:.3f}"
        snap_arg = "true" if snap else "false"
        self._run_js(
            f"typeof window.setLocomotionBatch === 'function' && "
            f"window.setLocomotionBatch({yaw_arg}, {vx:.1f}, {vy:.1f}, {int(facing)}, {snap_arg});"
        )

    def _sync_movement_facing(
        self,
        prev_x: float,
        prev_y: float,
        dt: float,
        fallback_dx: float = 0.0,
        fallback_dy: float = 0.0,
        snap: bool = False,
    ) -> None:
        """Computes 3D stage yaw strictly from actual screen displacement (post-clamp & post-recoil)
        so the character ALWAYS faces its real travel direction on screen."""
        safe_dt = max(0.008, dt)
        act_vx = (self._pos_x - prev_x) / safe_dt + getattr(self, "_phys_vx", 0.0)
        act_vy = (self._pos_y - prev_y) / safe_dt + getattr(self, "_phys_vy", 0.0)
        act_mag = math.hypot(act_vx, act_vy)
        if act_mag > 3.5:
            vx_use, vy_use = act_vx, act_vy
        elif math.hypot(fallback_dx, fallback_dy) > 1.0:
            vx_use, vy_use = fallback_dx, fallback_dy
        else:
            return
        # Slight 0.82 foreshortening on screen-Y keeps diagonal/upward walks visually crisp in 2.5D perspective
        # while still pointing accurately along (vx_use, vy_use) in all 360 degrees.
        target_yaw = math.atan2(vx_use, vy_use * 0.82 if abs(vx_use) > 6.0 else vy_use)
        prev_yaw = self._current_stage_yaw
        ang_diff = abs((target_yaw - prev_yaw + math.pi) % (2.0 * math.pi) - math.pi)
        self._current_stage_yaw = target_yaw
        if abs(vx_use) > 3.0:
            facing_dir = 1 if vx_use >= 0.0 else -1
        elif abs(fallback_dx) > 3.0:
            facing_dir = 1 if fallback_dx >= 0.0 else -1
        else:
            facing_dir = self._last_facing_dir or 0
        self._send_locomotion_batch(
            target_yaw,
            act_vx if act_mag > 3.5 else vx_use,
            act_vy if act_mag > 3.5 else vy_use,
            facing_dir,
            snap=bool(snap or ang_diff > 1.35),
        )

    def _set_3d_drag_state(self, active: bool, vx: float = 0.0, vy: float = 0.0) -> None:
        now = time.perf_counter()
        if active:
            if (now - getattr(self, "_last_drag_ipc_time", 0.0)) < 0.033:
                return
            self._last_drag_ipc_time = now
        else:
            self._last_drag_ipc_time = 0.0
        self._run_js(
            f"typeof window.setDragState === 'function' && "
            f"window.setDragState({'true' if active else 'false'}, {vx:.3f}, {vy:.3f});"
        )

    def _set_3d_falling_state(self, active: bool, vy: float = 0.0) -> None:
        now = time.perf_counter()
        if active:
            if (now - getattr(self, "_last_fall_ipc_time", 0.0)) < 0.033:
                return
            self._last_fall_ipc_time = now
        else:
            self._last_fall_ipc_time = 0.0
        self._run_js(
            f"typeof window.setFallingState === 'function' && "
            f"window.setFallingState({'true' if active else 'false'}, {vy:.3f});"
        )

    def _set_3d_petting_state(self, active: bool) -> None:
        self._run_js(
            f"typeof window.setPettingState === 'function' && "
            f"window.setPettingState({'true' if active else 'false'});"
        )

    def _trigger_3d_poke(self, zone: str) -> None:
        self._run_js(
            f"typeof window.triggerPokeReaction === 'function' && "
            f"window.triggerPokeReaction({json.dumps(zone)});"
        )

    def _on_web_loaded(self, ok: bool) -> None:
        self._web_ready = ok
        if ok:
            # Sync initial scale factor, meadow trail, and RPG state immediately;
            # defer greeting bubble & autonomous timer until Frame-2 'character_ready' signal!
            self._run_js(
                f"typeof window.setScaleFactor === 'function' && "
                f"window.setScaleFactor({self._scale_factor:.2f});"
            )
            self._run_js(
                f"typeof window.setMeadowTrailEnabled === 'function' && "
                f"window.setMeadowTrailEnabled({'true' if self._meadow_trail_enabled else 'false'});"
            )
            self._sync_rpg_to_js()
            if self.rpg_state.work_safe_mode:
                self.set_work_safe_mode(True, show_bubble=False)
            if not self._greeting_shown and hasattr(self, "_startup_fallback_timer"):
                self._startup_fallback_timer.start()

    def _on_character_ready(self) -> None:
        """Triggered on WebGL Frame-2 character_ready signal (or 6s failsafe): shows greeting AFTER 3D model is visible."""
        if hasattr(self, "_startup_fallback_timer"):
            self._startup_fallback_timer.stop()
        self._character_ready = True
        if self._greeting_shown:
            return
        self._greeting_shown = True
        self._sync_rpg_to_js()
        self.trigger_3d_action("Wave", speech_ms=4200, emotion="happy")
        greeting_msg = (
            "안녕! 나는 숲속 요정 트리야! 🎄🌟\n뽕뽕이 친구와 신나게 놀게!"
            if self.char_id == "tree"
            else "안녕! 나는 뽕뽕이야! 🦄🌈\n월드 탐험·디펜스 준비 완료!"
        )
        self.speech_bubble.show_message(
            greeting_msg,
            duration_ms=4200,
        )
        if self.char_id == "tree":
            self._schedule_next_decision(18000, 34000, use_freq=False)
        else:
            self._schedule_next_decision(10000, 20000, use_freq=False)

    # -------------------------------------------------------------------------
    # 3D World · Mining · Economy · Wave Defense RPG Subsystem (Phase 1 ~ 4)
    # -------------------------------------------------------------------------
    def _sync_rpg_to_js(self) -> None:
        if not self._web_ready or not hasattr(self, "rpg_state"):
            return
        self.rpg_state.tick_farm_growth()
        payload_json = json.dumps(self.rpg_state.to_js_payload(), ensure_ascii=False)
        xp_json = json.dumps(self.rpg_state.skill_xp, ensure_ascii=False)
        self._run_js(
            f"if (typeof window.syncRPGStateFromPython === 'function') window.syncRPGStateFromPython({payload_json}); "
            f"if (typeof window.setSoloSkillXP === 'function') window.setSoloSkillXP({xp_json});"
        )

    def _on_farm_growth_tick(self) -> None:
        if not hasattr(self, "rpg_state"):
            return
        prev_stage = self.rpg_state.farm_stage
        newly_ready = self.rpg_state.tick_farm_growth()
        new_stage = self.rpg_state.farm_stage
        if newly_ready or new_stage != prev_stage:
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            if newly_ready and not self.chat_bar.isVisible():
                self.speech_bubble.show_message(
                    "🌾 [3D 미니 텃밭] 황금 작물이 다 자랐어요! 사령부(Ctrl+R)에서 수확해보세요! ✨",
                    duration_ms=3800,
                )

    def _on_intermittent_skirmish_timer(self) -> None:
        """Defense & Skirmish are strictly user-triggered (no autonomous surprise defense popup)."""
        return

    def toggle_rpg_hub(self) -> None:
        coord = getattr(self, "coordinator", None)
        if self.char_id == "tree" and coord is not None and getattr(coord, "ppong_win", None) is not None and coord.ppong_win is not self:
            if coord.ppong_win.rpg_hub.isVisible():
                coord.ppong_win.rpg_hub.hide()
            else:
                coord.ppong_win._sync_rpg_to_js()
                coord.ppong_win.rpg_hub.show_beside_pet(self.frameGeometry())
                self.trigger_3d_action("Curious", emotion="curious")
            return
        if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
            self.rpg_hub.hide()
        else:
            self.show_rpg_hub()

    def show_rpg_hub(self) -> None:
        coord = getattr(self, "coordinator", None)
        if self.char_id == "tree" and coord is not None and getattr(coord, "ppong_win", None) is not None and coord.ppong_win is not self:
            coord.ppong_win._sync_rpg_to_js()
            coord.ppong_win.rpg_hub.show_beside_pet(self.frameGeometry())
            self.trigger_3d_action("Curious", emotion="curious")
            return
        if hasattr(self, "rpg_hub"):
            self._sync_rpg_to_js()
            self.rpg_hub.show_beside_pet(self.frameGeometry())
            self.trigger_3d_action("Curious", emotion="curious")

    def show_rpg_bag_hub(self) -> None:
        coord = getattr(self, "coordinator", None)
        if self.char_id == "tree" and coord is not None and getattr(coord, "ppong_win", None) is not None and coord.ppong_win is not self:
            coord.ppong_win._sync_rpg_to_js()
            coord.ppong_win.rpg_hub.open_bag_tab(self.frameGeometry())
            self.trigger_3d_action("Curious", emotion="happy")
            return
        if hasattr(self, "rpg_hub"):
            self._sync_rpg_to_js()
            self.rpg_hub.open_bag_tab(self.frameGeometry())
            self.trigger_3d_action("Curious", emotion="happy")

    def use_rpg_consumable(self, item_key: str) -> None:
        self._run_js(
            f"typeof window.useConsumableItem === 'function' && "
            f"window.useConsumableItem({json.dumps(item_key)});"
        )
        self._sync_rpg_to_js()

    def set_rpg_weapon_type(self, wep_key: str) -> None:
        if wep_key not in WEAPON_SPECS:
            return
        self.rpg_state.equipped_weapon = wep_key
        if wep_key not in self.rpg_state.unlocked_weapons:
            self.rpg_state.unlocked_weapons.append(wep_key)
        self.rpg_state.save()
        self._run_js(
            f"typeof window.setRPGWeaponType === 'function' && "
            f"window.setRPGWeaponType({json.dumps(wep_key)});"
        )
        self._sync_rpg_to_js()
        if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
            self.rpg_hub.refresh_ui()

    def equip_or_craft_weapon_by_key(self, wep_key: str) -> None:
        ok, msg = self.rpg_state.equip_or_craft_weapon(wep_key)
        if ok:
            self.set_rpg_weapon_type(self.rpg_state.equipped_weapon)
            self.trigger_3d_action("Proud", emotion="proud")
        self.speech_bubble.show_message(msg, duration_ms=3800)
        if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
            self.rpg_hub.set_feedback(msg)
            self.rpg_hub.refresh_ui()

    def _flush_deferred_rpg_save(self) -> None:
        if hasattr(self, "rpg_state"):
            self.rpg_state.save()
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()

    def _enter_desktop_battle_arena(self) -> None:
        """Expands the transparent 3D overlay seamlessly across the full desktop resolution so independent enemies emerge from the 4 real edges of the desktop and Ppong-ppong-i hunts them down."""
        if self._in_battle_arena:
            return
        if hasattr(self, "radial_menu"):
            self.radial_menu.close_all()
        # Cancel all autonomous partner actions & timers BEFORE hiding so spider webs / timers never leak during defense!
        coord = getattr(self, "coordinator", None)
        if coord is not None:
            coord._stop_minigame()
            if getattr(coord, "cairn_manager", None) is not None:
                coord.cairn_manager.set_arena_hidden(True)
            partner = coord.get_partner(self)
            if partner is not None:
                self._partner_was_visible_before_arena = partner.isVisible()
                partner.cancel_all_active_actions()
                partner._decision_timer.stop()
                partner.speech_bubble.hide()
                if partner.isVisible():
                    partner.hide()
            else:
                self._partner_was_visible_before_arena = False
        self.speech_bubble.hide()
        self._run_js("typeof window.prepareDefenseArena === 'function' && window.prepareDefenseArena();")
        self._pre_arena_pos = (self._pos_x, self._pos_y)
        self._in_battle_arena = True
        self._defense_overlay_active = False
        self._live_head_anchor = None
        self._live_body_rect = None
        self._set_win32_click_through(False)
        self._current_opacity = 1.0
        self.setWindowOpacity(1.0)
        avail = self._current_available_geometry()
        arena_w = max(860, avail.width())
        arena_h = max(620, avail.height())
        ax = avail.left()
        ay = avail.top()
        self._pos_x = float(ax)
        self._pos_y = float(ay)
        self.setUpdatesEnabled(False)
        self.setMinimumSize(arena_w, arena_h)
        self.setMaximumSize(arena_w, arena_h)
        self.web_view.setGeometry(0, 0, arena_w, arena_h)
        self.setGeometry(ax, ay, arena_w, arena_h)
        self.setUpdatesEnabled(True)

    def _exit_desktop_battle_arena(self) -> None:
        """Restores the compact desktop pet window after 360-degree defense concludes."""
        if not self._in_battle_arena:
            return
        self._in_battle_arena = False
        self._defense_overlay_active = False
        self._live_head_anchor = None
        self._live_body_rect = None
        if self._pre_arena_pos is not None:
            self._pos_x, self._pos_y = self._pre_arena_pos
            self._pre_arena_pos = None
        else:
            avail = self._current_available_geometry()
            self._pos_y = self._taskbar_floor_y(avail)
        self.setUpdatesEnabled(False)
        self.setMinimumSize(self.WINDOW_W, self.WINDOW_H)
        self.setMaximumSize(self.WINDOW_W, self.WINDOW_H)
        self.web_view.setGeometry(self.VIEWPORT_RECT)
        self.setGeometry(int(round(self._pos_x)), int(round(self._pos_y)), self.WINDOW_W, self.WINDOW_H)
        self.setUpdatesEnabled(True)
        self.speech_bubble.reposition()
        coord = getattr(self, "coordinator", None)
        if coord is not None and getattr(coord, "cairn_manager", None) is not None:
            coord.cairn_manager.set_arena_hidden(False)
        if getattr(self, "_partner_was_visible_before_arena", False):
            self._partner_was_visible_before_arena = False
            if coord is not None:
                partner = coord.get_partner(self)
                if partner is not None and not partner.isVisible():
                    partner.show()
                    partner._schedule_next_decision(6000, 14000, use_freq=False)

    def _is_point_on_character(self, lx: float, ly: float, pad: int = 10) -> bool:
        """Returns True ONLY when (lx, ly) inside the overlay lies on the tight rendered 3D character."""
        if (
            self._in_battle_arena
            or self._defense_overlay_active
            or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}
        ):
            return True
        if self._live_body_rect is not None and self._live_body_rect.width() > 4:
            return self._live_body_rect.adjusted(-pad, -pad, pad, pad).contains(int(round(lx)), int(round(ly)))
        sc = max(0.10, float(getattr(self, "_scale_factor", 0.10)))
        est_w = int(max(64, min(180, 320 * sc)))
        est_h = int(max(76, min(220, 360 * sc)))
        cx = self.WINDOW_W // 2
        bottom_y = int(round(490.0))
        fallback = QRect(cx - est_w // 2, bottom_y - est_h, est_w, est_h)
        return fallback.adjusted(-pad, -pad, pad, pad).contains(int(round(lx)), int(round(ly)))

    def is_click_through_active(self) -> bool:
        return bool(self._click_through_active)

    def _set_win32_click_through(self, enable: bool) -> None:
        """Caches and toggles Win32 WS_EX_TRANSPARENT so empty desktop pixels pass clicks cleanly through."""
        enable = bool(enable)
        if self._click_through_active is enable:
            return
        self._click_through_active = enable
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            cur_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                new_style = cur_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                new_style = cur_style & ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def _sync_dynamic_click_through_and_opacity(self) -> None:
        """Synchronizes ~30Hz tight-hitbox Win32 click-through AND stillness / hide-and-seek translucency."""
        if not self.isVisible():
            return
        now = time.perf_counter()
        cursor = QCursor.pos()
        local_pt = self.mapFromGlobal(cursor)
        in_widget = 0 <= local_pt.x() < self.width() and 0 <= local_pt.y() < self.height()
        on_char = in_widget and self._is_point_on_character(local_pt.x(), local_pt.y(), pad=10)
        if on_char or self._state not in {PetState.IDLE, PetState.SITTING}:
            if on_char or self._is_dragging or self.speech_bubble.isVisible() or self.chat_bar.isVisible():
                self._stillness_start_time = now
            elif self._state not in {PetState.IDLE, PetState.SITTING}:
                self._stillness_start_time = now

        # 1. Dynamic Click-Through Check
        if self.rpg_state.work_safe_mode:
            want_transparent = True
        elif (
            self._in_battle_arena
            or self._defense_overlay_active
            or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}
            or self._is_dragging
            or self._left_pressed
            or (hasattr(self, "radial_menu") and self.radial_menu.isVisible())
        ):
            want_transparent = False
        elif on_char:
            want_transparent = False
        else:
            want_transparent = True
        self._set_win32_click_through(want_transparent)

        # 2. Translucent Stillness & Hide-and-Seek Camouflage Check
        if self.rpg_state.work_safe_mode:
            target_op = 0.78
        elif (
            self._in_battle_arena
            or self._defense_overlay_active
            or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}
            or self._is_dragging
            or self._left_pressed
            or self.chat_bar.isVisible()
            or self.speech_bubble.isVisible()
            or (hasattr(self, "radial_menu") and self.radial_menu.isVisible())
        ):
            target_op = 1.0
        elif self._state == PetState.HIDE_AND_SEEK and not self._peek_revealed:
            target_op = 0.35 + 0.05 * math.sin(now * 2.8)
        elif on_char:
            target_op = 1.0
        elif self._state in {PetState.IDLE, PetState.SITTING} and (now - self._stillness_start_time) > 4.0:
            target_op = 0.46
        else:
            target_op = 1.0

        self._current_opacity += (target_op - self._current_opacity) * 0.22
        if abs(self._current_opacity - target_op) < 0.012:
            self._current_opacity = target_op
        if abs(self._current_opacity - self.windowOpacity()) > 0.015:
            self.setWindowOpacity(self._current_opacity)

    def set_auto_start_windows(self, enabled: bool) -> bool:
        """Toggles HKCU Windows Startup registration and syncs across preferences."""
        enabled = bool(enabled)
        ok = set_windows_startup_enabled(enabled)
        self._prefs.auto_start_windows = enabled
        self._prefs.save(self.char_id)
        coord = getattr(self, "coordinator", None)
        if coord is not None:
            partner = coord.get_partner(self)
            if partner is not None:
                partner._prefs.auto_start_windows = enabled
                partner._prefs.save(partner.char_id)
        return ok

    def set_work_safe_mode(self, enabled: bool, show_bubble: bool = True) -> None:
        """Applies Win32 WS_EX_TRANSPARENT click-through & semi-opacity so work is never interrupted."""
        enabled = bool(enabled)
        if enabled and hasattr(self, "radial_menu"):
            self.radial_menu.close_all()
        self.rpg_state.work_safe_mode = enabled
        self.rpg_state.save()
        if hasattr(self, "act_work_safe") and self.act_work_safe.isChecked() != enabled:
            self.act_work_safe.setChecked(enabled)
        if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
            self.rpg_hub.refresh_ui()

        self._set_win32_click_through(enabled)
        self._current_opacity = 0.78 if enabled else 1.0
        self.setWindowOpacity(self._current_opacity)
        if show_bubble:
            msg = (
                "💼 [업무 집중 모드 ON] 마우스 클릭이 뽕뽕이를 관통합니다! (해제: Ctrl+Shift+W 또는 사령부)"
                if enabled
                else "🦄 [업무 집중 모드 OFF] 다시 뽕뽕이와 직접 교감할 수 있어요!"
            )
            self.speech_bubble.show_message(msg, duration_ms=3500)

    def set_worldview_theme(self, theme_key: str) -> None:
        if theme_key not in WORLDVIEW_INFO:
            return
        self.rpg_state.worldview = theme_key
        self.rpg_state.save()
        self._sync_rpg_to_js()
        self._run_js(
            f"typeof window.applyWorldviewTheme === 'function' && "
            f"window.applyWorldviewTheme({json.dumps(theme_key)});"
        )
        if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
            self.rpg_hub.refresh_ui()
        meta = WORLDVIEW_INFO[theme_key]
        self.trigger_3d_action("HappySpin", emotion="excited")
        self.speech_bubble.show_message(
            f"🌌 세계관 전환 완료: [{meta['label']}]\n{meta['desc']} ✨",
            duration_ms=3600,
        )

    def handle_rpg_dispatch(self, task_key: str) -> None:
        """Dispatches a task immediately if idle, or pushes it to the 3-slot Task Queue."""
        if task_key == "auto_queue":
            self.rpg_state.dispatch_queue = ["mining", "gardening", "fishing"]
            self.rpg_state.save()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            if not self.is_action_busy():
                next_t = self.rpg_state.dispatch_queue.pop(0)
                self.rpg_state.save()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
                self._execute_dispatched_task(next_t)
            else:
                self.speech_bubble.show_message(
                    "🔄 [연속 3슬롯 예약 완료] 채굴 ➔ 농사 ➔ 낚시 순서로 자동 수행합니다!",
                    duration_ms=3200,
                )
            return

        if not self.is_action_busy() and self._state in {PetState.IDLE, PetState.WALK, PetState.RUN, PetState.SITTING}:
            self._execute_dispatched_task(task_key)
        else:
            if len(self.rpg_state.dispatch_queue) < 3:
                self.rpg_state.dispatch_queue.append(task_key)
                self.rpg_state.save()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
                self.speech_bubble.show_message(
                    f"📋 작업 대기열에 [{task_key}] 추가 완료! ({len(self.rpg_state.dispatch_queue)}/3)",
                    duration_ms=2600,
                )
            else:
                self._execute_dispatched_task(task_key)

    def _execute_dispatched_task(self, task_key: str) -> None:
        if task_key == "mining":
            self.start_roaming_excavation()
        elif task_key == "gardening":
            self.rpg_state.water_farm()
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            self.play_solo_action("gardening")
        elif task_key == "fishing":
            self.play_solo_action("fishing")
        elif task_key == "skirmish":
            self.start_desktop_skirmish()

    def start_roaming_excavation(self, manual: bool = True) -> None:
        """Roams across the desktop to locate a rich ore vein, then excavates with a 3D pickaxe."""
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        self._sync_rpg_to_js()

        pts = self._generate_2d_desktop_waypoints(1)
        self._excavating_target = pts[0] if pts else (self._pos_x, self._pos_y)
        self._state = PetState.EXCAVATING
        tx0, ty0 = self._excavating_target
        init_dx, init_dy = tx0 - self._pos_x, ty0 - self._pos_y
        if math.hypot(init_dx, init_dy) > 2.0:
            iyaw = math.atan2(init_dx, init_dy * 0.82 if abs(init_dx) > 6.0 else init_dy)
            self._current_stage_yaw = iyaw
            self._send_locomotion_batch(iyaw, init_dx, init_dy, 1 if init_dx >= 0 else -1, force=True, snap=True)
        self.trigger_3d_action("Run", emotion="excited")
        self.speech_bubble.show_message(
            "⛏️ 바탕화면 광맥 탐지 완료! 채굴 포인트로 출동합니다~! 💎",
            duration_ms=3000,
        )

    def start_desktop_skirmish(self) -> None:
        """Triggers a user-requested desktop skirmish (2~3 independent invaders from desktop edges) for Ppong-ppong-i to hunt down."""
        coord = getattr(self, "coordinator", None)
        if self.char_id == "tree" and coord is not None and getattr(coord, "ppong_win", None) is not None and coord.ppong_win is not self:
            coord.ppong_win.start_desktop_skirmish()
            return
        if self._is_dragging or self._left_pressed:
            return
        if coord is not None and coord.is_any_in_arena():
            return
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._enter_desktop_battle_arena()
        self._sync_rpg_to_js()
        self._state = PetState.SKIRMISH
        self._set_3d_facing(1)
        QTimer.singleShot(
            120,
            lambda: self._state == PetState.SKIRMISH and self._run_js("typeof window.startSkirmish === 'function' && window.startSkirmish();"),
        )

    def start_wave_defense_game(self, wave_num: int = 1) -> None:
        """Launches the 3D Desktop-Edge Hunter-Seeker Wave Defense across the full desktop resolution."""
        coord = getattr(self, "coordinator", None)
        if self.char_id == "tree" and coord is not None and getattr(coord, "ppong_win", None) is not None and coord.ppong_win is not self:
            coord.ppong_win.start_wave_defense_game(wave_num)
            return
        if self._is_dragging or self._left_pressed:
            return
        if coord is not None and coord.is_any_in_arena() and not self._in_battle_arena:
            return
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        wave_num = max(1, min(int(wave_num), self.rpg_state.highest_wave + 1))
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._enter_desktop_battle_arena()
        self._sync_rpg_to_js()
        self._state = PetState.WAVE_DEFENSE
        self._set_3d_facing(1)
        QTimer.singleShot(
            120,
            lambda w=wave_num: self._state == PetState.WAVE_DEFENSE and self._run_js(
                f"typeof window.startWaveDefense === 'function' && window.startWaveDefense({w});"
            ),
        )

    def stop_combat_and_defense(self) -> None:
        """Stops any active Skirmish or Wave Defense session and returns to peaceful mode."""
        self._run_js("typeof window.stopCombatAndDefense === 'function' && window.stopCombatAndDefense();")
        self._exit_desktop_battle_arena()
        if self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE, PetState.EXCAVATING}:
            self._state = PetState.IDLE
        self._set_3d_facing(0)
        self.trigger_3d_action("Idle")
        self._schedule_next_decision(2200, 3800)

    def _on_js_bridge_event(self, payload: dict) -> None:
        """Handles real-time events emitted by index.html, solo_play.js, and world_rpg_defense.js via __PPONG_SYNC__."""
        if not isinstance(payload, dict) or not hasattr(self, "rpg_state"):
            return
        etype = payload.get("type", "")

        if etype == "character_ready":
            self._on_character_ready()
            return

        if etype == "subsystems_ready":
            self._sync_rpg_to_js()
            return

        if etype == "head_anchor":
            try:
                hx = int(payload.get("x", 220))
                hy = int(payload.get("y", 340))
                self._live_head_anchor = (hx, hy)
                hand_x = int(payload.get("hx", hx))
                hand_y = int(payload.get("hy", hy + 18))
                self._live_hand_anchor = (hand_x, hand_y)
                if "bx0" in payload and "bx1" in payload and not self._in_battle_arena:
                    bx0 = int(payload.get("bx0", 0))
                    by0 = int(payload.get("by0", 0))
                    bx1 = int(payload.get("bx1", 0))
                    by1 = int(payload.get("by1", 0))
                    if bx1 > bx0 + 8 and by1 > by0 + 8:
                        self._live_body_rect = QRect(bx0, by0, bx1 - bx0, by1 - by0)
                if hasattr(self, "stolen_piece_widget") and self.stolen_piece_widget.isVisible():
                    self._reposition_stolen_piece_widget()
                if hasattr(self, "speech_bubble") and self.speech_bubble.isVisible():
                    self.speech_bubble.reposition()
            except Exception:
                pass
            return

        if etype == "tower_pad_action":
            if hasattr(self, "_deferred_rpg_save_timer") and self._deferred_rpg_save_timer.isActive():
                self._deferred_rpg_save_timer.stop()
            pad_id = str(payload.get("padId", ""))
            act = str(payload.get("action", "build"))
            t_type = str(payload.get("towerType") or "")
            new_lv = int(payload.get("level", 1) or 1)
            gold_delta = int(payload.get("goldDelta", -int(payload.get("cost", 0)) if act != "sell" else int(payload.get("refund", 0))))
            self.rpg_state.apply_pad_action(pad_id, act, t_type, new_lv, gold_delta)
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            coord = getattr(self, "coordinator", None)
            if coord is not None:
                partner = coord.get_partner(self)
                if partner is not None and getattr(partner, "_web_ready", False):
                    partner._sync_rpg_to_js()
            return

        if etype == "weapon_equipped":
            wep_key = str(payload.get("weapon") or "")
            if wep_key in WEAPON_SPECS and wep_key in self.rpg_state.unlocked_weapons:
                self.rpg_state.equipped_weapon = wep_key
                self.rpg_state.save()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
            return

        if etype == "consumable_used_in_js":
            item_key = str(payload.get("itemKey") or "")
            if item_key and int(self.rpg_state.consumables.get(item_key, 0)) > 0:
                self.rpg_state.consumables[item_key] = max(0, int(self.rpg_state.consumables.get(item_key, 0)) - 1)
                self.rpg_state.save()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
            return

        if etype == "defeat_action":
            act = str(payload.get("action", "close"))
            wave_retry = int(payload.get("wave", max(1, self.rpg_state.highest_wave + 1)) or 1)
            if act == "retry_wave":
                self._defense_overlay_active = True
                self._state = PetState.WAVE_DEFENSE
                self._set_win32_click_through(False)
                self._sync_rpg_to_js()
                return
            self._defense_overlay_active = False
            self._exit_desktop_battle_arena()
            if self._state in {PetState.WAVE_DEFENSE, PetState.SKIRMISH}:
                self._state = PetState.IDLE
                self._schedule_next_decision(2200, 3800)
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub"):
                if act in {"forge", "towers", "kitchen"}:
                    self.rpg_hub.open_section_tab(2, self.frameGeometry())
                elif act == "bag":
                    self.rpg_hub.open_section_tab(1, self.frameGeometry())
                elif act == "farm":
                    self.rpg_hub.open_section_tab(0, self.frameGeometry())
            return

        if etype == "solo_reward":
            prev_lv = self.rpg_state.pet_level
            summary_str = self.rpg_state.process_solo_reward(payload)
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            if self.rpg_state.pet_level > prev_lv:
                self.speech_bubble.show_message(
                    f"🎉 [레벨 업! Lv.{self.rpg_state.pet_level}] {summary_str} ✨",
                    duration_ms=4200,
                )

        elif etype == "bento_consumed":
            bento_key = payload.get("bentoKey")
            if self.rpg_state.consume_bento_from_js(bento_key):
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()

        elif etype == "enemy_defeated":
            gold_gain = int(payload.get("goldReward", payload.get("gold", 18)))
            xp_gain = int(payload.get("xpReward", payload.get("xp", 22)))
            core_drop = int(payload.get("coreDrop", 1))
            is_boss = bool(payload.get("isBoss", False))
            loot_name = str(payload.get("lootName", "침입자 정수"))
            loot_icon = str(payload.get("lootIcon", "👾"))
            loot_tier = str(payload.get("lootTier", "Rare" if is_boss else "Common"))
            self.rpg_state.gold += gold_gain
            self.rpg_state.total_enemies_defeated += 1
            self.rpg_state.record_monster_loot(loot_name, loot_icon, loot_tier)
            leveled = self.rpg_state.add_pet_xp(xp_gain)
            if is_boss or random.random() < 0.35:
                self.rpg_state.inventory["invader_core"] = self.rpg_state.inventory.get("invader_core", 0) + max(1, core_drop)

            # Progressive Weapon Drops from Hunting Enemies (맨손 -> 칼 -> 활 -> 총)
            wep_drop_msg: Optional[str] = None
            kills = self.rpg_state.total_enemies_defeated
            if kills >= 4 and "sword" not in self.rpg_state.unlocked_weapons:
                wep_drop_msg = self.rpg_state.unlock_weapon_drop("sword", auto_equip=True)
            elif kills >= 10 and "bow" not in self.rpg_state.unlocked_weapons:
                wep_drop_msg = self.rpg_state.unlock_weapon_drop("bow", auto_equip=True)
            elif (is_boss or kills >= 18) and "gun" not in self.rpg_state.unlocked_weapons:
                wep_drop_msg = self.rpg_state.unlock_weapon_drop("gun", auto_equip=True)

            if wep_drop_msg:
                self.set_rpg_weapon_type(self.rpg_state.equipped_weapon)
                self.speech_bubble.show_message(wep_drop_msg, duration_ms=4200)
            else:
                if hasattr(self, "_deferred_rpg_save_timer"):
                    self._deferred_rpg_save_timer.start()
                else:
                    self.rpg_state.save()
                    self._sync_rpg_to_js()
                if leveled:
                    self.speech_bubble.show_message(
                        f"⚔️ 적 처치 & 레벨 업! Lv.{self.rpg_state.pet_level} 달성! (전리품 [{loot_name}] 획득!) 🌟",
                        duration_ms=3500,
                    )

        elif etype == "skirmish_victory":
            bonus_gold = int(payload.get("bonusGold", 35))
            bonus_xp = int(payload.get("bonusXp", 30))
            self.rpg_state.gold += bonus_gold
            self.rpg_state.inventory["invader_core"] = self.rpg_state.inventory.get("invader_core", 0) + 1
            self.rpg_state.add_pet_xp(bonus_xp)
            wep_drop_msg = None
            if "sword" not in self.rpg_state.unlocked_weapons:
                wep_drop_msg = self.rpg_state.unlock_weapon_drop("sword", auto_equip=True)
            self.rpg_state.save()
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            self._exit_desktop_battle_arena()
            if self._state == PetState.SKIRMISH:
                self._state = PetState.IDLE
                self._schedule_next_decision(2600, 4200)
            extra = f"\n{wep_drop_msg}" if wep_drop_msg else ""
            self.speech_bubble.show_message(
                f"🛡️ 바탕화면 수호 완료! 🏆\n보상: +{bonus_gold}G, +{bonus_xp}XP, 코어 +1{extra}",
                duration_ms=4000,
            )

        elif etype == "solo_completed":
            self._on_solo_action_completed()

        elif etype == "wave_defense_result":
            victory = bool(payload.get("victory", False))
            wave_num = int(payload.get("wave", 1))
            reward_gold = int(payload.get("goldReward", payload.get("rewardGold", 80 + wave_num * 35)))
            reward_xp = int(payload.get("xpReward", payload.get("rewardXp", 45 + wave_num * 15)))
            reward_core = int(payload.get("coreReward", payload.get("rewardCore", 3 if wave_num % 5 == 0 else 1)))
            defeat_report = payload.get("defeatReport")
            if isinstance(defeat_report, dict):
                self.rpg_state.last_defense_report = defeat_report

            if victory or not isinstance(defeat_report, dict):
                self._defense_overlay_active = False
                self._exit_desktop_battle_arena()
                if self._state in {PetState.WAVE_DEFENSE, PetState.SKIRMISH}:
                    self._state = PetState.IDLE
                    self._schedule_next_decision(3000, 4800)
            else:
                # Keep desktop overlay alive so user can read #defense-defeat-report & click 1-click CTAs!
                self._defense_overlay_active = True
                self._set_win32_click_through(False)

            if victory:
                self.rpg_state.gold += reward_gold
                self.rpg_state.inventory["invader_core"] = self.rpg_state.inventory.get("invader_core", 0) + reward_core
                if wave_num % 5 == 0:
                    self.rpg_state.inventory["ore_legendary"] = self.rpg_state.inventory.get("ore_legendary", 0) + 1
                self.rpg_state.highest_wave = max(self.rpg_state.highest_wave, wave_num)
                self.rpg_state.add_pet_xp(reward_xp)

                wep_drop_msg = None
                if wave_num >= 1 and "sword" not in self.rpg_state.unlocked_weapons:
                    wep_drop_msg = self.rpg_state.unlock_weapon_drop("sword", auto_equip=True)
                elif wave_num >= 2 and "bow" not in self.rpg_state.unlocked_weapons:
                    wep_drop_msg = self.rpg_state.unlock_weapon_drop("bow", auto_equip=True)
                elif wave_num >= 4 and "gun" not in self.rpg_state.unlocked_weapons:
                    wep_drop_msg = self.rpg_state.unlock_weapon_drop("gun", auto_equip=True)

                self.rpg_state.save()
                self._sync_rpg_to_js()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
                extra = f"\n{wep_drop_msg}" if wep_drop_msg else ""
                msg = (
                    f"🏆 [Wave {wave_num} 디펜스 승리!]\n"
                    f"보상: +{reward_gold}G, +{reward_xp}XP, 침입자 코어 +{reward_core}개 획득!{extra} 🎉"
                )
                self.speech_bubble.show_message(msg, duration_ms=5800)
                if hasattr(self, "chat_window"):
                    self.chat_window.add_message("pet", msg, "defense_win")
            else:
                if reward_gold > 0:
                    self.rpg_state.gold += reward_gold
                self.rpg_state.save()
                self._sync_rpg_to_js()
                diag = self.rpg_state.diagnose_wave_readiness_dict(wave_num)
                advice_str = "\n".join(f"• {a}" for a in diag["advices"])
                msg = (
                    f"💥 [Wave {wave_num} 방어선 돌파됨 - 성장 가이드]\n"
                    f"{advice_str}\n(Ctrl+R 사령부에서 채굴·농사·낚시·강화로 스펙업 해보세요!)"
                )
                if not isinstance(defeat_report, dict):
                    self.speech_bubble.show_message(msg, duration_ms=6800)
                if hasattr(self, "chat_window"):
                    self.chat_window.add_message("pet", msg, "defense_fail")
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()

    def _sync_global_cursor_to_3d(self) -> None:
        if not self._web_ready:
            return
        now = time.perf_counter()
        cursor = QCursor.pos()
        dt = max(0.001, now - self._last_cursor_time)

        # Track cursor velocity for fast reaction
        dx_cursor = cursor.x() - self._last_cursor_global.x()
        dy_cursor = cursor.y() - self._last_cursor_global.y()
        cursor_dist = (dx_cursor * dx_cursor + dy_cursor * dy_cursor) ** 0.5
        self._cursor_speed_px = cursor_dist / dt
        self._last_cursor_global = cursor
        self._last_cursor_time = now

        # User activity detection
        if cursor_dist > 4.0:
            self._last_user_activity_time = now
            if self._is_napping:
                self._is_napping = False
                self.trigger_3d_action("Stretch", emotion="happy")
                self.speech_bubble.show_message("번쩍! 일어났다~! 반가워요! ☀️✨", duration_ms=2400)
                self._schedule_next_decision(2200, 3600)

        # 1. Natural Intermittent Gaze Scheduling
        is_direct_interaction = (
            self._is_dragging
            or self._left_pressed
            or self._state == PetState.PETTING
            or self._state == PetState.INTERACTING
            or self.chat_bar.isVisible()
        )

        if not self._intermittent_gaze_enabled or is_direct_interaction:
            # Direct engagement forces 100% focused attention
            attention_weight = 1.0
            self._gaze_mode = "watch"
            self._gaze_timer = random.uniform(3.0, 5.0)
        else:
            # If mouse suddenly moves quickly (> 420 px/s), pet notices and snaps to watch mode!
            if self._cursor_speed_px > 420.0 and self._gaze_mode != "watch":
                self._gaze_mode = "watch"
                self._gaze_timer = random.uniform(2.8, 5.2)

            self._gaze_timer -= dt
            if self._gaze_timer <= 0.0:
                if self._gaze_mode == "watch":
                    # Finished watching mouse, wander/look forward or around room
                    self._gaze_mode = "wander"
                    self._gaze_timer = random.uniform(1.8, 3.6)
                else:
                    # Glance back at the user's cursor
                    self._gaze_mode = "watch"
                    self._gaze_timer = random.uniform(2.8, 5.8)

            attention_weight = 1.0 if self._gaze_mode == "watch" else 0.12

        if abs(attention_weight - getattr(self, "_last_gaze_weight", -1.0)) > 0.02:
            self._last_gaze_weight = attention_weight
            self._run_js(
                f"typeof window.setGazeAttentionWeight === 'function' && "
                f"window.setGazeAttentionWeight({attention_weight:.2f});"
            )

        # Inactivity nap check (if pet has been idle without any interaction for > 150 seconds)
        if (
            not self._is_napping
            and self._state == PetState.IDLE
            and not self.chat_bar.isVisible()
            and (self._active_worker is None or not self._active_worker.isRunning())
            and now - self._last_user_activity_time >= 150.0
        ):
            self._is_napping = True
            self.trigger_3d_action("Sleepy", duration_ms=7500, emotion="sleepy")
            self.speech_bubble.show_message("Zzz... 포근해서 잠깐 낮잠 자는 중이에요... 💤", duration_ms=4500)

        # 2. Global head/eye cursor gaze tracking
        head_screen_x = self.x() + self.VIEWPORT_RECT.center().x()
        head_screen_y = self.y() + self.VIEWPORT_RECT.top() + 125
        dx_head = cursor.x() - head_screen_x
        dy_head = cursor.y() - head_screen_y

        nx = max(-1.0, min(1.0, dx_head / 520.0))
        ny = max(-1.0, min(1.0, -dy_head / 420.0))

        prev_x, prev_y = self._last_cursor_norm
        locomoting = self._state in {
            PetState.WALK, PetState.RUN, PetState.EVADING, PetState.EXCAVATING, PetState.WINDOW_HEIST
        }
        if (abs(nx - prev_x) > 0.008 or abs(ny - prev_y) > 0.008) and not (cursor_dist < 1.0 and locomoting):
            self._last_cursor_norm = (nx, ny)
            self._run_js(
                f"typeof window.updateCursorTarget === 'function' && "
                f"window.updateCursorTarget({nx:.3f}, {ny:.3f});"
            )

        # Mode 1: Fast Velocity Escape Trigger ONLY while strictly IDLE (never hijack running/cairn/minigame!)
        if (
            self._state == PetState.IDLE
            and not self._in_battle_arena
            and not self.is_action_busy(include_locomotion=True)
            and not self.chat_bar.isVisible()
            and (now - getattr(self, "_last_evasion_trigger_time", 0.0)) > 16.0
        ):
            pet_c = self.frameGeometry().center()
            to_pet_x = float(pet_c.x() - cursor.x())
            to_pet_y = float(pet_c.y() - cursor.y())
            dist_to_pet = math.hypot(to_pet_x, to_pet_y)
            step_x = float(dx_cursor)
            step_y = float(dy_cursor)
            approach_dot = step_x * to_pet_x + step_y * to_pet_y

            if self._cursor_speed_px > 680.0 and dist_to_pet < 340.0 and approach_dot > 0:
                self.start_mouse_evasion(mode="velocity")
                return

        # Skip tactile hover detectors while dragging, falling, or awaiting LLM
        llm_busy = self._active_worker is not None and self._active_worker.isRunning()
        if (
            self._is_dragging
            or self._left_pressed
            or self._in_battle_arena
            or self._state not in {PetState.IDLE, PetState.PETTING}
            or llm_busy
        ):
            if self._state == PetState.PETTING and (self._is_dragging or self._in_battle_arena or llm_busy):
                self._state = PetState.IDLE
                self._set_3d_petting_state(False)
            self._stroke_last_x = None
            self._curiosity_enter_time = None
            return

        # 2. Hover Head-Petting Stroke Detector (works seamlessly even while unfocused!)
        vp_top = self.y() + self.VIEWPORT_RECT.top()
        in_head_zone = (abs(dx_head) <= 84) and (vp_top + 28 <= cursor.y() <= vp_top + 198)

        if in_head_zone:
            if self._stroke_last_x is None:
                self._stroke_last_x = cursor.x()
                self._stroke_dir = 0
            else:
                step_x = cursor.x() - self._stroke_last_x
                if abs(step_x) >= 16:
                    new_dir = 1 if step_x > 0 else -1
                    if self._stroke_dir != 0 and new_dir != self._stroke_dir:
                        self._stroke_reversals = [t for t in self._stroke_reversals if now - t <= 1.25]
                        self._stroke_reversals.append(now)
                        if len(self._stroke_reversals) >= 3:
                            self._pet_release_deadline = now + 0.85
                            if self._state != PetState.PETTING:
                                self._pause_autonomous_walk(play_idle=False)
                                self._state = PetState.PETTING
                                self._set_3d_facing(0)
                                self._set_3d_petting_state(True)
                                if not self.chat_bar.isVisible() and now - self._last_poke_bubble_time > 3.5:
                                    self._last_poke_bubble_time = now
                                    self.speech_bubble.show_message("기분 최고야~ 계속 쓰다듬어 줘요! 🥰✨", duration_ms=2800)
                    elif self._state == PetState.PETTING:
                        self._pet_release_deadline = now + 0.85
                    self._stroke_dir = new_dir
                    self._stroke_last_x = cursor.x()
        else:
            self._stroke_last_x = None
            self._stroke_dir = 0

        if self._state == PetState.PETTING and (not in_head_zone or now > self._pet_release_deadline):
            self._state = PetState.IDLE
            self._set_3d_petting_state(False)
            self._stroke_reversals.clear()
            self._schedule_next_decision(1900, 3400)

        # 3. Cursor Proximity Curiosity (notices nearby cursor while IDLE!)
        dist_head = (dx_head * dx_head + dy_head * dy_head) ** 0.5
        if (
            self._state == PetState.IDLE
            and not self.chat_bar.isVisible()
            and 95.0 <= dist_head <= 255.0
            and now - self._last_curiosity_time >= 18.0
        ):
            if self._curiosity_enter_time is None:
                self._curiosity_enter_time = now
            elif now - self._curiosity_enter_time >= 1.55:
                self._last_curiosity_time = now
                self._curiosity_enter_time = None
                self.trigger_3d_action("Curious")
                self._schedule_next_decision(2200, 3800)
        else:
            self._curiosity_enter_time = None

    # -------------------------------------------------------------------------
    # Active "Bout-and-Pause" Autonomous Desktop Roaming FSM
    # -------------------------------------------------------------------------
    def _roll_next_special_cooldown(self) -> float:
        freq = getattr(getattr(self, "_prefs", None), "action_frequency", "normal")
        if freq == "frequent":
            return random.uniform(45.0, 95.0)
        if freq == "rare":
            return random.uniform(200.0, 420.0)
        return random.uniform(95.0, 210.0)

    def _schedule_next_decision(
        self,
        min_ms: Optional[int] = None,
        max_ms: Optional[int] = None,
        *,
        use_freq: bool = True,
    ) -> None:
        if self._state not in {PetState.IDLE, PetState.SITTING}:
            return
        coord = getattr(self, "coordinator", None)
        if coord is not None and coord.is_minigame_active():
            return
        if self._is_blocked_by_arena_or_hidden():
            return
        if not use_freq and min_ms is not None and max_ms is not None:
            delay = random.randint(int(min_ms), max(int(min_ms), int(max_ms)))
        else:
            freq = getattr(getattr(self, "_prefs", None), "action_frequency", "normal")
            if freq == "frequent":
                delay = random.randint(12000, 28000)
            elif freq == "rare":
                delay = random.randint(60000, 140000)
            elif freq == "off":
                delay = random.randint(60000, 90000)
            else:
                delay = random.randint(25000, 62000)
        self._decision_timer.start(delay)

    def _pause_autonomous_walk(self, play_idle: bool = True) -> None:
        self._sit_stand_pending = False
        if self._state in {PetState.WALK, PetState.RUN, PetState.SITTING}:
            self._state = PetState.IDLE
            self._roam_manual = False
            self._vel_x = 0.0
            self._vel_y = 0.0
            self._set_locomotion_velocity(0.0, 0.0)
            self._set_stage_yaw_override(None)
            self._current_stage_yaw = 0.0
            self._set_3d_facing(0)
            if play_idle:
                self.trigger_3d_action("Idle")
        if not self._decision_timer.isActive():
            self._schedule_next_decision(2200, 3800)

    def cancel_all_active_actions(self) -> None:
        """Cleanly stops and resets any currently running active action or solo activity, ensuring strict mutex."""
        prev_state = self._state
        if hasattr(self, "_decision_timer"):
            self._decision_timer.stop()
        if hasattr(self, "_solo_complete_timer"):
            self._solo_complete_timer.stop()
        if hasattr(self, "_heist_restore_timer"):
            self._heist_restore_timer.stop()
        if hasattr(self, "_heist_max_timeout_timer"):
            self._heist_max_timeout_timer.stop()
        if getattr(self, "_screen_hole_overlay", None) is not None:
            try:
                self._screen_hole_overlay.close()
            except Exception:
                pass
            self._screen_hole_overlay = None
        if getattr(self, "_spider_overlay", None) is not None:
            try:
                self._spider_overlay.close()
            except Exception:
                pass
            self._spider_overlay = None
        if hasattr(self, "stolen_piece_widget"):
            self.stolen_piece_widget.hide()
        if hasattr(self, "carried_stone_widget"):
            self.carried_stone_widget.hide()

        self._exit_desktop_battle_arena()

        self._run_js(
            "if (typeof window.setSpiderSwingState === 'function') window.setSpiderSwingState(false); "
            "if (typeof window.setWindowHeistState === 'function') window.setWindowHeistState(false); "
            "if (typeof window.setPeekState === 'function') window.setPeekState(false); "
            "if (typeof window.setMagicDoodleState === 'function') window.setMagicDoodleState(false); "
            "if (typeof window.setSupermanFlyState === 'function') window.setSupermanFlyState(false); "
            "if (typeof window.stopSoloAction === 'function') window.stopSoloAction(); "
            "if (typeof window.stopCombatAndDefense === 'function') window.stopCombatAndDefense();"
        )
        self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
        self._current_stage_yaw = 0.0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._phys_vx = 0.0
        self._phys_vy = 0.0
        self._doodle_proud_triggered = False
        self._choreo_active = False
        self._spider_current_swing = 1
        self._roam_waypoints.clear()
        self._roam_duration = 0.0
        self._roam_manual = False
        self._heist_waypoints.clear()
        self._excavating_target = None
        self._cairn_phase = "idle"
        self._cairn_mine_pos = None
        self._cairn_drop_pos = None
        self._cairn_delivered_cb = None
        if self._active_worker is not None and self._active_worker.isRunning():
            try:
                self._active_worker.terminate()
            except Exception:
                pass
            self._active_worker = None
        self._state = PetState.IDLE
        if prev_state in {PetState.SPIDER_SWING, PetState.SUPERMAN_FLY, PetState.HIDE_AND_SEEK, PetState.FALLING}:
            avail = self._current_available_geometry()
            self._pos_y = self._taskbar_floor_y(avail)
            self._update_window_pos()
        self._set_3d_facing(0)
        self.trigger_3d_action("Idle")

    def is_action_busy(self, include_locomotion: bool = True) -> bool:
        """Returns True if the pet is executing an active action, interaction, or (when include_locomotion=True) locomotion."""
        coord = getattr(self, "coordinator", None)
        busy_states = {
            PetState.SPIDER_SWING,
            PetState.HIDE_AND_SEEK,
            PetState.WINDOW_HEIST,
            PetState.MAGIC_DOODLE,
            PetState.SUPERMAN_FLY,
            PetState.SOLO_PLAY,
            PetState.EXCAVATING,
            PetState.SKIRMISH,
            PetState.WAVE_DEFENSE,
            PetState.FALLING,
            PetState.PETTING,
            PetState.INTERACTING,
            PetState.EVADING,
            PetState.MINIGAME,
            PetState.CAIRN_WORK,
        }
        if include_locomotion:
            busy_states |= {PetState.WALK, PetState.RUN, PetState.SITTING}
        return (
            self._is_dragging
            or self._left_pressed
            or self.is_popup_menu_open()
            or self._state in busy_states
            or (coord is not None and coord.is_minigame_active())
            or (hasattr(self, "chat_window") and self.chat_window.isVisible())
            or (self._active_worker is not None and self._active_worker.isRunning())
        )

    def _decide_next_autonomous_state(self) -> None:
        if self._is_blocked_by_arena_or_hidden():
            return
        if self._prefs.action_frequency == "off":
            if self._state == PetState.SITTING:
                self._sit_stand_pending = False
                self._state = PetState.IDLE
                self._set_3d_facing(0)
                self.trigger_3d_action("Idle")
            self._schedule_next_decision()
            return

        # Stand up cleanly from cozy taskbar Sit if pending
        if self._state == PetState.SITTING and self._sit_stand_pending and not self.is_action_busy(include_locomotion=False):
            self._sit_stand_pending = False
            self._state = PetState.IDLE
            self._set_3d_facing(0)
            self.trigger_3d_action("Stretch")
            self._schedule_next_decision()
            return

        # Strict Action Mutex: NEVER start or overlap a new autonomous action while busy/walking/running/minigame
        if self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True):
            return

        # Priority 0: Execute user's Intermittent Task Dispatch Queue (3-slot queue)
        if hasattr(self, "rpg_state") and self.rpg_state.dispatch_queue:
            next_task = self.rpg_state.dispatch_queue.pop(0)
            self.rpg_state.save()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            self._execute_dispatched_task(next_task)
            return

        avail = self._current_available_geometry()
        min_x = float(avail.left() + 16)
        max_x = float(max(avail.left() + 20, avail.right() - self.WINDOW_W - 16))
        roam_span = max_x - min_x
        roll = random.random()
        now = time.perf_counter()

        # 0. High-Energy Special Autonomous Actions gated by randomized special cooldown
        special_ready = (now - self._last_special_action_time) >= self._next_special_cooldown_sec
        if special_ready and self._prefs.action_frequency != "off":
            freq_mult = {"frequent": 1.6, "normal": 1.0, "rare": 0.45}.get(self._prefs.action_frequency, 1.0)
            threshold = 0.24 * freq_mult
            if roll < threshold:
                candidates = []
                if roam_span > 220:
                    candidates.append(lambda: self.start_roaming_excavation(manual=False))
                if self._prefs.enable_spider and roam_span > 260:
                    candidates.append(lambda: self.start_spider_swing(manual=False))
                if self._prefs.enable_peek:
                    candidates.append(lambda: self.start_hide_and_seek(manual=False))
                if self._prefs.enable_heist and roam_span > 240:
                    candidates.append(lambda: self.start_screen_content_heist(manual=False))
                if self._prefs.enable_doodle:
                    candidates.append(lambda: self.start_magic_doodle(manual=False))
                if self._prefs.enable_superman and roam_span > 260:
                    candidates.append(lambda: self.start_superman_fly(manual=False))
                if random.random() < 0.16:
                    candidates.append(lambda: self.start_mouse_evasion(mode="taunt", manual=False))

                if candidates:
                    chosen = random.choice(candidates)
                    chosen()
                    return

        if roam_span > 140 and roll < 0.50:
            # 1. Omnidirectional 2D Desktop RPG Roam: Cute waddle Walk
            self.start_omnidirectional_roam(mode="walk", manual=False)
        elif roam_span > 240 and roll < 0.68:
            # 2. Omnidirectional 2D Desktop RPG Roam: Energetic scamper Run
            self.start_omnidirectional_roam(mode="run", manual=False)
        elif roll < 0.90:
            # 3. Playful in-place game character expression or solo activity
            self._state = PetState.IDLE
            self._set_3d_facing(0)
            if random.random() < 0.35:
                chosen_solo = random.choice(list(SOLO_ACTIONS_INFO.keys()))
                self.play_solo_action(chosen_solo, manual=False)
            else:
                playful = random.choices(
                    ["Curious", "Dance", "HappySpin", "Wave", "Stretch"],
                    weights=[30, 25, 20, 15, 10],
                    k=1,
                )[0]
                dur_ms = 3040 if playful == "Dance" else 0
                self.trigger_3d_action(playful, duration_ms=dur_ms)
                self._schedule_next_decision()
        else:
            # 4. Cozy taskbar Sit (chains into Stretch when standing back up!)
            self._state = PetState.SITTING
            self._sit_stand_pending = True
            self._set_3d_facing(0)
            self.trigger_3d_action("Sit")
            self._schedule_next_decision()

    # -------------------------------------------------------------------------
    # Special High-Energy Interactive Actions
    # -------------------------------------------------------------------------
    def start_spider_swing(self, manual: bool = True) -> None:
        """Shoots a thin dark silk web to the upper ceiling and swings across the desktop in realistic
        gravity-driven Spider-Man circular pendulum arcs before a smooth parabolic landing!"""
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        self._spider_total_swings = random.randint(2, 3)
        self._spider_current_swing = 1
        avail = self._current_available_geometry()
        mid_x = (avail.left() + avail.right() - self.WINDOW_W) / 2.0
        self._spider_dir = 1.0 if self._pos_x <= mid_x else -1.0
        self._setup_spider_swing_segment()
        self._state = PetState.SPIDER_SWING
        self.trigger_3d_action("Jump")
        self.speech_bubble.show_message(
            f"🕸️ 거미줄 스윙 출발! 원호를 그리며 {self._spider_total_swings}연속 이동!",
            duration_ms=2400,
        )

    def _setup_spider_swing_segment(self) -> None:
        avail = self._current_available_geometry()
        floor_y = self._taskbar_floor_y(avail)
        self._spider_floor_y = floor_y
        self._spider_phase = "swing"
        self._spider_t = 0.0
        self._spider_seg_dur = random.uniform(1.18, 1.38)

        hand_anchor = getattr(self, "_live_hand_anchor", None)
        if hand_anchor is not None:
            hx, hy = float(hand_anchor[0]), float(hand_anchor[1])
        else:
            hx = float(self.WINDOW_W // 2)
            hy = float(469.1 - 150.0 * max(0.10, self._scale_factor))
        self._spider_hand_offset = (hx, hy)

        min_win_x = float(avail.left() + 24)
        max_win_x = float(max(avail.left() + 80, avail.right() - self.WINDOW_W - 24))

        # Keep forward momentum across arcs, reversing cleanly if approaching monitor side bezel
        if self._spider_dir > 0 and self._pos_x > (max_win_x - 320.0):
            self._spider_dir = -1.0
        elif self._spider_dir < 0 and self._pos_x < (min_win_x + 320.0):
            self._spider_dir = 1.0

        h0_x = self._pos_x + hx
        h0_y = self._pos_y + hy

        # Anchor high on the upper ceiling ahead of the character so the web traces a true U-shaped circular arc!
        anchor_y = float(avail.top() + 8)
        lead_span = random.uniform(215.0, 295.0) * self._spider_dir
        anchor_x = max(float(avail.left() + 140), min(float(avail.right() - 140), h0_x + lead_span))
        if abs(anchor_x - h0_x) < 95.0:
            self._spider_dir = -self._spider_dir
            anchor_x = max(
                float(avail.left() + 140),
                min(float(avail.right() - 140), h0_x + 250.0 * self._spider_dir),
            )

        dx0 = h0_x - anchor_x
        dy0 = max(65.0, h0_y - anchor_y)
        l_start = math.hypot(dx0, dy0)
        theta_start = math.atan2(dx0, dy0)

        # Safe pendulum radius so bottom dead center (theta = 0) swoops gracefully above taskbar without clipping
        max_safe_l = max(140.0, (floor_y + hy - 22.0) - anchor_y)
        l_arc = min(l_start * 0.90, max_safe_l * random.uniform(0.76, 0.89))

        # Forward upward swoop apex angle (clamped so window stays within horizontal desktop bounds)
        raw_theta_end = self._spider_dir * random.uniform(0.62, 0.80)
        max_hand_x = max_win_x + hx
        min_hand_x = min_win_x + hx
        if self._spider_dir > 0:
            max_sin = min(0.84, max(0.22, (max_hand_x - anchor_x) / max(1.0, l_arc)))
            theta_end = min(raw_theta_end, math.asin(max_sin))
        else:
            min_sin = max(-0.84, min(-0.22, (min_hand_x - anchor_x) / max(1.0, l_arc)))
            theta_end = max(raw_theta_end, math.asin(min_sin))

        self._spider_anchor_global = QPointF(anchor_x, anchor_y)
        self._spider_l_start = l_start
        self._spider_l_arc = l_arc
        self._spider_theta_start = theta_start
        self._spider_theta_end = theta_end

        init_yaw = 1.24 * self._spider_dir
        self._current_stage_yaw = init_yaw
        self._send_locomotion_batch(init_yaw, self._spider_dir * 160.0, 0.0, int(self._spider_dir), force=True, snap=True)
        if self._spider_overlay is None:
            self._spider_overlay = SpiderWebOverlay()

    def start_hide_and_seek(self, manual: bool = True) -> None:
        """Hides body behind the taskbar edge, peeking with eyes and horn, and emerges automatically after a timer if not found!"""
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        avail = self._current_available_geometry()
        self._peek_normal_y = self._taskbar_floor_y(avail)
        self._pos_y = self._peek_normal_y
        self._peek_depth = 0.0
        self._peek_revealed = False
        self._peek_start_time = time.perf_counter()
        self._peek_max_duration = random.uniform(7.5, 10.5)
        self._state = PetState.HIDE_AND_SEEK
        self.speech_bubble.show_message("나 찾아봐라~ 3초 센다! 1, 2, 3... 쏙! 🙈", duration_ms=2600)

    def start_screen_content_heist(self, manual: bool = True) -> None:
        """
        4. Screen Content Heist 2.0 with ScreenHoleOverlay:
           - Capturing desktop content via QGuiApplication.primaryScreen().grabWindow
           - Displaying a realistic torn hole / erased overlay patch at original spot
           - Pet holding the stolen content piece directly in its raised hands and running in 2D
           - Dual restoration: automatic after 10~15s, or immediate on mouse catch/click, with max 25s timeout.
        """
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()

        screen = QGuiApplication.primaryScreen()
        avail = self._current_available_geometry()

        gw, gh = 220, 140
        # Pick capture location near pet on desktop
        gx = max(avail.left() + 40, min(avail.right() - gw - 40, int(self._pos_x + (self.WINDOW_W - gw) // 2)))
        gy = max(avail.top() + 60, min(avail.bottom() - gh - 80, int(self._pos_y + 140)))
        grab_rect = QRect(gx, gy, gw, gh)

        # 1. Grab actual screen content
        captured_pixmap = screen.grabWindow(0, gx, gy, gw, gh)

        # 2. Display realistic torn-paper void hole overlay patch
        if self._screen_hole_overlay is not None:
            try:
                self._screen_hole_overlay.close()
            except Exception:
                pass
            self._screen_hole_overlay = None

        self._screen_hole_overlay = ScreenHoleOverlay(grab_rect)
        self._screen_hole_overlay.hole_clicked.connect(lambda: self.restore_screen_heist(caught_by_user=True))
        self._screen_hole_overlay.show()

        # 3. Mount stolen content piece card directly on pet's hands (zero white gap)
        self.stolen_piece_widget.set_content(captured_pixmap)
        self._reposition_stolen_piece_widget()
        self.stolen_piece_widget.show()
        self.stolen_piece_widget.raise_()

        self._state = PetState.WINDOW_HEIST
        self._heist_progress = 0.0
        self._heist_start_time = time.perf_counter()
        self._heist_duration = random.uniform(10.0, 15.0)

        # 4. Generate 2D multi-waypoint path for running with the stolen content
        self._heist_waypoints = self._generate_2d_desktop_waypoints(random.randint(4, 7))
        if self._heist_waypoints:
            hx0, hy0 = self._heist_waypoints[0]
            hdx, hdy = hx0 - self._pos_x, hy0 - self._pos_y
            if math.hypot(hdx, hdy) > 2.0:
                iyaw = math.atan2(hdx, hdy * 0.82 if abs(hdx) > 6.0 else hdy)
                self._current_stage_yaw = iyaw
                self._send_locomotion_batch(iyaw, hdx, hdy, 1 if hdx >= 0 else -1, force=True, snap=True)

        self.trigger_3d_action("Run", emotion="excited")
        self._run_js("typeof window.setWindowHeistState === 'function' && window.setWindowHeistState(true, '화면 조각 🪟');")
        self.speech_bubble.show_message("헤헤! 바탕화면 한 조각 훔쳤다~! 잡아봐라~!! 🪟💨", duration_ms=3500)

        # Dual restoration: auto timer (10~15s) and max failsafe timeout (25s)
        self._heist_restore_timer.start(int(self._heist_duration * 1000))
        self._heist_max_timeout_timer.start(25000)

    def restore_screen_heist(self, caught_by_user: bool = False, quiet: bool = False) -> None:
        """Restores screen content gracefully: closes hole overlay, hides piece card, returns to IDLE."""
        self._heist_restore_timer.stop()
        self._heist_max_timeout_timer.stop()

        if self._screen_hole_overlay is not None:
            try:
                self._screen_hole_overlay.close()
            except Exception:
                pass
            self._screen_hole_overlay = None

        if hasattr(self, "stolen_piece_widget"):
            self.stolen_piece_widget.hide()

        self._run_js("typeof window.setWindowHeistState === 'function' && window.setWindowHeistState(false);")
        self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
        self._current_stage_yaw = 0.0
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._phys_vx = 0.0
        self._phys_vy = 0.0

        if not quiet:
            if caught_by_user:
                self.trigger_3d_action("Shy", emotion="shy")
                self.speech_bubble.show_message("앗 들켰다! 헤헤 장난이었어요~ 원래대로 찰칵 붙여둘게요! 🩹💖", duration_ms=3500)
            else:
                self.trigger_3d_action("HappySpin", emotion="proud")
                self.speech_bubble.show_message("히히 실컷 구경했으니 다시 제자리에 쏙! 복구 완료! ✨", duration_ms=3500)

        self._state = PetState.IDLE
        self._schedule_next_decision(2200, 4200)

    def _generate_2d_desktop_waypoints(self, count: int = 4) -> list[tuple[float, float]]:
        """Generates random 2D waypoints spanning full desktop bounds (min_x..max_x, min_y..max_y)."""
        avail = self._current_available_geometry()
        min_x = float(avail.left() + 20)
        max_x = float(max(avail.left() + 30, avail.right() - self.WINDOW_W - 20))
        min_y = float(avail.top() + 30)
        max_y = float(self._taskbar_floor_y(avail))

        pts: list[tuple[float, float]] = []
        curr_x, curr_y = self._pos_x, self._pos_y
        for _ in range(count):
            cand_x, cand_y = curr_x, curr_y
            for _attempt in range(12):
                cand_x = random.uniform(min_x, max_x)
                cand_y = random.uniform(min_y, max_y)
                if math.hypot(cand_x - curr_x, cand_y - curr_y) >= 340.0:
                    break
            pts.append((cand_x, cand_y))
            curr_x, curr_y = cand_x, cand_y
        return pts

    def start_omnidirectional_roam(
        self, mode: str = "walk", duration: Optional[float] = None, manual: bool = False
    ) -> None:
        """
        1. Omnidirectional 2D Desktop RPG Roaming:
           - Walk and Run across full desktop (min_x to max_x, min_y to max_y)
           - Multi-waypoint pathing with duration randomized between 6.0 and 25.0 seconds
           - Smooth 3D yaw calculation using math.atan2 so character turns towards travel direction
        """
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()

        self._roam_duration = duration if duration is not None else random.uniform(6.0, 25.0)
        self._roam_start_time = time.perf_counter()
        self._last_tick_time = self._roam_start_time
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._roam_mode = mode
        self._roam_manual = bool(manual)
        self._state = PetState.RUN if mode == "run" else PetState.WALK

        self._roam_waypoints = self._generate_2d_desktop_waypoints(random.randint(3, 6))
        if self._roam_waypoints:
            wx0, wy0 = self._roam_waypoints[0]
            idx0, idy0 = wx0 - self._pos_x, wy0 - self._pos_y
            if math.hypot(idx0, idy0) > 2.0:
                iyaw = math.atan2(idx0, idy0 * 0.82 if abs(idx0) > 6.0 else idy0)
                self._current_stage_yaw = iyaw
                self._send_locomotion_batch(iyaw, idx0, idy0, 1 if idx0 >= 0 else -1, force=True, snap=True)
        self.trigger_3d_action("Run" if mode == "run" else "Walk")

    def _finish_omnidirectional_roam(self) -> None:
        self._roam_waypoints.clear()
        self._roam_duration = 0.0
        self._roam_manual = False
        was_running = (self._state == PetState.RUN)
        self._state = PetState.IDLE
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._set_locomotion_velocity(0.0, 0.0)
        self._set_stage_yaw_override(None)
        self._current_stage_yaw = 0.0
        self._set_3d_facing(0)

        if random.random() < 0.45:
            arrival_act = "HappySpin" if (was_running and random.random() < 0.5) else random.choice(["Curious", "Wave", "Stretch"])
            self.trigger_3d_action(arrival_act)
            self._schedule_next_decision(2200, 3800)
        else:
            self.trigger_3d_action("Idle")
            self._schedule_next_decision(1800, 3400)

    def start_mouse_evasion(
        self, mode: str = "velocity", custom_taunt: Optional[str] = None, manual: bool = False
    ) -> None:
        """
        3. 3-Mode Mouse Evasion AI:
           - Fast velocity escape (smart dodge away from high-speed cursor approach)
           - Distance escape (maintaining radial buffer zone)
           - Fleeing with taunt emotes ("잡아봐라~", "메롱!")
        """
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()

        self._evasion_mode = mode
        self._state = PetState.EVADING
        self._evasion_start_time = time.perf_counter()
        self._last_tick_time = self._evasion_start_time
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._evasion_duration = random.uniform(12.0, 18.0)
        self._last_taunt_time = time.perf_counter()
        self._last_evasion_trigger_time = time.perf_counter()

        cursor = QCursor.pos()
        pet_c = self.frameGeometry().center()
        dx = float(pet_c.x() - cursor.x())
        dy = float(pet_c.y() - cursor.y())
        dist = max(1.0, math.hypot(dx, dy))
        escape_dist = random.uniform(480.0, 780.0)

        avail = self._current_available_geometry()
        min_x = float(avail.left() + 20)
        max_x = float(avail.right() - self.WINDOW_W - 20)
        min_y = float(avail.top() + 30)
        max_y = float(self._taskbar_floor_y(avail))

        self._evasion_target_x = max(min_x, min(max_x, self._pos_x + (dx / dist) * escape_dist))
        self._evasion_target_y = max(min_y, min(max_y, self._pos_y + (dy / dist) * escape_dist))
        edx0 = self._evasion_target_x - self._pos_x
        edy0 = self._evasion_target_y - self._pos_y
        if math.hypot(edx0, edy0) > 2.0:
            iyaw = math.atan2(edx0, edy0 * 0.82 if abs(edx0) > 6.0 else edy0)
            self._current_stage_yaw = iyaw
            self._send_locomotion_batch(iyaw, edx0, edy0, 1 if edx0 >= 0 else -1, force=True, snap=True)

        self.trigger_3d_action("Run", emotion="excited")
        taunt = custom_taunt or (
            "으악! 엄청 빠르다! 도망쳐~! ⚡💨" if mode == "velocity" else "잡아봐라~ 💨 못 잡겠지롱! 😝"
        )
        self.speech_bubble.show_message(taunt, duration_ms=2500)

    def _finish_mouse_evasion(self, caught: bool) -> None:
        self._state = PetState.IDLE
        self._vel_x = 0.0
        self._vel_y = 0.0
        self._set_locomotion_velocity(0.0, 0.0)
        self._set_stage_yaw_override(None)
        self._current_stage_yaw = 0.0
        self._set_3d_facing(0)

        if caught:
            self.trigger_3d_action("HappySpin", emotion="surprised")
            reward_gold = 70 + getattr(self.rpg_state, "pet_level", 1) * 15
            reward_xp = 40
            bonus_item_text = ""
            if hasattr(self, "rpg_state"):
                self.rpg_state.gold += reward_gold
                leveled = self.rpg_state.add_pet_xp(reward_xp)
                if random.random() < 0.45:
                    drop_key, drop_label = random.choice([
                        ("hp_potion", "성소 치유 물약 🧪"),
                        ("haste_elixir", "신속의 비약 ⚡"),
                        ("rage_elixir", "광전사의 비약 🔥"),
                        ("luck_potion", "황금 행운 비약 🍀"),
                    ])
                    self.rpg_state.consumables[drop_key] = self.rpg_state.consumables.get(drop_key, 0) + 1
                    bonus_item_text = f" + [{drop_label}]"
                if leveled:
                    bonus_item_text += f" (🎉 Lv.{self.rpg_state.pet_level} 레벨 업!)"
                self.rpg_state.save()
                self._sync_rpg_to_js()
                if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                    self.rpg_hub.refresh_ui()
                total_g = self.rpg_state.gold
            else:
                total_g = reward_gold
            msg = (
                f"🏳️ 술래잡기 잡혔다! (+{reward_gold}G, +{reward_xp}XP)\n"
                f"보유 포인트: {total_g:,}G{bonus_item_text} 🎁"
            )
            self.speech_bubble.show_message(msg, duration_ms=3800)
            if hasattr(self, "chat_window"):
                self.chat_window.add_message("pet", msg, "evasion_win")
        else:
            self.trigger_3d_action("Proud", emotion="proud")
            if hasattr(self, "rpg_state"):
                self.rpg_state.gold += 20
                self.rpg_state.add_pet_xp(12)
                self.rpg_state.save()
                self._sync_rpg_to_js()
            self.speech_bubble.show_message(
                f"🏆 끝까지 도망 성공!\n{self.char_display_name} 승리! (+20G)",
                duration_ms=3200,
            )

        self._schedule_next_decision(2400, 4200)

    def start_magic_doodle(self, shape: Optional[str] = None, manual: bool = True) -> None:
        """Draws glowing grand neon graffiti (heart, star, fireworks festival) reaching across the screen!"""
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        shapes = ["heart", "star", "fireworks"]
        if shape == "smile":
            shape = "fireworks"
        self._doodle_shape = shape if shape in shapes else random.choice(shapes)
        self._doodle_progress = 0.0
        self._doodle_timer = 0.0
        self._doodle_proud_triggered = False
        self._state = PetState.MAGIC_DOODLE
        self._set_3d_facing(0)
        self.trigger_3d_action("Dance", emotion="excited")
        shape_kr = {"heart": "하트 💖", "star": "별 🌟", "fireworks": "불꽃 축제 🎆"}.get(self._doodle_shape, self._doodle_shape)
        self.speech_bubble.show_message(f"바탕화면에 화려한 마법 [{shape_kr}] 펼치는 중... 🎆✨", duration_ms=2800)

    def start_superman_fly(self, duration: Optional[float] = None, manual: bool = True) -> None:
        """
        2. Superhero Flight:
           Extended duration randomized between 8.0 and 25.0 seconds with multi-wave swoops across desktop.
           When mode == 1 (mouse stealer), physically carries the real OS mouse cursor along with the pet's hands!
        """
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return
        coord = getattr(self, "coordinator", None)
        if manual and coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._last_special_action_time = time.perf_counter()
        self._next_special_cooldown_sec = self._roll_next_special_cooldown()
        avail = self._current_available_geometry()
        floor_y = self._taskbar_floor_y(avail)
        self._superman_floor_y = floor_y
        self._superman_start_x = self._pos_x
        self._superman_start_y = self._pos_y
        self._superman_duration = duration if duration is not None else random.uniform(8.0, 25.0)
        self._superman_start_time = time.perf_counter()
        self._superman_progress = 0.0
        self._superman_waves = max(2, int(self._superman_duration / 3.8))
        self._superman_mode = random.choices([1, 0, 2], weights=[45, 30, 25], k=1)[0]
        self._superman_cursor_released = False
        self._stolen_cursor_pos = QCursor.pos()
        self._state = PetState.SUPERMAN_FLY

        mid_x = (avail.left() + avail.right() - self.WINDOW_W) / 2.0
        self._superman_dir = 1.0 if self._pos_x < mid_x else -1.0
        self._set_3d_facing(int(self._superman_dir))
        self.trigger_3d_action("WaveJump")
        self._run_js(
            f"typeof window.setSupermanFlyState === 'function' && "
            f"window.setSupermanFlyState(true, 0, {self._superman_mode});"
        )
        if self._superman_mode == 1:
            self.speech_bubble.show_message("쓩~! 🚀 실제 마우스 커서 낚아채서 성층권으로 들고 도망간다~!! (마우스를 크게 흔들면 놓아줘요!) 🖱️💨", duration_ms=3400)
        elif self._superman_mode == 2:
            self.speech_bubble.show_message("쓩~! 🚀 중요 서류 파일 들고 초고속 비행 출발~!! 📁💨", duration_ms=3200)
        else:
            self.speech_bubble.show_message(
                f"슈퍼맨 {self.char_display_name} 출동! 🚀 {int(self._superman_duration)}초 동안 전방위 무지개 비행 시작!",
                duration_ms=3200,
            )

    def start_cairn_mining_trip(
        self,
        mine_pos: tuple[float, float],
        drop_pos: tuple[float, float],
        stone_index: int,
        target_stones: int,
        on_delivered: Optional[object] = None,
        manual: bool = False,
    ) -> bool:
        """Sends the pet to mine a stone at `mine_pos` and carry it to the bottom-right cairn `drop_pos`."""
        if self._is_dragging or self._left_pressed or self._is_blocked_by_arena_or_hidden():
            return False
        if not manual and (self._state != PetState.IDLE or self.is_action_busy(include_locomotion=True)):
            return False
        self.cancel_all_active_actions()
        self._decision_timer.stop()

        self._cairn_mine_pos = (float(mine_pos[0]), float(mine_pos[1]))
        self._cairn_drop_pos = (float(drop_pos[0]), float(drop_pos[1]))
        self._cairn_stone_index = int(stone_index)
        self._cairn_target_stones = int(target_stones)
        self._cairn_delivered_cb = on_delivered
        self._cairn_phase = "go_mine"
        self._state = PetState.CAIRN_WORK
        mdx, mdy = self._cairn_mine_pos[0] - self._pos_x, self._cairn_mine_pos[1] - self._pos_y
        if math.hypot(mdx, mdy) > 2.0:
            iyaw = math.atan2(mdx, mdy * 0.82 if abs(mdx) > 6.0 else mdy)
            self._current_stage_yaw = iyaw
            self._send_locomotion_batch(iyaw, mdx, mdy, 1 if mdx >= 0 else -1, force=True, snap=True)
        self.trigger_3d_action("Run", emotion="excited")
        self.speech_bubble.show_message(
            f"⛏️ 돌탑 {self._cairn_stone_index}/{self._cairn_target_stones}번째 돌 캐러 출동~! 🪨",
            duration_ms=2600,
        )
        return True

    def _on_roam_tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self._last_tick_time)
        self._last_tick_time = now

        if not self.isVisible():
            self._choreo_active = False
            if getattr(self, "_spider_overlay", None) is not None:
                self._spider_overlay.hide()
            return

        if self._state == PetState.MINIGAME:
            return

        if self._state != PetState.SPIDER_SWING and getattr(self, "_spider_overlay", None) is not None:
            if self._spider_overlay.isVisible():
                self._spider_overlay.hide()

        if self._is_dragging:
            self._choreo_active = False
            self._phys_vx = 0.0
            self._phys_vy = 0.0
            return

        # Freeze all movement & advance active timers seamlessly while the right-click popup menu is open!
        if self.is_popup_menu_open():
            self._choreo_active = False
            self._vel_x = 0.0
            self._vel_y = 0.0
            self._phys_vx = 0.0
            self._phys_vy = 0.0
            if self._state in {PetState.WALK, PetState.RUN}:
                self._roam_start_time += dt
            elif self._state == PetState.EVADING:
                self._evasion_start_time += dt
            elif self._state == PetState.SUPERMAN_FLY:
                self._superman_start_time += dt
            elif self._state == PetState.CAIRN_WORK and getattr(self, "_cairn_phase", "") == "mining":
                self._cairn_mine_end_time += dt
            return

        # 0. Desktop-Scale Jump Arc (vertical-only, zero side-to-side bouncing on solo/mining actions)
        if getattr(self, "_choreo_active", False):
            if (
                self._state not in {PetState.IDLE, PetState.SITTING}
                or getattr(self, "_in_battle_arena", False)
            ):
                self._choreo_active = False
            else:
                self._choreo_t += dt
                avail = self._current_available_geometry()
                min_x = float(avail.left() + 8)
                max_x = float(max(avail.left() + 20, avail.right() - self.WINDOW_W - 8))
                min_y = float(avail.top() + 8)
                max_y = float(self._taskbar_floor_y(avail))
                if self._choreo_t >= self._choreo_dur:
                    self._choreo_active = False
                    self._pos_x = max(min_x, min(max_x, self._choreo_origin_x))
                    self._pos_y = max(min_y, min(max_y, self._choreo_origin_y))
                    self._update_window_pos()
                else:
                    u = self._choreo_t / max(0.1, self._choreo_dur)
                    dx = 0.0
                    dy = -math.sin(u * math.pi) * 44.0
                    self._pos_x = max(min_x, min(max_x, self._choreo_origin_x + dx))
                    self._pos_y = max(min_y, min(max_y, self._choreo_origin_y + dy))
                    self._update_window_pos()
                    return

        # 1. Taskbar Gravity Free-Fall & Cushioned Elastic Bounce
        if self._state == PetState.FALLING:
            avail = self._current_available_geometry()
            floor_y = self._taskbar_floor_y(avail)
            min_x = float(avail.left() - 24)
            max_x = float(avail.right() - self.WINDOW_W + 24)

            self._fall_vy += 2500.0 * dt
            self._pos_y += self._fall_vy * dt
            self._pos_x = max(min_x, min(max_x, self._pos_x + self._fall_vx * dt))

            if self._pos_y >= floor_y:
                self._pos_y = floor_y
                if not self._fall_bounced and self._fall_vy > 340.0:
                    self._fall_vy = -self._fall_vy * 0.24
                    self._fall_vx *= 0.55
                    self._fall_bounced = True
                    self._update_window_pos()
                    return

                self._update_window_pos()
                self._set_3d_falling_state(False, 0.0)
                self._state = PetState.IDLE
                self.trigger_3d_action("DropLand")
                self._schedule_next_decision(1900, 3400)
                return

            self._update_window_pos()
            norm_vy = max(-2.2, min(2.2, -self._fall_vy / 900.0))
            self._set_3d_falling_state(True, norm_vy)
            return

        # 1.8 Desktop Roaming Mining (EXCAVATING: runs to ore vein waypoint, then mines)
        if self._state == PetState.EXCAVATING:
            if not self._excavating_target:
                self.play_solo_action("mining")
                return
            tx, ty = self._excavating_target
            dx = tx - self._pos_x
            dy = ty - self._pos_y
            dist = math.hypot(dx, dy)
            scale_mult = max(0.72, min(1.22, 0.64 + self._scale_factor * 0.65))
            step_speed = (self._run_speed * 1.0) * scale_mult
            step = step_speed * dt
            if dist <= max(step, 10.0):
                self._pos_x = tx
                self._pos_y = ty
                self._vel_x = 0.0
                self._vel_y = 0.0
                self._update_window_pos()
                self._excavating_target = None
                self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                self._current_stage_yaw = 0.0
                self.play_solo_action(
                    "mining",
                    custom_speech="💎 여기서 반짝이는 광맥 소리가 나요! 바탕화면 채굴 시작! ⛏️✨",
                )
            else:
                prev_x, prev_y = self._pos_x, self._pos_y
                desired_vx = (dx / dist) * step_speed
                desired_vy = (dy / dist) * step_speed
                blend = 1.0 - math.exp(-11.0 * dt)
                self._vel_x += (desired_vx - self._vel_x) * blend
                self._vel_y += (desired_vy - self._vel_y) * blend
                self._pos_x += self._vel_x * dt
                self._pos_y += self._vel_y * dt
                self._update_window_pos()
                self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
            return

        # 1.9 Workday Stone Cairn Mining & Transport (CAIRN_WORK: run -> mine -> carry_to_cairn -> stack)
        if self._state == PetState.CAIRN_WORK:
            scale_mult = max(0.72, min(1.22, 0.64 + self._scale_factor * 0.65))
            step_speed = (self._run_speed * 0.98) * scale_mult
            if self._cairn_phase == "go_mine":
                if not self._cairn_mine_pos:
                    self._state = PetState.IDLE
                    self._schedule_next_decision()
                    return
                mx, my = self._cairn_mine_pos
                dx, dy = mx - self._pos_x, my - self._pos_y
                dist = math.hypot(dx, dy)
                step = step_speed * dt
                if dist <= max(step, 14.0):
                    self._pos_x, self._pos_y = mx, my
                    self._vel_x = 0.0
                    self._vel_y = 0.0
                    self._update_window_pos()
                    self._current_stage_yaw = 0.0
                    self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    self._cairn_phase = "mining"
                    self._cairn_mine_end_time = now + 4.7
                    self._run_js("typeof window.playSoloAction === 'function' && window.playSoloAction('mining');")
                    self.speech_bubble.show_message("⛏️ 뚝딱뚝딱! 반짝이는 돌 채굴 중~! 🪨", duration_ms=3200)
                else:
                    prev_x, prev_y = self._pos_x, self._pos_y
                    desired_vx = (dx / dist) * step_speed
                    desired_vy = (dy / dist) * step_speed
                    blend = 1.0 - math.exp(-11.0 * dt)
                    self._vel_x += (desired_vx - self._vel_x) * blend
                    self._vel_y += (desired_vy - self._vel_y) * blend
                    self._pos_x += self._vel_x * dt
                    self._pos_y += self._vel_y * dt
                    self._update_window_pos()
                    self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
                return

            if self._cairn_phase == "mining":
                if now >= self._cairn_mine_end_time:
                    self._run_js("typeof window.stopSoloAction === 'function' && window.stopSoloAction();")
                    if hasattr(self, "carried_stone_widget"):
                        is_cap = self._cairn_stone_index >= self._cairn_target_stones
                        self.carried_stone_widget.set_stone_palette(self._cairn_stone_index - 1, is_capstone=is_cap)
                        self._reposition_carried_stone_widget()
                        self.carried_stone_widget.show()
                        self.carried_stone_widget.raise_()
                    self._cairn_phase = "carry_to_cairn"
                    if self._cairn_drop_pos:
                        cdx, cdy = self._cairn_drop_pos[0] - self._pos_x, self._cairn_drop_pos[1] - self._pos_y
                        if math.hypot(cdx, cdy) > 2.0:
                            iyaw = math.atan2(cdx, cdy * 0.82 if abs(cdx) > 6.0 else cdy)
                            self._current_stage_yaw = iyaw
                            self._send_locomotion_batch(iyaw, cdx, cdy, 1 if cdx >= 0 else -1, force=True, snap=True)
                    self.trigger_3d_action("Run", emotion="happy")
                    self.speech_bubble.show_message("🪨 돌 획득! 오른쪽 아래 돌탑으로 운반 중~! 🐾", duration_ms=2600)
                return

            if self._cairn_phase == "carry_to_cairn":
                if hasattr(self, "carried_stone_widget") and self.carried_stone_widget.isVisible():
                    self._reposition_carried_stone_widget()
                if not self._cairn_drop_pos:
                    self._state = PetState.IDLE
                    self._schedule_next_decision()
                    return
                tx, ty = self._cairn_drop_pos
                dx, dy = tx - self._pos_x, ty - self._pos_y
                dist = math.hypot(dx, dy)
                step = step_speed * dt
                if dist <= max(step, 18.0):
                    self._pos_x, self._pos_y = tx, ty
                    self._vel_x = 0.0
                    self._vel_y = 0.0
                    self._update_window_pos()
                    if hasattr(self, "carried_stone_widget"):
                        self.carried_stone_widget.hide()
                    self._current_stage_yaw = 0.0
                    self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    cb = self._cairn_delivered_cb
                    self._cairn_phase = "idle"
                    self._cairn_mine_pos = None
                    self._cairn_drop_pos = None
                    self._cairn_delivered_cb = None
                    self._state = PetState.IDLE
                    self.trigger_3d_action("DropLand", emotion="proud")
                    if callable(cb):
                        cb()
                    self._schedule_next_decision()
                else:
                    prev_x, prev_y = self._pos_x, self._pos_y
                    desired_vx = (dx / dist) * step_speed
                    desired_vy = (dy / dist) * step_speed
                    blend = 1.0 - math.exp(-11.0 * dt)
                    self._vel_x += (desired_vx - self._vel_x) * blend
                    self._vel_y += (desired_vy - self._vel_y) * blend
                    self._pos_x += self._vel_x * dt
                    self._pos_y += self._vel_y * dt
                    self._update_window_pos()
                    self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
                return

        # 2. Omnidirectional 2D Desktop RPG Roam (Walk / Run across full desktop)
        if self._state in {PetState.WALK, PetState.RUN} and (self._roam_manual or not self.chat_bar.isVisible()):
            if self._roam_duration > 0 and (now - self._roam_start_time >= self._roam_duration):
                self._finish_omnidirectional_roam()
                return

            if not self._roam_waypoints:
                if self._roam_duration > 0 and (now - self._roam_start_time < self._roam_duration):
                    self._roam_waypoints = self._generate_2d_desktop_waypoints(random.randint(2, 4))
                else:
                    self._finish_omnidirectional_roam()
                    return

            target_x, target_y = self._roam_waypoints[0]
            dx = target_x - self._pos_x
            dy = target_y - self._pos_y
            dist = math.hypot(dx, dy)

            # Advance smoothly before colliding with exact waypoint (no position snap or velocity slash!)
            if dist <= 24.0:
                self._roam_waypoints.pop(0)
                if not self._roam_waypoints:
                    if self._roam_duration > 0 and (now - self._roam_start_time >= self._roam_duration):
                        self._finish_omnidirectional_roam()
                        return
                    self._roam_waypoints = self._generate_2d_desktop_waypoints(random.randint(2, 4))
                target_x, target_y = self._roam_waypoints[0]
                dx = target_x - self._pos_x
                dy = target_y - self._pos_y
                dist = math.hypot(dx, dy)

            base_speed = self._run_speed if self._state == PetState.RUN else self._walk_speed
            scale_mult = max(0.72, min(1.22, 0.64 + self._scale_factor * 0.65))
            speed = base_speed * scale_mult

            if dist > 1e-3:
                desired_vx = (dx / dist) * speed
                desired_vy = (dy / dist) * speed
            else:
                desired_vx = 0.0
                desired_vy = 0.0

            prev_x, prev_y = self._pos_x, self._pos_y
            blend = 1.0 - math.exp(-11.0 * dt)
            self._vel_x += (desired_vx - self._vel_x) * blend
            self._vel_y += (desired_vy - self._vel_y) * blend
            avail = self._current_available_geometry()
            min_x = float(avail.left() + 16)
            max_x = float(max(avail.left() + 26, avail.right() - self.WINDOW_W - 16))
            min_y = float(avail.top() + 20)
            max_y = float(self._taskbar_floor_y(avail))
            self._pos_x = max(min_x, min(max_x, self._pos_x + self._vel_x * dt))
            self._pos_y = max(min_y, min(max_y, self._pos_y + self._vel_y * dt))
            self._update_window_pos()
            self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
            return

        # 2.5 3-Mode Mouse Evasion AI
        if self._state == PetState.EVADING:
            elapsed = now - self._evasion_start_time

            if elapsed >= self._evasion_duration:
                self._finish_mouse_evasion(caught=False)
                return

            cursor = QCursor.pos()
            pet_c = self.frameGeometry().center()
            dx_c = pet_c.x() - cursor.x()
            dy_c = pet_c.y() - cursor.y()
            dist_c = math.hypot(dx_c, dy_c)

            # Proximity catch condition (< 65px)
            if dist_c < 65.0:
                self._finish_mouse_evasion(caught=True)
                return

            avail = self._current_available_geometry()
            min_x = float(avail.left() + 20)
            max_x = float(avail.right() - self.WINDOW_W - 20)
            min_y = float(avail.top() + 30)
            max_y = float(self._taskbar_floor_y(avail))

            # Mode 2: Distance escape retreat if cursor closes within 160px
            if dist_c < 160.0:
                norm_x = dx_c / max(1.0, dist_c)
                norm_y = dy_c / max(1.0, dist_c)
                self._evasion_target_x = max(min_x, min(max_x, self._pos_x + norm_x * 240.0))
                self._evasion_target_y = max(min_y, min(max_y, self._pos_y + norm_y * 240.0))

            # Mode 3: Fleeing with periodic taunts
            if now - self._last_taunt_time >= random.uniform(2.6, 3.6):
                self._last_taunt_time = now
                taunts = [
                    "잡아봐라~ 💨",
                    "메롱! 날렵한 뽕뽕이를 따라올 수 있을까? 😝",
                    "히히 못 잡겠지~? 🏃‍♂️✨",
                    "슉! 바람처럼 도망치기! ⚡",
                    "여기 있지롱~ 까꿍! 🦄💨",
                ]
                self.speech_bubble.show_message(random.choice(taunts), duration_ms=2000)
                self._run_js("typeof window.triggerEmotionEmote === 'function' && window.triggerEmotionEmote('excited');")

            # Sprint smoothly towards evasion target at scale-aware speed
            dx = self._evasion_target_x - self._pos_x
            dy = self._evasion_target_y - self._pos_y
            dist = math.hypot(dx, dy)
            scale_mult = max(0.55, min(1.22, 0.50 + self._scale_factor * 0.72))
            speed = (self._run_speed * 1.12) * scale_mult

            if dist <= 28.0:
                self._evasion_target_x = random.uniform(min_x, max_x)
                self._evasion_target_y = random.uniform(min_y, max_y)
                dx = self._evasion_target_x - self._pos_x
                dy = self._evasion_target_y - self._pos_y
                dist = math.hypot(dx, dy)

            if dist > 1e-3:
                prev_x, prev_y = self._pos_x, self._pos_y
                desired_vx = (dx / dist) * speed
                desired_vy = (dy / dist) * speed
                blend = 1.0 - math.exp(-12.0 * dt)
                self._vel_x += (desired_vx - self._vel_x) * blend
                self._vel_y += (desired_vy - self._vel_y) * blend
                self._pos_x = max(min_x, min(max_x, self._pos_x + self._vel_x * dt))
                self._pos_y = max(min_y, min(max_y, self._pos_y + self._vel_y * dt))
                self._update_window_pos()
                self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
            return

        # 3. Spider-Man Circular Pendulum Arc Swings + Smooth Parabolic Landing!
        if self._state == PetState.SPIDER_SWING:
            avail = self._current_available_geometry()
            floor_y = self._spider_floor_y
            min_win_x = float(avail.left() + 20)
            max_win_x = float(max(avail.left() + 60, avail.right() - self.WINDOW_W - 20))
            hx, hy = getattr(self, "_spider_hand_offset", (float(self.WINDOW_W // 2), 454.0))
            live_hand = getattr(self, "_live_hand_anchor", None)
            draw_hx = float(live_hand[0]) if live_hand is not None else hx
            draw_hy = float(live_hand[1]) if live_hand is not None else hy

            prev_x, prev_y = self._pos_x, self._pos_y
            phase = getattr(self, "_spider_phase", "swing")

            if phase == "swing":
                seg_dur = max(0.6, float(getattr(self, "_spider_seg_dur", 1.28)))
                self._spider_t += dt / seg_dur
                u = min(1.0, self._spider_t)

                anchor_pt = self._spider_anchor_global
                ax, ay = anchor_pt.x(), anchor_pt.y()
                l0 = float(getattr(self, "_spider_l_start", 380.0))
                l_arc = float(getattr(self, "_spider_l_arc", 340.0))
                th0 = float(getattr(self, "_spider_theta_start", -0.5))
                th1 = float(getattr(self, "_spider_theta_end", 0.68))

                if u < 0.08:
                    # Brief silk shoot-out & tensioning
                    shoot_u = u / 0.08
                    w_swing = 0.0
                    theta = th0
                    rope_l = l0
                    sag_px = (1.0 - shoot_u) * 8.5
                else:
                    w_swing = (u - 0.08) / 0.92
                    # Gravity-accelerated pendulum velocity profile: fastest at bottom of arc (w=0.5), gentle hang-time at ends!
                    s_arc = w_swing - 0.115 * math.sin(2.0 * math.pi * w_swing)
                    reel = min(1.0, w_swing / 0.36)
                    reel_s = reel * reel * (3.0 - 2.0 * reel)
                    rope_l = l0 + (l_arc - l0) * reel_s
                    theta = th0 + (th1 - th0) * s_arc
                    sag_px = 0.0

                hand_x = ax + rope_l * math.sin(theta)
                hand_y = ay + rope_l * math.cos(theta)
                self._pos_x = max(min_win_x, min(max_win_x, hand_x - hx))
                self._pos_y = max(float(avail.top() + 8), min(floor_y, hand_y - hy))
                self._update_window_pos()

                # Keep character facing swing travel vector while banking centripetally along rope angle `theta`
                swing_yaw = 1.22 * self._spider_dir
                self._current_stage_yaw = swing_yaw
                vx_est = (self._pos_x - prev_x) / max(0.008, dt)
                vy_est = (self._pos_y - prev_y) / max(0.008, dt)
                self._send_locomotion_batch(swing_yaw, vx_est, vy_est, int(self._spider_dir))

                hand_global = QPointF(self._pos_x + draw_hx, self._pos_y + draw_hy)
                if self._spider_overlay is None:
                    self._spider_overlay = SpiderWebOverlay()
                if u < 0.08:
                    # Extend silk progressively from hand toward ceiling anchor during shoot-out
                    su = max(0.15, u / 0.08)
                    tip_pt = QPointF(
                        hand_global.x() + (ax - hand_global.x()) * su,
                        hand_global.y() + (ay - hand_global.y()) * su,
                    )
                    self._spider_overlay.set_web_line(avail, hand_global, tip_pt, self.char_id, sag_px=sag_px)
                else:
                    self._spider_overlay.set_web_line(avail, hand_global, anchor_pt, self.char_id, sag_px=0.0)

                if u >= 1.0 or (now - self._last_spider_ipc_time) >= 0.018:
                    self._last_spider_ipc_time = now
                    self._run_js(
                        f"typeof window.setSpiderSwingState === 'function' && "
                        f"window.setSpiderSwingState(true, {w_swing:.3f}, {self._spider_dir:.1f}, {theta:.3f}, 'swing');"
                    )

                if u >= 1.0:
                    if self._spider_current_swing < self._spider_total_swings:
                        # Release high at apex and immediately fire the next forward ceiling web!
                        self._spider_current_swing += 1
                        self._setup_spider_swing_segment()
                    else:
                        # Final apex release: detach web and glide smoothly onto taskbar floor!
                        if self._spider_overlay is not None:
                            self._spider_overlay.hide()
                        self._spider_phase = "release"
                        self._spider_t = 0.0
                        self._spider_rel_x = self._pos_x
                        self._spider_rel_y = self._pos_y
                        self._spider_land_x = max(
                            min_win_x,
                            min(max_win_x, self._pos_x + self._spider_dir * 95.0),
                        )
                        self.trigger_3d_action("HappySpin")
                return

            # Ballistic parabolic landing glide after detaching final web
            self._spider_t += dt / 0.56
            rv = min(1.0, self._spider_t)
            rx0 = float(getattr(self, "_spider_rel_x", self._pos_x))
            ry0 = float(getattr(self, "_spider_rel_y", self._pos_y))
            lx1 = float(getattr(self, "_spider_land_x", rx0))
            self._pos_x = rx0 + (lx1 - rx0) * rv
            self._pos_y = ry0 + (floor_y - ry0) * (rv * rv) - math.sin(rv * math.pi) * 24.0
            self._update_window_pos()

            if rv >= 1.0 or (now - self._last_spider_ipc_time) >= 0.022:
                self._last_spider_ipc_time = now
                self._run_js(
                    f"typeof window.setSpiderSwingState === 'function' && "
                    f"window.setSpiderSwingState(true, {rv:.3f}, {self._spider_dir:.1f}, 0.0, 'release');"
                )

            if rv >= 1.0:
                if self._spider_overlay is not None:
                    self._spider_overlay.hide()
                self._state = PetState.IDLE
                self._pos_y = floor_y
                self._update_window_pos()
                self._run_js("typeof window.setSpiderSwingState === 'function' && window.setSpiderSwingState(false);")
                self._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                self._current_stage_yaw = 0.0
                self.trigger_3d_action("DropLand")
                self.speech_bubble.show_message(
                    f"🕸️ {self._spider_total_swings}연속 원호 스윙 착지 완료!",
                    duration_ms=2200,
                )
                self._schedule_next_decision(2200, 3800)
            return

        # 4. Hide-and-Seek / Translucent Peeking Spot-and-Catch
        if self._state == PetState.HIDE_AND_SEEK:
            if not self._peek_revealed:
                if self._peek_depth < 1.0:
                    self._peek_depth = min(1.0, self._peek_depth + dt * 1.4)
                    # Gentle subtle sink (22px max) so 10% pet stays visible & spottable while camouflaged!
                    self._pos_y = self._peek_normal_y + self._peek_depth * 22.0
                    self._update_window_pos()
                    if self._peek_depth >= 1.0 or (now - getattr(self, "_last_peek_ipc_time", 0.0)) >= 0.033:
                        self._last_peek_ipc_time = now
                        self._run_js(f"typeof window.setPeekState === 'function' && window.setPeekState(true, {self._peek_depth * 0.35:.3f});")

                cursor = QCursor.pos()
                local_c = self.mapFromGlobal(cursor)
                on_pet_cursor = self._is_point_on_character(local_c.x(), local_c.y(), pad=14)
                timed_out = (now - getattr(self, "_peek_start_time", now)) >= getattr(self, "_peek_max_duration", 9.0)
                if on_pet_cursor or timed_out:
                    self._finish_hide_and_seek(caught=on_pet_cursor and not timed_out)
            return

        # 5. Screen Content Heist 2.0 (Running in 2D with Stolen Content Card directly on hands)
        if self._state == PetState.WINDOW_HEIST:
            if hasattr(self, "stolen_piece_widget") and self.stolen_piece_widget.isVisible():
                self._reposition_stolen_piece_widget()

            # Proximity catch check (< 75px)
            cursor = QCursor.pos()
            pet_c = self.frameGeometry().center()
            if (cursor - pet_c).manhattanLength() < 75:
                self.restore_screen_heist(caught_by_user=True)
                return

            if not self._heist_waypoints:
                self._heist_waypoints = self._generate_2d_desktop_waypoints(random.randint(3, 5))

            target_x, target_y = self._heist_waypoints[0]
            dx = target_x - self._pos_x
            dy = target_y - self._pos_y
            dist = math.hypot(dx, dy)
            if dist <= 24.0:
                self._heist_waypoints.pop(0)
                if not self._heist_waypoints:
                    self._heist_waypoints = self._generate_2d_desktop_waypoints(random.randint(3, 5))
                target_x, target_y = self._heist_waypoints[0]
                dx = target_x - self._pos_x
                dy = target_y - self._pos_y
                dist = math.hypot(dx, dy)

            scale_mult = max(0.72, min(1.22, 0.64 + self._scale_factor * 0.65))
            step_speed = (self._run_speed * 1.0) * scale_mult
            if dist > 1e-3:
                prev_x, prev_y = self._pos_x, self._pos_y
                desired_vx = (dx / dist) * step_speed
                desired_vy = (dy / dist) * step_speed
                blend = 1.0 - math.exp(-11.0 * dt)
                self._vel_x += (desired_vx - self._vel_x) * blend
                self._vel_y += (desired_vy - self._vel_y) * blend
                avail = self._current_available_geometry()
                min_x = float(avail.left() + 16)
                max_x = float(max(avail.left() + 26, avail.right() - self.WINDOW_W - 16))
                min_y = float(avail.top() + 20)
                max_y = float(self._taskbar_floor_y(avail))
                self._pos_x = max(min_x, min(max_x, self._pos_x + self._vel_x * dt))
                self._pos_y = max(min_y, min(max_y, self._pos_y + self._vel_y * dt))
                self._update_window_pos()
                self._sync_movement_facing(prev_x, prev_y, dt, dx, dy)
            return

        # 6. Magic Rainbow Graffiti / Fireworks Festival
        if self._state == PetState.MAGIC_DOODLE:
            prev_dp = self._doodle_progress
            self._doodle_progress = min(1.0, self._doodle_progress + dt / 2.0)
            if (prev_dp < 1.0 and self._doodle_progress >= 1.0) or (self._doodle_progress < 1.0 and (now - self._last_doodle_ipc_time) >= 0.033):
                self._last_doodle_ipc_time = now
                self._run_js(f"typeof window.setMagicDoodleState === 'function' && window.setMagicDoodleState(true, '{self._doodle_shape}', {self._doodle_progress:.3f});")
            if self._doodle_progress >= 1.0:
                self._doodle_timer += dt
                if self._doodle_timer > 0.05 and not getattr(self, "_doodle_proud_triggered", False):
                    self._doodle_proud_triggered = True
                    self.trigger_3d_action("Proud", emotion="proud")
                    shape_kr = {"heart": "하트 💖", "star": "별 🌟", "fireworks": "불꽃 축제 🎆"}.get(self._doodle_shape, self._doodle_shape)
                    self.speech_bubble.show_message(f"짜잔! 🎆 바탕화면에 터뜨린 화려한 마법 [{shape_kr}] 완성! 멋지죠? ✨", duration_ms=4000)
                if self._doodle_timer >= 4.0:
                    self._state = PetState.IDLE
                    self._run_js("typeof window.setMagicDoodleState === 'function' && window.setMagicDoodleState(false);")
                    self._schedule_next_decision(2200, 3800)
            return

        # 7. Superhero Multi-Wave Flight (Extended 8.0 ~ 25.0s with multi-wave swoops & real OS mouse stealing)
        if self._state == PetState.SUPERMAN_FLY:
            elapsed = now - self._superman_start_time
            p = min(1.0, elapsed / max(0.1, self._superman_duration))
            self._superman_progress = p
            avail = self._current_available_geometry()
            min_x = float(avail.left() + 40)
            max_x = float(avail.right() - self.WINDOW_W - 40)
            sky_y = float(avail.top() + 60)
            floor_y = self._superman_floor_y

            prev_x = self._pos_x
            prev_y = self._pos_y

            mid_y = sky_y + (floor_y - sky_y) * 0.40
            amp_y = (floor_y - sky_y) * 0.35
            cruise_start_x = min_x
            cruise_start_y = mid_y
            end_osc = (math.sin(math.pi * self._superman_waves - math.pi / 2.0) + 1.0) / 2.0
            cruise_end_x = min_x + (max_x - min_x) * end_osc
            cruise_end_y = mid_y + math.sin(math.pi * self._superman_waves * 2.0) * amp_y

            # Phase 1: C0-Continuous Takeoff (0.00 <= p < 0.12)
            if p < 0.12:
                u = p / 0.12
                s = u * u * (3.0 - 2.0 * u)
                self._pos_x = self._superman_start_x + (cruise_start_x - self._superman_start_x) * s
                self._pos_y = (
                    self._superman_start_y
                    + (cruise_start_y - self._superman_start_y) * s
                    - math.sin(u * math.pi) * 65.0
                )

            # Phase 2: Multi-wave Swoop Cruise (0.12 <= p < 0.88)
            elif p < 0.88:
                cruise_p = (p - 0.12) / 0.76
                x_osc = (math.sin(cruise_p * math.pi * self._superman_waves - math.pi / 2.0) + 1.0) / 2.0
                self._pos_x = min_x + (max_x - min_x) * x_osc
                self._pos_y = mid_y + math.sin(cruise_p * math.pi * self._superman_waves * 2.0) * amp_y

            # Phase 3: C0-Continuous Glide Landing (0.88 <= p <= 1.0)
            else:
                land_p = (p - 0.88) / 0.12
                s = land_p * land_p * (3.0 - 2.0 * land_p)
                self._pos_x = cruise_end_x
                self._pos_y = cruise_end_y + (floor_y - cruise_end_y) * s

            self._update_window_pos()

            # Mode 1: Actually carry the real Windows mouse cursor along with the character's hands!
            if self._superman_mode == 1 and not getattr(self, "_superman_cursor_released", False):
                cur_mouse = QCursor.pos()
                if (cur_mouse - self._stolen_cursor_pos).manhattanLength() > 165:
                    # User intentionally jerked the physical mouse to reclaim control
                    self._superman_cursor_released = True
                else:
                    hand_anchor = getattr(self, "_live_hand_anchor", None)
                    if hand_anchor is not None:
                        hx, hy = hand_anchor
                    else:
                        hx = self.WINDOW_W // 2
                        hy = int(469.1 - 140.0 * max(0.10, self._scale_factor))
                    target_cursor = QPoint(int(round(self._pos_x + hx)), int(round(self._pos_y + hy)))
                    QCursor.setPos(target_cursor)
                    self._stolen_cursor_pos = target_cursor

            # Dynamic velocity, banking and batched yaw facing
            vx = self._pos_x - prev_x
            vy = self._pos_y - prev_y
            safe_dt = max(dt, 0.016)
            vel_x = vx / safe_dt
            vel_y = vy / safe_dt
            facing_dir = (1 if vx >= 0 else -1) if abs(vx) > 0.5 else (self._last_facing_dir or 0)
            flight_yaw = math.atan2(vx, vy) if math.hypot(vx, vy) > 0.8 else self._current_stage_yaw
            self._current_stage_yaw = flight_yaw
            self._send_locomotion_batch(flight_yaw, vel_x, vel_y, facing_dir)

            if p >= 1.0 or (now - self._last_superman_ipc_time) >= 0.033:
                self._last_superman_ipc_time = now
                self._run_js(
                    f"typeof window.setSupermanFlyState === 'function' && "
                    f"window.setSupermanFlyState(true, {p:.3f}, {self._superman_mode});"
                )

            if p >= 1.0:
                self._state = PetState.IDLE
                self._pos_y = floor_y
                self._update_window_pos()
                self._run_js("typeof window.setSupermanFlyState === 'function' && window.setSupermanFlyState(false);")
                self._set_stage_yaw_override(None)
                self._current_stage_yaw = 0.0
                self._set_3d_facing(0)
                self.trigger_3d_action("DropLand")
                if self._superman_mode == 1:
                    self.speech_bubble.show_message("히히! 낚아챈 마우스 포인터 안전하게 착륙 완료! 🖱️💖", duration_ms=3200)
                elif self._superman_mode == 2:
                    self.speech_bubble.show_message("서류 파일 안전 배송 완료! 📁 우주 여행 즐거웠어요~!", duration_ms=3200)
                else:
                    self.speech_bubble.show_message(
                        f"초음속 {int(self._superman_duration)}초 다방향 비행 완료! 🚀 상쾌해요!",
                        duration_ms=3200,
                    )
                self._schedule_next_decision(2200, 3800)
            return

    # -------------------------------------------------------------------------
    # Tactile Mouse Interactions (3-Zone Poke, Drag + Gravity, Dbl/Right Chat)
    # -------------------------------------------------------------------------
    def _finish_hide_and_seek(self, caught: bool = True) -> None:
        if self._peek_revealed:
            return
        self._peek_revealed = True
        self._peek_depth = 0.0
        self._pos_y = self._peek_normal_y
        self._update_window_pos()
        self._stillness_start_time = time.perf_counter()
        self._current_opacity = 1.0
        self.setWindowOpacity(1.0)
        self._run_js("typeof window.setPeekState === 'function' && window.setPeekState(false);")
        self.trigger_3d_action("Jump", emotion="excited")
        if caught and hasattr(self, "rpg_state"):
            self.rpg_state.gold += 45
            self.rpg_state.save()
            self._sync_rpg_to_js()
            if hasattr(self, "rpg_hub") and self.rpg_hub.isVisible():
                self.rpg_hub.refresh_ui()
            self.speech_bubble.show_message("까꿍! 🙈🎉 들켰다! 숨바꼭질 보너스 +45G!", duration_ms=3200)
        else:
            self.speech_bubble.show_message("까꿍! 🙈 먼저 짠 하고 나왔지롱~!", duration_ms=3200)
        self._state = PetState.IDLE
        self._schedule_next_decision(1600, 2800)

    def _on_single_click_poke(self) -> None:
        if (
            self._is_dragging
            or self._left_pressed
            or self._is_blocked_by_arena_or_hidden()
            or self.is_action_busy(include_locomotion=False)
        ):
            return
        rel_x, rel_y = self._pending_poke_rel
        vp_x = rel_x * max(1, self.VIEWPORT_RECT.width())
        vp_y = rel_y * max(1, self.VIEWPORT_RECT.height())
        if not self._is_point_on_character(vp_x, vp_y, pad=12):
            return

        self._stillness_start_time = time.perf_counter()
        self._pause_autonomous_walk(play_idle=False)
        self._set_3d_facing(0)

        now = time.perf_counter()
        show_bubble = (not self.chat_bar.isVisible()) and (now - self._last_poke_bubble_time >= 2.6)

        if rel_y < 0.30:
            self._trigger_3d_poke("horn")
            if show_bubble:
                self._last_poke_bubble_time = now
                horn_msg = (
                    "반짝! 🌟 황금 별 에너지 충전 완료~! 🎄✨"
                    if self.char_id == "tree"
                    else "뿅! 무지개 뿔 마법 충전 완료~! 🌈✨"
                )
                self.speech_bubble.show_message(horn_msg, duration_ms=2600)
        elif rel_y < 0.58:
            self._trigger_3d_poke("face")
            if show_bubble:
                self._last_poke_bubble_time = now
                face_msg = (
                    "헤헤, 말랑한 아기곰 볼 콕 찔렀지?! 🐻💕"
                    if self.char_id == "tree"
                    else "헤헤, 말랑한 모찌 볼 콕 찔렀지?! 😆💕"
                )
                self.speech_bubble.show_message(face_msg, duration_ms=2600)
        else:
            if random.random() < 0.45:
                self.trigger_3d_action("Dance", duration_ms=2600, emotion="excited")
            else:
                self._trigger_3d_poke("belly")
            if show_bubble:
                self._last_poke_bubble_time = now
                belly_msg = (
                    "까르르! 폭신한 코코아 배 간지러워요~! 🎄🎵"
                    if self.char_id == "tree"
                    else "까르르! 배 간지러워요~! 🦄🎵"
                )
                self.speech_bubble.show_message(belly_msg, duration_ms=2600)

        self._schedule_next_decision(2200, 3800)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QWidget) and (
            watched is self.web_view or self.web_view.isAncestorOf(watched)
        ):
            etype = event.type()

            if etype == QEvent.Type.ContextMenu:
                return True  # Suppress Chromium default context menu

            if etype == QEvent.Type.Wheel:
                if self._in_battle_arena or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                    return True
                vp_pt = self.web_view.mapFromGlobal(QCursor.pos())
                if not self._is_point_on_character(vp_pt.x(), vp_pt.y(), pad=14):
                    return True
                # Character scaling with mouse wheel strictly over pet
                self._last_user_activity_time = time.perf_counter()
                self._stillness_start_time = self._last_user_activity_time
                delta_y = event.angleDelta().y()
                if delta_y != 0:
                    step = 0.05 if delta_y > 0 else -0.05
                    self.set_scale_factor(self._scale_factor + step)
                    return True

            if etype == QEvent.Type.MouseButtonPress:
                self._last_user_activity_time = time.perf_counter()
                self._stillness_start_time = self._last_user_activity_time
                if self._is_napping:
                    self._is_napping = False
                    self.trigger_3d_action("Stretch", emotion="happy")
                btn = event.button()
                if btn == Qt.MouseButton.LeftButton:
                    # During 360-degree Desktop Defense/Skirmish, pass left-clicks directly to WebGL for Cursor Smite!
                    if self._in_battle_arena or self._defense_overlay_active or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                        return False

                    # Immediate catch during Hide-and-Seek, Screen Content Heist or Mouse Evasion
                    if self._state == PetState.HIDE_AND_SEEK:
                        self._finish_hide_and_seek(caught=True)
                        return True
                    if self._state == PetState.WINDOW_HEIST:
                        self.restore_screen_heist(caught_by_user=True)
                        return True
                    if self._state == PetState.EVADING:
                        self._finish_mouse_evasion(caught=True)
                        return True

                    vp_pt = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
                    if not self._is_point_on_character(vp_pt.x(), vp_pt.y(), pad=12):
                        return True

                    self._left_pressed = True
                    self._is_dragging = False
                    self._drag_vel_px = (0.0, 0.0)
                    self._drag_start_global = event.globalPosition().toPoint()
                    self._drag_last_global = self._drag_start_global
                    self._drag_last_time = time.perf_counter()
                    self._window_start_pos = self.frameGeometry().topLeft()

                    rx = max(0.0, min(1.0, vp_pt.x() / max(1, self.VIEWPORT_RECT.width())))
                    ry = max(0.0, min(1.0, vp_pt.y() / max(1, self.VIEWPORT_RECT.height())))
                    self._pending_poke_rel = (rx, ry)
                    return False
                if btn == Qt.MouseButton.RightButton:
                    vp_pt = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
                    if not self._is_point_on_character(vp_pt.x(), vp_pt.y(), pad=12):
                        self._right_press_on_char = False
                        return True
                    # Immediately halt movement on right-button press so the character never slips away before release!
                    self._right_press_on_char = True
                    self._freeze_for_popup_menu()
                    return True

            elif etype == QEvent.Type.MouseMove:
                if self._left_pressed and not (event.buttons() & Qt.MouseButton.LeftButton):
                    self._left_pressed = False
                    if self._is_dragging:
                        self._is_dragging = False
                        self._set_3d_drag_state(False, 0.0, 0.0)
                elif self._left_pressed:
                    cur_global = event.globalPosition().toPoint()
                    delta = cur_global - self._drag_start_global
                    if not self._is_dragging and delta.manhattanLength() > 6:
                        if self._in_battle_arena or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                            self._left_pressed = False
                            return False
                        self._is_dragging = True
                        self._single_click_timer.stop()
                        if hasattr(self, "radial_menu"):
                            self.radial_menu.close_all()
                        coord = getattr(self, "coordinator", None)
                        if coord is not None and coord.is_minigame_active():
                            coord._stop_minigame()
                        if self.is_action_busy(include_locomotion=False):
                            self.cancel_all_active_actions()
                        elif self._state == PetState.PETTING:
                            self._set_3d_petting_state(False)
                        self._pause_autonomous_walk(play_idle=True)
                        self._state = PetState.DRAGGING

                    if self._is_dragging:
                        now = time.perf_counter()
                        dt = max(0.008, now - self._drag_last_time)
                        step_dx = cur_global.x() - self._drag_last_global.x()
                        step_dy = cur_global.y() - self._drag_last_global.y()
                        raw_vx = step_dx / dt
                        raw_vy = step_dy / dt
                        self._drag_vel_px = (raw_vx, raw_vy)
                        vx = max(-1.5, min(1.5, raw_vx / 900.0))
                        vy = max(-1.5, min(1.5, -raw_vy / 900.0))
                        self._drag_last_global = cur_global
                        self._drag_last_time = now

                        new_pos = self._window_start_pos + delta
                        self._pos_x = float(new_pos.x())
                        self._pos_y = float(new_pos.y())
                        self._nudged_for_chat = 0
                        self.move(new_pos)
                        self._set_3d_drag_state(True, vx, vy)
                        return True

            elif etype == QEvent.Type.MouseButtonRelease:
                btn = event.button()
                if btn == Qt.MouseButton.LeftButton:
                    was_dragging = self._is_dragging
                    self._left_pressed = False
                    self._is_dragging = False
                    if self._in_battle_arena or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                        return False
                    if was_dragging:
                        self._set_3d_drag_state(False, 0.0, 0.0)
                        avail = self._current_available_geometry()
                        floor_y = self._taskbar_floor_y(avail)
                        if (
                            self._taskbar_gravity_enabled
                            and not self.chat_bar.isVisible()
                            and self._pos_y < floor_y - 8.0
                        ):
                            raw_vx, raw_vy = self._drag_vel_px
                            self._fall_vx = max(-420.0, min(420.0, raw_vx * 0.42))
                            self._fall_vy = max(-320.0, min(220.0, raw_vy * 0.32))
                            self._fall_bounced = False
                            self._last_tick_time = time.perf_counter()
                            self._state = PetState.FALLING
                            self._set_3d_falling_state(True, -0.5)
                        else:
                            if self._taskbar_gravity_enabled and not self.chat_bar.isVisible() and self._pos_y > floor_y:
                                self._pos_y = floor_y
                                self.move(int(round(self._pos_x)), int(round(self._pos_y)))
                            self._state = PetState.IDLE
                            self._schedule_next_decision(2000, 3600)
                        return True
                    else:
                        vp_pt = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
                        if not self._is_point_on_character(vp_pt.x(), vp_pt.y(), pad=12):
                            return True
                        # Candidate single-click tactile poke (waits 190ms in case of double-click)
                        self._single_click_timer.start()
                        return False
                elif btn == Qt.MouseButton.RightButton:
                    self._single_click_timer.stop()
                    was_right_on_char = getattr(self, "_right_press_on_char", False)
                    self._right_press_on_char = False
                    vp_pt = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
                    if not was_right_on_char and not self._is_point_on_character(vp_pt.x(), vp_pt.y(), pad=12):
                        return True
                    self.toggle_radial_menu()
                    return True

            elif etype == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self._in_battle_arena or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                        return False
                    self._single_click_timer.stop()
                    self._left_pressed = False
                    if self._is_dragging:
                        self._is_dragging = False
                        self._set_3d_drag_state(False, 0.0, 0.0)
                    self.on_pet_activated()
                    return True

        return super().eventFilter(watched, event)

    def on_pet_activated(self) -> None:
        """Triggered on double-left-click or radial '대화' item: plays Wave/Jump & toggles chat window."""
        if self._in_battle_arena or self._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
            return
        self._single_click_timer.stop()
        if hasattr(self, "radial_menu"):
            self.radial_menu.close_all()
        coord = getattr(self, "coordinator", None)
        if coord is not None and coord.is_minigame_active():
            coord._stop_minigame()
        if self.is_action_busy(include_locomotion=False):
            self.cancel_all_active_actions()
        elif self._state == PetState.PETTING:
            self._set_3d_petting_state(False)
        self._pause_autonomous_walk(play_idle=False)
        self._set_3d_facing(0)

        anim = "Jump" if self._greet_toggle_flip else "Wave"
        self._greet_toggle_flip = not self._greet_toggle_flip
        self.trigger_3d_action(anim)

        if self.chat_bar.isVisible():
            self._hide_chat_bar()
        else:
            self._show_chat_bar()

    def _show_chat_bar(self) -> None:
        self.chat_window.show_beside_pet(self.frameGeometry(), owner_pet=self)

    def toggle_gemini_chat(self) -> None:
        if self.chat_window.isVisible() and getattr(self.chat_window, "owner_pet", None) is self:
            self._hide_chat_bar()
        else:
            self.chat_window.open_gemini_web(self.frameGeometry(), owner_pet=self)

    def _hide_chat_bar(self) -> None:
        self.chat_window.hide()
        self._schedule_next_decision(2000, 3600)

    # -------------------------------------------------------------------------
    # Local LLM Conversation Flow & Decoupled Lip-Sync / Emotion-Motion Sync
    # -------------------------------------------------------------------------
    def _open_llm_settings(self) -> None:
        dlg = LLMSettingsDialog(self._llm_config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._prefs.llm_url = self._llm_config.api_url
            self._prefs.llm_model = self._llm_config.model
            self._prefs.llm_api_key = self._llm_config.api_key
            self._prefs.save(self.char_id)

    def _on_user_chat_submitted(self, user_text: str) -> None:
        if getattr(self.chat_window, "owner_pet", None) not in (None, self):
            return
        if self._active_worker is not None and self._active_worker.isRunning():
            return
        if not self._in_battle_arena and self._state not in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
            if self.is_action_busy(include_locomotion=False):
                self.cancel_all_active_actions()
            self._pause_autonomous_walk(play_idle=False)
            self._state = PetState.INTERACTING
            self._set_3d_facing(0)
        else:
            self._pause_autonomous_walk(play_idle=False)
            self._set_3d_facing(0)

        text_clean = str(user_text or "").lower().strip()

        # 0.0. Partner (Ppong-ppong-i & Tree) Dual-Pet Interaction Commands
        coord = getattr(self, "coordinator", None)
        if coord is not None:
            if any(w in text_clean for w in ["달리기 시합", "달리기 게임", "누가 이기나", "경주", "레이스", "같이 달리기"]):
                self.chat_bar.set_busy(False)
                coord.start_running_race()
                self.chat_window.add_message("pet", "뽕뽕이와 트리의 흥미진진한 바탕화면 달리기 시합 시작! 🏁🏃💨", "partner_race")
                return
            if any(w in text_clean for w in ["둘이 술래잡기", "서로 술래잡기", "친구랑 술래잡기", "트리랑 술래잡기", "뽕뽕이랑 술래잡기"]):
                self.chat_bar.set_busy(False)
                coord.start_mutual_tag()
                self.chat_window.add_message("pet", "뽕뽕이와 트리가 서로 쫓고 쫓기는 술래잡기를 시작해요! 👹🏃💨", "partner_tag")
                return
            if any(w in text_clean for w in ["박치기", "1:1 대결", "둘이 대결", "서로 대결", "트리랑 대결", "뽕뽕이랑 대결", "부딪혀"]):
                self.chat_bar.set_busy(False)
                coord.start_friendly_duel()
                self.chat_window.add_message("pet", "뽕뽕이와 트리의 1:1 박치기 파워 대결! ⚔️💥", "partner_duel")
                return
            if any(w in text_clean for w in ["둘이 인사", "서로 인사", "친구와 인사", "트리랑 인사", "뽕뽕이랑 인사"]):
                self.chat_bar.set_busy(False)
                coord.greet_each_other()
                self.chat_window.add_message("pet", "뽕뽕이와 트리가 서로 반갑게 인사해요! 🦄🤝🎄", "partner_greet")
                return
            if any(w in text_clean for w in ["같이 춤", "함께 춤", "둘이 춤", "듀엣 댄스", "합동 댄스"]):
                self.chat_bar.set_busy(False)
                coord.duet_dance()
                self.chat_window.add_message("pet", "뽕뽕이와 트리의 신나는 합동 듀엣 댄스 타임! 💃🕺✨", "partner_dance")
                return
            if any(w in text_clean for w in ["간식 파티", "같이 간식", "함께 간식", "둘이 간식"]):
                self.chat_bar.set_busy(False)
                coord.share_snack()
                self.chat_window.add_message("pet", "뽕뽕이와 트리가 맛있는 간식을 사이좋게 나눠 먹어요! 🍬🍪💖", "partner_snack")
                return
            if any(w in text_clean for w in ["같이 산책", "함께 산책", "둘이 산책"]):
                self.chat_bar.set_busy(False)
                coord.roam_together()
                self.chat_window.add_message("pet", "뽕뽕이와 트리가 나란히 바탕화면 동반 산책을 떠납니다! 🗺️🌈🎄", "partner_roam")
                return
            if any(w in text_clean for w in ["트리 불러", "트리 소환", "뽕뽕이 불러", "뽕뽕이 소환", "친구 불러"]):
                self.chat_bar.set_busy(False)
                partner = coord.get_partner(self)
                if partner is not None and not partner.isVisible():
                    partner.show_pet_from_tray()
                coord.greet_each_other()
                self.chat_window.add_message("pet", "친구를 불러서 함께 인사했어요! 🌟", "partner_summon")
                return

        # 0. Smart 3D Visual Alarm Natural Language Parsing & Management
        if any(w in text_clean for w in ["알람 목록", "알람 관리", "알람 매니저", "알람창", "타이머 목록", "타이머 관리", "알람 보여줘"]):
            self.chat_bar.set_busy(False)
            self.open_alarm_manager()
            return

        alarm_parsed = self.alarm_manager.try_parse_chat_alarm(user_text)
        if alarm_parsed:
            item, confirm_msg = alarm_parsed
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", confirm_msg, "alarm")
            self.trigger_3d_action("Proud", emotion="proud")
            self.speech_bubble.show_message(confirm_msg, duration_ms=5500)
            return

        # 0.1. 3D World · Mining · Economy · Wave Defense Natural Language Commands
        if any(w in text_clean for w in ["채굴", "광석", "곡괭이", "땅 파", "광산", "mining"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "⛏️ 바탕화면 광맥을 찾아 채굴 출동합니다! 희귀 광석을 캐올게요! 💎✨", "mining")
            self.start_roaming_excavation()
            return
        if any(w in text_clean for w in ["디펜스", "웨이브", "공성전", "보스전", "defense", "wave"]):
            self.chat_bar.set_busy(False)
            next_w = self.rpg_state.max_cleared_wave + 1
            self.chat_window.add_message("pet", f"⚔️ [Wave {next_w} 3D 웨이브 디펜스] 출격합니다! 성소를 함께 지켜요!", "defense")
            self.start_wave_defense_game(next_w)
            return
        if any(w in text_clean for w in ["침입", "수호", "몬스터", "적 물리", "전투", "skirmish"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "🛡️ 바탕화면 침입자 수호전을 시작합니다! 뽕뽕이가 바탕화면을 지킬게요! ⚡", "skirmish")
            self.start_desktop_skirmish()
            return
        if any(w in text_clean for w in ["사이버펑크", "네온", "cyberpunk"]):
            self.chat_bar.set_busy(False)
            self.set_worldview_theme("cyberpunk")
            self.chat_window.add_message("pet", "⚡ 네온 사이버펑크 넷러너 세계관으로 전환 완료!", "worldview")
            return
        if any(w in text_clean for w in ["우주 개척", "우주 기지", "scifi", "sci-fi"]):
            self.chat_bar.set_busy(False)
            self.set_worldview_theme("scifi")
            self.chat_window.add_message("pet", "🚀 성간 우주 개척단 세계관으로 전환 완료!", "worldview")
            return
        if any(w in text_clean for w in ["힐링 아일랜드", "코지", "cozy", "동물의 숲"]):
            self.chat_bar.set_busy(False)
            self.set_worldview_theme("cozy")
            self.chat_window.add_message("pet", "🏝️ 코지 힐링 아일랜드 세계관으로 전환 완료!", "worldview")
            return
        if any(w in text_clean for w in ["판타지 왕국", "판타지 세계", "fantasy"]):
            self.chat_bar.set_busy(False)
            self.set_worldview_theme("fantasy")
            self.chat_window.add_message("pet", "🏰 판타지 왕국 수호단 세계관으로 전환 완료!", "worldview")
            return
        if any(w in text_clean for w in ["업무 모드", "집중 모드", "클릭 관통", "방해 금지"]):
            self.chat_bar.set_busy(False)
            new_mode = not self.rpg_state.work_safe_mode
            self.set_work_safe_mode(new_mode, show_bubble=True)
            self.chat_window.add_message("pet", f"💼 업무 집중 클릭 관통 모드를 {'켰어요' if new_mode else '껐어요'}!", "work_safe")
            return
        if any(w in text_clean for w in ["맨손", "주먹", "격투", "무투", "fist"]):
            self.chat_bar.set_busy(False)
            self.equip_or_craft_weapon_by_key("fist")
            self.chat_window.add_message("pet", "👊 [맨손 무투] 장착 완료! 적에게 다가가 주먹과 어퍼컷으로 무찌를게요!", "weapon")
            return
        if any(w in text_clean for w in ["칼 장착", "검 장착", "명검", "칼로", "검으로", "sword"]):
            self.chat_bar.set_busy(False)
            self.equip_or_craft_weapon_by_key("sword")
            self.chat_window.add_message("pet", f"🗡️ [{WEAPON_SPECS['sword']['name']}] 무장 준비! 초승달 검기와 회전 참격을 선보일게요!", "weapon")
            return
        if any(w in text_clean for w in ["활 장착", "장궁", "활로", "화살", "bow"]):
            self.chat_bar.set_busy(False)
            self.equip_or_craft_weapon_by_key("bow")
            self.chat_window.add_message("pet", f"🏹 [{WEAPON_SPECS['bow']['name']}] 무장 준비! 원거리 깃털 화살과 멀티샷으로 요격합니다!", "weapon")
            return
        if any(w in text_clean for w in ["총 장착", "블래스터", "총으로", "플라즈마", "gun"]):
            self.chat_bar.set_busy(False)
            self.equip_or_craft_weapon_by_key("gun")
            self.chat_window.add_message("pet", f"🔫 [{WEAPON_SPECS['gun']['name']}] 무장 준비! 초고속 플라즈마 탄환과 폭발 캐논을 발사합니다!", "weapon")
            return
        if any(w in text_clean for w in ["가방", "인벤토리", "아이템", "소모품", "포션", "비약", "주문서", "전리품", "무기고", "bag", "inventory"]):
            self.chat_bar.set_busy(False)
            self.show_rpg_bag_hub()
            self.chat_window.add_message(
                "pet",
                "🎒 [가방 · 소모품 사령부 (Ctrl+I)]를 열어드렸어요! 채집·사냥으로 획득한 아이템 도감과 6종 전술 포션/주문서를 확인·사용해 보세요! ✨",
                "rpg_bag",
            )
            return
        if any(w in text_clean for w in ["사령부", "월드 허브", "상태창", "대장간", "포탑", "강화", "상점"]):
            self.chat_bar.set_busy(False)
            self.show_rpg_hub()
            self.chat_window.add_message("pet", "🏰 3D 월드 & 디펜스 사령부(Ctrl+R)를 열어드렸어요! 농장·채굴·요리·대장간·포탑·디펜스를 관리해보세요!", "rpg_hub")
            return

        # 0.2. 30 Spectacular Solo Play Activities Natural Language Parsing
        solo_keyword_map = [
            ("build_house", ["집 지어", "집짓기", "블록", "망치"]),
            ("fishing", ["낚시", "물고기", "월척"]),
            ("hunting", ["사냥", "곤충", "채집", "나비 잡"]),
            ("explorer", ["탐험", "쌍안경", "나침반", "대륙"]),
            ("camping", ["캠핑", "모닥불", "마시멜로", "불멍"]),
            ("drinking", ["건배", "맥주", "술", "음료", "짠해", "치어스"]),
            ("cooking", ["요리", "팬케이크", "뒤집기", "쉐프"]),
            ("gardening", ["정원", "물 줘", "꽃 심", "원예", "농사", "텃밭"]),
            ("music_guitar", ["기타", "우쿨렐레"]),
            ("painting", ["그림", "화가", "이젤", "캔버스"]),
            ("reading", ["책 읽", "독서", "마법서"]),
            ("snowman", ["눈사람", "눈 굴려"]),
            ("wizard", ["마법사", "마법 걸", "주문", "지팡이"]),
            ("astronaut", ["우주", "비행사", "문워크", "무중력"]),
            ("gamer", ["게임", "게이머", "콘솔", "패드"]),
            ("ninja", ["닌자", "은신", "분신"]),
            ("detective", ["탐정", "추리", "돋보기", "수사"]),
            ("barista", ["커피", "바리스타", "드립"]),
            ("fitness", ["헬스", "바벨", "역기", "근육", "운동해"]),
            ("bubbles", ["비눗방울", "방울"]),
            ("skateboard", ["스케이트", "보드", "킥플립"]),
            ("kite", ["연 날려", "연날리기"]),
            ("telescope", ["망원경", "별 관측", "천체"]),
            ("treasure", ["보물", "삽질", "금괴"]),
            ("picnic", ["피크닉", "도넛", "간식"]),
            ("sleeping", ["잠 자", "낮잠", "자자", "잘래", "쿨쿨"]),
            ("timemachine", ["타임머신", "시간 여행", "과거", "미래"]),
            ("surfing", ["서핑", "파도"]),
            ("paper_plane", ["종이비행기", "비행기 접"]),
            ("party_dj", ["디제이", "dj", "클럽", "파티", "비트"]),
        ]
        for solo_key, kws in solo_keyword_map:
            if any(kw in text_clean for kw in kws):
                self.chat_bar.set_busy(False)
                self.play_solo_action(solo_key)
                return

        # 0.5. PC Health & Clean-up Natural Language Parsing
        if any(w in text_clean for w in ["청소", "최적화", "메모리 정리", "쾌적", "pc 정리", "컴퓨터 청소"]):
            self.chat_bar.set_busy(False)
            res = self.run_pc_cleanup(show_bubble=True)
            self.chat_window.add_message("pet", "컴퓨터 환경을 쾌적하게 청소 및 최적화 완료했어요! 🧹✨", "cleanup")
            return

        # Outlook Natural Language Intent Detection
        mail_keywords = ["메일", "아웃룩", "outlook", "mail", "email", "편지", "받은편지함"]
        if any(kw in text_clean for kw in mail_keywords):
            self.trigger_3d_action("Curious", emotion="curious")
            items = self.outlook_service.cached_items
            unread_cnt = sum(1 for it in items if it.is_unread)
            urgent_cnt = sum(1 for it in items if it.urgency_level == "urgent")
            reply_msg = (
                f"네! 📬 Outlook 메일함을 확인했어요.\n"
                f"총 {len(items)}건 중 안 읽은 메일 {unread_cnt}건(긴급 {urgent_cnt}건)이 있어요!\n"
                f"AI 요약 허브 창을 열어드릴게요. ✨"
            )
            self.speech_bubble.show_message(reply_msg, duration_ms=6500)
            self.chat_window.add_message("pet", reply_msg, "outlook")
            self.show_outlook_hud()
            self.chat_bar.set_busy(False)
            return

        # Natural Language Active Action Commands (Spider-Man, Peek, Heist 2.0, Doodle, Superman, Evasion, Roam)
        if any(w in text_clean for w in ["술래잡기", "도망쳐", "도망가", "잡아봐", "도망", "회피", "evasion"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "술래잡기 시작! 3초 안에 도망간다~ 잡아봐라! 🏃‍♂️💨", "evasion")
            self.start_mouse_evasion(mode="velocity", manual=True)
            return
        elif any(w in text_clean for w in ["산책", "모험", "돌아다녀", "roam", "rpg"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "바탕화면 전방위 모험을 떠납니다! 🗺️✨", "roam")
            self.start_omnidirectional_roam(mode="walk", manual=True)
            return
        elif any(w in text_clean for w in ["스파이더", "거미줄", "스윙", "spider"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "쓩~! 🕸️ 스파이더 뽕뽕이 출동! 벽을 타고 비행합니다!", "spider")
            self.start_spider_swing()
            return
        elif any(w in text_clean for w in ["숨바꼭질", "숨어", "빼꼼", "까꿍", "hide"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "나 찾아봐라~ 3초 센다! 1, 2, 3... 쏙! 🙈", "hide")
            self.start_hide_and_seek()
            return
        elif any(w in text_clean for w in ["창 훔쳐", "창 들고", "화면 훔쳐", "화면 조각", "heist"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "헤헤! 바탕화면 한 조각 접수 완료! 잡아봐라~!! 🪟💨", "heist")
            self.start_screen_content_heist()
            return
        elif any(w in text_clean for w in ["불꽃", "불꽃놀이", "불꽃 축제", "불꽃축제", "낙서", "그림", "하트", "별", "doodle", "fireworks"]):
            self.chat_bar.set_busy(False)
            shape = "heart" if "하트" in text_clean else ("star" if "별" in text_clean else "fireworks")
            shape_kr = {"heart": "하트 💖", "star": "별 🌟", "fireworks": "불꽃 축제 🎆"}.get(shape, shape)
            self.chat_window.add_message("pet", f"바탕화면에 화려한 마법 [{shape_kr}] 펼치는 중... 🎆✨", "doodle")
            self.start_magic_doodle(shape)
            return
        elif any(w in text_clean for w in ["슈퍼맨", "하늘", "날아", "비행", "fly", "rocket"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "슈퍼맨 뽕뽕이 출동! 🚀 성층권으로 비행합니다!", "superman")
            self.start_superman_fly()
            return

        self.trigger_3d_action("Curious")

        self._conversation.append({"role": "user", "content": user_text})
        if len(self._conversation) > 13:
            self._conversation = [self._conversation[0]] + self._conversation[-12:]

        self.chat_bar.set_busy(True)
        self.speech_bubble.show_message("Thinking... ✨", duration_ms=0)

        worker = LLMWorker(self._conversation, self._llm_config, self)
        worker.response_ready.connect(self._on_llm_response)
        worker.error_occurred.connect(self._on_llm_error)
        worker.finished.connect(self._on_worker_finished)
        self._active_worker = worker
        worker.start()

    def _on_llm_response(self, reply: str, action: str, emotion: str = "") -> None:
        assistant_json: dict[str, str] = {"reply": reply, "action": action}
        if emotion:
            assistant_json["emotion"] = emotion
        self._conversation.append(
            {"role": "assistant", "content": json.dumps(assistant_json, ensure_ascii=False)}
        )
        self.chat_window.add_message("pet", reply, action)
        display_ms = self.speech_bubble.show_message(reply)
        loop_ms = min(display_ms, 6500) if action in {"Talk", "Dance", "Sit"} else 0
        self.trigger_3d_action(
            action,
            duration_ms=loop_ms,
            emotion=emotion or None,
            speech_ms=display_ms,
        )

    def _on_llm_error(self, err_detail: str) -> None:
        if len(self._conversation) > 1 and self._conversation[-1]["role"] == "user":
            self._conversation.pop()

        friendly_msg = (
            "Hmm, I couldn't reach your Local LLM! Start llama-server on :8080 "
            "or Ollama on :11434 (click ⚙ to change URL). 🦄"
        )
        if sys.stderr is not None:
            sys.stderr.write(f"[LLMWorker] Connection error: {err_detail}\n")
        self.chat_window.add_message("pet", friendly_msg, "error")
        disp_ms = self.speech_bubble.show_message(friendly_msg, duration_ms=7500)
        self.trigger_3d_action("Wave", speech_ms=min(disp_ms, 4200))

    def _on_worker_finished(self) -> None:
        self.chat_bar.set_busy(False)
        if self.chat_bar.isVisible():
            self.chat_bar.focus_input()
        self._state = PetState.IDLE
        self._active_worker = None
        self._schedule_next_decision(2400, 4200)

    def closeEvent(self, event) -> None:
        self._roam_tick_timer.stop()
        self._decision_timer.stop()
        self._single_click_timer.stop()
        self._cursor_timer.stop()
        if hasattr(self, "_startup_fallback_timer"):
            self._startup_fallback_timer.stop()
        if hasattr(self, "_skirmish_timer"):
            self._skirmish_timer.stop()
        if hasattr(self, "_farm_sync_timer"):
            self._farm_sync_timer.stop()
        if hasattr(self, "rpg_state"):
            self.rpg_state.save()
        if hasattr(self, "rpg_hub"):
            self.rpg_hub.close()
        if hasattr(self, "radial_menu"):
            self.radial_menu.close_all()
        if hasattr(self, "speech_bubble"):
            self.speech_bubble.close()
        if hasattr(self, "_heist_restore_timer"):
            self._heist_restore_timer.stop()
        if hasattr(self, "_heist_max_timeout_timer"):
            self._heist_max_timeout_timer.stop()
        if getattr(self, "_screen_hole_overlay", None) is not None:
            try:
                self._screen_hole_overlay.close()
            except Exception:
                pass
            self._screen_hole_overlay = None
        if getattr(self, "_spider_overlay", None) is not None:
            try:
                self._spider_overlay.close()
            except Exception:
                pass
            self._spider_overlay = None
        if hasattr(self, "chat_window"):
            self.chat_window.close()
        if hasattr(self, "outlook_hud"):
            self.outlook_hud.close()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        if self._active_worker is not None and self._active_worker.isRunning():
            self._active_worker.wait(1500)
        if hasattr(self, "web_view") and hasattr(self, "_web_page") and self._web_page is not None:
            try:
                self.web_view.setPage(None)
                self._web_page.deleteLater()
                self._web_page = None
            except Exception:
                pass
        super().closeEvent(event)


class MultiPetCoordinator(QObject):
    """Coordinates desktop coexistence and natural mutual interactions between
    '뽕뽕이' (Ppong-ppong-i) and '트리' (Tree):
    - Real physical character-body collision with smooth recoil velocity bounce
    - Mutual Tag Game (서로 술래잡기: Chaser vs Runner)
    - Desktop Running Race (달리기 시합: random speed boosts & photo-finish winner!)
    - Friendly Battle Duel (1:1 박치기/대결 시합)
    - Greeting, Duet Dance, Snack Party, and Companion Roam"""

    def __init__(
        self,
        ppong_win: DesktopPetWindow,
        tree_win: DesktopPetWindow,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.ppong_win = ppong_win
        self.tree_win = tree_win
        self.ppong_win.coordinator = self
        self.tree_win.coordinator = self
        self._last_social_time = time.perf_counter()
        self._social_cooldown_sec = self._roll_social_cooldown()
        self._interaction_cycle = 0
        self._last_bump_time = 0.0

        # Active multi-pet minigame state ("none" | "race" | "tag" | "duel")
        self._game_mode = "none"
        self._game_start_time = 0.0
        self._game_last_tick = 0.0
        self._race_dir = 1.0
        self._race_finish_x = 0.0
        self._race_speed_p = 240.0
        self._race_speed_t = 240.0
        self._race_boost_timer = 0.0
        self._tag_chaser: Optional[DesktopPetWindow] = None
        self._tag_runner: Optional[DesktopPetWindow] = None
        self._tag_duration = 8.0
        self._duel_phase = 0
        self._duel_center_x = 500.0
        self._duel_center_y = 500.0
        self._recoil_vx_p = 0.0
        self._recoil_vy_p = 0.0
        self._recoil_vx_t = 0.0
        self._recoil_vy_t = 0.0
        self._recoil_timer = 0.0

        self._social_timer = QTimer(self)
        self._social_timer.setInterval(4000)
        self._social_timer.timeout.connect(self._on_social_tick)
        self._social_timer.start()

        # Real-time refresh-matched physical collision & multi-pet minigame physics loop
        screen = QGuiApplication.primaryScreen()
        refresh_hz = float(screen.refreshRate() or 60.0) if screen else 60.0
        col_tick_ms = max(8, min(16, int(math.floor(1000.0 / max(60.0, refresh_hz)))))
        self._collision_timer = QTimer(self)
        self._collision_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._collision_timer.setInterval(col_tick_ms)
        self._collision_timer.timeout.connect(self._on_physics_and_game_tick)
        self._collision_timer.start()

        # Single cancellable social finish / yaw-reset timer
        self._social_finish_timer = QTimer(self)
        self._social_finish_timer.setSingleShot(True)
        self._social_finish_cb = None
        self._social_finish_timer.timeout.connect(self._run_social_finish_cb)

        # Workday Stone Cairn Manager (clock-in ~ 17:00 clock-out desktop cairn)
        self.cairn_manager = WorkdayCairnManager(
            ppong_win,
            tree_win,
            self,
            DATA_DIR,
            font_family=APP_FONT_FAMILY,
            parent=self,
        )

    def _run_social_finish_cb(self) -> None:
        cb = self._social_finish_cb
        self._social_finish_cb = None
        if callable(cb):
            cb()

    def _schedule_social_finish(self, delay_ms: int, cb) -> None:
        self._social_finish_timer.stop()
        self._social_finish_cb = cb
        self._social_finish_timer.start(max(10, int(delay_ms)))

    def _cancel_social_finish(self) -> None:
        self._social_finish_timer.stop()
        self._social_finish_cb = None

    def _roll_social_cooldown(self) -> float:
        freq = getattr(getattr(self.ppong_win, "_prefs", None), "action_frequency", "normal")
        if freq == "frequent":
            return random.uniform(55.0, 115.0)
        if freq == "rare":
            return random.uniform(240.0, 480.0)
        return random.uniform(110.0, 240.0)

    def is_minigame_active(self) -> bool:
        return self._game_mode != "none"

    def _stop_minigame(self) -> None:
        self._cancel_social_finish()
        was_active = self._game_mode != "none"
        self._game_mode = "none"
        self._recoil_timer = 0.0
        if was_active:
            for w in (self.ppong_win, self.tree_win):
                if w._state == PetState.MINIGAME:
                    w._state = PetState.IDLE
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    w.trigger_3d_action("Idle")
                    w._schedule_next_decision()

    def _on_physics_and_game_tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, max(0.005, now - self._game_last_tick)) if self._game_last_tick > 0 else 0.016
        self._game_last_tick = now

        p = self.ppong_win
        t = self.tree_win
        if not p.isVisible() or not t.isVisible():
            return
        if not getattr(p, "_character_ready", False) or not getattr(t, "_character_ready", False):
            return
        if getattr(p, "_in_battle_arena", False) or getattr(t, "_in_battle_arena", False):
            self._stop_minigame()
            return
        if p.is_popup_menu_open() or t.is_popup_menu_open():
            for w in (p, t):
                if w.is_popup_menu_open():
                    w._phys_vx = 0.0
                    w._phys_vy = 0.0
            if self._game_mode != "none":
                self._stop_minigame()
            return

        avail = p._current_available_geometry()
        min_x = float(avail.left() + 16)
        max_x = float(max(avail.left() + 26, avail.right() - p.WINDOW_W - 16))
        min_y = float(avail.top() + 20)
        max_y = float(p._taskbar_floor_y(avail))

        # 1. Continuous Non-Blocking 2D Rigid-Body Physics Integration (damped elastic momentum + wall bounce)
        phys_decay = math.exp(-5.4 * dt)
        for w in (p, t):
            vx = getattr(w, "_phys_vx", 0.0)
            vy = getattr(w, "_phys_vy", 0.0)
            if (vx * vx + vy * vy) > 4.0 and not w._is_dragging and not w.is_popup_menu_open():
                prev_wx, prev_wy = w._pos_x, w._pos_y
                nx = w._pos_x + vx * dt
                ny = w._pos_y + vy * dt
                if nx < min_x:
                    nx = min_x
                    vx = abs(vx) * 0.75
                elif nx > max_x:
                    nx = max_x
                    vx = -abs(vx) * 0.75
                if ny < min_y:
                    ny = min_y
                    vy = abs(vy) * 0.75
                elif ny > max_y:
                    ny = max_y
                    vy = -abs(vy) * 0.75
                w._pos_x = nx
                w._pos_y = ny
                w._update_window_pos()
                w._phys_vx = vx * phys_decay
                w._phys_vy = vy * phys_decay
                if w._state == PetState.IDLE and (vx * vx + vy * vy) > 36.0:
                    w._sync_movement_facing(prev_wx, prev_wy, dt, vx, vy)
            else:
                w._phys_vx = 0.0
                w._phys_vy = 0.0

        # 2. Active Running Race Minigame (달리기 시합)
        if self._game_mode == "race":
            if p._is_dragging or t._is_dragging:
                self._stop_minigame()
                return
            self._race_boost_timer -= dt
            if self._race_boost_timer <= 0:
                self._race_boost_timer = random.uniform(0.65, 1.15)
                # Random dynamic speed surges (comfortable smooth pace!)
                self._race_speed_p = random.uniform(145.0, 225.0)
                self._race_speed_t = random.uniform(145.0, 225.0)
                if random.random() < 0.40:
                    leader = p if self._race_speed_p >= self._race_speed_t else t
                    leader.speech_bubble.show_message("💨 스퍼트! 내가 먼저 간다~!", duration_ms=1300)

            blend_r = 1.0 - math.exp(-8.0 * dt)
            cur_p = getattr(self, "_race_cur_speed_p", self._race_speed_p)
            cur_t = getattr(self, "_race_cur_speed_t", self._race_speed_t)
            cur_p += (self._race_speed_p - cur_p) * blend_r
            cur_t += (self._race_speed_t - cur_t) * blend_r
            self._race_cur_speed_p = cur_p
            self._race_cur_speed_t = cur_t

            p._pos_x = max(min_x, min(max_x, p._pos_x + self._race_dir * cur_p * dt))
            t._pos_x = max(min_x, min(max_x, t._pos_x + self._race_dir * cur_t * dt))
            p._update_window_pos()
            t._update_window_pos()

            yaw = 1.48 if self._race_dir > 0 else -1.48
            for w, cur_spd in ((p, cur_p), (t, cur_t)):
                w._current_stage_yaw = yaw
                w._send_locomotion_batch(yaw, self._race_dir * cur_spd, 0.0, int(self._race_dir))

            p_done = (p._pos_x >= self._race_finish_x) if self._race_dir > 0 else (p._pos_x <= self._race_finish_x)
            t_done = (t._pos_x >= self._race_finish_x) if self._race_dir > 0 else (t._pos_x <= self._race_finish_x)
            if p_done or t_done or (now - self._game_start_time) > 11.5:
                self._game_mode = "none"
                if p_done and not t_done:
                    winner, loser = p, t
                elif t_done and not p_done:
                    winner, loser = t, p
                else:
                    p_dist = abs(self._race_finish_x - p._pos_x)
                    t_dist = abs(self._race_finish_x - t._pos_x)
                    winner, loser = (p, t) if p_dist <= t_dist else (t, p)

                for w in (p, t):
                    w._state = PetState.IDLE
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                self._face_each_other()
                winner.trigger_3d_action("HappySpin", duration_ms=2800, emotion="proud")
                loser.trigger_3d_action("Sit", duration_ms=2600, emotion="surprised")
                winner.speech_bubble.show_message(f"🏆 달리기 1등! {winner.char_display_name} 승리! 🥇✨", duration_ms=3400)
                loser.speech_bubble.show_message("헉헉... 아깝게 2등이네! 다음엔 내가 이긴다! 😆", duration_ms=3400)
                self._last_social_time = now
                self._social_cooldown_sec = self._roll_social_cooldown()
                self._schedule_social_finish(
                    3200,
                    lambda: [w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True) for w in (p, t) if w._state == PetState.IDLE],
                )
                p._schedule_next_decision()
                t._schedule_next_decision()
            return

        # 3. Active Mutual Tag Minigame (서로 술래잡기: Chaser vs Runner)
        if self._game_mode == "tag":
            chaser = self._tag_chaser
            runner = self._tag_runner
            if chaser is None or runner is None or chaser._is_dragging or runner._is_dragging:
                self._stop_minigame()
                return

            elapsed = now - self._game_start_time
            dx = runner._pos_x - chaser._pos_x
            dy = runner._pos_y - chaser._pos_y
            dist = math.hypot(dx, dy)

            # Check if Chaser caught Runner! (True character-body proximity <= 46px)
            if dist <= 46.0:
                self._game_mode = "none"
                # Damped elastic recoil velocity impulse (integrates smoothly in rigid-body loop!)
                nx = (dx / dist) if dist > 1e-3 else 1.0
                ny = (dy / dist) if dist > 1e-3 else 0.0
                runner._phys_vx = nx * 320.0
                runner._phys_vy = ny * 220.0
                chaser._phys_vx = -nx * 220.0
                chaser._phys_vy = -ny * 150.0
                for w in (chaser, runner):
                    w._state = PetState.IDLE
                    w._vel_x = 0.0
                    w._vel_y = 0.0
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                self._face_each_other()
                chaser.trigger_3d_action("Jump", duration_ms=2400, emotion="excited")
                runner.trigger_3d_action("HappySpin", duration_ms=2400, emotion="surprised")
                chaser.speech_bubble.show_message(f"✋ 터치! {runner.char_display_name} 잡았다! 술래잡기 승리! 🏆", duration_ms=3200)
                runner.speech_bubble.show_message("으악 잡혔다~! 엄청 빠르네! 🏳️😆", duration_ms=3200)
                self._last_social_time = now
                self._social_cooldown_sec = self._roll_social_cooldown()
                self._schedule_social_finish(
                    3200,
                    lambda: [w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True) for w in (chaser, runner) if w._state == PetState.IDLE],
                )
                chaser._schedule_next_decision()
                runner._schedule_next_decision()
                return

            if elapsed >= self._tag_duration:
                self._game_mode = "none"
                for w in (chaser, runner):
                    w._state = PetState.IDLE
                    w._vel_x = 0.0
                    w._vel_y = 0.0
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                self._face_each_other()
                runner.trigger_3d_action("Proud", duration_ms=2600, emotion="proud")
                chaser.trigger_3d_action("Sit", duration_ms=2400, emotion="sleepy")
                runner.speech_bubble.show_message(f"🏃 끝까지 도망 성공! {runner.char_display_name} 승리! ✌️", duration_ms=3200)
                chaser.speech_bubble.show_message("휴우~ 너무 빨라서 못 잡았어! 💦", duration_ms=3200)
                self._last_social_time = now
                self._social_cooldown_sec = self._roll_social_cooldown()
                self._schedule_social_finish(
                    3200,
                    lambda: [w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True) for w in (chaser, runner) if w._state == PetState.IDLE],
                )
                chaser._schedule_next_decision()
                runner._schedule_next_decision()
                return

            # Runner flees toward waypoints while dodging Chaser; Chaser pursues Runner directly
            if not runner._roam_waypoints or math.hypot(runner._roam_waypoints[0][0] - runner._pos_x, runner._roam_waypoints[0][1] - runner._pos_y) < 36.0:
                runner._roam_waypoints = runner._generate_2d_desktop_waypoints(2)
            r_tx, r_ty = runner._roam_waypoints[0]
            # Add repulsion away from chaser
            rep_x = (dx / max(1.0, dist)) * 140.0
            rep_y = (dy / max(1.0, dist)) * 90.0
            r_goal_x = max(min_x, min(max_x, r_tx + rep_x))
            r_goal_y = max(min_y, min(max_y, r_ty + rep_y))

            blend_t = 1.0 - math.exp(-10.0 * dt)
            r_dx = r_goal_x - runner._pos_x
            r_dy = r_goal_y - runner._pos_y
            r_dist = max(1.0, math.hypot(r_dx, r_dy))
            r_spd = 172.0
            prev_rx, prev_ry = runner._pos_x, runner._pos_y
            runner._vel_x += ((r_dx / r_dist) * r_spd - runner._vel_x) * blend_t
            runner._vel_y += ((r_dy / r_dist) * r_spd - runner._vel_y) * blend_t
            runner._pos_x = max(min_x, min(max_x, runner._pos_x + runner._vel_x * dt))
            runner._pos_y = max(min_y, min(max_y, runner._pos_y + runner._vel_y * dt))
            runner._update_window_pos()
            runner._sync_movement_facing(prev_rx, prev_ry, dt, r_dx, r_dy)

            c_spd = 196.0  # Chaser is slightly faster so catches happen naturally!
            prev_cx, prev_cy = chaser._pos_x, chaser._pos_y
            chaser._vel_x += ((dx / max(1.0, dist)) * c_spd - chaser._vel_x) * blend_t
            chaser._vel_y += ((dy / max(1.0, dist)) * c_spd - chaser._vel_y) * blend_t
            chaser._pos_x = max(min_x, min(max_x, chaser._pos_x + chaser._vel_x * dt))
            chaser._pos_y = max(min_y, min(max_y, chaser._pos_y + chaser._vel_y * dt))
            chaser._update_window_pos()
            chaser._sync_movement_facing(prev_cx, prev_cy, dt, dx, dy)
            return

        # 4. Active Friendly Battle Duel Minigame (1:1 박치기 대결!)
        if self._game_mode == "duel":
            if p._is_dragging or t._is_dragging:
                self._stop_minigame()
                return
            elapsed = now - self._game_start_time
            if self._duel_phase == 0:
                # Charge straight at each other until their 3D character bodies collide!
                dx = p._pos_x - t._pos_x
                if abs(dx) > 26.0:
                    step = 215.0 * dt
                    sign = 1.0 if dx > 0 else -1.0
                    p._pos_x -= sign * min(abs(dx) * 0.5, step)
                    t._pos_x += sign * min(abs(dx) * 0.5, step)
                    p._update_window_pos()
                    t._update_window_pos()
                    p_dir = int(-sign)
                    t_dir = int(sign)
                    p._current_stage_yaw = 1.45 * p_dir
                    t._current_stage_yaw = 1.45 * t_dir
                    p._send_locomotion_batch(1.45 * p_dir, p_dir * 215.0, 0.0, p_dir)
                    t._send_locomotion_batch(1.45 * t_dir, t_dir * 215.0, 0.0, t_dir)
                else:
                    # CLASH! Both bounce back dramatically and one wins randomly!
                    self._duel_phase = 1
                    self._game_start_time = now
                    winner, loser = (p, t) if random.random() < 0.5 else (t, p)
                    self._duel_winner = winner
                    self._duel_loser = loser
                    sign = 1.0 if (p._pos_x >= t._pos_x) else -1.0
                    # Loser gets knocked back farther!
                    p_kb = 290.0 if loser is p else 145.0
                    t_kb = 290.0 if loser is t else 145.0
                    self._recoil_vx_p = sign * p_kb
                    self._recoil_vx_t = -sign * t_kb
                    p.trigger_3d_action("Jump", duration_ms=1200, emotion="surprised")
                    t.trigger_3d_action("Jump", duration_ms=1200, emotion="surprised")
                    p.speech_bubble.show_message("💥 쾅!! 초특급 박치기 충돌!", duration_ms=1600)
            elif self._duel_phase == 1:
                decay = math.exp(-4.8 * dt)
                self._recoil_vx_p *= decay
                self._recoil_vx_t *= decay
                p._pos_x = max(min_x, min(max_x, p._pos_x + self._recoil_vx_p * dt))
                t._pos_x = max(min_x, min(max_x, t._pos_x + self._recoil_vx_t * dt))
                p._update_window_pos()
                t._update_window_pos()
                if elapsed >= 0.75:
                    self._game_mode = "none"
                    winner = getattr(self, "_duel_winner", p)
                    loser = getattr(self, "_duel_loser", t)
                    for w in (p, t):
                        w._state = PetState.IDLE
                        w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    self._face_each_other()
                    winner.trigger_3d_action("HappySpin", duration_ms=2600, emotion="proud")
                    loser.trigger_3d_action("Sit", duration_ms=2400, emotion="shy")
                    winner.speech_bubble.show_message(f"⚔️ 박치기 대결 승리! {winner.char_display_name} 완승! 🏆", duration_ms=3200)
                    loser.speech_bubble.show_message("으앗 튕겨 나갔다~! 파워 대단한걸! 💫😆", duration_ms=3200)
                    self._last_social_time = now
                    self._social_cooldown_sec = self._roll_social_cooldown()
                    self._schedule_social_finish(
                        3200,
                        lambda: [w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True) for w in (p, t) if w._state == PetState.IDLE],
                    )
                    p._schedule_next_decision()
                    t._schedule_next_decision()
            return

        # 5. Passive Physical Character-Body Collision Detection (Tight 3D body radius, never bubble collision!)
        self._check_physical_collision()

    def _check_physical_collision(self) -> None:
        """Continuous 2D rigid-body elastic collision between the two 3D character bodies
        (strictly decoupled from SpeechBubbleWidget geometry and never freezing active states)."""
        p = self.ppong_win
        t = self.tree_win
        non_collidable = {
            PetState.HIDE_AND_SEEK,
            PetState.SKIRMISH,
            PetState.WAVE_DEFENSE,
            PetState.SPIDER_SWING,
            PetState.SUPERMAN_FLY,
            PetState.MINIGAME,
            PetState.SOLO_PLAY,
            PetState.CAIRN_WORK,
            PetState.EXCAVATING,
            PetState.FALLING,
        }
        if p._state in non_collidable or t._state in non_collidable:
            return

        # Exact 3D character body screen centers inside the 440x560 window
        p_cx = p._pos_x + 220.0
        p_cy = p._pos_y + 469.1 - 75.0 * p._scale_factor
        t_cx = t._pos_x + 220.0
        t_cy = t._pos_y + 469.1 - 75.0 * t._scale_factor

        dx = p_cx - t_cx
        dy = p_cy - t_cy
        dist = math.hypot(dx, dy)
        avg_scale = (p._scale_factor + t._scale_factor) * 0.5
        body_diameter = 16.0 + 135.0 * avg_scale

        if dist >= body_diameter:
            return

        now = time.perf_counter()
        if dist < 1e-3:
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / dist, dy / dist

        avail = p._current_available_geometry()
        min_x = float(avail.left() + 16)
        max_x = float(max(avail.left() + 26, avail.right() - p.WINDOW_W - 16))
        min_y = float(avail.top() + 20)
        max_y = float(p._taskbar_floor_y(avail))

        # Positional penetration resolution split equally across unlocked bodies
        overlap = body_diameter - dist
        corr = overlap * 0.52 + 2.0
        if not p._is_dragging:
            p._pos_x = max(min_x, min(max_x, p._pos_x + nx * corr))
            p._pos_y = max(min_y, min(max_y, p._pos_y + ny * corr * 0.65))
            p._update_window_pos()
        if not t._is_dragging:
            t._pos_x = max(min_x, min(max_x, t._pos_x - nx * corr))
            t._pos_y = max(min_y, min(max_y, t._pos_y - ny * corr * 0.65))
            t._update_window_pos()

        # Newtonian 2D impulse exchange (restitution e = 0.85, unit equal masses)
        p_vx = p._vel_x + getattr(p, "_phys_vx", 0.0)
        p_vy = p._vel_y + getattr(p, "_phys_vy", 0.0)
        t_vx = t._vel_x + getattr(t, "_phys_vx", 0.0)
        t_vy = t._vel_y + getattr(t, "_phys_vy", 0.0)
        rel_vn = (p_vx - t_vx) * nx + (p_vy - t_vy) * ny
        if rel_vn < 0.0:
            impulse_j = max(145.0, -(1.0 + 0.85) * rel_vn * 0.55)
        else:
            impulse_j = 135.0
        p._phys_vx = max(-360.0, min(360.0, nx * impulse_j))
        p._phys_vy = max(-220.0, min(220.0, ny * impulse_j * 0.55))
        t._phys_vx = max(-360.0, min(360.0, -nx * impulse_j))
        t._phys_vy = max(-220.0, min(220.0, -ny * impulse_j * 0.55))

        # Gently deflect roam waypoints without interrupting or freezing character actions
        for w, sign in ((p, 1.0), (t, -1.0)):
            if w._state in {PetState.WALK, PetState.RUN, PetState.EVADING, PetState.WINDOW_HEIST}:
                speed = max(145.0, math.hypot(w._vel_x, w._vel_y))
                w._vel_x = sign * nx * speed
                w._vel_y = sign * ny * speed * 0.55
                if w._roam_waypoints:
                    wx = max(min_x, min(max_x, w._pos_x + sign * nx * 210.0))
                    wy = max(min_y, min(max_y, w._pos_y + sign * ny * 110.0))
                    w._roam_waypoints[0] = (wx, wy)

        # Light non-blocking reaction emote/bubble (zero state freeze)
        if (now - self._last_bump_time) >= 4.0:
            self._last_bump_time = now
            self._last_social_time = now
            p.speech_bubble.show_message("💥 쿵! 트리랑 톡 부딪혔다~!", duration_ms=1900)
            t.speech_bubble.show_message("🎄 앗 콩! 탄성 바운스~! 💫", duration_ms=1900)

    def is_any_in_arena(self) -> bool:
        for w in (self.ppong_win, self.tree_win):
            if getattr(w, "_in_battle_arena", False) or w._state in {PetState.SKIRMISH, PetState.WAVE_DEFENSE}:
                return True
        return False

    def get_partner(self, pet: DesktopPetWindow) -> Optional[DesktopPetWindow]:
        if pet is self.ppong_win:
            return self.tree_win
        if pet is self.tree_win:
            return self.ppong_win
        return None

    def toggle_partner_visibility(self, requester: DesktopPetWindow) -> None:
        partner = self.get_partner(requester)
        if partner is None:
            return
        if partner.isVisible():
            partner.hide_to_tray()
            requester.speech_bubble.show_message(
                f"{partner.char_display_name} 친구가 잠시 쉬러 갔어요! 다시 부르려면 메뉴에서 눌러주세요~ ✨",
                duration_ms=2800,
            )
        else:
            partner.show_pet_from_tray()
            self.greet_each_other()

    def _both_ready_and_free(self, allow_roam: bool = False) -> bool:
        if self.is_any_in_arena() or self.is_minigame_active():
            return False
        for w in (self.ppong_win, self.tree_win):
            if not w.isVisible() or not getattr(w, "_character_ready", False):
                return False
            if w.is_action_busy(include_locomotion=not allow_roam):
                return False
            allowed = {PetState.IDLE}
            if allow_roam:
                allowed |= {PetState.WALK, PetState.RUN}
            if w._state not in allowed:
                return False
        return True

    def _on_social_tick(self) -> None:
        now = time.perf_counter()
        if self.is_minigame_active():
            return
        freq = getattr(getattr(self.ppong_win, "_prefs", None), "action_frequency", "normal")
        if freq == "off":
            return
        if (now - self._last_social_time) < self._social_cooldown_sec:
            return
        if not self._both_ready_and_free(allow_roam=False):
            return

        dx = self.ppong_win._pos_x - self.tree_win._pos_x
        dy = self.ppong_win._pos_y - self.tree_win._pos_y
        dist = math.hypot(dx, dy)

        if dist <= 300.0 or (now - self._last_social_time) >= self._social_cooldown_sec:
            self._last_social_time = now
            self._social_cooldown_sec = self._roll_social_cooldown()
            mode = self._interaction_cycle % 7
            self._interaction_cycle += 1
            if mode == 0:
                self.start_running_race()
            elif mode == 1:
                self.start_mutual_tag()
            elif mode == 2:
                self.start_friendly_duel()
            elif mode == 3:
                self.greet_each_other()
            elif mode == 4:
                self.duet_dance()
            elif mode == 5:
                self.share_snack()
            else:
                self.roam_together()

    def start_running_race(self) -> None:
        """Lines up Ppong-ppong-i and Tree at one side of the desktop and races to the opposite side with random speed boosts!"""
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
            w._decision_timer.stop()

        avail = p._current_available_geometry()
        min_x = float(avail.left() + 30)
        max_x = float(max(avail.left() + 200, avail.right() - p.WINDOW_W - 30))
        floor_y = float(p._taskbar_floor_y(avail))

        mid_x = (min_x + max_x) * 0.5
        self._race_dir = 1.0 if ((p._pos_x + t._pos_x) * 0.5) <= mid_x else -1.0
        start_x = min_x + 20.0 if self._race_dir > 0 else max_x - 20.0
        self._race_finish_x = max_x - 20.0 if self._race_dir > 0 else min_x + 20.0

        # Place on two parallel running lanes so both characters and their bubbles are clearly visible!
        p._pos_x = start_x
        p._pos_y = floor_y
        t._pos_x = start_x
        t._pos_y = max(float(avail.top() + 30), floor_y - 52.0)
        p._update_window_pos()
        t._update_window_pos()

        self._race_speed_p = random.uniform(155.0, 215.0)
        self._race_speed_t = random.uniform(155.0, 215.0)
        self._race_cur_speed_p = self._race_speed_p
        self._race_cur_speed_t = self._race_speed_t
        self._race_boost_timer = 0.7
        self._game_start_time = time.perf_counter()
        self._game_last_tick = self._game_start_time
        self._game_mode = "race"

        init_race_yaw = 1.48 if self._race_dir > 0 else -1.48
        for w, spd in ((p, self._race_speed_p), (t, self._race_speed_t)):
            w._state = PetState.MINIGAME
            w._current_stage_yaw = init_race_yaw
            w._send_locomotion_batch(init_race_yaw, self._race_dir * spd, 0.0, int(self._race_dir), force=True, snap=True)
            w.trigger_3d_action("Run", emotion="excited")

        p.speech_bubble.show_message("🏁 트리야 달리기 시합하자! 준비~ 출발! 💨", duration_ms=2400)
        t.speech_bubble.show_message("🏃 좋아! 이번엔 내가 1등 할 거야! 🌟", duration_ms=2400)

    def start_mutual_tag(self) -> None:
        """Starts an interactive Tag Game between Ppong-ppong-i and Tree where one chases and the other flees!"""
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
            w._decision_timer.stop()

        self._arrange_pair_on_screen(170.0)
        if random.random() < 0.5:
            chaser, runner = p, t
        else:
            chaser, runner = t, p

        self._tag_chaser = chaser
        self._tag_runner = runner
        self._tag_duration = random.uniform(6.0, 8.5)
        self._game_start_time = time.perf_counter()
        self._game_last_tick = self._game_start_time
        self._game_mode = "tag"

        runner._roam_waypoints = runner._generate_2d_desktop_waypoints(3)
        for w in (chaser, runner):
            w._state = PetState.MINIGAME
            w.trigger_3d_action("Run", emotion="excited")

        chaser.speech_bubble.show_message(f"👹 내가 술래다! {runner.char_display_name} 거기 서~!! 💨", duration_ms=2500)
        runner.speech_bubble.show_message("😝 메롱~ 못 잡겠지롱! 도망쳐라! 🏃", duration_ms=2500)

    def start_friendly_duel(self) -> None:
        """Starts a playful 1v1 headbutt/clash duel where both charge at each other, collide, and bounce back!"""
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
            w._decision_timer.stop()

        self._arrange_pair_on_screen(210.0)
        self._face_each_other()
        self._duel_phase = 0
        self._game_start_time = time.perf_counter()
        self._game_last_tick = self._game_start_time
        self._game_mode = "duel"

        for w in (p, t):
            w._state = PetState.MINIGAME
            w.trigger_3d_action("Run", emotion="excited")

        p.speech_bubble.show_message("⚔️ 트리야 1:1 박치기 대결이다! 간다~!! 🔥", duration_ms=2200)
        t.speech_bubble.show_message("🛡️ 덤벼라 뽕뽕아! 내 황금 별 파워를 받아라! 🌟", duration_ms=2200)

    def _arrange_pair_on_screen(self, gap_px: float = 185.0) -> None:
        """Brings both pets onto a comfortable side-by-side spot if they are too far apart or overlapping."""
        p = self.ppong_win
        t = self.tree_win
        avail = p._current_available_geometry()
        min_x = float(avail.left() + 20)
        max_x = float(max(avail.left() + 30, avail.right() - p.WINDOW_W - 20))
        min_y = float(avail.top() + 30)
        max_y = float(p._taskbar_floor_y(avail))

        dx = p._pos_x - t._pos_x
        dy = p._pos_y - t._pos_y
        dist = math.hypot(dx, dy)
        if dist < 95.0 or dist > 380.0 or abs(dy) > 90.0:
            mid_x = max(min_x + gap_px * 0.6, min(max_x - gap_px * 0.6, (p._pos_x + t._pos_x) * 0.5))
            shared_y = max(min_y, min(max_y, (p._pos_y + t._pos_y) * 0.5))
            t._pos_x = max(min_x, min(max_x, mid_x - gap_px * 0.5))
            t._pos_y = shared_y
            p._pos_x = max(min_x, min(max_x, mid_x + gap_px * 0.5))
            p._pos_y = shared_y
            t._update_window_pos()
            p._update_window_pos()

    def _face_each_other(self) -> None:
        p = self.ppong_win
        t = self.tree_win
        if t._pos_x <= p._pos_x:
            t._set_3d_facing(1)
            t._set_stage_yaw_override(0.52)
            p._set_3d_facing(-1)
            p._set_stage_yaw_override(-0.52)
        else:
            t._set_3d_facing(-1)
            t._set_stage_yaw_override(-0.52)
            p._set_3d_facing(1)
            p._set_stage_yaw_override(0.52)

    def greet_each_other(self) -> None:
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        self._social_cooldown_sec = self._roll_social_cooldown()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
        self._arrange_pair_on_screen(185.0)
        self._face_each_other()
        for w in (p, t):
            w._state = PetState.INTERACTING

        p.trigger_3d_action("Wave", duration_ms=3400, emotion="happy", speech_ms=3400)
        t.trigger_3d_action("Jump", duration_ms=3400, emotion="excited", speech_ms=3400)
        p.speech_bubble.show_message("트리야 안녕~! 반짝이는 황금 별 모자 오늘도 정말 멋지다! 🦄🌈✨", duration_ms=3800)
        t.speech_bubble.show_message("안녕 뽕뽕아~! 너랑 같이 바탕화면에서 놀면 언제나 행복해! 🎄🌟💕", duration_ms=3800)

        def _reset_yaw() -> None:
            for w in (p, t):
                if w._state in {PetState.IDLE, PetState.INTERACTING}:
                    w._state = PetState.IDLE
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    w._schedule_next_decision()
        self._schedule_social_finish(3800, _reset_yaw)

    def duet_dance(self) -> None:
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        self._social_cooldown_sec = self._roll_social_cooldown()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
        self._arrange_pair_on_screen(180.0)
        for w in (p, t):
            w._state = PetState.INTERACTING
            w._set_stage_yaw_override(None)
            w._set_3d_facing(0)
            w.trigger_3d_action("Dance", duration_ms=4200, emotion="excited", speech_ms=4000)

        p.speech_bubble.show_message("원, 투, 쓰리! 🎵 트리와 함께하는 무지개 듀엣 댄스 타임! 💃🌈", duration_ms=4200)
        t.speech_bubble.show_message("신난다~! 🎶 뽕뽕이랑 맞춰 추는 숲속 별빛 댄스! 🕺🎄✨", duration_ms=4200)

        def _finish_dance() -> None:
            for w in (p, t):
                if w._state == PetState.INTERACTING:
                    w._state = PetState.IDLE
                    w._schedule_next_decision()
        self._schedule_social_finish(4250, _finish_dance)

    def share_snack(self) -> None:
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        self._social_cooldown_sec = self._roll_social_cooldown()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
        self._arrange_pair_on_screen(180.0)
        self._face_each_other()
        for w in (p, t):
            w._state = PetState.INTERACTING
            w.trigger_3d_action("Snack", duration_ms=3800, emotion="loving", speech_ms=3800)

        p.speech_bubble.show_message("냠냠! 트리야, 내 달콤한 무지개 솜사탕 반쪽 나눠 줄게! 🍬🌈💖", duration_ms=4000)
        t.speech_bubble.show_message("고마워 뽕뽕아~! 나는 바삭한 황금 별 쿠키 나눠 줄게! 🍪🌟🥰", duration_ms=4000)

        def _reset_yaw() -> None:
            for w in (p, t):
                if w._state in {PetState.IDLE, PetState.INTERACTING}:
                    w._state = PetState.IDLE
                    w._send_locomotion_batch(None, 0.0, 0.0, 0, force=True)
                    w._schedule_next_decision()
        self._schedule_social_finish(4000, _reset_yaw)

    def roam_together(self) -> None:
        if self.is_any_in_arena():
            return
        self._cancel_social_finish()
        self._last_social_time = time.perf_counter()
        self._social_cooldown_sec = self._roll_social_cooldown()
        p = self.ppong_win
        t = self.tree_win
        for w in (p, t):
            if not w.isVisible():
                w.show_pet_from_tray()
            w.cancel_all_active_actions()
        base_wps = p._generate_2d_desktop_waypoints(4)
        avail = p._current_available_geometry()
        min_x = float(avail.left() + 20)
        max_x = float(max(avail.left() + 30, avail.right() - p.WINDOW_W - 20))
        tree_wps = [(max(min_x, min(max_x, wx - 155.0)), wy) for (wx, wy) in base_wps]
        ppong_wps = [(max(min_x, min(max_x, wx)), wy) for (wx, wy) in base_wps]

        dur = 10.5
        p.start_omnidirectional_roam(mode="walk", duration=dur, manual=True)
        t.start_omnidirectional_roam(mode="walk", duration=dur, manual=True)
        p._roam_waypoints = ppong_wps
        t._roam_waypoints = tree_wps
        p.speech_bubble.show_message("트리야, 나란히 바탕화면 산책 가자~! 🗺️🌈", duration_ms=3400)
        t.speech_bubble.show_message("좋아 뽕뽕아! 발맞춰 걸어가자~! 🐾🎄🌟", duration_ms=3400)


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    import traceback
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        log_path = DATA_DIR / "crash_error.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Unhandled Exception:\n")
            f.write(err_msg)
    except Exception:
        pass
    if sys.stderr is not None:
        try:
            print("Unhandled Exception:", err_msg, file=sys.stderr)
        except Exception:
            pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = _handle_unhandled_exception


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Ppong-ppong-i & Tree Desktop Minipet")
    app.setQuitOnLastWindowClosed(False)
    loaded_family = load_app_fonts(BUNDLE_DIR)
    app.setFont(QFont(loaded_family, 10))

    asset_server = LocalAssetServer(APP_DIR)
    asset_server.start()

    shared_rpg = RPGWorldState(DATA_DIR)
    shared_chat = FloatingChatWindow(data_dir=DATA_DIR)
    ppong_window = DesktopPetWindow(asset_server, char_id="ppong", rpg_state=shared_rpg, chat_window=shared_chat)
    tree_window = DesktopPetWindow(asset_server, char_id="tree", rpg_state=shared_rpg, chat_window=shared_chat)
    shared_chat.set_owner_pet(ppong_window)
    coordinator = MultiPetCoordinator(ppong_window, tree_window, app)
    typing_tracker = GlobalTypingTracker(shared_rpg, [ppong_window, tree_window])

    if os.environ.get("MINIPET_SKIP_STARTUP_REG") != "1":
        set_windows_startup_enabled(bool(ppong_window._prefs.auto_start_windows))

    ppong_window.show()
    tree_window.show()

    def _cleanup() -> None:
        typing_tracker.stop()
        coordinator._social_timer.stop()
        coordinator._collision_timer.stop()
        if hasattr(coordinator, "cairn_manager"):
            coordinator.cairn_manager.cleanup()
        try:
            shared_chat.cleanup()
        except Exception:
            pass
        for w in (ppong_window, tree_window):
            if w.tray_icon is not None:
                w.tray_icon.hide()
        asset_server.stop()

    app.aboutToQuit.connect(_cleanup)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

