#!/usr/bin/env python3
"""
Radial Floating Ring Menu & Contextual Sub-Panel for Ppong-ppong-i
==================================================================
Warm ivory & terracotta orbital ring menu anchored cleanly around the pet's
live screen center, consolidating chat, 3D RPG world, 30 solo-play hobbies,
special desktop actions, emotions, assistant utilities, settings, hide, and quit.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    Qt,
    QVariantAnimation,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Color tokens matched to the orbital floating ring design
IVORY_BG = QColor("#FBF8F4")
IVORY_HOVER = QColor("#FFF5EE")
IVORY_BORDER = QColor("#E2D5C8")
TERRACOTTA = QColor("#C85A32")
TERRACOTTA_TOP = QColor("#D5673F")
TERRACOTTA_BOTTOM = QColor("#B94D27")
TERRACOTTA_HOVER = QColor("#DD7048")
ESPRESSO = QColor("#2E221D")
MUTED_TAUPE = QColor("#7A675E")
WHITE = QColor("#FFFFFF")


def _draw_soft_shadow_circle(painter: QPainter, cx: float, cy: float, r: float) -> None:
    """Draws a multi-ring soft drop shadow without QGraphicsDropShadowEffect clipping."""
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    for dr, alpha in ((5.0, 12), (3.5, 20), (2.0, 28), (0.8, 38)):
        painter.setBrush(QColor(22, 14, 10, alpha))
        painter.drawEllipse(QPointF(cx, cy + 3.0), r + dr, r + dr)
    painter.restore()


def _draw_button_icon(painter: QPainter, key: str, cx: float, cy: float, color: QColor) -> None:
    """Renders crisp custom vector QPainterPath icons cleanly inside orbital circles."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if key == "chat":
        # Rounded speech bubble + tail
        path = QPainterPath()
        path.moveTo(cx - 8.5, cy - 6.5)
        path.quadTo(cx - 8.5, cy - 9.0, cx - 5.5, cy - 9.0)
        path.lineTo(cx + 5.5, cy - 9.0)
        path.quadTo(cx + 8.5, cy - 9.0, cx + 8.5, cy - 6.5)
        path.lineTo(cx + 8.5, cy + 2.5)
        path.quadTo(cx + 8.5, cy + 5.0, cx + 5.5, cy + 5.0)
        path.lineTo(cx - 1.5, cy + 5.0)
        path.lineTo(cx - 5.5, cy + 8.5)
        path.lineTo(cx - 4.5, cy + 5.0)
        path.lineTo(cx - 5.5, cy + 5.0)
        path.quadTo(cx - 8.5, cy + 5.0, cx - 8.5, cy + 2.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        for dx in (-3.6, 0.0, 3.6):
            painter.drawEllipse(QPointF(cx + dx, cy - 2.0), 1.15, 1.15)

    elif key == "world":
        # Heraldic shield with crisp cross/chevron detail
        path = QPainterPath()
        path.moveTo(cx, cy - 8.5)
        path.lineTo(cx + 7.5, cy - 5.8)
        path.lineTo(cx + 7.5, cy + 0.5)
        path.quadTo(cx + 7.0, cy + 6.2, cx, cy + 9.0)
        path.quadTo(cx - 7.0, cy + 6.2, cx - 7.5, cy + 0.5)
        path.lineTo(cx - 7.5, cy - 5.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(cx, cy - 4.2), QPointF(cx, cy + 4.2))
        painter.drawLine(QPointF(cx - 3.6, cy - 0.6), QPointF(cx + 3.6, cy - 0.6))

    elif key == "play":
        # 4-point gleam sparkle + mini satellite star
        path = QPainterPath()
        pts = [
            (0, -8.5), (2.2, -2.2), (8.5, 0), (2.2, 2.2),
            (0, 8.5), (-2.2, 2.2), (-8.5, 0), (-2.2, -2.2),
        ]
        path.moveTo(cx + pts[0][0], cy + pts[0][1])
        for px, py in pts[1:]:
            path.lineTo(cx + px, cy + py)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx + 6.8, cy - 6.5), 1.4, 1.4)

    elif key == "action":
        # Dynamic lightning bolt
        path = QPainterPath()
        path.moveTo(cx + 1.5, cy - 8.8)
        path.lineTo(cx - 5.8, cy + 0.6)
        path.lineTo(cx - 0.5, cy + 0.6)
        path.lineTo(cx - 2.0, cy + 8.8)
        path.lineTo(cx + 5.8, cy - 0.8)
        path.lineTo(cx + 0.5, cy - 0.8)
        path.closeSubpath()
        painter.drawPath(path)

    elif key == "emotion":
        # Clean symmetric heart
        path = QPainterPath()
        path.moveTo(cx, cy + 7.6)
        path.cubicTo(cx - 10.5, cy + 1.2, cx - 9.5, cy - 8.2, cx, cy - 2.8)
        path.cubicTo(cx + 9.5, cy - 8.2, cx + 10.5, cy + 1.2, cx, cy + 7.6)
        painter.drawPath(path)

    elif key == "assistant":
        # Sleek service bell / portfolio badge
        arc = QPainterPath()
        arc.moveTo(cx - 6.5, cy + 3.5)
        arc.lineTo(cx - 6.5, cy - 0.5)
        arc.quadTo(cx - 6.5, cy - 6.5, cx, cy - 6.5)
        arc.quadTo(cx + 6.5, cy - 6.5, cx + 6.5, cy - 0.5)
        arc.lineTo(cx + 6.5, cy + 3.5)
        painter.drawPath(arc)
        painter.drawLine(QPointF(cx - 8.5, cy + 3.5), QPointF(cx + 8.5, cy + 3.5))
        painter.drawLine(QPointF(cx, cy - 8.5), QPointF(cx, cy - 6.5))
        painter.drawArc(QRectF(cx - 2.2, cy + 3.5, 4.4, 4.0), 180 * 16, 180 * 16)

    elif key == "settings":
        # Radial sun-gear (inner ring + 8 crisp spokes)
        painter.drawEllipse(QPointF(cx, cy), 3.6, 3.6)
        for i in range(8):
            ang = math.radians(i * 45.0)
            painter.drawLine(
                QPointF(cx + math.cos(ang) * 5.6, cy + math.sin(ang) * 5.6),
                QPointF(cx + math.cos(ang) * 8.4, cy + math.sin(ang) * 8.4),
            )

    elif key == "hide":
        # Eye with diagonal hide slash
        eye = QPainterPath()
        eye.moveTo(cx - 8.5, cy)
        eye.quadTo(cx, cy - 6.5, cx + 8.5, cy)
        eye.quadTo(cx, cy + 6.5, cx - 8.5, cy)
        painter.drawPath(eye)
        painter.drawEllipse(QPointF(cx, cy), 2.4, 2.4)
        painter.drawLine(QPointF(cx - 7.5, cy + 6.5), QPointF(cx + 7.5, cy - 6.5))

    elif key == "quit":
        # Clean power symbol (open arc + top stem)
        painter.drawArc(QRectF(cx - 7.2, cy - 6.2, 14.4, 14.4), 128 * 16, 284 * 16)
        painter.drawLine(QPointF(cx, cy - 8.5), QPointF(cx, cy - 1.0))

    painter.restore()


