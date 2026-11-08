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

from system_cleaner import clean_pc_environment
from alarm_service import AlarmManager
from alarm_dialog import Visual3DAlarmDialog
from alarm_manager_dialog import AlarmManagerDialog

# Configure Chromium flags BEFORE importing QtWebEngineWidgets / creating QApplication
# Ensures zero white flash on startup and unrestricted local GLB asset loading.
_CHROMIUM_FLAGS = (
    "--default-background-color=00000000 "
    "--allow-file-access-from-files "
    "--autoplay-policy=no-user-gesture-required "
    "--disable-features=Translate"
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
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGraphicsOpacityEffect,
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
from chat_window import FloatingChatWindow

# Ensure standard 3D asset MIME types are registered on Windows
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")

APP_DIR = Path(__file__).resolve().parent

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


# =============================================================================
# 1. Embedded Loopback HTTP Server (Zero-CORS Local GLB & ES Module Serving)
# =============================================================================
class _QuietAssetHandler(SimpleHTTPRequestHandler):
    """Serves index.html and ppong.glb strictly over 127.0.0.1 without console noise."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


class LocalAssetServer:
    """Ephemeral localhost-only HTTP server so Three.js GLTFLoader loads ppong.glb cleanly."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        handler = partial(_QuietAssetHandler, directory=str(root_dir))
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._httpd.daemon_threads = True
        self.port: int = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            name="PpongAssetServer",
            daemon=True,
        )

    @property
    def index_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/index.html"

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


CONFIG_FILE_PATH = APP_DIR / "pet_config.json"


@dataclass
class PetPreferences:
    """User preferences saved and loaded automatically from pet_config.json."""

    scale_factor: float = 1.0
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
    llm_url: str = os.environ.get("PPONG_LLM_URL", "http://localhost:8080/v1/chat/completions")
    llm_model: str = os.environ.get("PPONG_LLM_MODEL", "local-model")
    llm_api_key: str = os.environ.get("PPONG_LLM_API_KEY", "sk-local")

    @classmethod
    def load(cls) -> "PetPreferences":
        if CONFIG_FILE_PATH.exists():
            try:
                data = json.loads(CONFIG_FILE_PATH.read_text(encoding="utf-8"))
                return cls(
                    scale_factor=float(data.get("scale_factor", 1.0)),
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
                    llm_url=str(data.get("llm_url", os.environ.get("PPONG_LLM_URL", "http://localhost:8080/v1/chat/completions"))),
                    llm_model=str(data.get("llm_model", os.environ.get("PPONG_LLM_MODEL", "local-model"))),
                    llm_api_key=str(data.get("llm_api_key", os.environ.get("PPONG_LLM_API_KEY", "sk-local"))),
                )
            except Exception as e:
                sys.stderr.write(f"[Config] Error reading pet_config.json: {e}\n")
        return cls()

    def save(self) -> None:
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
                "llm_url": self.llm_url,
                "llm_model": self.llm_model,
                "llm_api_key": self.llm_api_key,
            }
            CONFIG_FILE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[Config] Error writing pet_config.json: {e}\n")


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


def parse_structured_llm_output(raw_text: str) -> tuple[str, str]:
    """Backward-compatible 2-tuple wrapper returning (reply, action)."""
    reply, action, _emotion = parse_structured_llm_output_with_emotion(raw_text)
    return (reply, action)


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
    """Floating dark-mode speech bubble with downward pointer tail above Ppong-ppong-i."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._tail_height = 10
        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont("Malgun Gothic", 10, QFont.Weight.DemiBold))
        self._label.setStyleSheet(
            f"color: {COLOR_TEXT_MAIN}; background: transparent; border: none; padding: 2px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12 + self._tail_height)
        layout.addWidget(self._label)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.fade_out)

        self._fading_out = False
        self.hide()

    def show_message(
        self,
        text: str,
        duration_ms: Optional[int] = None,
        anchor_bottom_y: Optional[int] = None,
        scale_factor: Optional[float] = None,
    ) -> int:
        self._dismiss_timer.stop()
        self._fade_anim.stop()
        self._fading_out = False

        self._label.setText(text)

        parent = self.parentWidget()
        win = self.window()
        if scale_factor is None:
            scale_factor = getattr(win, "_scale_factor", None) or (getattr(parent, "_scale_factor", 1.0) if parent else 1.0)

        # Ground foot baseline is ~475px from top of 505px window.
        # Character height from ground is ~355 * scale_factor.
        # Bottom of speech bubble tail sits ~8px above horn tip.
        if anchor_bottom_y is None:
            ground_y = 475
            char_top_y = ground_y - (355 * scale_factor)
            anchor_bottom_y = int(char_top_y - 8)

        parent_w = parent.width() if parent else 380
        # Dynamically scale bubble width and font size with pet scale
        base_w = int(210 + 120 * min(1.2, scale_factor))
        bubble_w = max(180, min(344, min(base_w, parent_w - 20)))
        inner_w = bubble_w - 28

        # Scale font size slightly for micro scales
        font_pt = max(8, min(10, int(8 + 2 * scale_factor)))
        self._label.setFont(QFont("Malgun Gothic", font_pt, QFont.Weight.DemiBold))

        fm = QFontMetrics(self._label.font())
        text_rect = fm.boundingRect(
            QRect(0, 0, inner_w, 400),
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter),
            text,
        )
        bubble_h = max(48, min(130, text_rect.height() + 24 + self._tail_height))
        x = (parent_w - bubble_w) // 2
        max_y = (parent.height() - bubble_h - 10) if parent else 400
        y = max(4, min(max_y, anchor_bottom_y - bubble_h))
        self.setGeometry(x, y, bubble_w, bubble_h)

        self.show()
        self.raise_()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        self.update()

        if duration_ms is None:
            duration_ms = max(4500, min(11000, len(text) * 85))
        if duration_ms > 0:
            self._dismiss_timer.start(duration_ms)
        return duration_ms

    def fade_out(self) -> None:
        if not self.isVisible():
            return
        self._fading_out = True
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        if self._fading_out:
            self.hide()
            self._fading_out = False

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        body_rect = QRectF(
            1.5,
            1.5,
            self.width() - 3.0,
            self.height() - self._tail_height - 2.0,
        )

        path = QPainterPath()
        path.addRoundedRect(body_rect, 14.0, 14.0)

        # Speech bubble pointer triangle centered at bottom
        cx = self.width() / 2.0
        by = body_rect.bottom()
        tail = QPolygonF(
            [
                QPointF(cx - 8.0, by - 1.0),
                QPointF(cx + 8.0, by - 1.0),
                QPointF(cx, by + self._tail_height),
            ]
        )
        tail_path = QPainterPath()
        tail_path.addPolygon(tail)
        full_path = path.united(tail_path)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(COLOR_SURFACE))   # #0f172a
        grad.setColorAt(1.0, QColor(COLOR_BG_DEEP))   # #020617

        painter.setBrush(QBrush(grad))
        pen = QPen(QColor(COLOR_BORDER), 1.5)         # #1e293b
        painter.setPen(pen)
        painter.drawPath(full_path)

        # Subtle top sky-blue highlight accent line
        accent_pen = QPen(QColor(56, 189, 248, 85), 1.0)
        painter.setPen(accent_pen)
        painter.drawLine(
            QPointF(body_rect.left() + 16, body_rect.top() + 1),
            QPointF(body_rect.right() - 16, body_rect.top() + 1),
        )


class LLMSettingsDialog(QDialog):
    """Dark-mode dialog (#020617 / #0f172a / #1e293b) to inspect or update Local LLM endpoint."""

    def __init__(self, config: LLMConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ppong-ppong-i — Local LLM Settings")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(420)
        self._config = config

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_BG_DEEP};
                color: {COLOR_TEXT_MAIN};
            }}
            QLabel {{
                color: {COLOR_TEXT_MAIN};
                font-family: 'Segoe UI';
                font-size: 12px;
            }}
            QLineEdit {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_ACCENT};
            }}
            QPushButton {{
                background-color: {COLOR_BORDER};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
                border-color: {COLOR_ACCENT};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

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
            "Supports llama-server (localhost:8080), Ollama (localhost:11434/v1/chat/completions), "
            "LM Studio, or vLLM."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel", self)
        save_btn = QPushButton("Save", self)
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


class ChatBarWidget(QWidget):
    """
    Sleek floating dark-mode chat input bar built with the requested dark-blue palette:
      - #020617 (input field deep obsidian base)
      - #0f172a (floating pill container surface)
      - #1e293b (crisp borders & interactive button states)
    """

    message_submitted = pyqtSignal(str)
    settings_requested = pyqtSignal()
    mail_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._panel = QWidget(self)
        self._panel.setObjectName("ChatPanel")
        self._panel.setStyleSheet(
            f"""
            QWidget#ChatPanel {{
                background-color: {COLOR_SURFACE};
                border: 1.5px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
            QLineEdit#ChatInput {{
                background-color: {COLOR_BG_DEEP};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 7px 11px;
                font-family: 'Segoe UI';
                font-size: 12px;
                selection-background-color: #1d4ed8;
            }}
            QLineEdit#ChatInput:focus {{
                border: 1px solid {COLOR_ACCENT};
            }}
            QPushButton#SendBtn {{
                background-color: {COLOR_BORDER};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 6px 13px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#SendBtn:hover {{
                background-color: #1d4ed8;
                border-color: {COLOR_ACCENT};
            }}
            QPushButton#SendBtn:disabled {{
                background-color: {COLOR_BG_DEEP};
                color: #475569;
                border-color: {COLOR_BORDER};
            }}
            QPushButton#IconBtn {{
                background-color: {COLOR_BG_DEEP};
                color: {COLOR_TEXT_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 9px;
                font-size: 12px;
                padding: 4px 7px;
            }}
            QPushButton#IconBtn:hover {{
                background-color: {COLOR_BORDER};
                color: {COLOR_TEXT_MAIN};
            }}
            """
        )

        row = QHBoxLayout(self._panel)
        row.setContentsMargins(8, 7, 8, 7)
        row.setSpacing(6)

        self.input_edit = QLineEdit(self._panel)
        self.input_edit.setObjectName("ChatInput")
        self.input_edit.setPlaceholderText("Chat with Ppong-ppong-i...")
        self.input_edit.returnPressed.connect(self._submit)

        self.send_btn = QPushButton("Send", self._panel)
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._submit)

        self.mail_btn = QPushButton("✉", self._panel)
        self.mail_btn.setObjectName("IconBtn")
        self.mail_btn.setToolTip("Outlook AI Mail Hub (Ctrl+M)")
        self.mail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mail_btn.clicked.connect(self.mail_requested.emit)

        self.settings_btn = QPushButton("⚙\uFE0E", self._panel)
        self.settings_btn.setObjectName("IconBtn")
        self.settings_btn.setToolTip("Local LLM Settings")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_requested.emit)

        self.close_btn = QPushButton("✕", self._panel)
        self.close_btn.setObjectName("IconBtn")
        self.close_btn.setToolTip("Hide Chat Bar (Esc)")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.close_requested.emit)

        row.addWidget(self.input_edit, stretch=1)
        row.addWidget(self.send_btn)
        row.addWidget(self.mail_btn)
        row.addWidget(self.settings_btn)
        row.addWidget(self.close_btn)

        outer.addWidget(self._panel)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc_shortcut.activated.connect(self.close_requested.emit)

    def _submit(self) -> None:
        text = self.input_edit.text().strip()
        if not text:
            return
        self.input_edit.clear()
        self.message_submitted.emit(text)

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.input_edit.setPlaceholderText(
            "Ppong-ppong-i is thinking..." if busy else "Chat with Ppong-ppong-i..."
        )

    def focus_input(self) -> None:
        self.activateWindow()
        self.input_edit.setFocus(Qt.FocusReason.MouseFocusReason)


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


