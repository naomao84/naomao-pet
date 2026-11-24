#!/usr/bin/env python3
"""
Workday Stone Cairn Companion v3 (출근 ~ 17:00 퇴근 동반 돌탑 미니게임)
======================================================================
Persists daily office companion progress in `pet_workday_cairn.json`, renders a
sculpted 9-layer Zen stone cairn with a Cupertino / Material Dark-Glass + Neumorphic
progress capsule above the bottom-right Windows taskbar, and runs a 6-phase workday
companion scenario (출근 체크인 -> 오전 집중 -> 점심 응원 -> 오후 협업 -> 퇴근 카운트다운 -> 17:00 칼퇴근 완공 세레머니).
"""

from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import (
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

# Natural Zen river-stone mineral palettes (matte light crest, midtone, shadow base, rim contour)
STONE_PALETTES: list[tuple[str, str, str, str]] = [
    ("#cbd5e1", "#8896a6", "#475569", "#1e293b"),  # Weathered Granite
    ("#94a3b8", "#64748b", "#334155", "#0f172a"),  # River Slate
    ("#a7f3d0", "#5f9ea0", "#2f5e4b", "#163026"),  # Nephrite Jade
    ("#e7d3b0", "#bfa074", "#856844", "#4a3723"),  # Warm Sandstone
    ("#e2afa0", "#b57056", "#7c4431", "#462317"),  # Terracotta Clay
    ("#fde68a", "#c49d56", "#856429", "#4b3612"),  # Ochre Riverstone
    ("#9ca3af", "#5b6370", "#2d333d", "#14181f"),  # Charcoal Basalt
    ("#e5c6ce", "#b88c96", "#7d5560", "#492e36"),  # Muted Rose Quartz
]
CAPSTONE_PALETTE = ("#fef9c3", "#eab308", "#a16207", "#713f12")  # Golden Summit Capstone

# 6-Phase Office Workday Timeline Specs
WORKDAY_PHASES: list[dict[str, Any]] = [
    {
        "key": "clock_in",
        "badge": "🌅 출근 체크인",
        "accent": "#38BDF8",
        "quote": "오늘 하루도 힘차게 출근 도장 꾹! 첫 주춧돌부터 함께 쌓아요 ☕",
    },
    {
        "key": "morning_focus",
        "badge": "💻 오전 집중",
        "accent": "#34D399",
        "quote": "타이핑 리듬 최고! 오전 집중 시간 동안 뽕뽕이와 트리가 돌을 모아요 ⛏️",
    },
    {
        "key": "lunch_break",
        "badge": "🍱 점심 충전",
        "accent": "#FBBF24",
        "quote": "맛있는 점심 드시고 에너지 충전하세요! 돌탑은 저희가 지켜둘게요 🍀",
    },
    {
        "key": "afternoon_coop",
        "badge": "☕ 오후 협업",
        "accent": "#818CF8",
        "quote": "나른한 오후엔 기지개 쭉~! 차곡차곡 올라가는 돌탑만큼 퇴근이 가까워져요 ✨",
    },
    {
        "key": "final_spurt",
        "badge": "🔥 퇴근 스퍼트",
        "accent": "#FB923C",
        "quote": "오후 5시 칼퇴근이 눈앞이에요! 마지막 정상석을 향해 라스트 스퍼트! 🚀",
    },
    {
        "key": "clock_out",
        "badge": "🎉 칼퇴근 완공",
        "accent": "#FDE047",
        "quote": "오늘 업무도 완벽 완주! 황금 정상석이 빛나니 기분 좋게 퇴근하세요! 🌅",
    },
]


def get_workday_phase_info(now_dt: Optional[datetime] = None, completed: bool = False) -> dict[str, Any]:
    """Resolves the active office workday companion phase from wall-clock time & completion state."""
    if completed:
        return WORKDAY_PHASES[5]
    dt = now_dt or datetime.now()
    hm = dt.hour * 60 + dt.minute
    if hm < (9 * 60 + 30):
        return WORKDAY_PHASES[0]
    if hm < (11 * 60 + 50):
        return WORKDAY_PHASES[1]
    if hm < (13 * 60 + 10):
        return WORKDAY_PHASES[2]
    if hm < (15 * 60 + 30):
        return WORKDAY_PHASES[3]
    if hm < (17 * 60):
        return WORKDAY_PHASES[4]
    return WORKDAY_PHASES[4]


def _build_river_stone_path(w: float, h: float, seed: int = 0) -> QPainterPath:
    """Builds an asymmetric, organically tapered river-stone silhouette (wider stable base)."""
    rng = random.Random(seed * 977 + 13)
    hw = w * 0.50
    hh = h * 0.50
    lx = -hw * rng.uniform(0.95, 1.03)
    rx = hw * rng.uniform(0.95, 1.03)
    top_peak_x = hw * rng.uniform(-0.18, 0.18)
    top_y = -hh * rng.uniform(0.94, 1.04)
    bot_y = hh * rng.uniform(0.94, 1.02)
    mid_y = hh * rng.uniform(0.06, 0.22)

    p = QPainterPath()
    p.moveTo(lx * 0.68, bot_y)
    p.cubicTo(lx * 1.06, bot_y * 0.96, lx * 1.08, mid_y, lx * 0.88, top_y * 0.52)
    p.cubicTo(lx * 0.62, top_y * 0.98, top_peak_x - hw * 0.22, top_y, top_peak_x, top_y)
    p.cubicTo(top_peak_x + hw * 0.24, top_y, rx * 0.66, top_y * 0.96, rx * 0.88, top_y * 0.50)
    p.cubicTo(rx * 1.08, mid_y, rx * 1.05, bot_y * 0.96, rx * 0.68, bot_y)
    p.cubicTo(hw * 0.28, bot_y * 1.04, -hw * 0.28, bot_y * 1.04, lx * 0.68, bot_y)
    p.closeSubpath()
    return p


def _draw_mineral_grain_and_highlight(painter: QPainter, path: QPainterPath, w: float, h: float, seed: int) -> None:
    """Adds a soft matte crest sheen, bottom ambient rim, and natural mineral speckles inside the stone clip."""
    painter.save()
    painter.setClipPath(path)
    painter.setPen(Qt.PenStyle.NoPen)

    # Top-left diffused specular highlight
    painter.setBrush(QColor(255, 255, 255, 48))
    painter.drawEllipse(QPointF(-w * 0.14, -h * 0.21), w * 0.26, h * 0.15)

    # Subtle lower-half core shadow band for sculpted 3D volume
    painter.setBrush(QColor(2, 6, 23, 38))
    painter.drawEllipse(QPointF(w * 0.06, h * 0.34), w * 0.46, h * 0.22)

    rng = random.Random(seed * 313 + 7)
    for k in range(4):
        fx = rng.uniform(-w * 0.30, w * 0.30)
        fy = rng.uniform(-h * 0.18, h * 0.24)
        fr = rng.uniform(0.7, 1.35)
        alpha = 46 if k % 2 == 0 else 32
        col = QColor(255, 255, 255, alpha) if k % 2 == 0 else QColor(15, 23, 42, alpha)
        painter.setBrush(col)
        painter.drawEllipse(QPointF(fx, fy), fr * 1.2, fr)
    painter.restore()


def _today_str(now_dt: Optional[datetime] = None) -> str:
    return (now_dt or datetime.now()).strftime("%Y-%m-%d")


class WorkdayCairnState:
    """Tracks and persists today's 9-layer x 10-stone workday cairn (90 stones across 08:00~17:00) + office metrics."""

    def __init__(
        self,
        data_dir: Path,
        target_layers: int = 9,
        stones_per_layer: int = 10,
        start_hour: int = 8,
        start_minute: int = 0,
        target_hour: int = 17,
        target_minute: int = 0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.save_path = self.data_dir / "pet_workday_cairn.json"
        self.schema_version: int = 3
        self.target_layers = max(1, int(target_layers))
        self.stones_per_layer = max(2, int(stones_per_layer))
        self.target_stones = self.target_layers * self.stones_per_layer
        self.start_hour = int(start_hour)
        self.start_minute = int(start_minute)
        self.target_hour = int(target_hour)
        self.target_minute = int(target_minute)

        now_dt = datetime.now()
        self.date: str = _today_str(now_dt)
        self.clock_in_time: str = now_dt.strftime("%H:%M")
        self.streak_days: int = 1
        self.last_completed_date: str = ""
        self.stones_placed: int = 0
        self.ppong_stones: int = 0
        self.tree_stones: int = 0
        self.layers: list[dict[str, Any]] = []
        self.current_layer_pebbles: list[dict[str, Any]] = []
        self.announced_phases: list[str] = []
        self.completed_today: bool = False
        self.clocked_out_today: bool = False
        self.bonus_claimed_today: bool = False
        self.load()

    @property
    def completed_layers(self) -> int:
        return min(self.target_layers, self.stones_placed // self.stones_per_layer)

    @property
    def current_layer_idx(self) -> int:
        return min(self.target_layers, self.completed_layers + 1)

    @property
    def current_layer_stones(self) -> int:
        if self.completed_layers >= self.target_layers:
            return self.stones_per_layer
        return self.stones_placed % self.stones_per_layer

    @property
    def progress_pct(self) -> int:
        return int(round(100.0 * self.stones_placed / max(1, self.target_stones)))

    def remaining_clockout_str(self, now_dt: Optional[datetime] = None) -> str:
        dt = now_dt or datetime.now()
        target_dt = dt.replace(hour=self.target_hour, minute=self.target_minute, second=0, microsecond=0)
        if dt >= target_dt or self.completed_today:
            return "퇴근 완료!"
        rem_sec = int((target_dt - dt).total_seconds())
        hh = rem_sec // 3600
        mm = (rem_sec % 3600) // 60
        if hh > 0:
            return f"퇴근 -{hh}시간 {mm:02d}분"
        return f"퇴근 -{mm}분"

    def ensure_current_date(self, now_dt: Optional[datetime] = None) -> bool:
        """Resets daily stones cleanly when calendar date rolls over while preserving streak."""
        dt_now = now_dt or datetime.now()
        today = _today_str(dt_now)
        if self.date != today:
            yesterday = (dt_now - timedelta(days=1)).strftime("%Y-%m-%d")
            if self.last_completed_date == yesterday:
                self.streak_days = max(1, self.streak_days)
            elif self.last_completed_date != today:
                self.streak_days = 1
            self.date = today
            self.clock_in_time = dt_now.strftime("%H:%M")
            self.stones_placed = 0
            self.ppong_stones = 0
            self.tree_stones = 0
            self.layers = []
            self.current_layer_pebbles = []
            self.announced_phases = []
            self.completed_today = False
            self.clocked_out_today = False
            self.bonus_claimed_today = False
            self.save()
            return True
        return False

    def _make_completed_layer_record(self, layer_idx: int, builder_id: str, dt_now: datetime) -> dict[str, Any]:
        is_capstone = layer_idx == (self.target_layers - 1)
        taper = max(0.46, 1.0 - layer_idx * 0.066)
        if is_capstone:
            pal_idx = -1
        else:
            recent = {s.get("palette_idx") for s in self.layers[-2:]}
            choices = [i for i in range(len(STONE_PALETTES)) if i not in recent] or list(range(len(STONE_PALETTES)))
            pal_idx = random.choice(choices)
        return {
            "layer": layer_idx + 1,
            "palette_idx": pal_idx,
            "is_capstone": is_capstone,
            "shape_seed": random.randint(1, 99999),
            "width_ratio": round(taper * random.uniform(0.96, 1.03), 3),
            "height_ratio": round((1.06 if is_capstone else random.uniform(0.93, 1.05)), 3),
            "tilt_deg": round(0.0 if is_capstone else random.uniform(-2.2, 2.2), 2),
            "x_jitter": round(0.0 if is_capstone else random.uniform(-1.5, 1.5), 2),
            "builder_id": str(builder_id or "ppong"),
            "completed_at": dt_now.strftime("%H:%M:%S"),
        }

    def load(self) -> None:
        dt_now = datetime.now()
        today = _today_str(dt_now)
        if self.save_path.exists():
            try:
                raw = json.loads(self.save_path.read_text(encoding="utf-8"))
                self.last_completed_date = str(raw.get("last_completed_date", ""))
                self.streak_days = max(1, int(raw.get("streak_days", 1)))
                if raw.get("date") == today:
                    self.date = today
                    self.clock_in_time = str(raw.get("clock_in_time") or dt_now.strftime("%H:%M"))
                    self.target_layers = max(1, int(raw.get("target_layers", self.target_layers)))
                    self.stones_per_layer = max(2, int(raw.get("stones_per_layer", self.stones_per_layer)))
                    self.target_stones = self.target_layers * self.stones_per_layer
                    self.start_hour = int(raw.get("start_hour", self.start_hour))
                    self.start_minute = int(raw.get("start_minute", self.start_minute))
                    self.target_hour = int(raw.get("target_hour", self.target_hour))
                    self.target_minute = int(raw.get("target_minute", self.target_minute))
                    self.stones_placed = max(0, min(self.target_stones, int(raw.get("stones_placed", 0))))
                    self.ppong_stones = max(0, int(raw.get("ppong_stones", (self.stones_placed + 1) // 2)))
                    self.tree_stones = max(0, int(raw.get("tree_stones", self.stones_placed // 2)))
                    self.layers = list(raw.get("layers", []))[: self.completed_layers]
                    while len(self.layers) < self.completed_layers:
                        self.layers.append(self._make_completed_layer_record(len(self.layers), "ppong", dt_now))
                    expected_pebs = 0 if self.completed_layers >= self.target_layers else (self.stones_placed % self.stones_per_layer)
                    self.current_layer_pebbles = list(raw.get("current_layer_pebbles", []))[:expected_pebs]
                    while len(self.current_layer_pebbles) < expected_pebs:
                        idx = len(self.current_layer_pebbles)
                        self.current_layer_pebbles.append({
                            "index": idx + 1,
                            "palette_idx": idx % len(STONE_PALETTES),
                            "shape_seed": random.randint(1, 99999),
                            "builder_id": "ppong",
                            "placed_at": dt_now.strftime("%H:%M:%S"),
                        })
                    self.announced_phases = list(raw.get("announced_phases", []))
                    self.completed_today = self.stones_placed >= self.target_stones
                    self.clocked_out_today = bool(raw.get("clocked_out_today", False))
                    self.bonus_claimed_today = bool(raw.get("bonus_claimed_today", False))
                    self.schema_version = 3
                    return
                # Date rolled over from previous session
                yesterday = (dt_now - timedelta(days=1)).strftime("%Y-%m-%d")
                if self.last_completed_date != yesterday:
                    self.streak_days = 1
            except Exception:
                pass
        self.date = today
        self.clock_in_time = dt_now.strftime("%H:%M")
        self.stones_placed = 0
        self.ppong_stones = 0
        self.tree_stones = 0
        self.layers = []
        self.current_layer_pebbles = []
        self.announced_phases = []
        self.completed_today = False
        self.clocked_out_today = False
        self.bonus_claimed_today = False
        self.schema_version = 3
        self.save()

    def save(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": self.schema_version,
                "date": self.date,
                "clock_in_time": self.clock_in_time,
                "streak_days": self.streak_days,
                "last_completed_date": self.last_completed_date,
                "start_hour": self.start_hour,
                "start_minute": self.start_minute,
                "target_hour": self.target_hour,
                "target_minute": self.target_minute,
                "target_layers": self.target_layers,
                "stones_per_layer": self.stones_per_layer,
                "target_stones": self.target_stones,
                "stones_placed": self.stones_placed,
                "ppong_stones": self.ppong_stones,
                "tree_stones": self.tree_stones,
                "completed_layers": self.completed_layers,
                "layers": self.layers,
                "current_layer_pebbles": self.current_layer_pebbles,
                "announced_phases": self.announced_phases,
                "completed_today": self.completed_today,
                "clocked_out_today": self.clocked_out_today,
                "bonus_claimed_today": self.bonus_claimed_today,
            }
            self.save_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def add_stone(self, builder_id: str = "ppong", now_dt: Optional[datetime] = None) -> dict[str, Any]:
        """Adds 1 gathered stone into current layer; every 10th stone fuses into a solid completed layer."""
        dt_now = now_dt or datetime.now()
        self.ensure_current_date(dt_now)
        if self.stones_placed >= self.target_stones:
            top = self.layers[-1] if self.layers else {}
            return {**top, "layer_completed": False, "layer_number": self.completed_layers, "pebble_in_layer": self.stones_per_layer}

        b_id = str(builder_id or "ppong").lower()
        if b_id == "tree":
            self.tree_stones += 1
        else:
            self.ppong_stones += 1

        recent_p = {s.get("palette_idx") for s in self.current_layer_pebbles[-2:]}
        choices = [i for i in range(len(STONE_PALETTES)) if i not in recent_p] or list(range(len(STONE_PALETTES)))
        pal_idx = random.choice(choices)
        pebble = {
            "index": len(self.current_layer_pebbles) + 1,
            "palette_idx": pal_idx,
            "shape_seed": random.randint(1, 99999),
            "builder_id": b_id,
            "placed_at": dt_now.strftime("%H:%M:%S"),
        }
        self.current_layer_pebbles.append(pebble)
        self.stones_placed = min(self.target_stones, self.stones_placed + 1)

        layer_completed = False
        layer_num = self.completed_layers
        if len(self.current_layer_pebbles) >= self.stones_per_layer and len(self.layers) < self.target_layers:
            layer_idx = len(self.layers)
            layer_rec = self._make_completed_layer_record(layer_idx, b_id, dt_now)
            self.layers.append(layer_rec)
            self.current_layer_pebbles = []
            layer_completed = True
            layer_num = layer_idx + 1

        was_complete = self.completed_today
        self.completed_today = self.stones_placed >= self.target_stones
        if self.completed_today and not was_complete:
            today_s = _today_str(dt_now)
            yesterday_s = (dt_now - timedelta(days=1)).strftime("%Y-%m-%d")
            if self.last_completed_date == yesterday_s:
                self.streak_days += 1
            elif self.last_completed_date != today_s:
                self.streak_days = max(1, self.streak_days)
            self.last_completed_date = today_s
        self.save()
        return {
            **pebble,
            "layer_completed": layer_completed,
            "layer_number": layer_num if layer_completed else self.current_layer_idx,
            "pebble_in_layer": self.stones_per_layer if layer_completed else len(self.current_layer_pebbles),
        }

    def reset_today(self) -> None:
        dt_now = datetime.now()
        self.date = _today_str(dt_now)
        self.clock_in_time = dt_now.strftime("%H:%M")
        self.stones_placed = 0
        self.ppong_stones = 0
        self.tree_stones = 0
        self.layers = []
        self.current_layer_pebbles = []
        self.announced_phases = []
        self.completed_today = False
        self.clocked_out_today = False
        self.save()

    def compute_next_mining_delay_sec(self, now_dt: Optional[datetime] = None, live_cpm: int = 0) -> Optional[float]:
        """Closed-loop adaptive pacing across 08:00~17:00 (90 stones = 9 layers) with lunch & typing rhythm awareness."""
        dt_now = now_dt or datetime.now()
        self.ensure_current_date(dt_now)
        if self.stones_placed >= self.target_stones:
            return None

        start_dt = dt_now.replace(hour=self.start_hour, minute=self.start_minute, second=0, microsecond=0)
        target_dt = dt_now.replace(hour=self.target_hour, minute=self.target_minute, second=0, microsecond=0)

        if dt_now < start_dt and self.stones_placed == 0:
            wait_sec = (start_dt - dt_now).total_seconds() + random.uniform(5.0, 25.0)
            return max(5.0, wait_sec)

        if dt_now >= target_dt:
            return random.uniform(22.0, 42.0)

        # First clock-in foundation stone arrives briskly within ~35~65s so the user feels greeted right away!
        if self.stones_placed == 0:
            return random.uniform(32.0, 62.0)

        t_trip = 11.5
        t_buffer = 65.0
        remaining_sec = max(10.0, (target_dt - dt_now).total_seconds())
        rem_stones = max(1, self.target_stones - self.stones_placed)
        if rem_stones == 1:
            return max(8.0, min(max(12.0, remaining_sec - t_trip), remaining_sec - t_trip - random.uniform(0.0, 55.0)))

        eff_rem = max(10.0, remaining_sec - (rem_stones - 1) * t_trip - t_buffer)
        avg_gap = eff_rem / rem_stones

        # Phase modulation: slightly calmer during lunch break (12:00~13:00), slightly livelier when user is actively typing!
        phase_key = get_workday_phase_info(dt_now)["key"]
        if phase_key == "lunch_break" and remaining_sec > 3600.0:
            avg_gap *= 1.18
        elif live_cpm >= 90:
            avg_gap *= 0.90

        span = min(0.26, 0.08 + 0.18 * (rem_stones / float(self.target_stones)))
        floor_sec = 6.0 if remaining_sec < 600.0 else 14.0
        max_cap = max(floor_sec, min(avg_gap * 1.30, 540.0))
        jittered = avg_gap * random.uniform(1.0 - span, 1.0 + span)
        return max(floor_sec, min(max_cap, jittered))


class CarriedStoneWidget(QWidget):
    """Floating organically sculpted mineral pebble scaled proportionally to the pet."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._palette_idx: int = 0
        self._is_capstone: bool = False
        self._scale_factor: float = 0.10
        self.set_scale_factor(0.10)
        self.hide()

    def set_scale_factor(self, scale: float) -> None:
        s = max(0.10, min(1.80, float(scale)))
        self._scale_factor = s
        w = max(22, min(52, int(round(20.0 + 28.0 * s))))
        h = max(19, min(44, int(round(17.0 + 23.0 * s))))
        if (w, h) != (self.width(), self.height()):
            self.setFixedSize(w, h)
        self.update()

    def set_stone_palette(self, palette_idx: int, is_capstone: bool = False) -> None:
        self._is_capstone = bool(is_capstone)
        self._palette_idx = int(palette_idx) % len(STONE_PALETTES)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pal = CAPSTONE_PALETTE if self._is_capstone else STONE_PALETTES[self._palette_idx % len(STONE_PALETTES)]
        c_hi, c_mid, c_dk, c_rim = (QColor(x) for x in pal)

        wobble_deg = math.sin(time.perf_counter() * 9.5) * 4.0
        w = float(self.width())
        h = float(self.height())
        sw = w * 0.72
        sh = h * 0.62
        cx, cy = w * 0.5, h * 0.54

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(wobble_deg)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(15, 23, 42, 72))
        painter.drawEllipse(QPointF(1.0, sh * 0.24), sw * 0.50, sh * 0.42)

        stone_path = _build_river_stone_path(sw, sh, seed=self._palette_idx + 17)
        grad = QRadialGradient(-sw * 0.16, -sh * 0.22, sw * 0.68)
        grad.setColorAt(0.0, c_hi)
        grad.setColorAt(0.58, c_mid)
        grad.setColorAt(1.0, c_dk)
        painter.setBrush(grad)
        painter.setPen(QPen(c_rim, 1.25))
        painter.drawPath(stone_path)

        _draw_mineral_grain_and_highlight(painter, stone_path, sw, sh, seed=self._palette_idx + 17)

        if self._is_capstone:
            star = QPolygonF()
            r_out = max(3.6, min(6.2, sh * 0.34))
            r_in = r_out * 0.44
            for k in range(10):
                ang = -math.pi * 0.5 + k * (math.pi / 5.0)
                r = r_out if k % 2 == 0 else r_in
                star.append(QPointF(math.cos(ang) * r, math.sin(ang) * r - 0.5))
            painter.setBrush(QColor("#fef9c3"))
            painter.setPen(QPen(QColor("#92400e"), 0.85))
            painter.drawPolygon(star)

        painter.restore()
        painter.end()


class WorkdayStatusCardPopup(QWidget):
    """Cupertino / Material Dark-Glass + Neumorphic Office Companion Briefing Card docked above the cairn."""

    mine_now_requested = pyqtSignal()

    def __init__(self, state: WorkdayCairnState, font_family: str = "Pretendard", always_on_top: bool = True) -> None:
        super().__init__(None)
        self._state = state
        self._font_family = font_family or "Pretendard"
        self._hover_btn: Optional[str] = None
        self._mine_btn_rect = QRectF()
        self._close_btn_rect = QRectF()
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self.setFixedSize(292, 206)
        self._apply_window_flags(always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.hide()

    def _apply_window_flags(self, on_top: bool) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def set_always_on_top(self, on_top: bool) -> None:
        was_vis = self.isVisible()
        self._apply_window_flags(on_top)
        if was_vis:
            self.show()

    def show_above_cairn(self, cairn_geom: QRect, duration_ms: int = 6800) -> None:
        screen = QGuiApplication.screenAt(cairn_geom.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1040)
        x = max(avail.left() + 8, min(avail.right() - self.width() - 10, cairn_geom.right() - self.width()))
        y = max(avail.top() + 8, cairn_geom.top() - self.height() + 18)
        self.move(x, y)
        self.show()
        self.raise_()
        self.update()
        if duration_ms > 0:
            self._auto_hide_timer.start(duration_ms)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        prev = self._hover_btn
        if self._mine_btn_rect.contains(pos):
            self._hover_btn = "mine"
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._close_btn_rect.contains(pos):
            self._hover_btn = "close"
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._hover_btn = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if prev != self._hover_btn:
            self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
            if self._mine_btn_rect.contains(pos):
                self.mine_now_requested.emit()
                self._auto_hide_timer.start(4500)
                self.update()
                event.accept()
                return
            if self._close_btn_rect.contains(pos):
                self.hide()
                event.accept()
                return
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        card = QRectF(4.0, 4.0, w - 8.0, h - 8.0)
        now_dt = datetime.now()
        phase = get_workday_phase_info(now_dt, completed=self._state.completed_today)
        accent = QColor(phase["accent"])

        # 1. Minimal ambient shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(2, 6, 23, 82))
        painter.drawRoundedRect(card.translated(0.0, 2.5), 16.0, 16.0)

        # 2. Cupertino Dark-Glass body + 1px specular border
        bg_grad = QLinearGradient(0, card.top(), 0, card.bottom())
        bg_grad.setColorAt(0.0, QColor(17, 24, 39, 238))
        bg_grad.setColorAt(1.0, QColor(10, 15, 28, 246))
        painter.setBrush(QBrush(bg_grad))
        painter.setPen(QPen(QColor(255, 255, 255, 42), 1.0))
        painter.drawRoundedRect(card, 16.0, 16.0)

        # Inner specular highlight
        hi_grad = QLinearGradient(0, card.top() + 1.0, 0, card.bottom() - 1.0)
        hi_grad.setColorAt(0.0, QColor(255, 255, 255, 30))
        hi_grad.setColorAt(0.4, QColor(255, 255, 255, 4))
        hi_grad.setColorAt(1.0, QColor(2, 6, 23, 55))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(hi_grad), 1.0))
        painter.drawRoundedRect(card.adjusted(1.0, 1.0, -1.0, -1.0), 15.0, 15.0)

        # Left semantic accent bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRectF(card.left() + 12.0, card.top() + 14.0, 3.2, 20.0), 1.6, 1.6)

        # Header title + streak chip + close button
        title_font = QFont(self._font_family, 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(
            QRectF(card.left() + 21.0, card.top() + 11.0, 168.0, 22.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            f"{phase['badge']} 동반 돌탑",
        )

        # Streak badge
        streak_rect = QRectF(card.right() - 96.0, card.top() + 12.0, 62.0, 20.0)
        painter.setBrush(QColor(30, 41, 59, 210))
        painter.setPen(QPen(QColor(251, 191, 36, 95), 1.0))
        painter.drawRoundedRect(streak_rect, 9.5, 9.5)
        chip_font = QFont(self._font_family, 8, QFont.Weight.Bold)
        painter.setFont(chip_font)
        painter.setPen(QColor("#FDE047"))
        painter.drawText(streak_rect, Qt.AlignmentFlag.AlignCenter, f"🔥 {self._state.streak_days}일째")

        # Close circle
        self._close_btn_rect = QRectF(card.right() - 28.0, card.top() + 12.0, 20.0, 20.0)
        painter.setBrush(QColor(51, 65, 85, 215 if self._hover_btn == "close" else 135))
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
        painter.drawEllipse(self._close_btn_rect)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(self._close_btn_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        # Neumorphic recessed office timecard box
        well = QRectF(card.left() + 12.0, card.top() + 39.0, card.width() - 24.0, 58.0)
        painter.setBrush(QColor(7, 11, 21, 210))
        painter.setPen(QPen(QColor(255, 255, 255, 22), 1.0))
        painter.drawRoundedRect(well, 11.0, 11.0)

        meta_font = QFont(self._font_family, 8, QFont.Weight.DemiBold)
        painter.setFont(meta_font)
        painter.setPen(QColor("#94A3B8"))
        row1 = f"🕘 출근 {self._state.clock_in_time}   ·   🕔 목표 {self._state.target_hour:02d}:{self._state.target_minute:02d} ({self._state.remaining_clockout_str(now_dt)})"
        painter.drawText(
            QRectF(well.left() + 10.0, well.top() + 6.0, well.width() - 20.0, 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            row1,
        )

        painter.setPen(QColor("#E2E8F0"))
        row2 = (
            f"🪨 공정 {self._state.progress_pct}% ({self._state.completed_layers}/{self._state.target_layers}층 · "
            f"{self._state.stones_placed}/{self._state.target_stones}돌)  |  🦄{self._state.ppong_stones} · 🎄{self._state.tree_stones}"
        )
        painter.drawText(
            QRectF(well.left() + 10.0, well.top() + 24.0, well.width() - 20.0, 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            row2,
        )

        # Progress bar inside recessed well
        track = QRectF(well.left() + 10.0, well.bottom() - 10.5, well.width() - 20.0, 5.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 41, 59, 220))
        painter.drawRoundedRect(track, 2.5, 2.5)
        frac = min(1.0, max(0.0, self._state.stones_placed / float(max(1, self._state.target_stones))))
        if frac > 0.0:
            fill_grad = QLinearGradient(track.left(), 0, track.right(), 0)
            fill_grad.setColorAt(0.0, accent)
            fill_grad.setColorAt(1.0, QColor("#FDE047") if self._state.completed_today else QColor("#38BDF8"))
            painter.setBrush(QBrush(fill_grad))
            painter.drawRoundedRect(QRectF(track.left(), track.top(), max(6.0, track.width() * frac), track.height()), 2.5, 2.5)

        # Companion quote
        quote_font = QFont(self._font_family, 8, QFont.Weight.Medium)
        painter.setFont(quote_font)
        painter.setPen(QColor("#CBD5E1"))
        painter.drawText(
            QRectF(card.left() + 14.0, well.bottom() + 7.0, card.width() - 28.0, 36.0),
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            phase["quote"],
        )

        # Bottom CTA pill button
        self._mine_btn_rect = QRectF(card.left() + 12.0, card.bottom() - 36.0, card.width() - 24.0, 26.0)
        is_hov = self._hover_btn == "mine"
        btn_grad = QLinearGradient(0, self._mine_btn_rect.top(), 0, self._mine_btn_rect.bottom())
        if self._state.completed_today:
            btn_grad.setColorAt(0.0, QColor(161, 98, 7, 210 if is_hov else 175))
            btn_grad.setColorAt(1.0, QColor(113, 63, 18, 225))
            btn_txt = "🎉 오늘 돌탑 완공 완료! 즐거운 퇴근 되세요"
            btn_border = QColor(253, 224, 71, 140)
        else:
            btn_grad.setColorAt(0.0, QColor(30, 58, 95, 235) if is_hov else QColor(23, 37, 64, 220))
            btn_grad.setColorAt(1.0, QColor(15, 23, 42, 240))
            btn_txt = f"⛏️ 지금 돌 하나 더 쌓기 ({self._state.current_layer_idx}층 {self._state.current_layer_stones}/{self._state.stones_per_layer})"
            btn_border = QColor(56, 189, 248, 165 if is_hov else 95)

        painter.setBrush(QBrush(btn_grad))
        painter.setPen(QPen(btn_border, 1.0))
        painter.drawRoundedRect(self._mine_btn_rect, 9.0, 9.0)
        btn_font = QFont(self._font_family, 8, QFont.Weight.Bold)
        painter.setFont(btn_font)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(self._mine_btn_rect, Qt.AlignmentFlag.AlignCenter, btn_txt)

        painter.end()


class DesktopStoneCairnWidget(QWidget):
    """Non-focus-stealing bottom-right desktop stone cairn stacked progressively from clock-in until 17:00."""

    cairn_clicked = pyqtSignal()
    status_requested = pyqtSignal()

    def __init__(
        self,
        state: WorkdayCairnState,
        always_on_top: bool = True,
        font_family: str = "Pretendard",
    ) -> None:
        super().__init__(None)
        self._state = state
        self._always_on_top = bool(always_on_top)
        self._font_family = font_family or "Pretendard"
        self._drop_anim_t = 1.0
        self._layer_snap_anim_t = 1.0
        self._hovered = False
        self._drop_timer = QTimer(self)
        self._drop_timer.setInterval(33)
        self._drop_timer.timeout.connect(self._on_drop_anim_tick)

        self.setFixedSize(196, 244)
        self._apply_window_flags(self._always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("🪨 출근~17:00 퇴근 동반 돌탑! 클릭하면 출퇴근 브리핑 & 즉시 채굴")
        self.reposition_bottom_right()

    def _apply_window_flags(self, on_top: bool) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def set_always_on_top(self, on_top: bool) -> None:
        was_vis = self.isVisible()
        self._always_on_top = bool(on_top)
        self._apply_window_flags(self._always_on_top)
        if was_vis:
            self.show()

    def reposition_bottom_right(self, avail: Optional[QRect] = None) -> None:
        if avail is None:
            screen = QGuiApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1040)
        x = avail.right() - self.width() - 12
        y = avail.bottom() - self.height() - 2
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def refresh_from_state(self, animate_drop: bool = False, layer_snapped: bool = False) -> None:
        if animate_drop and self._state.stones_placed > 0:
            self._drop_anim_t = 0.0
            if layer_snapped:
                self._layer_snap_anim_t = 0.0
            if not self._drop_timer.isActive():
                self._drop_timer.start()
        else:
            self._drop_anim_t = 1.0
            self._layer_snap_anim_t = 1.0
            self._drop_timer.stop()
        self.update()

    def _on_drop_anim_tick(self) -> None:
        self._drop_anim_t = min(1.0, self._drop_anim_t + 0.078)
        if self._layer_snap_anim_t < 1.0:
            self._layer_snap_anim_t = min(1.0, self._layer_snap_anim_t + 0.055)
        if self._drop_anim_t >= 1.0 and self._layer_snap_anim_t >= 1.0:
            self._drop_timer.stop()
        self.update()

    def _active_hit_rect(self) -> QRect:
        w = self.width()
        h = self.height()
        layers_count = len(self._state.layers)
        pebble_h = 22 if (layers_count < self._state.target_layers) else 0
        stack_h = max(38, int(round(layers_count * 12.6 + pebble_h + (24 if self._state.completed_today else 14))))
        top_y = max(4, h - 54 - stack_h)
        return QRect(6, top_y, w - 12, h - top_y - 2)

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self._active_hit_rect().contains(pos):
                if pos.y() >= self.height() - 48:
                    self.status_requested.emit()
                else:
                    self.cairn_clicked.emit()
                event.accept()
                return
            event.ignore()
            return
        if event.button() == Qt.MouseButton.RightButton:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            if self._active_hit_rect().contains(pos):
                self.status_requested.emit()
                event.accept()
                return
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:
        self._drop_timer.stop()
        super().closeEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cx = w * 0.5
        pill_h = 38.0
        pedestal_y = h - pill_h - 14.0
        now_dt = datetime.now()
        phase = get_workday_phase_info(now_dt, completed=self._state.completed_today)
        phase_accent = QColor(phase["accent"])

        # 1. Time-of-day / Completion Ambient Halo behind the Cairn
        layers = self._state.layers[: self._state.target_layers]
        total_layers = len(layers)
        aura_cy = pedestal_y - max(26.0, min(112.0, total_layers * 12.2 + 18.0))
        if self._state.completed_today:
            aura = QRadialGradient(cx, aura_cy, 76.0)
            aura.setColorAt(0.0, QColor(253, 224, 71, 138))
            aura.setColorAt(0.55, QColor(251, 146, 60, 52))
            aura.setColorAt(1.0, QColor(251, 146, 60, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(aura)
            painter.drawEllipse(QPointF(cx, aura_cy), 74.0, 66.0)
        elif self._hovered or total_layers > 0:
            aura = QRadialGradient(cx, aura_cy, 62.0)
            c_glow = QColor(phase_accent.red(), phase_accent.green(), phase_accent.blue(), 46 if self._hovered else 24)
            aura.setColorAt(0.0, c_glow)
            aura.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(aura)
            painter.drawEllipse(QPointF(cx, aura_cy), 60.0, 52.0)

        # 2. Ground Shadow + Sculpted Dark-Slate Sanctuary Pedestal + Warm Mini Desk-Lantern Post
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(2, 6, 23, 96))
        painter.drawEllipse(QPointF(cx, pedestal_y + 8.0), 66.0, 8.5)

        # Miniature wooden milestone lantern post on the right side of the pedestal (lights up warm amber near 17:00!)
        post_x = cx + 52.0
        painter.setPen(QPen(QColor("#451a03"), 1.0))
        painter.setBrush(QColor("#78350f"))
        painter.drawRoundedRect(QRectF(post_x - 2.0, pedestal_y - 30.0, 4.0, 28.0), 1.5, 1.5)
        painter.drawRoundedRect(QRectF(post_x - 8.0, pedestal_y - 30.0, 10.0, 3.2), 1.2, 1.2)
        lantern_lit = self._state.completed_today or now_dt.hour >= 15
        lantern_col = QColor("#fde047") if lantern_lit else QColor("#bae6fd")
        if lantern_lit:
            l_glow = QRadialGradient(post_x - 6.0, pedestal_y - 22.0, 14.0)
            l_glow.setColorAt(0.0, QColor(253, 224, 71, 120))
            l_glow.setColorAt(1.0, QColor(253, 224, 71, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(l_glow)
            painter.drawEllipse(QPointF(post_x - 6.0, pedestal_y - 22.0), 14.0, 14.0)
        painter.setPen(QPen(QColor("#334155"), 0.9))
        painter.setBrush(lantern_col)
        painter.drawRoundedRect(QRectF(post_x - 9.0, pedestal_y - 26.2, 6.2, 7.8), 2.0, 2.0)

        ped_grad = QLinearGradient(cx - 58.0, pedestal_y - 6.0, cx + 58.0, pedestal_y + 9.0)
        ped_grad.setColorAt(0.0, QColor("#64748b"))
        ped_grad.setColorAt(0.5, QColor("#475569"))
        ped_grad.setColorAt(1.0, QColor("#1e293b"))
        painter.setBrush(ped_grad)
        painter.setPen(QPen(QColor("#0f172a"), 1.3))
        painter.drawRoundedRect(QRectF(cx - 60.0, pedestal_y - 5.0, 120.0, 14.0), 6.5, 6.5)

        # Moss clusters tucked on pedestal corners
        painter.setPen(Qt.PenStyle.NoPen)
        for mx, my, mr, col in (
            (cx - 48.0, pedestal_y + 1.5, 5.4, "#4d7c0f"),
            (cx - 41.0, pedestal_y + 2.2, 4.1, "#65a30d"),
            (cx + 43.0, pedestal_y + 1.4, 5.4, "#4d7c0f"),
            (cx + 36.5, pedestal_y + 2.3, 4.1, "#65a30d"),
        ):
            painter.setBrush(QColor(col))
            painter.drawEllipse(QPointF(mx, my), mr * 1.35, mr * 0.65)

        # 3. Stack Completed Layers Bottom-Up (0..9 solid sculpted river slabs)
        cur_y = pedestal_y - 5.0
        for i, st in enumerate(layers):
            is_top_layer = i == (total_layers - 1)
            is_cap = bool(st.get("is_capstone", False))
            pal_idx = int(st.get("palette_idx", i))
            pal = CAPSTONE_PALETTE if (is_cap or pal_idx < 0) else STONE_PALETTES[pal_idx % len(STONE_PALETTES)]
            c_hi, c_mid, c_dk, c_rim = (QColor(x) for x in pal)
            seed = int(st.get("shape_seed", (i + 1) * 37))

            sw = max(38.0, min(92.0, 88.0 * float(st.get("width_ratio", 1.0))))
            sh = max(12.2, min(17.8, (14.6 if not is_cap else 16.4) * float(st.get("height_ratio", 1.0))))
            sx = cx + float(st.get("x_jitter", 0.0))
            tilt = float(st.get("tilt_deg", 0.0))

            scale_snap_x = 1.0
            scale_snap_y = 1.0
            snap_glow = 0.0
            if is_top_layer and self._layer_snap_anim_t < 1.0:
                u = self._layer_snap_anim_t
                scale_snap_x = 1.0 + 0.14 * math.sin(u * math.pi)
                scale_snap_y = 1.0 - 0.12 * math.sin(u * math.pi)
                snap_glow = max(0.0, 1.0 - u)

            stone_cy = cur_y - sh * 0.5
            cur_y -= sh * 0.80

            painter.save()
            painter.translate(sx, stone_cy)
            painter.rotate(tilt)
            painter.scale(scale_snap_x, scale_snap_y)

            if snap_glow > 0.02:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(253, 224, 71, int(150 * snap_glow)))
                painter.drawEllipse(QPointF(0.0, 0.0), sw * 0.66, sh * 0.92)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(2, 6, 23, 76))
            painter.drawEllipse(QPointF(0.0, sh * 0.44), sw * 0.46, 3.0)

            stone_path = _build_river_stone_path(sw, sh, seed=seed)
            s_grad = QRadialGradient(-sw * 0.16, -sh * 0.22, sw * 0.74)
            s_grad.setColorAt(0.0, c_hi)
            s_grad.setColorAt(0.58, c_mid)
            s_grad.setColorAt(1.0, c_dk)
            painter.setBrush(s_grad)
            painter.setPen(QPen(c_rim, 1.3))
            painter.drawPath(stone_path)

            _draw_mineral_grain_and_highlight(painter, stone_path, sw, sh, seed=seed)

            if is_cap:
                star = QPolygonF()
                for k in range(10):
                    ang = -math.pi * 0.5 + k * (math.pi / 5.0)
                    r = 6.8 if k % 2 == 0 else 3.0
                    star.append(QPointF(math.cos(ang) * r, math.sin(ang) * r - sh * 0.78))
                painter.setBrush(QColor("#fde047"))
                painter.setPen(QPen(QColor("#92400e"), 1.0))
                painter.drawPolygon(star)

            painter.restore()

        # 3B. Active In-Progress Layer Masonry (1..9 mini pebbles filling next tier before snap!)
        if not self._state.completed_today and total_layers < self._state.target_layers:
            next_idx = total_layers
            next_taper = max(0.46, 1.0 - next_idx * 0.066)
            tier_w = max(38.0, min(90.0, 88.0 * next_taper))
            tier_h = 15.0
            pebbles = self._state.current_layer_pebbles[: self._state.stones_per_layer]

            painter.setPen(QPen(QColor(148, 163, 184, 115), 1.0, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(15, 23, 42, 42))
            painter.drawRoundedRect(QRectF(cx - tier_w * 0.5, cur_y - tier_h - 1.0, tier_w, tier_h + 1.0), 7.5, 7.5)

            n_peb = len(pebbles)
            for pi, peb in enumerate(pebbles):
                row = 0 if pi < 5 else 1
                slot_in_row = pi if row == 0 else (pi - 5)
                row_cap = 5 if row == 0 else 4
                row_span = tier_w * (0.76 if row == 0 else 0.58)
                px = cx - row_span * 0.5 + (slot_in_row / max(1, row_cap - 1)) * row_span
                py_base = (cur_y - 4.5) - row * 6.4

                y_drop_off = 0.0
                if pi == (n_peb - 1) and self._drop_anim_t < 1.0:
                    u = self._drop_anim_t
                    if u < 0.65:
                        p = u / 0.65
                        y_drop_off = -24.0 * (1.0 - p * p)
                py = py_base + y_drop_off

                pw = max(9.6, min(14.2, tier_w * 0.21))
                ph = pw * 0.70
                p_idx = int(peb.get("palette_idx", pi)) % len(STONE_PALETTES)
                c_hi, c_mid, c_dk, c_rim = (QColor(x) for x in STONE_PALETTES[p_idx])

                painter.save()
                painter.translate(px, py)
                p_path = _build_river_stone_path(pw, ph, seed=int(peb.get("shape_seed", pi + 19)))
                p_grad = QRadialGradient(-pw * 0.15, -ph * 0.2, pw * 0.65)
                p_grad.setColorAt(0.0, c_hi)
                p_grad.setColorAt(0.6, c_mid)
                p_grad.setColorAt(1.0, c_dk)
                painter.setBrush(p_grad)
                painter.setPen(QPen(c_rim, 1.0))
                painter.drawPath(p_path)
                painter.restore()

            cur_y -= (tier_h + 2.0)

        # Celebration sparkles above completed 9-layer cairn
        if self._state.completed_today:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#fde047"))
            for sx, sy, sr in ((cx - 36.0, cur_y - 6.0, 4.4), (cx + 34.0, cur_y - 12.0, 5.0), (cx - 12.0, cur_y - 24.0, 3.6)):
                spark = QPolygonF()
                for k in range(8):
                    ang = k * (math.pi / 4.0)
                    r = sr if k % 2 == 0 else sr * 0.34
                    spark.append(QPointF(sx + math.cos(ang) * r, sy + math.sin(ang) * r))
                painter.drawPolygon(spark)

        # 4. Cupertino / Material Dark-Glass + Neumorphic 2-Line Workday Capsule
        pill_rect = QRectF(5.0, h - pill_h - 3.0, w - 10.0, pill_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(2, 6, 23, 72))
        painter.drawRoundedRect(pill_rect.translated(0.0, 1.5), 12.5, 12.5)

        pill_grad = QLinearGradient(0, pill_rect.top(), 0, pill_rect.bottom())
        pill_grad.setColorAt(0.0, QColor(17, 24, 39, 236))
        pill_grad.setColorAt(1.0, QColor(10, 15, 28, 244))
        painter.setBrush(QBrush(pill_grad))
        border_col = QColor(253, 224, 71, 155) if self._state.completed_today else QColor(
            phase_accent.red(), phase_accent.green(), phase_accent.blue(), 135 if self._hovered else 72
        )
        painter.setPen(QPen(border_col, 1.0))
        painter.drawRoundedRect(pill_rect, 12.5, 12.5)

        # Left semantic accent dot/pill inside capsule
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(phase_accent)
        painter.drawRoundedRect(QRectF(pill_rect.left() + 8.5, pill_rect.top() + 7.5, 2.8, 14.0), 1.4, 1.4)

        top_font = QFont(self._font_family, 8, QFont.Weight.Bold)
        painter.setFont(top_font)
        painter.setPen(QColor("#FDE047") if self._state.completed_today else QColor("#F8FAFC"))
        if self._state.completed_today:
            line1 = f"🎉 9층 완공 ({self._state.stones_placed}/{self._state.target_stones}) · 칼퇴근!"
        else:
            line1 = (
                f"{phase['badge']} · {self._state.completed_layers}/{self._state.target_layers}층 "
                f"({self._state.current_layer_stones}/{self._state.stones_per_layer})"
            )
        painter.drawText(
            QRectF(pill_rect.left() + 15.0, pill_rect.top() + 3.0, pill_rect.width() - 21.0, 16.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            line1,
        )

        # Bottom line: Neumorphic recessed progress bar + remaining time text
        sub_font = QFont(self._font_family, 7, QFont.Weight.DemiBold)
        painter.setFont(sub_font)
        rem_txt = self._state.remaining_clockout_str(now_dt)
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(
            QRectF(pill_rect.right() - 78.0, pill_rect.bottom() - 16.5, 71.0, 13.0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            rem_txt,
        )

        bar_track = QRectF(pill_rect.left() + 15.0, pill_rect.bottom() - 10.8, pill_rect.width() - 98.0, 4.2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 41, 59, 215))
        painter.drawRoundedRect(bar_track, 2.1, 2.1)

        frac = min(1.0, max(0.0, self._state.stones_placed / float(max(1, self._state.target_stones))))
        if frac > 0.0:
            bar_fill = QLinearGradient(bar_track.left(), 0, bar_track.right(), 0)
            bar_fill.setColorAt(0.0, phase_accent)
            bar_fill.setColorAt(1.0, QColor("#FDE047") if self._state.completed_today else QColor("#38BDF8"))
            painter.setBrush(QBrush(bar_fill))
            painter.drawRoundedRect(
                QRectF(bar_track.left(), bar_track.top(), max(4.0, bar_track.width() * frac), bar_track.height()),
                2.1,
                2.1,
            )

        painter.end()


class WorkdayCairnManager(QObject):
    """Coordinates the 08:00~17:00 workday stone cairn scenario, phase greetings, status briefing popup, and clock-out ceremony."""

    def __init__(
        self,
        ppong_win: Any,
        tree_win: Any,
        coordinator: Any,
        data_dir: Path,
        font_family: str = "Pretendard",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent or coordinator)
        self.ppong_win = ppong_win
        self.tree_win = tree_win
        self.coordinator = coordinator
        self.state = WorkdayCairnState(data_dir)
        self.enabled = bool(getattr(getattr(ppong_win, "_prefs", None), "enable_workday_cairn", True))
        self._builder_flip = 0
        self._arena_hidden = False
        self.suppress_alarm_dialog: bool = False
        self.clockout_alarm_fired: bool = False

        on_top = bool(getattr(ppong_win, "_always_on_top", True))
        self.widget = DesktopStoneCairnWidget(self.state, always_on_top=on_top, font_family=font_family)
        self.status_popup = WorkdayStatusCardPopup(self.state, font_family=font_family, always_on_top=on_top)
        self.widget.cairn_clicked.connect(self._on_cairn_clicked)
        self.widget.status_requested.connect(self.toggle_status_card)
        self.status_popup.mine_now_requested.connect(self._on_popup_mine_requested)
        if self.enabled:
            self.widget.show()

        self._trip_timer = QTimer(self)
        self._trip_timer.setSingleShot(True)
        self._trip_timer.timeout.connect(self._on_trip_timer_fired)

        self._clock_check_timer = QTimer(self)
        self._clock_check_timer.setInterval(30 * 1000)
        self._clock_check_timer.timeout.connect(self._on_clock_check_tick)
        self._clock_check_timer.start()

        # Subtle morning / clock-in welcome briefing shortly after pet readiness
        self._welcome_timer = QTimer(self)
        self._welcome_timer.setSingleShot(True)
        self._welcome_timer.timeout.connect(self._maybe_announce_workday_phase)
        if self.enabled:
            self._welcome_timer.start(8500)

        if self.enabled and not self.state.completed_today:
            self._schedule_next_trip()

    def _live_cpm(self) -> int:
        rpg = getattr(self.ppong_win, "rpg_state", None)
        return int(getattr(rpg, "live_cpm", 0) or 0) if rpg is not None else 0

    def _schedule_next_trip(self, override_delay_ms: Optional[int] = None) -> None:
        self._trip_timer.stop()
        if not self.enabled or self.state.completed_today:
            return
        if override_delay_ms is not None:
            delay_ms = max(5000, int(override_delay_ms))
        else:
            delay_sec = self.state.compute_next_mining_delay_sec(live_cpm=self._live_cpm())
            if delay_sec is None:
                return
            delay_ms = max(8000, int(round(delay_sec * 1000.0)))
        self._trip_timer.start(delay_ms)

    def toggle_status_card(self) -> None:
        if self.status_popup.isVisible():
            self.status_popup.hide()
        else:
            self.status_popup.show_above_cairn(self.widget.frameGeometry(), duration_ms=7500)

    def _on_popup_mine_requested(self) -> None:
        if self.state.completed_today:
            return
        self.dispatch_stone_trip(self.ppong_win, manual=True)
        self.status_popup.update()

    def _on_cairn_clicked(self) -> None:
        self.status_popup.show_above_cairn(self.widget.frameGeometry(), duration_ms=7000)
        if self.state.completed_today:
            if self.ppong_win.isVisible() and not self.coordinator.is_any_in_arena():
                self.ppong_win.speech_bubble.show_message(
                    f"🎉 오늘 {self.state.target_layers}층 돌탑 완공({self.state.stones_placed}/{self.state.target_stones})! 오후 {self.state.target_hour:02d}:{self.state.target_minute:02d} 칼퇴근 준비 끝! 🌅",
                    duration_ms=3200,
                )
            return
        started = self.dispatch_stone_trip(self.ppong_win, manual=True)
        if not started and self.ppong_win.isVisible():
            self.ppong_win.speech_bubble.show_message(
                f"🪨 {self.state.completed_layers}/{self.state.target_layers}층 진행 ({self.state.current_layer_stones}/{self.state.stones_per_layer} · 총 {self.state.stones_placed}/{self.state.target_stones})",
                duration_ms=2600,
            )

    def _maybe_announce_workday_phase(self) -> None:
        if not self.enabled or self._arena_hidden or self.coordinator.is_any_in_arena():
            return
        now_dt = datetime.now()
        phase = get_workday_phase_info(now_dt, completed=self.state.completed_today)
        pkey = phase["key"]
        if pkey in self.state.announced_phases or self.state.completed_today:
            return
        if not self.ppong_win.isVisible() or not getattr(self.ppong_win, "_character_ready", False):
            return

        phase_messages = {
            "clock_in": f"🌅 출근 체크인({self.state.clock_in_time})! 오후 5시 퇴근까지 뽕뽕이·트리와 9층 돌탑 함께 쌓아봐요 ☕🪨",
            "lunch_break": "🍱 점심시간이에요! 맛있는 식사로 에너지 충전하세요~ 돌탑은 저희가 지키고 있을게요! 🍀",
            "afternoon_coop": f"☕ 오후 업무 시작! 벌써 {self.state.completed_layers}/{self.state.target_layers}층 쌓았어요. 기지개 한 번 쭉 펴요! ✨",
            "final_spurt": f"🔥 퇴근 카운트다운({self.state.remaining_clockout_str(now_dt)})! 마지막 정상석까지 조금만 더 화이팅! 🚀",
        }
        msg = phase_messages.get(pkey)
        if msg:
            self.state.announced_phases.append(pkey)
            self.state.save()
            self.ppong_win.speech_bubble.show_message(msg, duration_ms=4200)
        self.widget.update()

    def _is_any_cairn_work_active(self) -> bool:
        return any(
            getattr(getattr(w, "_state", None), "name", "") == "CAIRN_WORK"
            for w in (self.ppong_win, self.tree_win)
        )

    def _is_parallel_catchup_needed(self) -> bool:
        now_dt = datetime.now()
        target_dt = now_dt.replace(hour=self.state.target_hour, minute=self.state.target_minute, second=0, microsecond=0)
        rem_stones = max(1, self.state.target_stones - self.state.stones_placed)
        if now_dt >= target_dt:
            return True
        rem_sec = max(1.0, (target_dt - now_dt).total_seconds())
        return (rem_sec / rem_stones) < 30.0

    def _on_clock_check_tick(self) -> None:
        if not self.enabled:
            return
        rolled = self.state.ensure_current_date()
        if rolled:
            self.clockout_alarm_fired = False
            self.widget.refresh_from_state(animate_drop=False)
            self._schedule_next_trip()
            if self.ppong_win.isVisible() and not self.coordinator.is_any_in_arena():
                self.ppong_win.speech_bubble.show_message(
                    f"🌅 좋은 아침({self.state.clock_in_time})! 오늘도 동반 출근 돌탑 0/{self.state.target_layers}층 시작해요~ 🪨💼",
                    duration_ms=3600,
                )
            return

        self.widget.update()
        if self.status_popup.isVisible():
            self.status_popup.update()
        self._maybe_announce_workday_phase()

        now_dt = datetime.now()
        at_or_past_clockout = (now_dt.hour > self.state.target_hour) or (
            now_dt.hour == self.state.target_hour and now_dt.minute >= self.state.target_minute
        )
        if at_or_past_clockout and not self.state.clocked_out_today:
            if self.state.completed_today:
                self._trigger_clock_out_ceremony(self.ppong_win)
                return
            self._fire_clockout_alarm(
                f"⏰ 오후 {self.state.target_hour:02d}:{self.state.target_minute:02d} 퇴근 시간이에요! (돌탑 {self.state.stones_placed}/{self.state.target_stones}) 🌅"
            )
            self.state.clocked_out_today = True
            self.state.save()

        if not self.state.completed_today and self.state.stones_placed == self.state.target_stones - 1:
            if at_or_past_clockout or (
                now_dt.hour == self.state.target_hour - 1 and now_dt.minute >= 58 and self.state.target_minute == 0
            ):
                if self._trip_timer.isActive() and self._trip_timer.remainingTime() > 25000:
                    self._schedule_next_trip(override_delay_ms=random.randint(6000, 15000))
                elif not self._trip_timer.isActive():
                    self._on_trip_timer_fired()

    def _pick_free_builder(self) -> Optional[Any]:
        pair = (self.ppong_win, self.tree_win) if (self._builder_flip % 2 == 0) else (self.tree_win, self.ppong_win)
        self._builder_flip += 1
        for w in pair:
            if (
                w.isVisible()
                and getattr(w, "_character_ready", False)
                and not w.is_action_busy(include_locomotion=True)
                and getattr(getattr(w, "_state", None), "name", "") == "IDLE"
            ):
                return w
        return None

    def _on_trip_timer_fired(self) -> None:
        if not self.enabled or self.state.completed_today:
            return
        parallel = self._is_parallel_catchup_needed()
        if not parallel and self._is_any_cairn_work_active():
            return
        if self.coordinator.is_any_in_arena() or self.coordinator.is_minigame_active():
            self._schedule_next_trip(override_delay_ms=random.randint(15000, 25000))
            return
        builder = self._pick_free_builder()
        if builder is None:
            self._schedule_next_trip(override_delay_ms=random.randint(12000, 24000))
            return
        ok = self.dispatch_stone_trip(builder, manual=False, allow_parallel=parallel)
        if not ok:
            self._schedule_next_trip(override_delay_ms=random.randint(15000, 25000))
        elif parallel and not self.state.completed_today:
            self._schedule_next_trip()

    def dispatch_stone_trip(self, pet: Optional[Any] = None, manual: bool = False, allow_parallel: bool = False) -> bool:
        target_pet = pet or self.ppong_win
        if self.coordinator.is_any_in_arena():
            return False
        if hasattr(target_pet, "is_popup_menu_open") and target_pet.is_popup_menu_open():
            return False
        if self.state.completed_today:
            if manual and target_pet.isVisible():
                target_pet.speech_bubble.show_message(
                    f"🎉 오늘 {self.state.target_layers}층 돌탑 이미 완성됐어요! (오후 {self.state.target_hour:02d}:{self.state.target_minute:02d} 칼퇴근!) ✨",
                    duration_ms=2800,
                )
            return False
        if not self.enabled:
            if manual:
                for w in (self.ppong_win, self.tree_win):
                    w._prefs.enable_workday_cairn = True
                    w._prefs.save(w.char_id)
                self.set_enabled(True)
            else:
                return False
        if not target_pet.isVisible():
            return False
        worker = getattr(target_pet, "_active_worker", None)
        if worker is not None and worker.isRunning():
            return False
        if self._is_any_cairn_work_active() and not manual and not allow_parallel:
            return False
        if manual:
            if self.coordinator.is_minigame_active():
                self.coordinator._stop_minigame()
            for w in (self.ppong_win, self.tree_win):
                if getattr(getattr(w, "_state", None), "name", "") == "CAIRN_WORK":
                    w.cancel_all_active_actions()
        else:
            if (
                target_pet.is_action_busy(include_locomotion=True)
                or getattr(getattr(target_pet, "_state", None), "name", "") != "IDLE"
            ):
                return False

        avail = target_pet._current_available_geometry()
        self.widget.reposition_bottom_right(avail)
        floor_y = float(target_pet._taskbar_floor_y(avail))
        drop_x = float(max(avail.left() + 20, min(avail.right() - target_pet.WINDOW_W - 20, self.widget.x() - 185)))
        drop_pos = (drop_x, floor_y)

        min_x = float(avail.left() + 24)
        max_x = float(max(avail.left() + 40, avail.right() - target_pet.WINDOW_W - 40))
        min_y = float(avail.top() + 40)
        mine_x, mine_y = min_x + 80.0, floor_y
        for _ in range(16):
            cx = random.uniform(min_x, max_x)
            cy = random.uniform(min_y, floor_y)
            if math.hypot(cx - drop_pos[0], cy - drop_pos[1]) >= 320.0:
                mine_x, mine_y = cx, cy
                break

        next_idx = self.state.stones_placed + 1
        started = target_pet.start_cairn_mining_trip(
            mine_pos=(mine_x, mine_y),
            drop_pos=drop_pos,
            stone_index=next_idx,
            target_stones=self.state.target_stones,
            on_delivered=lambda w=target_pet: self.on_stone_delivered(w),
            manual=manual,
        )
        return bool(started)

    def on_stone_delivered(self, builder_pet: Any) -> None:
        info = self.state.add_stone(getattr(builder_pet, "char_id", "ppong"))
        layer_done = bool(info.get("layer_completed", False))
        self.widget.refresh_from_state(animate_drop=True, layer_snapped=layer_done)
        if self.status_popup.isVisible():
            self.status_popup.update()
        if not self._arena_hidden and self.enabled:
            self.widget.show()

        # Small RPG gold reward on each completed tier so workday stone-stacking ties into RPG growth!
        rpg = getattr(self.ppong_win, "rpg_state", None)
        if layer_done and rpg is not None:
            rpg.gold += 25
            rpg.save()
            if hasattr(self.ppong_win, "_sync_rpg_to_js"):
                self.ppong_win._sync_rpg_to_js()

        if self.state.completed_today:
            self._trigger_clock_out_ceremony(builder_pet)
        else:
            n = self.state.stones_placed
            target = self.state.target_stones
            if builder_pet.isVisible() and not self.coordinator.is_any_in_arena():
                if layer_done:
                    layer_no = info.get("layer_number", self.state.completed_layers)
                    builder_pet.speech_bubble.show_message(
                        f"🪨 제 {layer_no}층 적층 완료! (+25G · {n}/{target}돌 · {self.state.remaining_clockout_str()}) ✨",
                        duration_ms=3400,
                    )
                else:
                    builder_pet.speech_bubble.show_message(
                        f"🪨 {self.state.current_layer_idx}층 {info.get('pebble_in_layer', self.state.current_layer_stones)}/{self.state.stones_per_layer}돌 적립! ({n}/{target})",
                        duration_ms=2400,
                    )
            self._schedule_next_trip()

    def _fire_clockout_alarm(self, label: str) -> None:
        if self.clockout_alarm_fired:
            return
        self.clockout_alarm_fired = True
        if self.suppress_alarm_dialog:
            return
        if hasattr(self.ppong_win, "_on_alarm_triggered"):
            try:
                self.ppong_win._on_alarm_triggered(
                    "workday_clockout_1700",
                    label,
                    f"{self.state.target_hour:02d}:{self.state.target_minute:02d}",
                )
            except Exception:
                pass

    def _trigger_clock_out_ceremony(self, builder_pet: Any) -> None:
        if self.state.clocked_out_today:
            return
        self._trip_timer.stop()
        self.state.clocked_out_today = True

        # Grant daily workday completion bonus once per day (+180G, +2 Invader Cores)
        bonus_suffix = ""
        rpg = getattr(self.ppong_win, "rpg_state", None)
        if not self.state.bonus_claimed_today and rpg is not None:
            self.state.bonus_claimed_today = True
            rpg.gold += 180
            rpg.inventory["invader_core"] = rpg.inventory.get("invader_core", 0) + 2
            rpg.save()
            if hasattr(self.ppong_win, "_sync_rpg_to_js"):
                self.ppong_win._sync_rpg_to_js()
            bonus_suffix = " (+180G · 코어+2 퇴근 보너스!)"
        self.state.save()

        avail = self.ppong_win._current_available_geometry()
        floor_y = float(self.ppong_win._taskbar_floor_y(avail))
        base_x = float(max(avail.left() + 30, self.widget.x() - 195))

        for idx, w in enumerate((self.ppong_win, self.tree_win)):
            if not w.isVisible() or getattr(w, "_in_battle_arena", False):
                continue
            if w._state.name == "IDLE" and not w.is_action_busy(include_locomotion=False):
                w._decision_timer.stop()
                w._pos_x = max(float(avail.left() + 20), base_x - idx * 92.0)
                w._pos_y = floor_y
                w._update_window_pos()
                w._set_3d_facing(0)
                w.trigger_3d_action("HappySpin" if idx == 0 else "Wave", duration_ms=4200, emotion="proud")
                w._schedule_next_decision(5000, 9000, use_freq=False)

        if self.ppong_win.isVisible() and not self.coordinator.is_any_in_arena():
            self.ppong_win.speech_bubble.show_message(
                f"🎉 {self.state.target_layers}층 황금 정상석 완공! 오후 {self.state.target_hour:02d}:{self.state.target_minute:02d} 퇴근하세요!{bonus_suffix} 🌅",
                duration_ms=5400,
            )
        if self.tree_win.isVisible() and not self.coordinator.is_any_in_arena():
            self.tree_win.speech_bubble.show_message(
                f"🪨 오늘도 함께 일해서 든든했어요! (🔥 연속 {self.state.streak_days}일 완주) 내일 아침에 또 만나요! 👋✨",
                duration_ms=5400,
            )
        if not self._arena_hidden and self.enabled:
            self.status_popup.show_above_cairn(self.widget.frameGeometry(), duration_ms=9000)
        self._fire_clockout_alarm("🎉 9층 돌탑 완공! 오후 5시 퇴근 시간이에요! 오늘 하루도 정말 수고하셨습니다!")

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if self.enabled:
            if not self._arena_hidden:
                self.widget.reposition_bottom_right()
                self.widget.show()
            if not self.state.completed_today:
                self._schedule_next_trip()
        else:
            self._trip_timer.stop()
            self.status_popup.hide()
            for w in (self.ppong_win, self.tree_win):
                if getattr(getattr(w, "_state", None), "name", "") == "CAIRN_WORK":
                    w.cancel_all_active_actions()
            self.widget.hide()

    def set_arena_hidden(self, hidden: bool) -> None:
        self._arena_hidden = bool(hidden)
        if self._arena_hidden:
            self.status_popup.hide()
            self.widget.hide()
        elif self.enabled:
            self.widget.reposition_bottom_right()
            self.widget.show()

    def reset_cairn(self, requester: Optional[Any] = None) -> None:
        for w in (self.ppong_win, self.tree_win):
            if getattr(getattr(w, "_state", None), "name", "") == "CAIRN_WORK":
                w.cancel_all_active_actions()
        self.clockout_alarm_fired = False
        self.state.reset_today()
        self.widget.refresh_from_state(animate_drop=False)
        if self.status_popup.isVisible():
            self.status_popup.update()
        if self.enabled and not self._arena_hidden:
            self.widget.show()
            self._schedule_next_trip()
        pet = requester or self.ppong_win
        if pet.isVisible() and not self.coordinator.is_any_in_arena():
            pet.speech_bubble.show_message(
                f"🪨 오늘 돌탑을 0/{self.state.target_layers}층(0/{self.state.target_stones}돌)으로 초기화했어요! ✨",
                duration_ms=3000,
            )

    def cleanup(self) -> None:
        self._trip_timer.stop()
        self._clock_check_timer.stop()
        self._welcome_timer.stop()
        self.status_popup.close()
        self.widget.close()