PLAY_CATEGORIES: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "모험",
        [
            ("집 짓기", "build_house"),
            ("낚시", "fishing"),
            ("곤충 채집", "hunting"),
            ("탐험", "explorer"),
            ("캠핑", "camping"),
            ("건배", "drinking"),
        ],
    ),
    (
        "취미",
        [
            ("요리", "cooking"),
            ("정원 가꾸기", "gardening"),
            ("기타 연주", "music_guitar"),
            ("그림 그리기", "painting"),
            ("독서", "reading"),
            ("눈사람", "snowman"),
        ],
    ),
    (
        "직업",
        [
            ("마법사", "wizard"),
            ("우주비행사", "astronaut"),
            ("게이머", "gamer"),
            ("닌자", "ninja"),
            ("탐정", "detective"),
            ("바리스타", "barista"),
        ],
    ),
    (
        "스포츠",
        [
            ("헬스", "fitness"),
            ("비눗방울", "bubbles"),
            ("스케이트", "skateboard"),
            ("연날리기", "kite"),
            ("망원경", "telescope"),
            ("보물찾기", "treasure"),
        ],
    ),
    (
        "힐링",
        [
            ("피크닉", "picnic"),
            ("낮잠", "sleeping"),
            ("타임머신", "timemachine"),
            ("서핑", "surfing"),
            ("종이비행기", "paper_plane"),
            ("파티 DJ", "party_dj"),
        ],
    ),
]