class SilentWebEnginePage(QWebEnginePage):
    """Forwards critical JS console errors to stderr while keeping info logs quiet."""

    def javaScriptConsoleMessage(self, level, message: str, line_id: int, source_id: str) -> None:
        if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            sys.stderr.write(f"[WebGL JS Error] {message} (line {line_id})\n")


SOLO_ACTIONS_INFO: dict[str, dict[str, str]] = {
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
      1. Floating SpeechBubbleWidget (top)
      2. Transparent QWebEngineView rendering Three.js Ppong-ppong-i (spans full window, zero clipping)
      3. Toggleable Dark-Mode ChatBarWidget (bottom)
      4. Autonomous Roaming State Machine + Global Cursor Head Tracking + QThread LLM Sync
    """

    WINDOW_W = 380
    WINDOW_H = 505
    VIEWPORT_RECT = QRect(0, 0, 380, 505)
    CHATBAR_RECT = QRect(12, 442, 356, 54)

    def __init__(self, asset_server: LocalAssetServer) -> None:
        super().__init__()
        self._asset_server = asset_server
        self._prefs = PetPreferences.load()
        self._llm_config = LLMConfig(
            api_url=self._prefs.llm_url,
            model=self._prefs.llm_model,
            api_key=self._prefs.llm_api_key,
        )
        self._conversation: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._active_worker: Optional[LLMWorker] = None
        self._web_ready = False

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
        self._walk_speed = 98.0   # px/s matched to 0.64s Walk stride at 66.5 deg yaw
        self._run_speed = 224.0   # px/s matched to 0.46s Run stride at 74.5 deg yaw
        self._sit_stand_pending = False
        self._last_tick_time = time.perf_counter()
        self._last_cursor_norm = (0.0, 0.0)

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

        # Special Active Actions Tracking State (Spider-Man, Peek, Heist, Doodle, Superman)
        self._spider_t = 0.0
        self._spider_dir = 1.0
        self._spider_start_x = 0.0
        self._spider_target_x = 0.0
        self._spider_floor_y = 0.0
        self._peek_depth = 0.0
        self._peek_revealed = False
        self._peek_normal_y = 0.0
        self._heist_progress = 0.0
        self._heist_dir = 1.0
        self._doodle_shape = "heart"
        self._doodle_progress = 0.0
        self._doodle_timer = 0.0
        self._doodle_proud_triggered = False
        self._superman_progress = 0.0
        self._superman_start_x = 0.0
        self._superman_target_x = 0.0
        self._superman_floor_y = 0.0
        self._last_gaze_weight = -1.0

        self._init_window_flags()
        self._init_widgets()
        self._init_timers()
        self._init_tray_icon()
        self._place_on_taskbar()

        # Intercept mouse events across QWebEngineView & its internal Chromium delegate child widgets
        QApplication.instance().installEventFilter(self)

    def _init_window_flags(self) -> None:
        self.setWindowTitle("Ppong-ppong-i")
        self.setFixedSize(self.WINDOW_W, self.WINDOW_H)
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
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

        page = SilentWebEnginePage(self.web_view)
        page.setBackgroundColor(Qt.GlobalColor.transparent)
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        self.web_view.setPage(page)

        self.web_view.loadFinished.connect(self._on_web_loaded)
        self.web_view.setUrl(QUrl(self._asset_server.index_url))

        # 2. Floating Speech Bubble above Ppong-ppong-i
        self.speech_bubble = SpeechBubbleWidget(central)
        self.speech_bubble.raise_()

        # 3. Top-Level Executive AI Chat & History Drawer (Floats on top, zero occlusion by 3D canvas)
        self.chat_window = FloatingChatWindow()
        self.chat_bar = self.chat_window  # Backward-compatible alias for visibility/busy checks
        self.chat_window.message_submitted.connect(self._on_user_chat_submitted)
        self.chat_window.settings_requested.connect(self._open_llm_settings)
        self.chat_window.mail_requested.connect(self.toggle_outlook_hud)
        self.chat_window.alarm_requested.connect(self.open_alarm_manager)
        self.chat_window.cleanup_requested.connect(lambda: self.run_pc_cleanup(True))

        # Outlook AI Service & HUD Drawer
        self.outlook_service = OutlookAIAssistantService(self)
        self.outlook_hud = OutlookHUDDrawer(self.outlook_service)
        self.outlook_service.new_urgent_mail_received.connect(self._on_urgent_mail_received)

        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(QApplication.instance().quit)

        # Hotkey Ctrl+M to toggle Outlook AI Mail Hub
        mail_shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        mail_shortcut.activated.connect(self.toggle_outlook_hud)

        # Hotkeys for character scaling: Ctrl+= / Ctrl++ (zoom in), Ctrl+- (zoom out), Ctrl+0 (reset)
        zoom_in_1 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_in_1.activated.connect(lambda: self.set_scale_factor(self._scale_factor + 0.10))
        zoom_in_2 = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in_2.activated.connect(lambda: self.set_scale_factor(self._scale_factor + 0.10))
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_out.activated.connect(lambda: self.set_scale_factor(self._scale_factor - 0.10))
        zoom_reset = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_reset.activated.connect(lambda: self.set_scale_factor(1.0))

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
        heist_shortcut.activated.connect(self.start_window_heist)

        doodle_shortcut = QShortcut(QKeySequence("Ctrl+4"), self)
        doodle_shortcut.activated.connect(lambda: self.start_magic_doodle())

        super_shortcut = QShortcut(QKeySequence("Ctrl+5"), self)
        super_shortcut.activated.connect(self.start_superman_fly)

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

    def _init_timers(self) -> None:
        # 60 FPS movement & gravity physics tick
        self._roam_tick_timer = QTimer(self)
        self._roam_tick_timer.setInterval(16)
        self._roam_tick_timer.timeout.connect(self._on_roam_tick)
        self._roam_tick_timer.start()

        # Active "Bout-and-Pause" autonomous FSM decision timer (1.8s - 3.6s lively cadence)
        self._decision_timer = QTimer(self)
        self._decision_timer.setSingleShot(True)
        self._decision_timer.timeout.connect(self._decide_next_autonomous_state)
        self._schedule_next_decision(2600, 3800)

        # Disambiguates single-left-click tactile poke from double-click chat toggle
        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.setInterval(190)
        self._single_click_timer.timeout.connect(self._on_single_click_poke)

        # 30 FPS global Windows cursor tracker + head-petting & curiosity detector
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(33)
        self._cursor_timer.timeout.connect(self._sync_global_cursor_to_3d)
        self._cursor_timer.start()

    def _init_tray_icon(self) -> None:
        self.tray_icon: Optional[QSystemTrayIcon] = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon = _create_unicorn_tray_icon()
        self.setWindowIcon(icon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Ppong-ppong-i — 3D Desktop AI Pet")

        menu = QMenu()
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_BORDER};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: #1d4ed8;
            }}
            """
        )

        act_chat = QAction("Toggle Chat Bar (더블클릭)", self)
        act_chat.triggered.connect(self.on_pet_activated)

        act_mail = QAction("Outlook AI Mail Hub (메일 AI 비서 ✉️ / Ctrl+M)", self)
        act_mail.triggered.connect(self.toggle_outlook_hud)

        act_mail_check = QAction("Check Mail Now (새 메일 확인 & AI 요약)", self)
        act_mail_check.triggered.connect(self.check_mail_now)

        act_snack = QAction("Feed Rainbow Treat 🍬 (F)", self)
        act_snack.triggered.connect(self.feed_snack)

        # 1. Pet Size Scaling Submenu (supports down to 35% micro size!)
        size_menu = QMenu("Pet Size (크기 조절)", menu)
        size_menu.setStyleSheet(menu.styleSheet())
        for pct, scale_val in [
            ("35%  (Micro / 초미니 🔍)", 0.35),
            ("50%  (Mini / 미니)", 0.50),
            ("65%  (Compact / 소형)", 0.65),
            ("75%  (Small / 축소)", 0.75),
            ("90%  (Medium Small)", 0.90),
            ("100% (Default / 기본)", 1.00),
            ("120% (Medium Large)", 1.20),
            ("140% (Large / 대형)", 1.40),
            ("160% (Giant / 특대)", 1.60),
        ]:
            act_s = QAction(pct, self)
            act_s.triggered.connect(lambda _checked, s=scale_val: self.set_scale_factor(s))
            size_menu.addAction(act_s)
        size_menu.addSeparator()
        act_reset_scale = QAction("Reset Scale (100% / Ctrl+0)", self)
        act_reset_scale.triggered.connect(lambda: self.set_scale_factor(1.00))
        size_menu.addAction(act_reset_scale)

        # 2. 10 Canonical Emotions Submenu
        emotion_menu = QMenu("10 Emotions (10가지 감정)", menu)
        emotion_menu.setStyleSheet(menu.styleSheet())
        emotions_display = [
            ("1. Happy / 행복 (기쁨)", "happy"),
            ("2. Excited / 신남 (열정)", "excited"),
            ("3. Curious / 호기심 (궁금)", "curious"),
            ("4. Sleepy / 졸림 (나른함)", "sleepy"),
            ("5. Shy / 수줍음 (부끄러움)", "shy"),
            ("6. Surprised / 놀람 (깜짝)", "surprised"),
            ("7. Pouty / 뾰로통 (토라짐)", "pouty"),
            ("8. Loving / 사랑 (애정)", "loving"),
            ("9. Sad / 슬픔 (시무룩)", "sad"),
            ("10. Proud / 뿌듯 (자신감)", "proud"),
        ]
        for label, em_key in emotions_display:
            act_em = QAction(label, self)
            act_em.triggered.connect(lambda _checked, k=em_key: self.trigger_emotion(k))
            emotion_menu.addAction(act_em)

        # 3. 21 3D Actions Submenu
        action_menu = QMenu("21 3D Actions (21가지 액션)", menu)
        action_menu.setStyleSheet(menu.styleSheet())
        actions_list = [
            ("Wave (손흔들기)", "Wave", 0),
            ("Jump (점프 환호)", "Jump", 0),
            ("HappySpin (회전 댄스)", "HappySpin", 0),
            ("Dance (리듬 댄스)", "Dance", 3200),
            ("Curious (고개 갸웃)", "Curious", 0),
            ("Stretch (기지개)", "Stretch", 0),
            ("Sit (얌전히 앉기)", "Sit", 0),
            ("Walk (당당한 걷기)", "Walk", 0),
            ("Run (신나는 달리기)", "Run", 0),
            ("Poke (찌르기 반응)", "Poke", 0),
            ("Pet (쓰다듬기 골골)", "Pet", 0),
            ("DropLand (착지 쿠션)", "DropLand", 0),
            ("Sleepy (하품 졸음)", "Sleepy", 3500),
            ("Shy (수줍은 꼼지락)", "Shy", 3400),
            ("Pout (뾰로통 토라짐)", "Pout", 3400),
            ("Love (하트 뿜뿜)", "Love", 3500),
            ("Sad (훌쩍 시무룩)", "Sad", 3400),
            ("Proud (위풍당당 으쓱)", "Proud", 3400),
            ("Snack (간식 냠냠)", "Snack", 3600),
            ("Talk (쫑알쫑알)", "Talk", 3000),
            ("Idle (평화로운 대기)", "Idle", 0),
        ]
        for label, act_name, d_ms in actions_list:
            act_a = QAction(label, self)
            act_a.triggered.connect(lambda _checked, a=act_name, d=d_ms: self.trigger_3d_action(a, duration_ms=d))
            action_menu.addAction(act_a)

        # 4. Special Active Actions Submenu (Spider-Man, Hide&Seek, Heist, Doodle, Superman)
        special_menu = QMenu("Special Active Actions (특수 활동 액션 🎮)", menu)
        special_menu.setStyleSheet(menu.styleSheet())
        act_spider = QAction("🕷️ Spider-Ppong Web Swing (스파이더맨 스윙 / Ctrl+1)", self)
        act_spider.triggered.connect(self.start_spider_swing)
        act_hide = QAction("🙈 Hide-and-Seek & Peek (숨바꼭질 & 빼꼼 / Ctrl+2)", self)
        act_hide.triggered.connect(self.start_hide_and_seek)
        act_heist = QAction("🪟 Window Heist Prank (창 들고 도망가기 / Ctrl+3)", self)
        act_heist.triggered.connect(self.start_window_heist)
        act_doodle = QAction("🎨 Magic Rainbow Doodle (바탕화면 낙서 / Ctrl+4)", self)
        act_doodle.triggered.connect(lambda: self.start_magic_doodle())
        act_super = QAction("🚀 Superhero Flight (슈퍼맨 비행 / Ctrl+5)", self)
        act_super.triggered.connect(self.start_superman_fly)

        special_menu.addAction(act_spider)
        special_menu.addAction(act_hide)
        special_menu.addAction(act_heist)
        special_menu.addAction(act_doodle)
        special_menu.addAction(act_super)

        # 4.5. Solo Play Activities Submenu (30 Diverse Solo Activities)
        solo_menu = QMenu("Solo Play Activities (혼자 놀기 30종 🎪)", menu)
        solo_menu.setStyleSheet(menu.styleSheet())
        categories = ["모험 & 일상", "취미 & 예술", "직업 & 판타지", "스포츠 & 놀이", "힐링 & 특별"]
        for cat_name in categories:
            sub = QMenu(f"✨ {cat_name}", solo_menu)
            sub.setStyleSheet(menu.styleSheet())
            for key, val in SOLO_ACTIONS_INFO.items():
                if val["cat"] == cat_name:
                    act_item = QAction(val["title"], self)
                    act_item.triggered.connect(lambda _c, k=key: self.play_solo_action(k))
                    sub.addAction(act_item)
            solo_menu.addMenu(sub)

        # 5. Smart Alarm Manager Action
        act_alarm_mgr = QAction("⏰ Smart Alarm Manager (스마트 알람 관리자 / Ctrl+7)", self)
        act_alarm_mgr.triggered.connect(self.open_alarm_manager)

        # 6. Action Frequency & Feature Controls Submenu
        ctrl_menu = QMenu("Action Frequency & Controls (액션 빈도 & 설정 ⚙️)", menu)
        ctrl_menu.setStyleSheet(menu.styleSheet())

        freq_group = [
            ("⚡ Frequency: Frequent / 자주 (1~2분)", "frequent"),
            ("⏱️ Frequency: Normal / 보통 (3~5분)", "normal"),
            ("🐢 Frequency: Rare / 가끔 (8~10분)", "rare"),
            ("⏸️ Disable Autonomous Actions (자율 액션 끄기)", "off"),
        ]
        for f_label, f_key in freq_group:
            act_f = QAction(f_label, self)
            act_f.setCheckable(True)
            act_f.setChecked(self._prefs.action_frequency == f_key)
            act_f.triggered.connect(lambda _c, k=f_key: self.set_action_frequency(k))
            ctrl_menu.addAction(act_f)

        ctrl_menu.addSeparator()

        features = [
            ("🕷️ Enable Spider-Man Swings", "enable_spider"),
            ("🙈 Enable Hide-and-Seek Peek", "enable_peek"),
            ("🪟 Enable Window Heist Run", "enable_heist"),
            ("🎨 Enable Magic Neon Doodles", "enable_doodle"),
            ("🚀 Enable Superman Flight", "enable_superman"),
            ("🧹 Periodic PC Auto-Clean (45m)", "enable_pc_clean"),
        ]
        for feat_label, feat_attr in features:
            act_feat = QAction(feat_label, self)
            act_feat.setCheckable(True)
            act_feat.setChecked(getattr(self._prefs, feat_attr, True))
            act_feat.toggled.connect(lambda chk, a=feat_attr: self.toggle_action_feature(a, chk))
            ctrl_menu.addAction(act_feat)

        act_clean = QAction("🧹 PC Environment Clean-up (PC 환경 쾌적화 / Ctrl+6)", self)
        act_clean.triggered.connect(lambda: self.run_pc_cleanup(show_bubble=True))

        # Toggles
        self.act_always_on_top = QAction("Always on Top (항상 위에 표시 📌 / Ctrl+T)", self)
        self.act_always_on_top.setCheckable(True)
        self.act_always_on_top.setChecked(self._always_on_top)
        self.act_always_on_top.toggled.connect(self.set_always_on_top)

        act_gaze = QAction("Intermittent Mouse Gaze (간헐적 시선)", self)
        act_gaze.setCheckable(True)
        act_gaze.setChecked(self._intermittent_gaze_enabled)
        act_gaze.toggled.connect(self.set_intermittent_gaze_enabled)

        act_meadow = QAction("Grass Meadow & Footprints (풀밭 & 발자국)", self)
        act_meadow.setCheckable(True)
        act_meadow.setChecked(self._meadow_trail_enabled)
        act_meadow.toggled.connect(self.set_meadow_trail_enabled)

        act_gravity = QAction("Taskbar Gravity on Drop", self)
        act_gravity.setCheckable(True)
        act_gravity.setChecked(self._taskbar_gravity_enabled)
        act_gravity.toggled.connect(self._set_taskbar_gravity_enabled)

        act_settings = QAction("Local LLM Settings...", self)
        act_settings.triggered.connect(self._open_llm_settings)

        act_reload = QAction("Reload 3D View", self)
        act_reload.triggered.connect(self.web_view.reload)

        act_reset = QAction("Reset to Bottom Taskbar", self)
        act_reset.triggered.connect(self._place_on_taskbar)

        act_quit = QAction("Quit Ppong-ppong-i (Ctrl+Q)", self)
        act_quit.triggered.connect(QApplication.instance().quit)

        menu.addAction(act_chat)
        menu.addAction(act_mail)
        menu.addAction(act_mail_check)
        menu.addAction(act_snack)
        menu.addSeparator()
        menu.addMenu(size_menu)
        menu.addMenu(emotion_menu)
        menu.addMenu(action_menu)
        menu.addMenu(special_menu)
        menu.addMenu(solo_menu)
        menu.addAction(act_alarm_mgr)
        menu.addAction(act_clean)
        menu.addMenu(ctrl_menu)
        menu.addSeparator()
        menu.addAction(self.act_always_on_top)
        menu.addAction(act_gaze)
        menu.addAction(act_meadow)
        menu.addAction(act_gravity)
        menu.addSeparator()
        menu.addAction(act_settings)
        menu.addAction(act_reload)
        menu.addAction(act_reset)
        menu.addSeparator()
        menu.addAction(act_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _set_taskbar_gravity_enabled(self, enabled: bool) -> None:
        self._taskbar_gravity_enabled = bool(enabled)
        self._prefs.taskbar_gravity = self._taskbar_gravity_enabled
        self._prefs.save()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.on_pet_activated()

    def _current_available_geometry(self) -> QRect:
        center = self.frameGeometry().center()
        screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        return screen.availableGeometry()

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

    def set_always_on_top(self, enabled: bool) -> None:
        self._always_on_top = bool(enabled)
        self._prefs.always_on_top = self._always_on_top
        self._prefs.save()
        if hasattr(self, "act_always_on_top") and self.act_always_on_top.isChecked() != self._always_on_top:
            self.act_always_on_top.setChecked(self._always_on_top)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._always_on_top)
        self.show()
        if hasattr(self, "outlook_hud") and self.outlook_hud is not None:
            self.outlook_hud.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._always_on_top)
            if self.outlook_hud.isVisible():
                self.outlook_hud.show()
        msg = "항상 위에 표시 켜짐 📌" if self._always_on_top else "일반 창 모드로 전환 🪟"
        if not self.chat_bar.isVisible():
            self.speech_bubble.show_message(msg, duration_ms=1800)

    def set_action_frequency(self, freq: str) -> None:
        self._prefs.action_frequency = freq
        self._prefs.save()
        label_kr = {
            "frequent": "자주 (1~2분)",
            "normal": "보통 (3~5분)",
            "rare": "가끔 (8~10분)",
            "off": "자율 액션 끄기",
        }.get(freq, freq)
        self.speech_bubble.show_message(f"액션 빈도 설정: {label_kr} ⚙️", duration_ms=2200)

    def toggle_action_feature(self, feat_name: str, enabled: bool) -> None:
        setattr(self._prefs, feat_name, bool(enabled))
        self._prefs.save()
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

    def play_solo_action(self, action_key: str, custom_speech: Optional[str] = None) -> None:
        """Plays one of the 30 interactive Solo Play / Transformation activities with strict action mutex."""
        if action_key not in SOLO_ACTIONS_INFO:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._state = PetState.SOLO_PLAY
        self._set_3d_facing(0)
        info = SOLO_ACTIONS_INFO[action_key]
        self._run_js(f"typeof window.playSoloAction === 'function' && window.playSoloAction('{action_key}');")
        msg = custom_speech or info["speech"]
        self.speech_bubble.show_message(msg, duration_ms=4500)
        if hasattr(self, "chat_window"):
            self.chat_window.add_message("pet", f"[{info['title']}] {msg}", action_key)
        QTimer.singleShot(8500, self._on_solo_action_completed)

    def _on_solo_action_completed(self) -> None:
        if self._state == PetState.SOLO_PLAY:
            self._state = PetState.IDLE
            self._schedule_next_decision(2400, 4200)

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
        self.trigger_3d_action("Wave", emotion="excited")

    def set_scale_factor(self, scale: float, show_bubble: bool = True) -> None:
        self._scale_factor = round(max(0.30, min(1.80, float(scale))), 2)
        self._prefs.scale_factor = self._scale_factor
        self._prefs.save()
        self._run_js(
            f"typeof window.setScaleFactor === 'function' && "
            f"window.setScaleFactor({self._scale_factor:.2f});"
        )
        if show_bubble and not self.chat_bar.isVisible():
            self.speech_bubble.show_message(
                f"크기 조절: {int(self._scale_factor * 100)}% 🔍",
                duration_ms=1600,
            )

    def set_intermittent_gaze_enabled(self, enabled: bool) -> None:
        self._intermittent_gaze_enabled = bool(enabled)
        self._prefs.intermittent_gaze = self._intermittent_gaze_enabled
        self._prefs.save()
        if not self._intermittent_gaze_enabled:
            self._run_js(
                "typeof window.setGazeAttentionWeight === 'function' && "
                "window.setGazeAttentionWeight(1.0);"
            )

    def set_meadow_trail_enabled(self, enabled: bool) -> None:
        self._meadow_trail_enabled = bool(enabled)
        self._prefs.meadow_trail = self._meadow_trail_enabled
        self._prefs.save()
        self._run_js(
            f"typeof window.setMeadowTrailEnabled === 'function' && "
            f"window.setMeadowTrailEnabled({'true' if self._meadow_trail_enabled else 'false'});"
        )

    def feed_snack(self) -> None:
        self._last_user_activity_time = time.perf_counter()
        self._is_napping = False
        self._pause_autonomous_walk(play_idle=False)
        self._set_3d_facing(0)
        self.trigger_3d_action("Snack", duration_ms=3600, emotion="loving", speech_ms=3600)
        self.speech_bubble.show_message(
            "냠냠! 달콤한 무지개 솜사탕 간식 최고야~! 🍬🌈✨",
            duration_ms=3600,
        )
        self._schedule_next_decision(3600, 4800)

    def trigger_emotion(self, emotion_name: str) -> None:
        canonical = _normalize_emotion(emotion_name) or "happy"
        self._last_user_activity_time = time.perf_counter()
        self._is_napping = False
        self._pause_autonomous_walk(play_idle=False)
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
        self._run_js(
            f"typeof window.setFacingDirection === 'function' && "
            f"window.setFacingDirection({int(direction)});"
        )

    def _set_3d_drag_state(self, active: bool, vx: float = 0.0, vy: float = 0.0) -> None:
        self._run_js(
            f"typeof window.setDragState === 'function' && "
            f"window.setDragState({'true' if active else 'false'}, {vx:.3f}, {vy:.3f});"
        )

    def _set_3d_falling_state(self, active: bool, vy: float = 0.0) -> None:
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
            # Sync initial scale factor and meadow trail state
            self._run_js(
                f"typeof window.setScaleFactor === 'function' && "
                f"window.setScaleFactor({self._scale_factor:.2f});"
            )
            self._run_js(
                f"typeof window.setMeadowTrailEnabled === 'function' && "
                f"window.setMeadowTrailEnabled({'true' if self._meadow_trail_enabled else 'false'});"
            )
            QTimer.singleShot(
                520,
                lambda: (
                    self.trigger_3d_action("Wave", speech_ms=4200, emotion="happy"),
                    self.speech_bubble.show_message(
                        "안녕! 나는 뽕뽕이야! 10가지 감정과 풀밭 발자국, 휠 크기 조절까지 준비 완료! 🌈✨",
                        duration_ms=5200,
                    ),
                ),
            )

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
        if abs(nx - prev_x) > 0.008 or abs(ny - prev_y) > 0.008:
            self._last_cursor_norm = (nx, ny)
            self._run_js(
                f"typeof window.updateCursorTarget === 'function' && "
                f"window.updateCursorTarget({nx:.3f}, {ny:.3f});"
            )

        # Skip tactile hover detectors while dragging, falling, or awaiting LLM
        llm_busy = self._active_worker is not None and self._active_worker.isRunning()
        if self._is_dragging or self._left_pressed or self._state == PetState.FALLING or llm_busy:
            if self._state == PetState.PETTING:
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
    def _schedule_next_decision(self, min_ms: int = 1800, max_ms: int = 3600) -> None:
        self._decision_timer.start(random.randint(min_ms, max_ms))

    def _pause_autonomous_walk(self, play_idle: bool = True) -> None:
        self._sit_stand_pending = False
        if self._state in {PetState.WALK, PetState.RUN, PetState.SITTING}:
            self._state = PetState.IDLE
            self._set_3d_facing(0)
            if play_idle:
                self.trigger_3d_action("Idle")
        if not self._decision_timer.isActive():
            self._schedule_next_decision(2200, 3800)

    def _pick_bounded_target_x(self, min_x: float, max_x: float, min_dist: float, max_dist: float) -> float:
        dist = random.uniform(min_dist, max_dist)
        prefer_dir = 1.0 if random.random() < 0.5 else -1.0
        cand1 = self._pos_x + prefer_dir * dist
        cand2 = self._pos_x - prefer_dir * dist
        if min_x <= cand1 <= max_x:
            return cand1
        if min_x <= cand2 <= max_x:
            return cand2
        # Clamp toward whichever side has more room!
        room_right = max_x - self._pos_x
        room_left = self._pos_x - min_x
        if room_right >= room_left:
            return min(max_x, self._pos_x + max(90.0, min(dist, room_right)))
        return max(min_x, self._pos_x - max(90.0, min(dist, room_left)))

    def cancel_all_active_actions(self) -> None:
        """Cleanly stops and resets any currently running active action or solo activity, ensuring strict mutex."""
        self._run_js(
            "if (typeof window.setSpiderSwingState === 'function') window.setSpiderSwingState(false); "
            "if (typeof window.setWindowHeistState === 'function') window.setWindowHeistState(false); "
            "if (typeof window.setPeekState === 'function') window.setPeekState(false); "
            "if (typeof window.setMagicDoodleState === 'function') window.setMagicDoodleState(false); "
            "if (typeof window.setSupermanFlyState === 'function') window.setSupermanFlyState(false); "
            "if (typeof window.stopSoloAction === 'function') window.stopSoloAction();"
        )
        self._doodle_proud_triggered = False
        self._spider_current_swing = 1
        if self._active_worker is not None and self._active_worker.isRunning():
            try:
                self._active_worker.terminate()
            except Exception:
                pass
            self._active_worker = None
        self._state = PetState.IDLE
        avail = self._current_available_geometry()
        self._pos_y = self._taskbar_floor_y(avail)
        self._update_window_pos()
        self._set_3d_facing(0)
        self.trigger_3d_action("Idle")

    def is_action_busy(self) -> bool:
        """Returns True if the pet is currently executing an uninterruptible action or interaction."""
        return (
            self._is_dragging
            or self._left_pressed
            or self._state in {
                PetState.SPIDER_SWING,
                PetState.HIDE_AND_SEEK,
                PetState.WINDOW_HEIST,
                PetState.MAGIC_DOODLE,
                PetState.SUPERMAN_FLY,
                PetState.SOLO_PLAY,
                PetState.FALLING,
                PetState.PETTING,
                PetState.INTERACTING,
            }
            or (hasattr(self, "chat_window") and self.chat_window.isVisible())
            or (self._active_worker is not None and self._active_worker.isRunning())
        )

    def _decide_next_autonomous_state(self) -> None:
        if self.is_action_busy():
            if self._state in {PetState.WALK, PetState.RUN, PetState.SITTING}:
                self._pause_autonomous_walk()
            self._schedule_next_decision(3000, 5000)
            return

        # Stand up from cozy taskbar sit with a cute morning Stretch!
        if self._state == PetState.SITTING and self._sit_stand_pending:
            self._sit_stand_pending = False
            self._state = PetState.IDLE
            self._set_3d_facing(0)
            self.trigger_3d_action("Stretch")
            self._schedule_next_decision(2100, 3400)
            return

        avail = self._current_available_geometry()
        min_x = float(avail.left() + 16)
        max_x = float(max(avail.left() + 20, avail.right() - self.WINDOW_W - 16))
        roam_span = max_x - min_x
        roll = random.random()

        # 0. High-Energy Special Autonomous Actions (Respects Action Frequency & Controls)
        if self._prefs.action_frequency != "off":
            freq_mult = {"frequent": 2.2, "normal": 1.0, "rare": 0.35}.get(self._prefs.action_frequency, 1.0)
            threshold = 0.25 * freq_mult
            if roll < threshold:
                candidates = []
                if self._prefs.enable_spider and roam_span > 260:
                    candidates.append(self.start_spider_swing)
                if self._prefs.enable_peek:
                    candidates.append(self.start_hide_and_seek)
                if self._prefs.enable_heist and roam_span > 240:
                    candidates.append(self.start_window_heist)
                if self._prefs.enable_doodle:
                    candidates.append(self.start_magic_doodle)
                if self._prefs.enable_superman and roam_span > 260:
                    candidates.append(self.start_superman_fly)

                if candidates:
                    chosen = random.choice(candidates)
                    chosen()
                    return

        if roam_span > 140 and roll < 0.52:
            # 1. Brisk cute waddle Walk (capped 130 - 340 px bout!)
            self._walk_target_x = self._pick_bounded_target_x(min_x, max_x, 130.0, 340.0)
            direction = 1 if self._walk_target_x >= self._pos_x else -1
            self._state = PetState.WALK
            self._last_tick_time = time.perf_counter()
            self._set_3d_facing(direction)
            self.trigger_3d_action("Walk")
        elif roam_span > 240 and roll < 0.74:
            # 2. Energetic scamper Run (capped 260 - 560 px bout!)
            self._walk_target_x = self._pick_bounded_target_x(min_x, max_x, 260.0, 560.0)
            direction = 1 if self._walk_target_x >= self._pos_x else -1
            self._state = PetState.RUN
            self._last_tick_time = time.perf_counter()
            self._set_3d_facing(direction)
            self.trigger_3d_action("Run")
        elif roll < 0.92:
            # 3. Playful in-place game character expression or solo activity!
            self._state = PetState.IDLE
            self._set_3d_facing(0)
            if random.random() < 0.40:
                chosen_solo = random.choice(list(SOLO_ACTIONS_INFO.keys()))
                self.play_solo_action(chosen_solo)
                self._schedule_next_decision(4800, 6800)
            else:
                playful = random.choices(
                    ["Curious", "Dance", "HappySpin", "Wave", "Stretch"],
                    weights=[30, 25, 20, 15, 10],
                    k=1,
                )[0]
                dur_ms = 3040 if playful == "Dance" else 0
                self.trigger_3d_action(playful, duration_ms=dur_ms)
                self._schedule_next_decision(2200, 3800)
        else:
            # 4. Cozy taskbar Sit (chains into Stretch when standing back up!)
            self._state = PetState.SITTING
            self._sit_stand_pending = True
            self._set_3d_facing(0)
            self.trigger_3d_action("Sit")
            self._schedule_next_decision(4400, 6400)

    # -------------------------------------------------------------------------
    # Special High-Energy Interactive Actions
    # -------------------------------------------------------------------------
    @staticmethod
    def _get_active_window_title() -> str:
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, buf, 256)
                val = buf.value.strip()
                if val and val != "Ppong-ppong-i":
                    return val[:22]
        except Exception:
            pass
        return "내 컴퓨터"

    def start_spider_swing(self) -> None:
        """Shoots glowing web lines to screen edges/ceiling, chaining 2~5 acrobatic swings across desktop!"""
        if self._is_dragging or self._left_pressed:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        self._spider_total_swings = random.randint(2, 5)
        self._spider_current_swing = 1
        self._setup_spider_swing_segment()
        self._state = PetState.SPIDER_SWING
        self.trigger_3d_action("Jump")
        self.speech_bubble.show_message(
            f"쓩~! 🕸️ 스파이더 뽕뽕이 출동! (벽 타고 연속 {self._spider_total_swings}회 비행)",
            duration_ms=2800,
        )

    def _setup_spider_swing_segment(self) -> None:
        avail = self._current_available_geometry()
        floor_y = self._taskbar_floor_y(avail)
        self._spider_floor_y = floor_y
        self._spider_start_x = self._pos_x
        mid_x = (avail.left() + avail.right() - self.WINDOW_W) / 2.0

        if self._spider_current_swing == 1:
            self._spider_dir = 1.0 if self._pos_x < mid_x else -1.0
        else:
            if self._pos_x < avail.left() + 180:
                self._spider_dir = 1.0
            elif self._pos_x > avail.right() - self.WINDOW_W - 180:
                self._spider_dir = -1.0
            else:
                self._spider_dir = -self._spider_dir

        dist = random.uniform(320.0, 560.0)
        self._spider_target_x = max(
            float(avail.left() + 30),
            min(float(avail.right() - self.WINDOW_W - 30), self._spider_start_x + self._spider_dir * dist),
        )
        self._spider_t = 0.0
        self._set_3d_facing(int(self._spider_dir))

        # Anchor towards ceiling edge or side wall in Three.js coordinates
        self._spider_anchor_x = self._spider_dir * random.uniform(2.2, 3.2)
        self._spider_anchor_y = random.uniform(2.6, 3.2)

    def start_hide_and_seek(self) -> None:
        """Hides body behind the taskbar edge, peeking with eyes and horn until discovered!"""
        if self._is_dragging or self._left_pressed:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        avail = self._current_available_geometry()
        self._peek_normal_y = self._taskbar_floor_y(avail)
        self._pos_y = self._peek_normal_y
        self._peek_depth = 0.0
        self._peek_revealed = False
        self._state = PetState.HIDE_AND_SEEK
        self.speech_bubble.show_message("나 찾아봐라~ 3초 센다! 1, 2, 3... 쏙! 🙈", duration_ms=2600)
        self._schedule_next_decision(12000, 16000)

    def start_window_heist(self) -> None:
        """Playfully holds a holographic desktop window overhead and sprints across screen!"""
        if self._is_dragging or self._left_pressed:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        avail = self._current_available_geometry()
        mid_x = (avail.left() + avail.right() - self.WINDOW_W) / 2.0
        self._heist_dir = 1.0 if self._pos_x < mid_x else -1.0
        self._heist_progress = 0.0
        self._state = PetState.WINDOW_HEIST
        self._set_3d_facing(int(self._heist_dir))
        self.trigger_3d_action("Run")

        title = self._get_active_window_title()
        self._heist_title = title
        safe_title = title.replace("'", "\\'").replace('"', '\\"')
        self._run_js(f"typeof window.setWindowHeistState === 'function' && window.setWindowHeistState(true, '{safe_title} 🪟');")
        self.speech_bubble.show_message(f"헤헤! [{title}] 창은 뽕뽕이가 접수했다~! 잡아봐라~!! 🪟💨", duration_ms=3500)

    def start_magic_doodle(self, shape: Optional[str] = None) -> None:
        """Draws glowing grand neon graffiti (heart, star, smiley) reaching across the screen center!"""
        if self._is_dragging or self._left_pressed:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        shapes = ["heart", "star", "smile"]
        self._doodle_shape = shape if shape in shapes else random.choice(shapes)
        self._doodle_progress = 0.0
        self._doodle_timer = 0.0
        self._doodle_proud_triggered = False
        self._state = PetState.MAGIC_DOODLE
        self._set_3d_facing(0)
        self.trigger_3d_action("Dance")
        self.speech_bubble.show_message(f"바탕화면 한가운데에 대형 마법 {self._doodle_shape} 그리는 중... 🎨✨", duration_ms=2800)

    def start_superman_fly(self) -> None:
        """Launches into the sky: acrobatic wave flight, mouse cursor kidnap prank, or folder snatch!"""
        if self._is_dragging or self._left_pressed:
            return
        self.cancel_all_active_actions()
        self._decision_timer.stop()
        avail = self._current_available_geometry()
        floor_y = self._taskbar_floor_y(avail)
        self._superman_floor_y = floor_y
        self._superman_start_x = self._pos_x
        mid_x = (avail.left() + avail.right() - self.WINDOW_W) / 2.0
        self._superman_dir = 1.0 if self._pos_x < mid_x else -1.0
        flight_span = random.uniform(450.0, 750.0)
        self._superman_target_x = max(
            float(avail.left() + 40),
            min(float(avail.right() - self.WINDOW_W - 40), self._pos_x + self._superman_dir * flight_span),
        )
        self._superman_progress = 0.0
        self._superman_mode = random.choice([0, 1, 2])
        self._state = PetState.SUPERMAN_FLY
        self._set_3d_facing(int(self._superman_dir))
        self.trigger_3d_action("WaveJump")
        self._run_js(f"typeof window.setSupermanFlyState === 'function' && window.setSupermanFlyState(true, 0, {self._superman_mode});")
        if self._superman_mode == 1:
            self.speech_bubble.show_message("쓩~! 🚀 마우스 포인터 낚아채서 하늘로 도망간다~!! 🖱️✨", duration_ms=3200)
        elif self._superman_mode == 2:
            self.speech_bubble.show_message("쓩~! 🚀 중요 서류 파일 들고 성층권으로 날아간다~!! 📁💨", duration_ms=3200)
        else:
            self.speech_bubble.show_message("슈퍼맨 뽕뽕이 출동! 🚀 하늘에 무지개 궤적을 그리며 다방향 비행 중!", duration_ms=3200)

    def _on_roam_tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.05, now - self._last_tick_time)
        self._last_tick_time = now

        if self._is_dragging:
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

        # 2. Horizontal Zero-Slip Walk / Run Locomotion
        if self._state in {PetState.WALK, PetState.RUN} and not self.chat_bar.isVisible():
            was_running = self._state == PetState.RUN
            speed = self._run_speed if was_running else self._walk_speed
            diff = self._walk_target_x - self._pos_x
            step = speed * dt

            if abs(diff) <= step:
                self._pos_x = self._walk_target_x
                self._update_window_pos()
                self._state = PetState.IDLE
                self._set_3d_facing(0)

                # 40% Arrival Chaining: finish walk/run with a lively flourish!
                if random.random() < 0.42:
                    arrival_act = "HappySpin" if (was_running and random.random() < 0.45) else random.choice(["Curious", "Wave"])
                    self.trigger_3d_action(arrival_act)
                    self._schedule_next_decision(2000, 3500)
                else:
                    self.trigger_3d_action("Idle")
                    self._schedule_next_decision(1800, 3400)
            else:
                direction = 1.0 if diff > 0 else -1.0
                self._pos_x += direction * step
                self._update_window_pos()
            return

        # 3. Spider-Man Web Multi-Swings Across Screen Edges
        if self._state == PetState.SPIDER_SWING:
            self._spider_t += dt / 1.7
            t = min(1.0, self._spider_t)
            arc_y = math.sin(t * math.pi) * 380.0
            self._pos_y = self._spider_floor_y - arc_y
            self._pos_x = self._spider_start_x + (self._spider_target_x - self._spider_start_x) * t
            self._update_window_pos()
            self._run_js(
                f"typeof window.setSpiderSwingState === 'function' && "
                f"window.setSpiderSwingState(true, {t:.3f}, {self._spider_dir:.1f}, {self._spider_anchor_x:.2f}, {self._spider_anchor_y:.2f});"
            )
            if t >= 1.0:
                if self._spider_current_swing < self._spider_total_swings:
                    # Mid-air flip and chain into next swing!
                    self._spider_current_swing += 1
                    self.trigger_3d_action("HappySpin")
                    self.speech_bubble.show_message(
                        f"슉! 🕸️ 벽 차고 {self._spider_current_swing}단 거미줄 발사!!",
                        duration_ms=2000,
                    )
                    self._setup_spider_swing_segment()
                else:
                    self._state = PetState.IDLE
                    self._pos_y = self._spider_floor_y
                    self._update_window_pos()
                    self._run_js("typeof window.setSpiderSwingState === 'function' && window.setSpiderSwingState(false);")
                    self.trigger_3d_action("DropLand")
                    self.speech_bubble.show_message(
                        f"연속 {self._spider_total_swings}단 스파이더 비행 완벽 착지! 🦸‍♂️✨ 멋있었죠?",
                        duration_ms=2800,
                    )
                    self._schedule_next_decision(2200, 3800)
            return

        # 4. Hide-and-Seek / Peekaboo Behind Windows & Taskbar
        if self._state == PetState.HIDE_AND_SEEK:
            if not self._peek_revealed:
                if self._peek_depth < 1.0:
                    self._peek_depth = min(1.0, self._peek_depth + dt * 1.6)
                    self._pos_y = self._peek_normal_y + self._peek_depth * 135.0
                    self._update_window_pos()
                    self._run_js(f"typeof window.setPeekState === 'function' && window.setPeekState(true, {self._peek_depth:.3f});")

                cursor = QCursor.pos()
                head_c = self.frameGeometry().center()
                dx = cursor.x() - head_c.x()
                dy = cursor.y() - head_c.y()
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < 145.0:
                    self._peek_revealed = True
                    self._peek_depth = 0.0
                    self._pos_y = self._peek_normal_y
                    self._update_window_pos()
                    self._run_js("typeof window.setPeekState === 'function' && window.setPeekState(false);")
                    self.trigger_3d_action("Jump", emotion="excited")
                    self.speech_bubble.show_message("까꿍! 🙈🎉 들켰다~ 어떻게 찾았지?!", duration_ms=3200)
                    self._state = PetState.IDLE
                    self._schedule_next_decision(2400, 4200)
            return

        # 5. Window Heist / Prank Sprint Running Overhead
        if self._state == PetState.WINDOW_HEIST:
            self._heist_progress += dt * 0.4
            step = 260.0 * dt * self._heist_dir
            self._pos_x += step
            avail = self._current_available_geometry()
            if self._pos_x < avail.left() + 20:
                self._pos_x = avail.left() + 20
                self._heist_dir = 1.0
                self._set_3d_facing(1)
            elif self._pos_x > avail.right() - self.WINDOW_W - 20:
                self._pos_x = avail.right() - self.WINDOW_W - 20
                self._heist_dir = -1.0
                self._set_3d_facing(-1)
            self._update_window_pos()

            cursor = QCursor.pos()
            pet_c = self.frameGeometry().center()
            if (cursor - pet_c).manhattanLength() < 150 or self._heist_progress >= 1.0:
                self._state = PetState.IDLE
                self._run_js("typeof window.setWindowHeistState === 'function' && window.setWindowHeistState(false);")
                self.trigger_3d_action("Shy", emotion="shy")
                title = getattr(self, "_heist_title", "작업창")
                self.speech_bubble.show_message(f"헉 들켰다! 헤헤 장난이었어요~ [{title}] 창 다시 제자리에 둘게요! 🪟💖", duration_ms=3200)
                self._set_3d_facing(0)
                self._schedule_next_decision(2200, 3600)
            return

        # 6. Magic Rainbow Graffiti / Doodling
        if self._state == PetState.MAGIC_DOODLE:
            self._doodle_progress = min(1.0, self._doodle_progress + dt / 2.0)
            self._run_js(f"typeof window.setMagicDoodleState === 'function' && window.setMagicDoodleState(true, '{self._doodle_shape}', {self._doodle_progress:.3f});")
            if self._doodle_progress >= 1.0:
                self._doodle_timer += dt
                if self._doodle_timer > 0.05 and not getattr(self, "_doodle_proud_triggered", False):
                    self._doodle_proud_triggered = True
                    self.trigger_3d_action("Proud", emotion="proud")
                    self.speech_bubble.show_message(f"짜잔! 🎨 화면 한가운데에 그린 대형 마법 {self._doodle_shape} 그림이에요! 멋지죠? ✨", duration_ms=4000)
                if self._doodle_timer >= 4.0:
                    self._state = PetState.IDLE
                    self._run_js("typeof window.setMagicDoodleState === 'function' && window.setMagicDoodleState(false);")
                    self._schedule_next_decision(2200, 3800)
            return

        # 7. Superman Multi-Directional Flight & Prank
        if self._state == PetState.SUPERMAN_FLY:
            self._superman_progress += dt / 3.4
            p = min(1.0, self._superman_progress)
            avail = self._current_available_geometry()
            sky_y = float(avail.top() + 80)
            floor_y = self._superman_floor_y

            # Multi-directional curved trajectory
            if p < 0.25:
                u = p / 0.25
                self._pos_y = floor_y - (floor_y - sky_y) * (u * u)
            elif p < 0.75:
                u = (p - 0.25) / 0.50
                # Wave swoop & loop
                wave = math.sin(u * math.pi * 4) * 45.0
                self._pos_y = sky_y + wave
                self._pos_x = self._superman_start_x + (self._superman_target_x - self._superman_start_x) * u
            else:
                u = (p - 0.75) / 0.25
                self._pos_y = sky_y + (floor_y - sky_y) * (u * u)

            self._update_window_pos()
            self._run_js(f"typeof window.setSupermanFlyState === 'function' && window.setSupermanFlyState(true, {p:.3f}, {self._superman_mode});")
            if p >= 1.0:
                self._state = PetState.IDLE
                self._pos_y = floor_y
                self._update_window_pos()
                self._run_js("typeof window.setSupermanFlyState === 'function' && window.setSupermanFlyState(false);")
                self.trigger_3d_action("DropLand")
                if self._superman_mode == 1:
                    self.speech_bubble.show_message("히히! 낚아챈 마우스 포인터 안전하게 돌려드렸어요~ 🖱️💖", duration_ms=3000)
                elif self._superman_mode == 2:
                    self.speech_bubble.show_message("서류 배달 완료! 📁 우주 구경 잘 하고 왔어요~!", duration_ms=3000)
                else:
                    self.speech_bubble.show_message("초음속 다방향 비행 완료! 🚀 하늘 위 공기가 정말 상쾌해요!", duration_ms=3000)
                self._schedule_next_decision(2200, 3800)
            return

    # -------------------------------------------------------------------------
    # Tactile Mouse Interactions (3-Zone Poke, Drag + Gravity, Dbl/Right Chat)
    # -------------------------------------------------------------------------
    def _on_single_click_poke(self) -> None:
        if self._is_dragging or self._left_pressed:
            return
        rel_x, rel_y = self._pending_poke_rel
        # Ignore clicks far outside the 3D character silhouette margins
        if not (0.16 <= rel_x <= 0.84 and 0.04 <= rel_y <= 0.96):
            return

        self._pause_autonomous_walk(play_idle=False)
        self._set_3d_facing(0)

        now = time.perf_counter()
        show_bubble = (not self.chat_bar.isVisible()) and (now - self._last_poke_bubble_time >= 2.6)

        if rel_y < 0.30:
            self._trigger_3d_poke("horn")
            if show_bubble:
                self._last_poke_bubble_time = now
                self.speech_bubble.show_message("뿅! 무지개 뿔 마법 충전 완료~! 🌈✨", duration_ms=2600)
        elif rel_y < 0.58:
            self._trigger_3d_poke("face")
            if show_bubble:
                self._last_poke_bubble_time = now
                self.speech_bubble.show_message("헤헤, 말랑한 모찌 볼 콕 찔렀지?! 😆💕", duration_ms=2600)
        else:
            if random.random() < 0.45:
                self.trigger_3d_action("Dance", duration_ms=2600, emotion="excited")
            else:
                self._trigger_3d_poke("belly")
            if show_bubble:
                self._last_poke_bubble_time = now
                self.speech_bubble.show_message("까르르! 배 간지러워요~! 🦄🎵", duration_ms=2600)

        self._schedule_next_decision(2200, 3800)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QWidget) and (
            watched is self.web_view or self.web_view.isAncestorOf(watched)
        ):
            etype = event.type()

            if etype == QEvent.Type.ContextMenu:
                return True  # Suppress Chromium default context menu

            if etype == QEvent.Type.Wheel:
                # Character scaling with mouse wheel over pet
                self._last_user_activity_time = time.perf_counter()
                delta_y = event.angleDelta().y()
                if delta_y != 0:
                    step = 0.05 if delta_y > 0 else -0.05
                    self.set_scale_factor(self._scale_factor + step)
                    return True

            if etype == QEvent.Type.MouseButtonPress:
                self._last_user_activity_time = time.perf_counter()
                if self._is_napping:
                    self._is_napping = False
                    self.trigger_3d_action("Stretch", emotion="happy")
                btn = event.button()
                if btn == Qt.MouseButton.LeftButton:
                    self._left_pressed = True
                    self._is_dragging = False
                    self._drag_vel_px = (0.0, 0.0)
                    self._drag_start_global = event.globalPosition().toPoint()
                    self._drag_last_global = self._drag_start_global
                    self._drag_last_time = time.perf_counter()
                    self._window_start_pos = self.frameGeometry().topLeft()

                    vp_pt = self.web_view.mapFromGlobal(self._drag_start_global)
                    rx = max(0.0, min(1.0, vp_pt.x() / max(1, self.VIEWPORT_RECT.width())))
                    ry = max(0.0, min(1.0, vp_pt.y() / max(1, self.VIEWPORT_RECT.height())))
                    self._pending_poke_rel = (rx, ry)
                    return False
                if btn == Qt.MouseButton.RightButton:
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
                        self._is_dragging = True
                        self._single_click_timer.stop()
                        if self._state == PetState.PETTING:
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
                        # Candidate single-click tactile poke (waits 190ms in case of double-click)
                        self._single_click_timer.start()
                        return False
                elif btn == Qt.MouseButton.RightButton:
                    self._single_click_timer.stop()
                    self.on_pet_activated()
                    return True

            elif etype == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._single_click_timer.stop()
                    self._left_pressed = False
                    if self._is_dragging:
                        self._is_dragging = False
                        self._set_3d_drag_state(False, 0.0, 0.0)
                    self.on_pet_activated()
                    return True

        return super().eventFilter(watched, event)

    def on_pet_activated(self) -> None:
        """Triggered on double-left-click or right-click: plays Wave/Jump & toggles chat bar."""
        self._single_click_timer.stop()
        if self._state == PetState.PETTING:
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
        self.chat_window.show_beside_pet(self.frameGeometry())

    def _hide_chat_bar(self) -> None:
        self.chat_window.hide()
        self._schedule_next_decision(2000, 3600)

    # -------------------------------------------------------------------------
    # Local LLM Conversation Flow & Decoupled Lip-Sync / Emotion-Motion Sync
    # -------------------------------------------------------------------------
    def _open_llm_settings(self) -> None:
        dlg = LLMSettingsDialog(self._llm_config, self)
        dlg.exec()

    def _on_user_chat_submitted(self, user_text: str) -> None:
        if self._active_worker is not None and self._active_worker.isRunning():
            return

        self._pause_autonomous_walk(play_idle=False)
        self._state = PetState.INTERACTING
        self._set_3d_facing(0)

        text_clean = str(user_text or "").lower().strip()

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

        # 0.2. 30 Spectacular Solo Play Activities Natural Language Parsing
        solo_keyword_map = [
            ("build_house", ["집 지어", "집짓기", "블록", "망치"]),
            ("fishing", ["낚시", "물고기", "월척"]),
            ("hunting", ["사냥", "곤충", "채집", "나비 잡"]),
            ("explorer", ["탐험", "쌍안경", "나침반", "대륙"]),
            ("camping", ["캠핑", "모닥불", "마시멜로", "불멍"]),
            ("drinking", ["건배", "맥주", "술", "음료", "짠해", "치어스"]),
            ("cooking", ["요리", "팬케이크", "뒤집기", "쉐프"]),
            ("gardening", ["정원", "물 줘", "꽃 심", "원예"]),
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

        # Natural Language Active Action Commands (Spider-Man, Peek, Heist, Doodle, Superman)
        if any(w in text_clean for w in ["스파이더", "거미줄", "스윙", "spider"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "쓩~! 🕸️ 스파이더 뽕뽕이 출동! 벽을 타고 비행합니다!", "spider")
            self.start_spider_swing()
            return
        elif any(w in text_clean for w in ["숨바꼭질", "숨어", "빼꼼", "까꿍", "hide"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "나 찾아봐라~ 3초 센다! 1, 2, 3... 쏙! 🙈", "hide")
            self.start_hide_and_seek()
            return
        elif any(w in text_clean for w in ["창 훔쳐", "창 들고", "도망", "잡아봐", "heist"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "헤헤! 작업창 들고 달립니다~! 잡아봐라~!! 🪟💨", "heist")
            self.start_window_heist()
            return
        elif any(w in text_clean for w in ["낙서", "그림", "하트", "별", "doodle"]):
            self.chat_bar.set_busy(False)
            shape = "heart" if "하트" in text_clean else ("star" if "별" in text_clean else "smile")
            self.chat_window.add_message("pet", f"화면 한가운데에 대형 마법 {shape} 그리는 중... 🎨✨", "doodle")
            self.start_magic_doodle(shape)
            return
        elif any(w in text_clean for w in ["슈퍼맨", "하늘", "날아", "비행", "fly", "rocket"]):
            self.chat_bar.set_busy(False)
            self.chat_window.add_message("pet", "슈퍼맨 뽕뽕이 출동! 🚀 하늘 위로 날아갑니다!", "superman")
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
        if hasattr(self, "chat_window"):
            self.chat_window.close()
        if hasattr(self, "outlook_hud"):
            self.outlook_hud.close()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        if self._active_worker is not None and self._active_worker.isRunning():
            self._active_worker.wait(1500)
        self._asset_server.stop()
        super().closeEvent(event)


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    import traceback
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        log_path = APP_DIR / "crash_error.log"
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
    app.setApplicationName("Ppong-ppong-i Desktop Pet")
    app.setQuitOnLastWindowClosed(False)

    asset_server = LocalAssetServer(APP_DIR)
    asset_server.start()

    window = DesktopPetWindow(asset_server)
    window.show()

    def _cleanup() -> None:
        if window.tray_icon is not None:
            window.tray_icon.hide()
        asset_server.stop()

    app.aboutToQuit.connect(_cleanup)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