class RadialSubPanel(QWidget):
    """Warm ivory contextual sub-panel docked neatly beside the radial menu."""

    SHADOW_PAD = 8

    def __init__(self, ring: "RadialFloatingMenu") -> None:
        super().__init__(None)
        self._ring = ring
        self._pet = ring._pet
        self._font_family = "Pretendard"
        self._active_key: str = ""
        self._play_tab_idx: int = 0
        self._content_layout: Optional[QVBoxLayout] = None

        self._apply_window_flags(getattr(self._pet, "_always_on_top", True))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(self.SHADOW_PAD + 14, self.SHADOW_PAD + 12, self.SHADOW_PAD + 14, self.SHADOW_PAD + 14)
        outer.setSpacing(10)
        self._outer = outer

        # Header row
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self._title_lbl = QLabel("", self)
        self._title_lbl.setFont(QFont(self._font_family, 12, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet(f"color: #2E221D; font-family: '{self._font_family}', 'Malgun Gothic'; font-size: 15px; font-weight: 800; background: transparent;")

        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: #F2EAE1; color: #7A675E; border: 1px solid #E2D5C8; "
            f"border-radius: 13px; font-family: '{self._font_family}', 'Malgun Gothic'; font-size: 13px; font-weight: 700; }}"
            f"QPushButton:hover {{ background: #C85A32; color: #FFFFFF; border-color: #C85A32; }}"
        )
        self._close_btn.clicked.connect(self.hide_panel)

        header.addWidget(self._title_lbl)
        header.addStretch(1)
        header.addWidget(self._close_btn)
        outer.addLayout(header)

        self._body_container = QWidget(self)
        self._body_container.setStyleSheet("background: transparent;")
        self._body_layout = QVBoxLayout(self._body_container)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(8)
        outer.addWidget(self._body_container)

        self.hide()

    def _apply_window_flags(self, always_on_top: bool) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def sync_always_on_top(self, enabled: bool) -> None:
        was_vis = self.isVisible()
        self._apply_window_flags(enabled)
        if was_vis:
            self.show()

    def hide_panel(self) -> None:
        self._active_key = ""
        self.hide()

    def set_font_family(self, family: str) -> None:
        self._font_family = family or "Pretendard"

    def _clear_body(self) -> None:
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            sub_l = item.layout()
            if sub_l is not None:
                self._clear_sub_layout(sub_l)

    def _clear_sub_layout(self, lay) -> None:
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            sub_l = item.layout()
            if sub_l is not None:
                self._clear_sub_layout(sub_l)

    def _pill_style(self, active: bool = False, featured: bool = False, pad: str = "8px 10px", font_px: int = 14) -> str:
        eff_px = max(13, font_px)
        ff = f"'{self._font_family}', 'Malgun Gothic', sans-serif"
        if featured or active:
            return (
                f"QPushButton {{ background: #C85A32; color: #FFFFFF; border: 1.5px solid #B94D27; "
                f"border-radius: 12px; padding: {pad}; font-family: {ff}; font-size: {eff_px}px; font-weight: 700; }}"
                f"QPushButton:hover {{ background: #DD7048; border-color: #C85A32; }}"
            )
        return (
            f"QPushButton {{ background: #FFFFFF; color: #2E221D; border: 1.5px solid #E4D7CA; "
            f"border-radius: 12px; padding: {pad}; font-family: {ff}; font-size: {eff_px}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: #FFF5EE; color: #C85A32; border-color: #C85A32; }}"
        )

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text, self._body_container)
        lbl.setStyleSheet(
            f"color: #7A675E; font-family: '{self._font_family}', 'Malgun Gothic'; "
            f"font-size: 12px; font-weight: 700; padding-top: 2px; background: transparent;"
        )
        return lbl

    def _make_btn(
        self,
        label: str,
        cb: Callable[[], None],
        active: bool = False,
        featured: bool = False,
        close_after: bool = True,
        font_px: int = 13,
        pad: str = "8px 10px",
    ) -> QPushButton:
        btn = QPushButton(label, self._body_container)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(34)
        btn.setStyleSheet(self._pill_style(active=active, featured=featured, pad=pad, font_px=font_px))

        def _on_click() -> None:
            if close_after:
                self._ring.close_all()
            cb()

        btn.clicked.connect(_on_click)
        return btn

    def open_for(self, key: str, btn_global_center: QPoint) -> None:
        self._active_key = key
        self._rebuild_contents()
        self.adjustSize()
        self._position_beside_ring(btn_global_center)
        self.show()
        self.raise_()

    def refresh_if_open(self) -> None:
        if not self.isVisible() or not self._active_key:
            return
        self._rebuild_contents()
        self.adjustSize()

    def _position_beside_ring(self, btn_global_center: QPoint) -> None:
        ring_rect = self._ring.frameGeometry()
        screen = QGuiApplication.screenAt(ring_rect.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        w = max(250, self.width())
        h = max(120, self.height())
        gap = 10

        if ring_rect.right() + gap + w <= avail.right() - 8:
            x = ring_rect.right() + gap
        elif ring_rect.left() - gap - w >= avail.left() + 8:
            x = ring_rect.left() - gap - w
        else:
            x = max(avail.left() + 8, min(avail.right() - w - 8, avail.right() - w - 8))

        y = btn_global_center.y() - h // 2
        y = max(avail.top() + 8, min(avail.bottom() - h - 8, y))
        self.move(x, y)

    def _rebuild_contents(self) -> None:
        self._clear_body()
        key = self._active_key
        pet = self._pet

        if key == "world":
            self._title_lbl.setText("월드 & 전투")
            self.setFixedWidth(272)
            grid = QGridLayout()
            grid.setSpacing(7)
            items: list[tuple[str, Callable[[], None]]] = [
                ("사령부", pet.toggle_rpg_hub),
                ("가방", pet.show_rpg_bag_hub),
                ("채굴 출동", pet.start_roaming_excavation),
                ("침입자 수호", pet.start_desktop_skirmish),
                ("웨이브 디펜스", lambda: pet.start_wave_defense_game(pet.rpg_state.max_cleared_wave + 1)),
            ]
            for idx, (lbl, fn) in enumerate(items):
                r, c = divmod(idx, 2)
                grid.addWidget(self._make_btn(lbl, fn), r, c)

            in_combat = bool(
                getattr(pet, "_in_battle_arena", False)
                or str(getattr(getattr(pet, "_state", None), "name", "")) in {"SKIRMISH", "WAVE_DEFENSE"}
            )
            if in_combat:
                grid.addWidget(
                    self._make_btn("전투 종료", pet.stop_combat_and_defense, featured=True),
                    3,
                    0,
                    1,
                    2,
                )
            self._body_layout.addLayout(grid)

        elif key == "play":
            self._title_lbl.setText("놀이 · 30종")
            self.setFixedWidth(308)
            tab_row = QHBoxLayout()
            tab_row.setSpacing(5)
            for idx, (cat_name, _acts) in enumerate(PLAY_CATEGORIES):
                is_cur = idx == self._play_tab_idx

                def _switch(i=idx) -> None:
                    self._play_tab_idx = i
                    self._rebuild_contents()
                    self.adjustSize()
                    avail = (QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()).availableGeometry()
                    y = max(avail.top() + 8, min(avail.bottom() - self.height() - 8, self.y()))
                    self.move(self.x(), y)

                tab_btn = self._make_btn(
                    cat_name,
                    _switch,
                    active=is_cur,
                    close_after=False,
                    font_px=12,
                    pad="6px 6px",
                )
                tab_btn.setMinimumHeight(30)
                tab_row.addWidget(tab_btn)
            self._body_layout.addLayout(tab_row)

            _cat_name, activities = PLAY_CATEGORIES[self._play_tab_idx]
            grid = QGridLayout()
            grid.setSpacing(7)
            for idx, (lbl, act_key) in enumerate(activities):
                r, c = divmod(idx, 2)
                grid.addWidget(
                    self._make_btn(lbl, lambda k=act_key: pet.play_solo_action(k)),
                    r,
                    c,
                )
            self._body_layout.addLayout(grid)

        elif key == "action":
            self._title_lbl.setText("특수 액션")
            self.setFixedWidth(284)
            grid = QGridLayout()
            grid.setSpacing(7)
            specs: list[tuple[str, Callable[[], None]]] = [
                ("거미줄 스윙", pet.start_spider_swing),
                ("숨바꼭질", pet.start_hide_and_seek),
                ("화면 훔치기", pet.start_screen_content_heist),
                ("불꽃 축제", lambda: pet.start_magic_doodle("fireworks")),
                ("무지개 낙서", lambda: pet.start_magic_doodle()),
                ("슈퍼맨 비행", lambda: pet.start_superman_fly()),
                ("술래잡기", lambda: pet.start_mouse_evasion(mode="velocity", manual=True)),
                ("자유 산책", lambda: pet.start_omnidirectional_roam(mode="walk", manual=True)),
            ]
            for idx, (lbl, fn) in enumerate(specs):
                r, c = divmod(idx, 2)
                if idx == len(specs) - 1 and len(specs) % 2 == 1:
                    grid.addWidget(self._make_btn(lbl, fn), r, 0, 1, 2)
                else:
                    grid.addWidget(self._make_btn(lbl, fn), r, c)
            self._body_layout.addLayout(grid)

            coord = getattr(pet, "coordinator", None)
            if coord is not None:
                self._body_layout.addWidget(self._section_label("친구와 교감 (뽕뽕이 & 트리)"))
                p_grid = QGridLayout()
                p_grid.setSpacing(6)
                partner_specs: list[tuple[str, Callable[[], None]]] = [
                    ("달리기 시합", coord.start_running_race),
                    ("서로 술래잡기", coord.start_mutual_tag),
                    ("1:1 박치기 대결", coord.start_friendly_duel),
                    ("둘이 인사", coord.greet_each_other),
                    ("함께 춤추기", coord.duet_dance),
                    ("간식 파티", coord.share_snack),
                ]
                for idx, (lbl, fn) in enumerate(partner_specs):
                    r, c = divmod(idx, 2)
                    p_grid.addWidget(self._make_btn(lbl, fn, font_px=13, pad="6px 8px"), r, c)
                self._body_layout.addLayout(p_grid)
                partner_win = coord.get_partner(pet)
                if partner_win is not None:
                    p_name = getattr(partner_win, "char_display_name", "친구")
                    p_vis = partner_win.isVisible()
                    vis_lbl = f"{p_name} 숨기기" if p_vis else f"{p_name} 부르기"
                    self._body_layout.addWidget(
                        self._make_btn(
                            vis_lbl,
                            lambda p=pet: coord.toggle_partner_visibility(p),
                            active=p_vis,
                            font_px=13,
                            pad="6px 8px",
                        )
                    )

        elif key == "emotion":
            self._title_lbl.setText("감정 & 간식")
            self.setFixedWidth(286)
            self._body_layout.addWidget(
                self._make_btn("간식 주기", pet.feed_snack, featured=True, font_px=14)
            )
            self._body_layout.addWidget(self._section_label("감정 표현"))
            grid = QGridLayout()
            grid.setSpacing(6)
            emotions = [
                ("행복", "happy"),
                ("신남", "excited"),
                ("호기심", "curious"),
                ("졸림", "sleepy"),
                ("수줍음", "shy"),
                ("놀람", "surprised"),
                ("뾰로통", "pouty"),
                ("사랑", "loving"),
                ("슬픔", "sad"),
                ("뿌듯", "proud"),
            ]
            for idx, (lbl, em_key) in enumerate(emotions):
                r, c = divmod(idx, 2)
                grid.addWidget(
                    self._make_btn(lbl, lambda k=em_key: pet.trigger_emotion(k), font_px=13, pad="6px 8px"),
                    r,
                    c,
                )
            self._body_layout.addLayout(grid)

            self._body_layout.addWidget(self._section_label("기본 모션"))
            m_row = QHBoxLayout()
            m_row.setSpacing(6)

            def _play_basic_motion(act: str, dur: int) -> None:
                if pet._is_blocked_by_arena_or_hidden():
                    return
                coord_m = getattr(pet, "coordinator", None)
                if coord_m is not None and coord_m.is_minigame_active():
                    coord_m._stop_minigame()
                pet.cancel_all_active_actions()
                pet._decision_timer.stop()
                pet._set_3d_facing(0)
                pet.trigger_3d_action(act, duration_ms=dur)
                pet._schedule_next_decision(2600, 4200)

            for lbl, act_name, dur_ms in (
                ("인사", "Wave", 0),
                ("점프", "Jump", 0),
                ("댄스", "Dance", 3200),
                ("앉기", "Sit", 0),
            ):
                b = self._make_btn(
                    lbl,
                    lambda a=act_name, d=dur_ms: _play_basic_motion(a, d),
                    font_px=12,
                    pad="6px 6px",
                )
                b.setMinimumHeight(30)
                m_row.addWidget(b)
            self._body_layout.addLayout(m_row)

        elif key == "assistant":
            self._title_lbl.setText("업무 비서")
            self.setFixedWidth(266)
            grid = QGridLayout()
            grid.setSpacing(7)
            grid.addWidget(self._make_btn("메일함", pet.toggle_outlook_hud), 0, 0)
            grid.addWidget(self._make_btn("새 메일 확인", pet.check_mail_now), 0, 1)
            grid.addWidget(self._make_btn("알람", pet.open_alarm_manager), 1, 0)
            grid.addWidget(self._make_btn("PC 정리", lambda: pet.run_pc_cleanup(show_bubble=True)), 1, 1)
            self._body_layout.addLayout(grid)

            work_safe = bool(getattr(pet.rpg_state, "work_safe_mode", False))
            ws_lbl = "클릭 관통 모드 · 켜짐" if work_safe else "클릭 관통 모드 · 꺼짐"
            self._body_layout.addWidget(
                self._make_btn(
                    ws_lbl,
                    lambda cur=work_safe: pet.set_work_safe_mode(not cur, show_bubble=True),
                    active=work_safe,
                    close_after=not work_safe,
                )
            )

            coord = getattr(pet, "coordinator", None)
            cairn_mgr = getattr(coord, "cairn_manager", None) if coord is not None else None
            if cairn_mgr is not None:
                st = cairn_mgr.state
                self._body_layout.addWidget(
                    self._section_label(
                        f"출근~퇴근 돌탑 ({st.completed_layers}/{st.target_layers}층 · {st.current_layer_stones}/{st.stones_per_layer}돌)"
                    )
                )
                cairn_on = bool(cairn_mgr.enabled)
                c_lbl = "돌탑 쌓기 · 켜짐" if cairn_on else "돌탑 쌓기 · 꺼짐"

                def _toggle_cairn(cur=cairn_on, mgr=cairn_mgr) -> None:
                    nxt = not cur
                    for w in (mgr.ppong_win, mgr.tree_win):
                        w._prefs.enable_workday_cairn = nxt
                        w._prefs.save(w.char_id)
                    mgr.set_enabled(nxt)
                    self._rebuild_contents()

                self._body_layout.addWidget(
                    self._make_btn(
                        c_lbl,
                        _toggle_cairn,
                        active=cairn_on,
                        close_after=False,
                        font_px=12,
                        pad="6px 8px",
                    )
                )
                c_row = QHBoxLayout()
                c_row.setSpacing(6)
                c_row.addWidget(
                    self._make_btn(
                        "돌 1개 캐오기",
                        lambda m=cairn_mgr, p=pet: m.dispatch_stone_trip(p, manual=True),
                        font_px=12,
                        pad="6px 6px",
                    )
                )
                c_row.addWidget(
                    self._make_btn(
                        "돌탑 초기화",
                        lambda m=cairn_mgr, p=pet: m.reset_cairn(p),
                        close_after=False,
                        font_px=12,
                        pad="6px 6px",
                    )
                )
                self._body_layout.addLayout(c_row)

        elif key == "settings":
            self._title_lbl.setText("환경 설정")
            self.setFixedWidth(318)

            # 1. Size segmented row
            self._body_layout.addWidget(self._section_label("캐릭터 크기"))
            size_row = QHBoxLayout()
            size_row.setSpacing(5)
            cur_scale = round(float(getattr(pet, "_scale_factor", 0.10)), 2)
            scales = [0.10, 0.30, 0.50, 0.80, 1.00]
            closest = min(scales, key=lambda v: abs(v - cur_scale))
            for s in scales:
                def _set_size(val=s) -> None:
                    pet.set_scale_factor(val)
                    self._rebuild_contents()
                    self._ring.reposition_around_pet()

                b = self._make_btn(
                    f"{int(round(s * 100))}%",
                    _set_size,
                    active=(abs(s - closest) < 0.01),
                    close_after=False,
                    font_px=12,
                    pad="6px 4px",
                )
                b.setMinimumHeight(30)
                size_row.addWidget(b)
            self._body_layout.addLayout(size_row)

            # 2. Autonomous action frequency
            self._body_layout.addWidget(self._section_label("자율 액션 빈도"))
            freq_row = QHBoxLayout()
            freq_row.setSpacing(6)
            cur_freq = getattr(pet._prefs, "action_frequency", "normal")
            for f_lbl, f_key in (("자주", "frequent"), ("보통", "normal"), ("가끔", "rare"), ("끄기", "off")):
                def _set_freq(k=f_key) -> None:
                    pet.set_action_frequency(k)
                    self._rebuild_contents()

                b = self._make_btn(
                    f_lbl,
                    _set_freq,
                    active=(cur_freq == f_key),
                    close_after=False,
                    font_px=12,
                    pad="6px 6px",
                )
                b.setMinimumHeight(30)
                freq_row.addWidget(b)
            self._body_layout.addLayout(freq_row)

            # 3. Display & physics toggles
            self._body_layout.addWidget(self._section_label("표시 및 동작"))
            env_grid = QGridLayout()
            env_grid.setSpacing(6)
            env_toggles: list[tuple[str, bool, Callable[[bool], None]]] = [
                ("항상 위", bool(getattr(pet, "_always_on_top", True)), pet.set_always_on_top),
                ("풀밭·발자국", bool(getattr(pet, "_meadow_trail_enabled", True)), pet.set_meadow_trail_enabled),
                ("작업표시줄 중력", bool(getattr(pet, "_taskbar_gravity_enabled", True)), pet._set_taskbar_gravity_enabled),
                ("간헐 시선", bool(getattr(pet, "_intermittent_gaze_enabled", True)), pet.set_intermittent_gaze_enabled),
                ("PC 자동정리", bool(getattr(pet._prefs, "enable_pc_clean", True)), lambda chk: pet.toggle_action_feature("enable_pc_clean", chk)),
                ("윈도우 자동 시작", bool(getattr(pet._prefs, "auto_start_windows", True)), pet.set_auto_start_windows),
            ]
            for idx, (lbl, is_on, setter) in enumerate(env_toggles):
                def _toggle(cur=is_on, fn=setter) -> None:
                    fn(not cur)
                    self._rebuild_contents()

                r, c = divmod(idx, 2)
                b = self._make_btn(lbl, _toggle, active=is_on, close_after=False, font_px=12, pad="6px 8px")
                b.setMinimumHeight(30)
                if idx == len(env_toggles) - 1 and len(env_toggles) % 2 == 1:
                    env_grid.addWidget(b, r, 0, 1, 2)
                else:
                    env_grid.addWidget(b, r, c)
            self._body_layout.addLayout(env_grid)

            # 4. Autonomous special action allow-list
            self._body_layout.addWidget(self._section_label("자율 액션 허용"))
            feat_grid = QGridLayout()
            feat_grid.setSpacing(6)
            feat_items = [
                ("거미줄", "enable_spider"),
                ("숨바꼭질", "enable_peek"),
                ("화면훔치기", "enable_heist"),
                ("불꽃·낙서", "enable_doodle"),
                ("비행", "enable_superman"),
            ]
            for idx, (lbl, attr) in enumerate(feat_items):
                cur_on = bool(getattr(pet._prefs, attr, True))

                def _toggle_feat(a=attr, val=cur_on) -> None:
                    pet.toggle_action_feature(a, not val)
                    self._rebuild_contents()

                r, c = divmod(idx, 3)
                b = self._make_btn(lbl, _toggle_feat, active=cur_on, close_after=False, font_px=12, pad="5px 6px")
                b.setMinimumHeight(28)
                feat_grid.addWidget(b, r, c)
            self._body_layout.addLayout(feat_grid)

            # 5. Tools row
            self._body_layout.addWidget(self._section_label("도구"))
            tool_row = QHBoxLayout()
            tool_row.setSpacing(6)
            tool_row.addWidget(self._make_btn("AI 설정", pet._open_llm_settings, close_after=True, font_px=12, pad="6px 6px"))
            tool_row.addWidget(self._make_btn("위치 복귀", pet._place_on_taskbar, close_after=True, font_px=12, pad="6px 6px"))
            tool_row.addWidget(self._make_btn("3D 새로고침", pet.web_view.reload, close_after=True, font_px=12, pad="6px 6px"))
            self._body_layout.addLayout(tool_row)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._ring.close_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        pad = self.SHADOW_PAD
        card_rect = QRectF(pad, pad, self.width() - 2 * pad, self.height() - 2 * pad)

        # Soft multi-ring rounded shadow
        painter.setPen(Qt.PenStyle.NoPen)
        for expand, alpha in ((5.0, 12), (3.5, 18), (2.0, 26), (1.0, 34)):
            painter.setBrush(QColor(22, 14, 10, alpha))
            painter.drawRoundedRect(card_rect.adjusted(-expand, -expand + 2.5, expand, expand + 2.5), 18.0 + expand, 18.0 + expand)

        painter.setBrush(IVORY_BG)
        painter.setPen(QPen(IVORY_BORDER, 1.5))
        painter.drawRoundedRect(card_rect, 18.0, 18.0)
        painter.end()


class RadialFloatingMenu(QWidget):
    """
    Orbital radial floating menu surrounding Ppong-ppong-i in screen coordinates.
    """

    menu_closed = pyqtSignal()

    CANVAS_W = 368
    CANVAS_H = 378
    RING_CX = 184.0
    RING_CY = 192.0
    ORBIT_R = 128.0
    STD_R = 33.0
    FEATURED_R = 39.0

    # 9 orbital items arranged clockwise from 12:00 (-90 deg), spaced 40 deg apart
    BUTTON_SPECS: list[tuple[str, str, bool, bool]] = [
        ("chat", "Gemini", True, True),        # 0: 12:00 -90 deg (featured terracotta)
        ("world", "월드", False, False),     # 1: -50 deg
        ("play", "놀이", False, False),      # 2: -10 deg
        ("action", "액션", False, False),    # 3: +30 deg
        ("emotion", "감정", False, False),   # 4: +70 deg
        ("assistant", "비서", False, False), # 5: +110 deg
        ("settings", "설정", False, False),  # 6: +150 deg
        ("hide", "숨기기", True, False),     # 7: +190 deg
        ("quit", "끝내기", True, False),     # 8: +230 deg
    ]

    def __init__(self, pet_window) -> None:
        super().__init__(None)
        self._pet = pet_window
        self._font_family = "Pretendard"
        self._progress = 1.0
        self._ring_scale = 1.0
        self._ring_cx = self.RING_CX
        self._ring_cy = self.RING_CY
        self._orbit_r = self.ORBIT_R
        self._hover_idx: Optional[int] = None
        self._active_sub_idx: Optional[int] = None
        self._pill_hovered = False
        self._pill_rect = QRectF()
        self._event_filter_installed = False

        self._apply_window_flags(getattr(pet_window, "_always_on_top", True))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.CANVAS_W, self.CANVAS_H)

        self._sub_panel = RadialSubPanel(self)

        self._open_anim = QVariantAnimation(self)
        self._open_anim.setDuration(210)
        self._open_anim.setStartValue(0.15)
        self._open_anim.setEndValue(1.0)
        self._open_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._open_anim.valueChanged.connect(self._on_anim_tick)

        self.hide()

    def _apply_window_flags(self, always_on_top: bool) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def sync_always_on_top(self, enabled: bool) -> None:
        was_vis = self.isVisible()
        self._apply_window_flags(enabled)
        self._sub_panel.sync_always_on_top(enabled)
        if was_vis:
            self.show()

    def set_font_family(self, family: str) -> None:
        self._font_family = family or "Pretendard"
        self._sub_panel.set_font_family(self._font_family)

    def _on_anim_tick(self, val) -> None:
        self._progress = float(val)
        self.update()

    def _button_center(self, idx: int, scale_mult: float = 1.0) -> QPointF:
        angle_rad = math.radians(-90.0 + idx * 40.0)
        r = self._orbit_r * scale_mult
        return QPointF(self._ring_cx + r * math.cos(angle_rad), self._ring_cy + r * math.sin(angle_rad))

    def _button_radius(self, idx: int, scale_mult: float = 1.0) -> float:
        base = self.FEATURED_R if self.BUTTON_SPECS[idx][3] else self.STD_R
        return base * max(0.25, scale_mult)

    def _hit_button(self, pos: QPointF) -> Optional[int]:
        for idx in range(len(self.BUTTON_SPECS)):
            c = self._button_center(idx, self._progress)
            r = self._button_radius(idx, self._progress)
            dx = pos.x() - c.x()
            dy = pos.y() - c.y()
            if (dx * dx + dy * dy) <= r * r:
                return idx
        return None

    def open_around_pet(self) -> None:
        self._hover_idx = None
        self._active_sub_idx = None
        self._pill_hovered = False
        self._sub_panel.hide_panel()
        self.reposition_around_pet()

        if not self._event_filter_installed:
            app = QApplication.instance()
            if app is not None:
                app.installEventFilter(self)
                self._event_filter_installed = True

        self._progress = 0.15
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._open_anim.stop()
        self._open_anim.start()

    def reposition_around_pet(self) -> None:
        pet = self._pet
        scale = float(getattr(pet, "_scale_factor", 0.10))
        ring_scale = 1.0 if scale <= 0.35 else min(1.52, 1.0 + (scale - 0.35) * 1.65)
        self._ring_scale = ring_scale
        self._orbit_r = self.ORBIT_R * ring_scale
        cw = int(round(2.0 * (self._orbit_r + self.FEATURED_R + 17.0)))
        ch = cw + 10
        self._ring_cx = cw / 2.0
        self._ring_cy = ch / 2.0 + 3.0
        if self.width() != cw or self.height() != ch:
            self.setFixedSize(cw, ch)

        pet_cx = pet.x() + 220
        pet_cy = int(round(pet.y() + 469.1 - 185.75 * scale))

        screen = QGuiApplication.screenAt(QPoint(pet_cx, pet_cy)) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        x = pet_cx - int(round(self._ring_cx))
        y = pet_cy - int(round(self._ring_cy))
        margin = 6
        x = max(avail.left() + margin, min(avail.right() - cw - margin, x))
        y = max(avail.top() + margin, min(avail.bottom() - ch - margin, y))
        self.move(x, y)

        if self._sub_panel.isVisible() and self._active_sub_idx is not None:
            btn_local = self._button_center(self._active_sub_idx, 1.0)
            self._sub_panel._position_beside_ring(self.mapToGlobal(btn_local.toPoint()))

    def close_all(self) -> None:
        was_vis = self.isVisible()
        self._open_anim.stop()
        self._sub_panel.hide_panel()
        self._active_sub_idx = None
        self._hover_idx = None
        self._pill_hovered = False
        if self._event_filter_installed:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
            self._event_filter_installed = False
        self.hide()
        if was_vis:
            self.menu_closed.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self.isVisible() and event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(event, "globalPosition"):
                gp = event.globalPosition().toPoint()
            else:
                gp = QPoint(-9999, -9999)
            inside_ring = self.frameGeometry().contains(gp)
            inside_sub = self._sub_panel.isVisible() and self._sub_panel.frameGeometry().contains(gp)
            if not inside_ring and not inside_sub:
                self.close_all()
        return super().eventFilter(watched, event)

    def _activate_button(self, idx: int) -> None:
        key, _label, is_direct, _featured = self.BUTTON_SPECS[idx]
        if is_direct:
            self.close_all()
            if key == "chat":
                self._pet.on_pet_activated()
            elif key == "hide":
                self._pet.hide_to_tray()
            elif key == "quit":
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            return

        if self._active_sub_idx == idx and self._sub_panel.isVisible():
            self._active_sub_idx = None
            self._sub_panel.hide_panel()
            self.update()
            return

        self._active_sub_idx = idx
        btn_global = self.mapToGlobal(self._button_center(idx, 1.0).toPoint())
        self._sub_panel.open_for(key, btn_global)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        hit = self._hit_button(pos)
        pill_hit = (hit is None) and self._pill_rect.contains(pos)
        if hit != self._hover_idx or pill_hit != self._pill_hovered:
            self._hover_idx = hit
            self._pill_hovered = pill_hit
            if hit is not None or pill_hit:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_idx = None
        self._pill_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            hit = self._hit_button(pos)
            if hit is not None:
                self._activate_button(hit)
                event.accept()
                return
            if self._pill_rect.contains(pos):
                self.close_all()
                self._pet.toggle_rpg_hub()
                event.accept()
                return
            # Center transparent area or outside buttons -> close cleanly
            self.close_all()
            event.accept()
            return
        elif event.button() == Qt.MouseButton.RightButton:
            self.close_all()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_all()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        prog = max(0.05, self._progress)
        alpha_mult = max(0.0, min(1.0, (prog - 0.1) / 0.9))
        painter.setOpacity(alpha_mult)

        # 1. Dashed circular orbital track connecting button centers
        orbit_r = self._orbit_r * prog
        orbit_pen = QPen(QColor(255, 255, 255, 210), 2.2)
        orbit_pen.setStyle(Qt.PenStyle.CustomDashLine)
        orbit_pen.setDashPattern([5.0, 5.0])
        orbit_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(orbit_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(self._ring_cx, self._ring_cy), orbit_r, orbit_r)

        # 2. Compact status pill directly beneath 12:00 featured circle
        rpg = getattr(self._pet, "rpg_state", None)
        lv = int(getattr(rpg, "pet_level", 1))
        gold = int(getattr(rpg, "gold", 0))
        pill_text = f"Lv.{lv} · {gold:,} G"
        pill_font = QFont(self._font_family, 10, QFont.Weight.Bold)
        pill_font.setPixelSize(12)
        fm = QFontMetrics(pill_font)
        text_w = fm.horizontalAdvance(pill_text)
        pill_w = max(98.0, text_w + 30.0)
        pill_h = 25.0
        pill_cx = self._ring_cx
        pill_offset = max(74.0, self._orbit_r - self.FEATURED_R - 15.0)
        pill_cy = self._ring_cy - pill_offset * prog
        self._pill_rect = QRectF(pill_cx - pill_w / 2.0, pill_cy - pill_h / 2.0, pill_w, pill_h)

        # Pill shadow + background
        painter.setPen(Qt.PenStyle.NoPen)
        for expand, a in ((3.0, 16), (1.5, 28)):
            painter.setBrush(QColor(20, 12, 8, a))
            painter.drawRoundedRect(self._pill_rect.adjusted(-expand, -expand + 2.0, expand, expand + 2.0), 12.5 + expand, 12.5 + expand)
        painter.setBrush(QColor(251, 248, 244, 244) if not self._pill_hovered else IVORY_HOVER)
        painter.setPen(QPen(TERRACOTTA if self._pill_hovered else QColor("#E8DED3"), 1.3))
        painter.drawRoundedRect(self._pill_rect, 12.5, 12.5)

        # Small terracotta diamond/dot accent + status label
        dot_x = self._pill_rect.left() + 11.0
        painter.setBrush(TERRACOTTA)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(dot_x, pill_cy), 3.4, 3.4)

        painter.setFont(pill_font)
        painter.setPen(QColor("#3D2E27"))
        text_rect = QRectF(dot_x + 6.0, self._pill_rect.top(), self._pill_rect.right() - dot_x - 10.0, pill_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, pill_text)

        # 3. Render 9 orbital buttons (featured button drawn last so it sits crisply on top)
        draw_order = [i for i in range(len(self.BUTTON_SPECS)) if not self.BUTTON_SPECS[i][3]] + [
            i for i in range(len(self.BUTTON_SPECS)) if self.BUTTON_SPECS[i][3]
        ]
        for idx in draw_order:
            key, label, _direct, is_featured = self.BUTTON_SPECS[idx]
            center = self._button_center(idx, prog)
            r = self._button_radius(idx, prog)
            is_hovered = idx == self._hover_idx
            is_active = idx == self._active_sub_idx
            if is_hovered:
                r *= 1.05

            _draw_soft_shadow_circle(painter, center.x(), center.y(), r)

            if is_featured:
                grad = QLinearGradient(center.x(), center.y() - r, center.x(), center.y() + r)
                grad.setColorAt(0.0, TERRACOTTA_HOVER if is_hovered else TERRACOTTA_TOP)
                grad.setColorAt(1.0, TERRACOTTA_BOTTOM)
                painter.setBrush(grad)
                border_pen = QPen(QColor(255, 255, 255, 190 if is_hovered else 95), 2.2 if is_hovered else 1.4)
                painter.setPen(border_pen)
                painter.drawEllipse(center, r, r)

                _draw_button_icon(painter, key, center.x(), center.y() - 9.5, WHITE)
                lbl_font = QFont(self._font_family, 10, QFont.Weight.Bold)
                lbl_font.setPixelSize(14)
                painter.setFont(lbl_font)
                painter.setPen(WHITE)
                painter.drawText(
                    QRectF(center.x() - r, center.y() + 4.5, r * 2.0, 23.0),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )
            else:
                painter.setBrush(IVORY_HOVER if (is_hovered or is_active) else IVORY_BG)
                if is_hovered or is_active:
                    border_pen = QPen(TERRACOTTA, 2.6)
                else:
                    border_pen = QPen(QColor(226, 213, 200, 225), 1.5)
                painter.setPen(border_pen)
                painter.drawEllipse(center, r, r)

                _draw_button_icon(painter, key, center.x(), center.y() - 9.0, TERRACOTTA)
                lbl_font = QFont(self._font_family, 10, QFont.Weight.Bold)
                lbl_font.setPixelSize(13)
                painter.setFont(lbl_font)
                painter.setPen(TERRACOTTA if (is_hovered or is_active) else ESPRESSO)
                painter.drawText(
                    QRectF(center.x() - r + 2.0, center.y() + 4.0, r * 2.0 - 4.0, 22.0),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )

        painter.end()
