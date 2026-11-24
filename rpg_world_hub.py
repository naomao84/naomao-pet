#!/usr/bin/env python3
"""
Ppong-ppong-i 3D World RPG, Economy, Task Dispatch & Wave Defense Hub (v2.0)
============================================================================
Provides:
  1. RPGWorldState: Persistent JSON save/load (`pet_rpg_save.json`), offline crop growth,
     mandatory causality economy formulas (Mining + Farming + Fishing -> Cooking + Blacksmith + Turrets -> Wave Defense).
  2. RPGWorldHubDrawer: Non-intrusive glassmorphic floating command center (`Ctrl+R`) for:
     - 3-Slot Task Dispatch Queue (채굴 / 농사 / 낚시 / 경비 오더)
     - 4 Multi-Worldview Theme Switcher (판타지 / 사이버펑크 / 스페이스 SF / 코지 힐링)
     - Work-Safe Click-Through Mode Toggle (`Ctrl+Shift+W`)
     - Shop & Trade (Crop/Fish selling for Gold)
     - Battle Bento Kitchen (Crop + Fish -> Defense Buff Bento)
     - Blacksmith & Turret Workshop (Ore + Gold + Core -> Weapon 4-Tier Evolution & 4 Defense Turrets)
     - Skirmish & 3D Wave Siege Defense Mini-Game Launcher
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


SAVE_FILE_NAME = "pet_rpg_save.json"

WORLDVIEW_INFO = {
    "fantasy": {
        "title": "🌿 판타지 왕국",
        "label": "🌿 판타지 왕국",
        "desc": "마나 수정과 룬 블레이드, 슬라임과 드래곤의 정통 판타지 월드",
        "unlock_wave": 0,
    },
    "cyberpunk": {
        "title": "🌃 사이버펑크 네온",
        "label": "🌃 사이버펑크 네온",
        "desc": "양자 코어 채굴과 플라즈마 카타나, 해커 드론이 침입하는 네온 시티",
        "unlock_wave": 5,
    },
    "scifi": {
        "title": "🚀 스페이스 오디세이",
        "label": "🚀 스페이스 오디세이",
        "desc": "소행성 다크매터 채굴과 광선검, 외계 함대를 막아내는 우주 기지",
        "unlock_wave": 10,
    },
    "cozy": {
        "title": "🌼 코지 힐링 아일랜드",
        "label": "🌼 코지 힐링 아일랜드",
        "desc": "별의 조각 발굴과 비눗방울 정화 마법! 폭력 없는 평화로운 힐링 섬",
        "unlock_wave": 15,
    },
}

BENTO_RECIPES = {
    "potato_fish": {
        "name": "🥔 감자 생선구이",
        "crops": 2,
        "fish_common": 1,
        "fish_rare": 0,
        "desc": "HP +120 즉시 회복 / 공격력 +12% / 공속 +10% (Wave 1~4 권장)",
    },
    "trout_steak": {
        "name": "🍣 무지개 송어 스테이크",
        "crops": 2,
        "fish_common": 1,
        "fish_rare": 1,
        "desc": "HP +180 회복 / 공격력 +20% / 공속 +28% (Wave 5 보스 필수!)",
    },
    "carp_stew": {
        "name": "🍲 황금 잉어 매운탕",
        "crops": 3,
        "fish_common": 0,
        "fish_rare": 2,
        "desc": "HP +280 회복 / 공격력 +35% / 공속 +20% (Wave 10 보스 필수!)",
    },
    "star_emperor": {
        "name": "🍱 별빛 해산물 황제 도시락",
        "crops": 4,
        "fish_common": 2,
        "fish_rare": 2,
        "desc": "HP +500 회복 / 공격력 +45% / 공속 +35% (Wave 15+ 보스 필수!)",
    },
}

TURRET_SPECS = {
    "barricade": {
        "name": "🧱 성소 성벽 요새",
        "base_gold": 80,
        "ore_common": 3,
        "ore_rare": 0,
        "wood": 2,
        "core": 0,
        "desc": "성소 최대 HP +260/Lv 증가 및 적 공격 피해 8%/Lv 경감 (최대 40%)",
    },
    "ballista": {
        "name": "🏹 연발 발리스타",
        "base_gold": 80,
        "ore_common": 3,
        "ore_rare": 1,
        "wood": 2,
        "core": 0,
        "desc": "초고속 연발 물리 화살 (Lv.3 더블볼트 / Lv.5 치명타+표식 +15%)",
    },
    "cannon": {
        "name": "💣 공성 박격포",
        "base_gold": 130,
        "ore_common": 4,
        "ore_rare": 1,
        "wood": 1,
        "core": 0,
        "desc": "광역 포격(방패병 피해 1.65배!) — Lv.4 기절 / Lv.5 3연발 클러스터",
    },
    "frost": {
        "name": "❄️ 프로스트 타워",
        "base_gold": 110,
        "ore_common": 2,
        "ore_rare": 2,
        "wood": 0,
        "core": 1,
        "desc": "빙결 감속 38~58% + 취약(+12~28%) + Lv.3 주술사 치유 억제(-45~65%)",
    },
    "arc": {
        "name": "⚡ 테슬라 코일",
        "base_gold": 160,
        "ore_common": 2,
        "ore_rare": 3,
        "wood": 0,
        "core": 2,
        "desc": "3~7연쇄 번개(마도사·주술사 +35% 피해) — Lv.4 빙결 적 추가피해",
    },
    "sniper": {
        "name": "🔮 아케인 저격탑",
        "base_gold": 180,
        "ore_common": 2,
        "ore_rare": 3,
        "wood": 1,
        "core": 1,
        "desc": "초장거리(11.5~17m) 방어 85~100% 관통 — 보스·원거리 마도사 암살",
    },
}

PLACEABLE_TOWER_TYPES: tuple[str, ...] = ("ballista", "cannon", "frost", "arc", "sniper")
PAD_IDS: tuple[str, ...] = ("pad_0", "pad_1", "pad_2", "pad_3", "pad_4")

TYPING_RANK_TITLES: list[tuple[int, str]] = [
    (1, "⌨️ 수습 타자견습"),
    (2, "⌨️ 숙련 키보드전사"),
    (3, "⌨️ 철갑 손가락 기사"),
    (4, "🔥 기계식 축의 지배자"),
    (5, "⚡ 광속 타건 마스터"),
    (6, "💎 에테르 키캡 군주"),
    (7, "🌟 성소 수호 대장군"),
    (8, "👑 차원 타건 패왕"),
    (9, "🏆 전설의 신화 타자왕"),
    (10, "🌌 초월 그랜드마스터"),
]


def typing_delta_for_level(level: int) -> int:
    """Hardcore escalating keystroke requirement: Lv.1->2 = 10,000 keystrokes, scaling by L^1.35."""
    lv = max(1, int(level))
    return int(round((10000.0 * (lv ** 1.35)) / 100.0)) * 100


def get_typing_rank_title(level: int) -> str:
    lv = max(1, int(level))
    title = TYPING_RANK_TITLES[0][1]
    for min_lv, label in TYPING_RANK_TITLES:
        if lv >= min_lv:
            title = label
    return title


def calc_typing_level_progress(total_keystrokes: int) -> tuple[int, int, int, str]:
    """Returns (level, current_progress_in_level, required_for_next_level, rank_title)."""
    rem = max(0, int(total_keystrokes))
    lv = 1
    while lv < 99:
        req = typing_delta_for_level(lv)
        if rem < req:
            return lv, rem, req, get_typing_rank_title(lv)
        rem -= req
        lv += 1
    req = typing_delta_for_level(lv)
    return lv, rem, req, get_typing_rank_title(lv)

CONSUMABLE_SPECS = {
    "hp_potion": {
        "name": "🧪 생명의 빨간 포션",
        "icon": "🧪",
        "gold": 45,
        "crops": 1,
        "ore_common": 0,
        "ore_rare": 0,
        "core": 0,
        "desc": "즉시 영웅 HP +220 및 성소 코어 HP +120 회복",
    },
    "haste_elixir": {
        "name": "⚡ 질풍의 가속 비약",
        "icon": "⚡",
        "gold": 75,
        "crops": 1,
        "ore_common": 1,
        "ore_rare": 0,
        "core": 0,
        "desc": "25초간 이동속도·공격속도·포탑 연사력 +50% 가속",
    },
    "rage_elixir": {
        "name": "🔥 광전사의 분노 비약",
        "icon": "🔥",
        "gold": 95,
        "crops": 1,
        "ore_common": 2,
        "ore_rare": 0,
        "core": 0,
        "desc": "25초간 영웅 및 포탑 공격력 +65% 증폭",
    },
    "meteor_scroll": {
        "name": "📜 천벌 메테오 주문서",
        "icon": "☄️",
        "gold": 140,
        "crops": 0,
        "ore_common": 1,
        "ore_rare": 1,
        "core": 0,
        "desc": "바탕화면 전장 전체에 6발의 유성우 폭격 (광역 대화력)",
    },
    "shield_scroll": {
        "name": "🛡️ 성소 절대방어 주문서",
        "icon": "🛡️",
        "gold": 130,
        "crops": 0,
        "ore_common": 2,
        "ore_rare": 0,
        "core": 1,
        "desc": "성소 수호 코어 HP +350 수리 및 12초간 피해 무적 방어막",
    },
    "luck_potion": {
        "name": "🧲 행운의 황금 비약",
        "icon": "🍀",
        "gold": 110,
        "crops": 1,
        "ore_common": 0,
        "ore_rare": 1,
        "core": 0,
        "desc": "45초간 사냥·채집 골드 및 희귀 전리품 획득량 2배",
    },
}

WEAPON_SPECS = {
    "fist": {
        "name": "👊 맨손 무투 (기본 근접)",
        "short": "👊 맨손",
        "icon": "👊",
        "gold": 0,
        "ore_common": 0,
        "ore_rare": 0,
        "wood": 0,
        "core": 0,
        "desc": "기본 근접 격투: 적에게 달려가 왼손 잽 ➔ 오른손 훅 ➔ 승룡 어퍼컷 & 회전 발차기로 제압합니다.",
    },
    "sword": {
        "name": "🗡️ 기사단 룬 명검 (칼)",
        "short": "🗡️ 칼(명검)",
        "icon": "🗡️",
        "gold": 90,
        "ore_common": 3,
        "ore_rare": 0,
        "wood": 1,
        "core": 0,
        "desc": "근중거리 도검 무장: 3연속 초승달 검기 베기 및 도약 회전 참격(광역 스플래시)을 구사합니다.",
    },
    "bow": {
        "name": "🏹 엘프의 바람 장궁 (활)",
        "short": "🏹 활(장궁)",
        "icon": "🏹",
        "gold": 160,
        "ore_common": 2,
        "ore_rare": 1,
        "wood": 3,
        "core": 0,
        "desc": "중장거리 궁술 무장: 적과 거리를 유지하며 3D 깃털 화살 곡사 사격 및 3타 부채꼴 3연발 멀티샷을 발사합니다.",
    },
    "gun": {
        "name": "🔫 네온 플라즈마 블래스터 (총)",
        "short": "🔫 총(블래스터)",
        "icon": "🔫",
        "gold": 260,
        "ore_common": 3,
        "ore_rare": 2,
        "wood": 0,
        "core": 1,
        "desc": "장거리 중화기 무장: 초고속 플라즈마 탄환 직사 사격 및 3타 광역 폭발 에너지 캐논을 발포합니다.",
    },
}


class RPGWorldState:
    """Manages persistent RPG stats, inventory, farm growth, economy, and defense progression."""

    def __init__(self, data_dir: Path) -> None:
        self.save_path = data_dir / SAVE_FILE_NAME
        self.schema_version: int = 2
        self.worldview: str = "fantasy"
        self.unlocked_worldviews: list[str] = ["fantasy", "cyberpunk", "scifi", "cozy"]
        self.work_safe_mode: bool = False
        self.basecamp_visible: bool = True

        self.pet_level: int = 1
        self.pet_xp: int = 0
        self.gold: int = 250
        self.live_cpm: int = 0

        self.equipped_weapon: str = "fist"
        self.unlocked_weapons: list[str] = ["fist"]
        self.weapon_enhance: int = 0
        self.pickaxe_tier: int = 1
        self.rod_tier: int = 1
        self.watering_tier: int = 1

        self.inventory: dict[str, int] = {
            "ore_common": 6,
            "ore_rare": 2,
            "ore_legendary": 0,
            "invader_core": 1,
            "crops": 4,
            "wood": 3,
            "fish_common": 2,
            "fish_rare": 1,
        }
        self.bentos: dict[str, int] = {
            "potato_fish": 1,
            "trout_steak": 0,
            "carp_stew": 0,
            "star_emperor": 0,
        }
        self.turrets: dict[str, int] = {
            "barricade": 1,
            "ballista": 1,
            "cannon": 0,
            "frost": 0,
            "arc": 0,
            "sniper": 0,
        }
        self.tower_pads: dict[str, Optional[dict]] = {
            "pad_0": {"type": "ballista", "level": 1},
            "pad_1": None,
            "pad_2": None,
            "pad_3": None,
            "pad_4": None,
        }
        today_str = time.strftime("%Y-%m-%d")
        self.typing_stats: dict[str, object] = {
            "total_keystrokes": 0,
            "today_date": today_str,
            "today_keystrokes": 0,
            "peak_cpm_today": 0,
            "daily_milestones_claimed": [],
            "fever_buff_date": "",
            "legacy_combat_xp": 0,
        }
        self.last_defense_report: Optional[dict] = None
        self.consumables: dict[str, int] = {
            "hp_potion": 2,
            "haste_elixir": 1,
            "rage_elixir": 1,
            "meteor_scroll": 1,
            "shield_scroll": 1,
            "luck_potion": 1,
        }
        self.collected_items: dict[str, dict] = {
            "구리 원석": {"icon": "🪨", "tier": "Common", "count": 6, "category": "채굴 광물"},
            "자수정 클러스터": {"icon": "💎", "tier": "Rare", "count": 2, "category": "채굴 광물"},
            "튼튼 감자": {"icon": "🥔", "tier": "Common", "count": 4, "category": "농장 작물"},
            "은빛 피라미": {"icon": "🐟", "tier": "Common", "count": 2, "category": "낚시 어종"},
            "슬라임 젤리 핵": {"icon": "🟢", "tier": "Common", "count": 1, "category": "사냥 전리품"},
        }
        self.farm: dict[str, object] = {
            "planted": True,
            "growth": 0.45,
            "watered": True,
            "cropType": "튼튼 감자",
            "last_update_ts": time.time(),
        }
        self.dispatch_queue: list[str] = []
        self.highest_wave: int = 0
        self.total_enemies_defeated: int = 0
        self.skill_xp: dict[str, int] = {
            "mining": 0,
            "fishing": 0,
            "gardening": 0,
            "cooking": 0,
            "hunting": 0,
        }
        self.load()

    @property
    def level(self) -> int:
        return self.pet_level

    @property
    def max_cleared_wave(self) -> int:
        return self.highest_wave

    @max_cleared_wave.setter
    def max_cleared_wave(self, val: int) -> None:
        self.highest_wave = max(self.highest_wave, int(val))

    @property
    def farm_stage(self) -> int:
        g = float(self.farm.get("growth", 0.0))
        if g >= 1.0:
            return 3
        if g >= 0.60:
            return 2
        if g >= 0.25:
            return 1
        return 0

    @property
    def weapon_tier(self) -> int:
        if self.weapon_enhance >= 10:
            return 4
        if self.weapon_enhance >= 7:
            return 3
        if self.weapon_enhance >= 3:
            return 2
        return 1

    @property
    def fever_active(self) -> bool:
        today_str = time.strftime("%Y-%m-%d")
        if self.typing_stats.get("today_date") != today_str:
            return False
        return self.pet_level >= 5 and int(self.typing_stats.get("today_keystrokes", 0)) >= 1000

    @property
    def hero_atk(self) -> int:
        L = max(1, int(self.pet_level))
        base_wep = 6 + self.weapon_tier * 4
        raw = 18 + 6 * (L - 1) + base_wep * (1.0 + 0.14 * self.weapon_enhance)
        lv_mult = 1.0 + 0.08 * (L - 1)
        fever_mult = 1.12 if self.fever_active else 1.0
        return int(round(raw * lv_mult * fever_mult))

    @property
    def hero_max_hp(self) -> int:
        L = max(1, int(self.pet_level))
        bar = int(self.turrets.get("barricade", 0))
        raw = 280 + 65 * (L - 1) + self.weapon_enhance * 28 + bar * 140
        return int(round(raw * (1.0 + 0.05 * (L - 1))))

    @property
    def base_max_hp(self) -> int:
        L = max(1, int(self.pet_level))
        bar = int(self.turrets.get("barricade", 0))
        return int(round(920 + 120 * (L - 1) + bar * 260))

    @property
    def partner_cp(self) -> int:
        L = max(1, int(self.pet_level))
        return int(round(self.hero_atk * 0.68 * 3.5 + (L - 1) * 18))

    def typing_bonuses(self) -> dict:
        L = max(1, int(self.pet_level))
        total_k = int(self.typing_stats.get("total_keystrokes", 0))
        _, cur_in, req_next, rank_title = calc_typing_level_progress(total_k)
        return {
            "level": L,
            "totalKeystrokes": total_k,
            "curLevelProgress": cur_in,
            "curLevelReq": req_next,
            "todayKeystrokes": int(self.typing_stats.get("today_keystrokes", 0)),
            "liveCpm": int(self.live_cpm),
            "peakCpmToday": int(self.typing_stats.get("peak_cpm_today", 0)),
            "feverActive": self.fever_active,
            "rankTitle": rank_title,
            "atkMult": round(1.0 + 0.08 * (L - 1), 3),
            "towerDmgMult": round(1.0 + 0.05 * (L - 1), 3),
            "towerSpdMult": round((1.0 + 0.02 * min(15, L - 1)) * (1.10 if L >= 10 else 1.0), 3),
            "critChance": round(min(0.55, 0.16 + 0.025 * (L - 1)), 3),
            "critMult": round(1.35 + 0.05 * min(10, L - 1), 3),
            "upgradeDiscount": 0.08 if L >= 4 else 0.0,
            "waveStartGoldBonus": 60 if L >= 2 else 0,
            "skillCdMult": 0.94 if L >= 2 else 1.0,
            "armorPenBonus": 0.10 if L >= 7 else 0.0,
        }

    def record_keystrokes(self, delta: int, live_cpm: int = 0) -> dict:
        """Records real OS keyboard keystrokes toward the hardcore 10,000-keystroke leveling curve."""
        today_str = time.strftime("%Y-%m-%d")
        if self.typing_stats.get("today_date") != today_str:
            self.typing_stats["today_date"] = today_str
            self.typing_stats["today_keystrokes"] = 0
            self.typing_stats["peak_cpm_today"] = 0
            self.typing_stats["daily_milestones_claimed"] = []

        self.live_cpm = max(0, int(live_cpm))
        if self.live_cpm > int(self.typing_stats.get("peak_cpm_today", 0)):
            self.typing_stats["peak_cpm_today"] = self.live_cpm

        add = max(0, int(delta))
        if add <= 0:
            return {
                "leveled_up": False,
                "new_level": self.pet_level,
                "rank_title": get_typing_rank_title(self.pet_level),
                "milestones": [],
            }

        prev_lv = self.pet_level
        total_k = int(self.typing_stats.get("total_keystrokes", 0)) + add
        today_k = int(self.typing_stats.get("today_keystrokes", 0)) + add
        self.typing_stats["total_keystrokes"] = total_k
        self.typing_stats["today_keystrokes"] = today_k
        self.pet_xp = total_k

        new_lv, _, _, rank_title = calc_typing_level_progress(total_k)
        self.pet_level = new_lv
        leveled_up = new_lv > prev_lv

        claimed = list(self.typing_stats.get("daily_milestones_claimed", []))
        milestones: list[str] = []
        milestone_rewards = [
            (500, "일일 500타 달성 (+25G)", {"gold": 25}),
            (2000, "일일 2,000타 달성 (+100G, 희귀광석 +1)", {"gold": 100, "ore_rare": 1}),
            (5000, "일일 5,000타 달성 (+250G, 송어스테이크 +1)", {"gold": 250, "trout_steak": 1}),
            (10000, "일일 10,000타 피버 달성 (+500G, 코어 +1)", {"gold": 500, "invader_core": 1, "fever": True}),
        ]
        for threshold, label, rew in milestone_rewards:
            if today_k >= threshold and threshold not in claimed:
                claimed.append(threshold)
                if rew.get("gold"):
                    self.gold += int(rew["gold"])
                if rew.get("ore_rare"):
                    self.inventory["ore_rare"] = self.inventory.get("ore_rare", 0) + int(rew["ore_rare"])
                if rew.get("invader_core"):
                    self.inventory["invader_core"] = self.inventory.get("invader_core", 0) + int(rew["invader_core"])
                if rew.get("trout_steak"):
                    self.bentos["trout_steak"] = self.bentos.get("trout_steak", 0) + int(rew["trout_steak"])
                if rew.get("fever"):
                    self.typing_stats["fever_buff_date"] = today_str
                milestones.append(label)
        self.typing_stats["daily_milestones_claimed"] = claimed
        return {
            "leveled_up": leveled_up,
            "new_level": new_lv,
            "rank_title": rank_title,
            "milestones": milestones,
        }

    @property
    def tool_bonus_rare(self) -> float:
        avg_tool = (self.pickaxe_tier + self.rod_tier + self.watering_tier) / 3.0
        return min(0.25, (avg_tool - 1.0) * 0.06)

    def add_pet_xp(self, amount: int) -> bool:
        """Casual combat/solo XP accrues into legacy_combat_xp; pet_level advances strictly via typing."""
        gain = max(0, int(amount))
        self.typing_stats["legacy_combat_xp"] = int(self.typing_stats.get("legacy_combat_xp", 0)) + gain
        return False

    def add_xp(self, amount: int) -> bool:
        return self.add_pet_xp(amount)

    def consume_bento_from_js(self, bento_key: Optional[str] = None) -> bool:
        """Deducts the consumed battle bento from persistent inventory when auto-eaten in JS."""
        if bento_key and self.bentos.get(bento_key, 0) > 0:
            self.bentos[bento_key] -= 1
            self.save()
            return True
        for k in ["star_emperor", "carp_stew", "trout_steak", "potato_fish"]:
            if self.bentos.get(k, 0) > 0:
                self.bentos[k] -= 1
                self.save()
                return True
        return False

    def tick_farm_growth(self) -> bool:
        """Advances crop growth based on elapsed real/offline time. Returns True if newly ready."""
        now = time.time()
        last_ts = float(self.farm.get("last_update_ts", now))
        elapsed = max(0.0, now - last_ts)
        self.farm["last_update_ts"] = now
        if not self.farm.get("planted", True):
            return False
        prev_g = float(self.farm.get("growth", 0.0))
        if prev_g >= 1.0:
            return False
        speed_mult = (1.5 if self.farm.get("watered", False) else 0.8) * (1.0 + (self.watering_tier - 1) * 0.25)
        # Full growth in ~120 seconds of watered real/offline time
        new_g = min(1.0, prev_g + (elapsed / 120.0) * speed_mult)
        self.farm["growth"] = round(new_g, 3)
        return prev_g < 1.0 and new_g >= 1.0

    def harvest_farm(self) -> tuple[bool, str]:
        self.tick_farm_growth()
        g = float(self.farm.get("growth", 0.0))
        if g < 1.0:
            pct = int(g * 100)
            return False, f"아직 작물이 자라는 중이에요! (현재 성장률 {pct}% — 물주기로 가속 가능 🌱)"
        yield_crops = 2 + self.watering_tier
        yield_wood = 1 + (1 if self.watering_tier >= 2 else 0)
        self.inventory["crops"] = self.inventory.get("crops", 0) + yield_crops
        self.inventory["wood"] = self.inventory.get("wood", 0) + yield_wood
        self.farm["growth"] = 0.10
        self.farm["watered"] = True
        self.farm["last_update_ts"] = time.time()
        self.add_pet_xp(20)
        self.save()
        return True, f"🌾 텃밭 대풍작 수확 완료! 농작물 +{yield_crops}개, 농장 목재 +{yield_wood}개 획득!"

    def water_farm(self) -> str:
        self.tick_farm_growth()
        self.farm["watered"] = True
        prev_g = float(self.farm.get("growth", 0.0))
        boost = 0.28 + (self.watering_tier - 1) * 0.08
        self.farm["growth"] = min(1.0, round(prev_g + boost, 3))
        self.farm["last_update_ts"] = time.time()
        self.save()
        pct = int(float(self.farm["growth"]) * 100)
        return f"💧 정성껏 물을 주었어요! 작물 성장률 {pct}% 달성!"

    def process_solo_reward(self, payload: dict) -> str:
        """Converts solo_play.js rewards into persistent RPG ores, crops, fish, bentos, and XP."""
        key = str(payload.get("key", ""))
        item_name = str(payload.get("item", "보상 아이템"))
        tier = str(payload.get("tier", "Common"))
        gained_xp = int(payload.get("gained", 25))
        total_xp = int(payload.get("xp", 0))

        if key:
            self.skill_xp[key] = max(self.skill_xp.get(key, 0), total_xp)
        leveled = self.add_pet_xp(gained_xp)

        icon_map = {
            "mining": "⛏️",
            "treasure": "👑",
            "explorer": "🧭",
            "fishing": "🐟",
            "gardening": "🌱",
            "hunting": "🏹",
            "cooking": "🍳",
            "barista": "☕",
            "picnic": "🧺",
        }
        cat_map = {
            "mining": "채굴 광물",
            "treasure": "보물 탐사",
            "explorer": "오지 탐험",
            "fishing": "낚시 어종",
            "gardening": "농장 채집",
            "hunting": "사냥 전리품",
            "cooking": "요리 특산품",
        }
        self.record_collected_item(
            name=item_name,
            icon=str(payload.get("icon", icon_map.get(key, "🎁"))),
            tier=tier,
            category=cat_map.get(key, "생활/탐험 획득"),
            amount=1,
        )

        bonus_msg = ""
        if key in {"mining", "treasure", "explorer"}:
            if tier == "Legendary":
                self.inventory["ore_legendary"] += 1
                self.inventory["ore_rare"] += 2
                bonus_msg = "전설 광석 +1, 희귀 광석 +2"
            elif tier == "Rare":
                self.inventory["ore_rare"] += 2
                self.inventory["ore_common"] += 2
                bonus_msg = "희귀 광석 +2, 일반 광석 +2"
            else:
                amt = 2 + self.pickaxe_tier
                self.inventory["ore_common"] += amt
                bonus_msg = f"일반 광석 +{amt}"
        elif key == "fishing":
            if tier in {"Rare", "Legendary"}:
                amt = 2 if tier == "Legendary" else 1
                self.inventory["fish_rare"] += amt
                self.gold += 35 * amt
                bonus_msg = f"희귀 어종 +{amt}, 납품 보너스 +{35 * amt}G"
            else:
                amt = 1 + (1 if self.rod_tier >= 2 else 0)
                self.inventory["fish_common"] += amt
                self.gold += 15
                bonus_msg = f"일반 어종 +{amt}, +15G"
        elif key in {"gardening", "hunting"}:
            amt = 2 + (1 if tier != "Common" else 0)
            self.inventory["crops"] += amt
            self.inventory["wood"] += 1
            self.farm["growth"] = min(1.0, float(self.farm.get("growth", 0.3)) + 0.35)
            bonus_msg = f"농작물 +{amt}, 목재 +1 (텃밭 성장 가속!)"
        elif key in {"cooking", "barista", "picnic"}:
            self.bentos["potato_fish"] = self.bentos.get("potato_fish", 0) + 1
            bonus_msg = "전투 도시락(감자 생선구이) +1"
        else:
            gold_gain = 25 if tier == "Common" else (50 if tier == "Rare" else 100)
            self.gold += gold_gain
            bonus_msg = f"활동 보상 +{gold_gain}G"

        self.save()
        lv_str = f" (🎉 미니펫 Lv.{self.pet_level} 레벨업!)" if leveled else ""
        return f"[{item_name}] 획득! ({bonus_msg}){lv_str}"

    def sell_crops(self) -> tuple[bool, str]:
        cnt = self.inventory.get("crops", 0)
        if cnt <= 0:
            return False, "판매할 농작물이 없어요! [🌱 정원/농사]를 통해 작물을 수확해 보세요."
        sell_amt = max(1, cnt // 2) if cnt > 2 else cnt
        earned = sell_amt * 28
        self.inventory["crops"] -= sell_amt
        self.gold += earned
        self.save()
        return True, f"🏪 농작물 {sell_amt}개를 상점에 납품하여 +{earned}G를 벌었어요! (보유 골드: {self.gold}G)"

    def sell_fish(self) -> tuple[bool, str]:
        c_cnt = self.inventory.get("fish_common", 0)
        r_cnt = self.inventory.get("fish_rare", 0)
        if c_cnt <= 0 and r_cnt <= 0:
            return False, "판매할 물고기가 없어요! [🎣 낚시하기]로 물고기를 낚아보세요."
        sell_c = max(1, c_cnt // 2) if c_cnt > 1 else c_cnt
        sell_r = max(0, r_cnt - 1) if r_cnt > 1 else (1 if c_cnt == 0 and r_cnt == 1 else 0)
        earned = sell_c * 32 + sell_r * 85
        self.inventory["fish_common"] -= sell_c
        self.inventory["fish_rare"] -= sell_r
        self.gold += earned
        self.save()
        return True, f"🐟 물고기(일반 {sell_c}, 희귀 {sell_r})를 상점에 판매해 +{earned}G 획득! (보유: {self.gold}G)"

    def cook_bento(self, bento_key: str) -> tuple[bool, str]:
        spec = BENTO_RECIPES.get(bento_key)
        if not spec:
            return False, "존재하지 않는 요리 레시피입니다."
        need_c = int(spec["crops"])
        need_fc = int(spec["fish_common"])
        need_fr = int(spec["fish_rare"])
        if self.inventory.get("crops", 0) < need_c:
            return False, f"농작물이 부족해요! (필요: {need_c}개 / 보유: {self.inventory.get('crops', 0)}개) ➔ 농사를 지어주세요!"
        if self.inventory.get("fish_common", 0) < need_fc:
            return False, f"일반 물고기가 부족해요! (필요: {need_fc}마리) ➔ 낚시를 진행해 주세요!"
        if self.inventory.get("fish_rare", 0) < need_fr:
            return False, f"희귀 물고기가 부족해요! (필요: {need_fr}마리) ➔ 낚시로 희귀 어종을 낚아보세요!"

        self.inventory["crops"] -= need_c
        self.inventory["fish_common"] -= need_fc
        self.inventory["fish_rare"] -= need_fr
        self.bentos[bento_key] = self.bentos.get(bento_key, 0) + 1
        self.add_pet_xp(30)
        self.save()
        return True, f"🍳 [{spec['name']}] 요리 완성! 디펜스 전투 시 자동으로 섭취하여 강력한 버프를 발휘합니다!"

    def enhance_weapon(self) -> tuple[bool, str]:
        k = self.weapon_enhance
        if k >= 15:
            return False, "이미 무기가 최고 단계(+15 신화 등급)에 도달했어요! 🌟"
        gold_cost = 50 * ((k + 1) ** 2)
        ore_c_cost = 2 * (k + 1)
        ore_r_cost = 0 if k < 4 else (k - 2)
        ore_l_cost = 1 if k >= 10 else 0
        if self.gold < gold_cost:
            return False, f"강화 골드가 부족해요! (필요: {gold_cost}G / 보유: {self.gold}G) ➔ 농사/낚시 납품으로 골드를 모아보세요!"
        if self.inventory.get("ore_common", 0) < ore_c_cost:
            return False, f"일반 광석이 부족해요! (필요: {ore_c_cost}개) ➔ [⛏️ 바탕화면 채굴]을 지시해 광석을 캐보세요!"
        if self.inventory.get("ore_rare", 0) < ore_r_cost:
            return False, f"희귀 광석이 부족해요! (필요: {ore_r_cost}개) ➔ 채굴을 통해 미스릴/마나수정을 발굴하세요!"
        if ore_l_cost > 0 and self.inventory.get("ore_legendary", 0) < ore_l_cost:
            return False, f"전설 광석(🌟)이 부족해요! (+11~+15 신화 제련에는 전설 광석 {ore_l_cost}개가 필요합니다 — 채굴·보스 웨이브에서 획득!)"

        self.gold -= gold_cost
        self.inventory["ore_common"] -= ore_c_cost
        self.inventory["ore_rare"] -= ore_r_cost
        if ore_l_cost > 0:
            self.inventory["ore_legendary"] -= ore_l_cost
        self.weapon_enhance += 1
        self.add_pet_xp(35)
        self.save()
        return True, f"🔨 대장간 강화 성공! 무기 +{self.weapon_enhance}강 달성! (티어 {self.weapon_tier} 외형 진화 / 공격력 {self.hero_atk})"

    def upgrade_tools(self) -> tuple[bool, str]:
        if self.pickaxe_tier >= 5:
            return False, "모든 생활 도구(곡괭이·낚싯대·물뿌리개)가 이미 최고 등급(Lv.5)입니다!"
        cost_gold = 120 * self.pickaxe_tier
        cost_ore = 3 * self.pickaxe_tier
        if self.gold < cost_gold or self.inventory.get("ore_common", 0) < cost_ore:
            return False, f"도구 승급 재료 부족! (필요: 골드 {cost_gold}G + 일반 광석 {cost_ore}개)"
        self.gold -= cost_gold
        self.inventory["ore_common"] -= cost_ore
        self.pickaxe_tier += 1
        self.rod_tier += 1
        self.watering_tier += 1
        self.save()
        return True, f"⚒️ 곡괭이·낚싯대·물뿌리개 Lv.{self.pickaxe_tier} 승급 완료! 채굴량 및 희귀 획득 확률이 상승합니다!"

    def upgrade_turret(self, turret_key: str) -> tuple[bool, str]:
        spec = TURRET_SPECS.get(turret_key)
        if not spec:
            return False, "알 수 없는 방어 시설입니다."
        cur_lv = self.turrets.get(turret_key, 0)
        if cur_lv >= 5:
            return False, f"[{spec['name']}]은(는) 이미 최고 레벨(Lv.5)입니다!"
        mult = cur_lv + 1
        g_cost = int(spec["base_gold"]) * mult
        oc_cost = int(spec["ore_common"]) * mult
        or_cost = int(spec["ore_rare"]) * mult
        w_cost = int(spec["wood"]) * mult
        core_cost = int(spec["core"]) * mult
        leg_cost = 1 if mult == 5 and turret_key in {"arc", "sniper", "cannon"} else 0

        if self.gold < g_cost:
            return False, f"골드 부족! (필요: {g_cost}G / 보유: {self.gold}G)"
        if self.inventory.get("ore_common", 0) < oc_cost:
            return False, f"일반 광석 부족! (필요: {oc_cost}개) ➔ 채굴을 진행해 주세요!"
        if self.inventory.get("ore_rare", 0) < or_cost:
            return False, f"희귀 광석 부족! (필요: {or_cost}개) ➔ 채굴을 진행해 주세요!"
        if self.inventory.get("wood", 0) < w_cost:
            return False, f"농장 목재 부족! (필요: {w_cost}개) ➔ 텃밭 수확/정원 가꾸기를 진행해 주세요!"
        if self.inventory.get("invader_core", 0) < core_cost:
            return False, f"침입자 코어 부족! (필요: {core_cost}개) ➔ 간헐적 침입 수호/디펜스로 코어를 획득하세요!"
        if leg_cost > 0 and self.inventory.get("ore_legendary", 0) < leg_cost:
            return False, f"전설 광석(🌟) 부족! (Lv.5 궁극 증축에는 전설 광석 {leg_cost}개가 필요합니다!)"

        self.gold -= g_cost
        self.inventory["ore_common"] -= oc_cost
        self.inventory["ore_rare"] -= or_cost
        self.inventory["wood"] -= w_cost
        self.inventory["invader_core"] -= core_cost
        if leg_cost > 0:
            self.inventory["ore_legendary"] -= leg_cost
        new_lv = cur_lv + 1
        self.turrets[turret_key] = new_lv
        if turret_key in PLACEABLE_TOWER_TYPES:
            matching_pads = [
                pid for pid in PAD_IDS
                if isinstance(self.tower_pads.get(pid), dict) and self.tower_pads[pid].get("type") == turret_key
            ]
            if matching_pads:
                lowest_pid = min(matching_pads, key=lambda pid: int(self.tower_pads[pid].get("level", 1)))
                self.tower_pads[lowest_pid] = {"type": turret_key, "level": min(5, max(new_lv, int(self.tower_pads[lowest_pid].get("level", 1)) + 1))}
            else:
                for pid in PAD_IDS:
                    if self.tower_pads.get(pid) is None:
                        self.tower_pads[pid] = {"type": turret_key, "level": min(5, new_lv)}
                        break
        self.add_pet_xp(40)
        self.save()
        return True, f"🏰 [{spec['name']}] Lv.{new_lv} 건설/증축 완료! 웨이브 디펜스 전장에 배치됩니다!"

    def apply_pad_action(
        self,
        pad_id: str,
        action: str,
        tower_type: str,
        new_level: int,
        gold_delta: int,
    ) -> bool:
        """Applies an in-combat 3D pad build/upgrade/sell action cleanly into persistent save state.
        Preserves permanent workshop turret research levels even when a battlefield pad is sold (#9)."""
        if pad_id not in PAD_IDS:
            return False
        self.gold = max(0, self.gold + int(gold_delta))
        act = str(action or "").lower()
        if act == "sell":
            self.tower_pads[pad_id] = None
        elif str(tower_type) in PLACEABLE_TOWER_TYPES:
            lv = max(1, min(5, int(new_level)))
            self.tower_pads[pad_id] = {"type": str(tower_type), "level": lv}
        else:
            return False

        for t_key in PLACEABLE_TOWER_TYPES:
            max_lv = 0
            for pid in PAD_IDS:
                rec = self.tower_pads.get(pid)
                if isinstance(rec, dict) and rec.get("type") == t_key:
                    max_lv = max(max_lv, int(rec.get("level", 1)))
            self.turrets[t_key] = max(int(self.turrets.get(t_key, 0)), max_lv)

        self.add_pet_xp(25)
        self.save()
        return True

    def record_collected_item(
        self,
        name: str,
        icon: str = "🎁",
        tier: str = "Common",
        category: str = "채집/탐험",
        amount: int = 1,
    ) -> None:
        if not name:
            return
        entry = self.collected_items.get(name)
        if isinstance(entry, dict):
            entry["count"] = int(entry.get("count", 0)) + max(1, int(amount))
            if icon:
                entry["icon"] = icon
            if tier:
                entry["tier"] = tier
            if category:
                entry["category"] = category
        else:
            self.collected_items[name] = {
                "icon": icon or "🎁",
                "tier": tier or "Common",
                "count": max(1, int(amount)),
                "category": category or "채집/탐험",
            }

    def record_monster_loot(self, loot_name: str, loot_icon: str = "👾", loot_tier: str = "Common") -> None:
        self.record_collected_item(
            name=loot_name,
            icon=loot_icon,
            tier=loot_tier,
            category="사냥 전리품",
            amount=1,
        )

    def craft_consumable(self, item_key: str) -> tuple[bool, str]:
        spec = CONSUMABLE_SPECS.get(item_key)
        if not spec:
            return False, "존재하지 않는 소모품 레시피입니다."
        g_cost = int(spec.get("gold", 0))
        c_cost = int(spec.get("crops", 0))
        oc_cost = int(spec.get("ore_common", 0))
        or_cost = int(spec.get("ore_rare", 0))
        core_cost = int(spec.get("core", 0))

        if self.gold < g_cost:
            return False, f"골드가 부족해요! (필요: {g_cost}G / 보유: {self.gold}G)"
        if self.inventory.get("crops", 0) < c_cost:
            return False, f"농작물이 부족해요! (필요: {c_cost}개 / 보유: {self.inventory.get('crops', 0)}개)"
        if self.inventory.get("ore_common", 0) < oc_cost:
            return False, f"일반 광석이 부족해요! (필요: {oc_cost}개 / 보유: {self.inventory.get('ore_common', 0)}개)"
        if self.inventory.get("ore_rare", 0) < or_cost:
            return False, f"희귀 광석이 부족해요! (필요: {or_cost}개 / 보유: {self.inventory.get('ore_rare', 0)}개)"
        if self.inventory.get("invader_core", 0) < core_cost:
            return False, f"침입자 코어가 부족해요! (필요: {core_cost}개 / 보유: {self.inventory.get('invader_core', 0)}개)"

        self.gold -= g_cost
        self.inventory["crops"] -= c_cost
        self.inventory["ore_common"] -= oc_cost
        self.inventory["ore_rare"] -= or_cost
        self.inventory["invader_core"] -= core_cost
        self.consumables[item_key] = self.consumables.get(item_key, 0) + 1
        self.add_pet_xp(20)
        self.save()
        return True, f"⚗️ [{spec['name']}] 연금 제작 완료! (보유: {self.consumables[item_key]}개)"

    def use_consumable(self, item_key: str) -> tuple[bool, str]:
        spec = CONSUMABLE_SPECS.get(item_key)
        if not spec:
            return False, "존재하지 않는 소모품입니다."
        cur = self.consumables.get(item_key, 0)
        if cur <= 0:
            return False, f"[{spec['name']}] 보유 수량이 부족합니다! 연금 제작 후 사용해 주세요."
        self.consumables[item_key] = cur - 1
        self.save()
        return True, f"✨ [{spec['name']}] 발동! — {spec['desc']}"

    def equip_or_craft_weapon(self, wep_key: str) -> tuple[bool, str]:
        spec = WEAPON_SPECS.get(wep_key)
        if not spec:
            return False, "존재하지 않는 무기 유형입니다."
        if wep_key in self.unlocked_weapons or wep_key == "fist":
            if wep_key not in self.unlocked_weapons:
                self.unlocked_weapons.append(wep_key)
            self.equipped_weapon = wep_key
            self.save()
            return True, f"⚔️ [{spec['name']}] 장착 완료! — {spec['desc']}"

        g_cost = int(spec.get("gold", 0))
        oc_cost = int(spec.get("ore_common", 0))
        or_cost = int(spec.get("ore_rare", 0))
        w_cost = int(spec.get("wood", 0))
        core_cost = int(spec.get("core", 0))

        if self.gold < g_cost:
            return False, f"골드 부족! (필요: {g_cost}G / 보유: {self.gold}G)"
        if self.inventory.get("ore_common", 0) < oc_cost:
            return False, f"일반 광석 부족! (필요: {oc_cost}개 / 보유: {self.inventory.get('ore_common', 0)}개)"
        if self.inventory.get("ore_rare", 0) < or_cost:
            return False, f"희귀 광석 부족! (필요: {or_cost}개 / 보유: {self.inventory.get('ore_rare', 0)}개)"
        if self.inventory.get("wood", 0) < w_cost:
            return False, f"농장 목재 부족! (필요: {w_cost}개 / 보유: {self.inventory.get('wood', 0)}개)"
        if self.inventory.get("invader_core", 0) < core_cost:
            return False, f"침입자 코어 부족! (필요: {core_cost}개 / 보유: {self.inventory.get('invader_core', 0)}개)"

        self.gold -= g_cost
        self.inventory["ore_common"] -= oc_cost
        self.inventory["ore_rare"] -= or_cost
        self.inventory["wood"] -= w_cost
        self.inventory["invader_core"] -= core_cost
        self.unlocked_weapons.append(wep_key)
        self.equipped_weapon = wep_key
        self.record_collected_item(
            name=spec["name"],
            icon=spec["icon"],
            tier="Legendary" if wep_key == "gun" else "Rare",
            category="전투 무기고",
            amount=1,
        )
        self.add_pet_xp(45)
        self.save()
        return True, f"🔨 [{spec['name']}] 제작 및 장착 완료! — {spec['desc']}"

    def unlock_weapon_drop(self, wep_key: str, auto_equip: bool = True) -> Optional[str]:
        spec = WEAPON_SPECS.get(wep_key)
        if not spec or wep_key in self.unlocked_weapons:
            return None
        self.unlocked_weapons.append(wep_key)
        if auto_equip:
            self.equipped_weapon = wep_key
        self.record_collected_item(
            name=spec["name"],
            icon=spec["icon"],
            tier="Legendary" if wep_key == "gun" else "Rare",
            category="전투 무기고",
            amount=1,
        )
        self.save()
        return f"🎁 전리품 무장 획득! [{spec['name']}] 해금 및 자동 장착 완료!"

    def diagnose_wave_readiness(self, target_wave: int) -> str:
        """Returns a concise readiness diagnosis linking Defense difficulty to Towers, Gear, Bento & Typing Level."""
        diag = self.diagnose_wave_readiness_dict(target_wave)
        return str(diag.get("summary", ""))

    def diagnose_wave_readiness_dict(self, target_wave: int) -> dict:
        """Returns dual-hero + tower combat power, typing level readiness, and specific counter-tower advices."""
        w = max(1, int(target_wave))
        pad_levels = sum(
            int(rec.get("level", 1))
            for rec in self.tower_pads.values()
            if isinstance(rec, dict)
        )
        placed_types = {
            rec.get("type")
            for rec in self.tower_pads.values()
            if isinstance(rec, dict) and rec.get("type") in PLACEABLE_TOWER_TYPES
        }
        barricade_lv = int(self.turrets.get("barricade", 0))
        hero_cp = int(round(self.hero_atk * 4.2 + self.hero_max_hp * 0.28))
        partner_cp = self.partner_cp
        tower_cp = pad_levels * 55 + barricade_lv * 40
        bento_cp = sum(self.bentos.values()) * 25
        player_cp = hero_cp + partner_cp + tower_cp + bento_cp
        rec_cp = int(round(180 + w * 72 + (w ** 1.45) * 14))

        rec_enh = max(1, (w + 1) // 2)
        rec_typing_lv = 1 + (w // 3)
        bonuses = self.typing_bonuses()
        rem_keys = max(0, int(bonuses["curLevelReq"]) - int(bonuses["curLevelProgress"]))

        advices: list[str] = []
        if self.weapon_enhance < rec_enh:
            advices.append(f"[채굴 ➔ 대장간] 무기 강화 부족 (현재 +{self.weapon_enhance}강, 권장 +{rec_enh}강)")
        if w >= 2 and "cannon" not in placed_types and "sniper" not in placed_types:
            advices.append("[방패병 카운터] 빈 패드에 💣 공성 박격포(방패 1.65배) 또는 🔮 저격탑 배치를 권장합니다")
        if w >= 4 and "frost" not in placed_types:
            advices.append("[주술사·돌격병 감속] ❄️ 프로스트 타워로 이속 감속 및 치유 억제를 확보하세요")
        if w >= 5 and ("sniper" not in placed_types and "arc" not in placed_types):
            advices.append("[후방 마도사·보스] 🔮 아케인 저격탑 또는 ⚡ 테슬라 코일이 유리합니다")
        if sum(self.bentos.values()) < 1:
            advices.append("[농사+낚시 ➔ 요리] 전투 도시락을 요리해 두면 위기 시 자동 회복+공격력 버프가 발동됩니다")
        if self.pet_level < rec_typing_lv:
            advices.append(f"[키보드 타이핑] 타건 Lv.{self.pet_level} (권장 Lv.{rec_typing_lv}, 다음까지 {rem_keys:,}타 — 영웅·트리 ATK +8%↑)")

        if not advices:
            summary = f"✅ [Wave {w} 듀얼 출격 준비 완료] 총 전투력 {player_cp} (권장 {rec_cp}) | 뽕뽕이+트리+포탑 {len(placed_types)}종"
            advices.append(summary)
        else:
            summary = f"⚠️ [Wave {w} 전략 진단] 전투력 {player_cp}/{rec_cp} — {advices[0]}"

        return {
            "hero_cp": hero_cp,
            "partner_cp": partner_cp,
            "tower_cp": tower_cp,
            "player_cp": player_cp,
            "rec_cp": rec_cp,
            "rec_typing_level": rec_typing_lv,
            "keystrokes_to_next": rem_keys,
            "advices": advices,
            "summary": summary,
        }

    def to_js_payload(self) -> dict:
        self.tick_farm_growth()
        return {
            "worldview": self.worldview,
            "workSafeMode": self.work_safe_mode,
            "basecampVisible": self.basecamp_visible,
            "petLevel": self.pet_level,
            "petXP": self.pet_xp,
            "gold": self.gold,
            "equippedWeapon": self.equipped_weapon,
            "unlockedWeapons": list(self.unlocked_weapons),
            "weaponEnhance": self.weapon_enhance,
            "weaponTier": self.weapon_tier,
            "pickaxeTier": self.pickaxe_tier,
            "rodTier": self.rod_tier,
            "wateringTier": self.watering_tier,
            "toolBonusRare": self.tool_bonus_rare,
            "turrets": dict(self.turrets),
            "towerPads": {pid: (dict(v) if isinstance(v, dict) else None) for pid, v in self.tower_pads.items()},
            "typingStats": self.typing_bonuses(),
            "dualHeroEnabled": True,
            "bentos": dict(self.bentos),
            "consumables": dict(self.consumables),
            "farm": {
                "planted": bool(self.farm.get("planted", True)),
                "growth": float(self.farm.get("growth", 0.45)),
                "watered": bool(self.farm.get("watered", True)),
                "cropType": str(self.farm.get("cropType", "튼튼 감자")),
            },
            "highestWave": self.highest_wave,
        }

    def save(self) -> None:
        try:
            data = {
                "schema_version": self.schema_version,
                "worldview": self.worldview,
                "unlocked_worldviews": self.unlocked_worldviews,
                "work_safe_mode": self.work_safe_mode,
                "basecamp_visible": self.basecamp_visible,
                "pet_level": self.pet_level,
                "pet_xp": self.pet_xp,
                "gold": self.gold,
                "equipped_weapon": self.equipped_weapon,
                "unlocked_weapons": self.unlocked_weapons,
                "weapon_enhance": self.weapon_enhance,
                "pickaxe_tier": self.pickaxe_tier,
                "rod_tier": self.rod_tier,
                "watering_tier": self.watering_tier,
                "inventory": self.inventory,
                "bentos": self.bentos,
                "turrets": self.turrets,
                "tower_pads": self.tower_pads,
                "typing_stats": self.typing_stats,
                "last_defense_report": self.last_defense_report,
                "consumables": self.consumables,
                "collected_items": self.collected_items,
                "farm": self.farm,
                "dispatch_queue": self.dispatch_queue,
                "highest_wave": self.highest_wave,
                "total_enemies_defeated": self.total_enemies_defeated,
                "skill_xp": self.skill_xp,
            }
            self.save_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def load(self) -> None:
        if not self.save_path.exists():
            return
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            raw_ver = int(data.get("schema_version", 1))
            self.worldview = str(data.get("worldview", "fantasy"))
            self.unlocked_worldviews = list(data.get("unlocked_worldviews", ["fantasy", "cyberpunk", "scifi", "cozy"]))
            self.work_safe_mode = bool(data.get("work_safe_mode", False))
            self.basecamp_visible = bool(data.get("basecamp_visible", True))
            self.gold = int(data.get("gold", 250))
            self.equipped_weapon = str(data.get("equipped_weapon", "fist"))
            if self.equipped_weapon not in WEAPON_SPECS:
                self.equipped_weapon = "fist"
            raw_unlocked = data.get("unlocked_weapons", ["fist"])
            if isinstance(raw_unlocked, list):
                self.unlocked_weapons = [str(w) for w in raw_unlocked if str(w) in WEAPON_SPECS]
            if "fist" not in self.unlocked_weapons:
                self.unlocked_weapons.insert(0, "fist")
            self.weapon_enhance = int(data.get("weapon_enhance", 0))
            self.pickaxe_tier = int(data.get("pickaxe_tier", 1))
            self.rod_tier = int(data.get("rod_tier", 1))
            self.watering_tier = int(data.get("watering_tier", 1))
            if isinstance(data.get("inventory"), dict):
                self.inventory.update(data["inventory"])
            if isinstance(data.get("bentos"), dict):
                self.bentos.update(data["bentos"])
            if isinstance(data.get("turrets"), dict):
                for k, v in data["turrets"].items():
                    if k in TURRET_SPECS:
                        self.turrets[k] = max(0, int(v))
            if isinstance(data.get("consumables"), dict):
                self.consumables.update(data["consumables"])
            if isinstance(data.get("collected_items"), dict):
                self.collected_items.update(data["collected_items"])
            if isinstance(data.get("farm"), dict):
                self.farm.update(data["farm"])
            if isinstance(data.get("dispatch_queue"), list):
                self.dispatch_queue = [str(x) for x in data["dispatch_queue"][:5]]
            self.highest_wave = int(data.get("highest_wave", 0))
            self.total_enemies_defeated = int(data.get("total_enemies_defeated", 0))
            if isinstance(data.get("skill_xp"), dict):
                self.skill_xp.update(data["skill_xp"])
            if isinstance(data.get("last_defense_report"), dict):
                self.last_defense_report = data["last_defense_report"]

            # Load / migrate typing_stats and hardcore typing level
            today_str = time.strftime("%Y-%m-%d")
            raw_ts = data.get("typing_stats")
            if isinstance(raw_ts, dict):
                self.typing_stats.update(raw_ts)
            if self.typing_stats.get("today_date") != today_str:
                self.typing_stats["today_date"] = today_str
                self.typing_stats["today_keystrokes"] = 0
                self.typing_stats["peak_cpm_today"] = 0
                self.typing_stats["daily_milestones_claimed"] = []

            if raw_ver < 2:
                legacy_xp = int(data.get("pet_xp", 0))
                self.typing_stats["legacy_combat_xp"] = int(self.typing_stats.get("legacy_combat_xp", 0)) + legacy_xp
                self.gold += 250  # One-time v2 migration transition bonus

            total_k = max(0, int(self.typing_stats.get("total_keystrokes", 0)))
            self.pet_xp = total_k
            self.pet_level, _, _, _ = calc_typing_level_progress(total_k)

            # Load / auto-populate 5 tower pads
            raw_pads = data.get("tower_pads")
            if isinstance(raw_pads, dict) and raw_ver >= 2:
                for pid in PAD_IDS:
                    val = raw_pads.get(pid)
                    if isinstance(val, dict) and val.get("type") in PLACEABLE_TOWER_TYPES:
                        self.tower_pads[pid] = {
                            "type": str(val["type"]),
                            "level": max(1, min(5, int(val.get("level", 1)))),
                        }
                    else:
                        self.tower_pads[pid] = None
            else:
                # Auto-populate from v1 non-zero turrets cleanly
                self.tower_pads = {pid: None for pid in PAD_IDS}
                slot_idx = 0
                for t_key in PLACEABLE_TOWER_TYPES:
                    lv = max(0, min(5, int(self.turrets.get(t_key, 0))))
                    if lv > 0 and slot_idx < len(PAD_IDS):
                        self.tower_pads[PAD_IDS[slot_idx]] = {"type": t_key, "level": lv}
                        slot_idx += 1
                if slot_idx == 0:
                    self.tower_pads["pad_0"] = {"type": "ballista", "level": 1}
                    self.turrets["ballista"] = max(1, int(self.turrets.get("ballista", 1)))

            self.schema_version = 2
            self.tick_farm_growth()
            if raw_ver < 2:
                self.save()
        except Exception:
            pass


class RPGWorldHubDrawer(QWidget):
    """
    Cupertino / Material Dark Glassmorphism + Neumorphism + Flat Minimal
    RPG World, Economy, Dispatch & Defense Command Center (Ctrl+R / Bag Ctrl+I).
    Floats independently beside Ppong-ppong-i so the 3D viewport is never clipped.
    """

    dispatch_requested = pyqtSignal(str)          # 'mining' | 'gardening' | 'fishing' | 'skirmish' | 'auto_queue'
    worldview_changed = pyqtSignal(str)           # 'fantasy' | 'cyberpunk' | 'scifi' | 'cozy'
    work_safe_toggled = pyqtSignal(bool)
    skirmish_requested = pyqtSignal()
    wave_defense_requested = pyqtSignal(int)      # wave_number
    stop_combat_requested = pyqtSignal()
    consumable_used = pyqtSignal(str)             # item_key ('hp_potion', 'meteor_scroll', etc.)
    weapon_changed = pyqtSignal(str)              # 'fist' | 'sword' | 'bow' | 'gun'
    state_modified = pyqtSignal(str)              # feedback toast message

    _SHORT_WEAPONS = {"fist": "👊 맨손", "sword": "🗡️ 명검", "bow": "🏹 장궁", "gun": "🔫 블래스터"}
    _SHORT_CONS = {
        "hp_potion": "🧪 생명 포션",
        "haste_elixir": "⚡ 가속 비약",
        "rage_elixir": "🔥 분노 비약",
        "meteor_scroll": "☄️ 메테오 서",
        "shield_scroll": "🛡️ 절대방어",
        "luck_potion": "🍀 황금 행운",
    }
    _SHORT_BENTOS = {
        "potato_fish": "🥔 감자 생선구이",
        "trout_steak": "🍣 송어 스테이크",
        "carp_stew": "🍲 황금 매운탕",
        "star_emperor": "🍱 별빛 황제도시락",
    }
    _SHORT_TURRETS = {
        "barricade": "🧱 성소 성벽요새",
        "ballista": "🏹 연발 발리스타",
        "cannon": "💣 공성 박격포",
        "frost": "❄️ 프로스트 타워",
        "arc": "⚡ 테슬라 코일",
        "sniper": "🔮 아케인 저격탑",
    }

    _SCROLL_CSS = """
        QScrollArea { background: transparent; border: none; }
        QScrollBar:vertical {
            background: rgba(10, 15, 28, 0.35);
            width: 6px;
            margin: 4px 2px 4px 0px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical {
            background: rgba(148, 163, 184, 0.32);
            min-height: 28px;
            border-radius: 3px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(56, 189, 248, 0.65);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
            background: none;
            border: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
    """

    def __init__(self, rpg_state: RPGWorldState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.rpg = rpg_state
        self.setWindowTitle("⚔️ 뽕뽕이 3D 월드 & 디펜스 사령부 (Ctrl+R / 가방 Ctrl+I)")
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        w = min(940, max(780, int(avail.width() * 0.62)))
        h = min(790, max(660, int(avail.height() * 0.82)))
        self.setFixedSize(w, h)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._drag_pos: Optional[QPoint] = None
        self._worldview_btns: dict[str, QPushButton] = {}
        self._stage_jump_btns: dict[int, QPushButton] = {}
        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.refresh_labels)
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 18, 22, 18)
        root_layout.setSpacing(10)

        # 1. Cupertino Dark-Glass Command Header Bar
        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel("⚔️ 뽕뽕이 3D 월드 & 디펜스 사령부")
        title_lbl.setStyleSheet(
            "color: #F8FAFC; font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; "
            "font-size: 21px; font-weight: 800; letter-spacing: -0.3px;"
        )
        sub_lbl = QLabel("CUPERTINO DARK-GLASS COMMAND HUB · 원정 · 무장 · 대장간 · 바탕화면 웨이브 디펜스")
        sub_lbl.setStyleSheet(
            "color: #94A3B8; font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; "
            "font-size: 11px; font-weight: 700; letter-spacing: 0.7px;"
        )
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch()

        self.btn_work_safe = QPushButton("💼 클릭 투과 OFF")
        self.btn_work_safe.setCheckable(True)
        self.btn_work_safe.setChecked(self.rpg.work_safe_mode)
        self.btn_work_safe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_work_safe.setToolTip("업무 집중 클릭 투과 모드 (Ctrl+Shift+W)")
        self.btn_work_safe.clicked.connect(self._on_work_safe_clicked)
        self.btn_work_safe.setStyleSheet(self._pill_btn_style("#38BDF8"))
        header.addWidget(self.btn_work_safe)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(36, 36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.hide)
        btn_close.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.05); color: #94A3B8; "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; font-size: 15px; font-weight: 800; }"
            "QPushButton:hover { background: rgba(239,68,68,0.22); color: #FCA5A5; border-color: rgba(248,113,113,0.55); }"
        )
        header.addWidget(btn_close)
        root_layout.addLayout(header)

        # 2. Neumorphic Sunken Telemetry HUD Card (Hero Level / Weapon / Gold / Wave + Resources)
        self.lbl_hero_summary = QLabel()
        self.lbl_hero_summary.setWordWrap(True)
        self.lbl_hero_summary.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(7,11,21,0.92), stop:1 rgba(13,20,36,0.90)); "
            "color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.10); "
            "border-top: 1px solid rgba(2, 6, 23, 0.90); "
            "border-radius: 13px; padding: 10px 16px; "
            "font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; font-size: 14px; line-height: 1.48;"
        )
        root_layout.addWidget(self.lbl_hero_summary)

        # 3. 4-Worldview Segmented Cupertino Pill Bar
        wv_frame = QFrame()
        wv_frame.setStyleSheet(
            "QFrame { background: rgba(7, 11, 21, 0.78); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 11px; }"
        )
        wv_bar = QHBoxLayout(wv_frame)
        wv_bar.setContentsMargins(4, 4, 4, 4)
        wv_bar.setSpacing(6)
        short_wv_labels = {
            "fantasy": "🌿 판타지 왕국",
            "cyberpunk": "🌃 사이버펑크",
            "scifi": "🚀 스페이스 SF",
            "cozy": "🌼 코지 힐링",
        }
        for wv_key, wv_meta in WORLDVIEW_INFO.items():
            btn_wv = QPushButton(short_wv_labels.get(wv_key, wv_meta["title"]))
            btn_wv.setToolTip(f"{wv_meta['title']} — {wv_meta['desc']}")
            btn_wv.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_wv.setMinimumHeight(34)
            btn_wv.setStyleSheet(self._segmented_btn_style(active=False))
            btn_wv.clicked.connect(lambda _c, k=wv_key: self._on_worldview_selected(k))
            self._worldview_btns[wv_key] = btn_wv
            wv_bar.addWidget(btn_wv)
        root_layout.addWidget(wv_frame)

        # 4. 4 Main Section Tabs (Cupertino / Material Dark Glass)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.11);
                background: rgba(9, 14, 26, 0.78);
                border-radius: 14px;
                padding: 2px;
            }
            QTabBar::tab {
                background: rgba(15, 23, 42, 0.65);
                color: #94A3B8;
                padding: 9px 20px;
                margin-right: 6px;
                margin-bottom: 4px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 800;
            }
            QTabBar::tab:hover {
                color: #F8FAFC;
                background: rgba(30, 41, 59, 0.82);
                border-color: rgba(56, 189, 248, 0.35);
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(56, 189, 248, 0.24), stop:1 rgba(14, 165, 233, 0.14));
                color: #F8FAFC;
                border: 1px solid rgba(56, 189, 248, 0.62);
            }
            """
        )
        self.tabs.addTab(self._build_tab_dispatch_economy(), "⚡ 원정 · 농장")
        self.tabs.addTab(self._build_tab_bag_consumables(), "🎒 가방 · 무장")
        self.tabs.addTab(self._build_tab_craft_cooking(), "🔨 대장간 · 포탑")
        self.tabs.addTab(self._build_tab_defense(), "⚔️ 디펜스 출격")
        root_layout.addWidget(self.tabs, 1)

        # 5. Bottom Minimal Status Capsule
        self.lbl_feedback = QLabel("✅ 사령부 대기 중 — 원하는 원정이나 디펜스를 바로 실행하세요!")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setStyleSheet(
            "background: rgba(7, 11, 21, 0.90); color: #E2E8F0; "
            "border: 1px solid rgba(255, 255, 255, 0.10); border-left: 3px solid #38BDF8; "
            "border-radius: 10px; padding: 8px 14px; "
            "font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; font-size: 13px; font-weight: 700;"
        )
        root_layout.addWidget(self.lbl_feedback)
        self.refresh_labels()

    @staticmethod
    def _section_header(title: str, subtitle: str, accent: str = "#38BDF8") -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(row)
        h.setContentsMargins(2, 2, 2, 0)
        h.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {accent}; font-size: 10px; font-weight: 900; background: transparent;")
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #F8FAFC; font-size: 14px; font-weight: 800; letter-spacing: -0.2px; background: transparent;")
        lbl_s = QLabel(subtitle)
        lbl_s.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; background: transparent;")
        h.addWidget(dot)
        h.addWidget(lbl_t)
        h.addWidget(lbl_s)
        h.addStretch()
        return row

    def _build_tab_dispatch_economy(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._SCROLL_CSS)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(9)

        lay.addWidget(self._section_header("1. 자율 원정 & 생활 임무 파견", "바탕화면 채굴 · 농사 · 낚시 · 수호전 즉시 오더", "#38BDF8"))

        grid_disp = QGridLayout()
        grid_disp.setSpacing(8)
        for idx, (label, key, col) in enumerate([
            ("⛏️ 광맥 채굴 출동  ·  광석 & 희귀 보석 발굴", "mining", "#38BDF8"),
            ("🌱 정원 농사 가꾸기  ·  작물 재배 & 성장 촉진", "gardening", "#34D399"),
            ("🎣 강가 낚시 출동  ·  황금 잉어 & 송어 낚시", "fishing", "#2DD4BF"),
            ("🛡️ 바탕화면 수호전  ·  침입자 격퇴 & 코어 획득", "skirmish", "#A78BFA"),
        ]):
            b = QPushButton(label)
            b.setMinimumHeight(52)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(self._action_btn_style(col))
            b.clicked.connect(lambda _c, k=key: self.dispatch_requested.emit(k))
            grid_disp.addWidget(b, idx // 2, idx % 2)
        lay.addLayout(grid_disp)

        btn_auto_q = QPushButton("🔄 3연속 자동 순환 오더 예약  (채굴 ➔ 농사 ➔ 낚시 논스톱 수행)")
        btn_auto_q.setMinimumHeight(44)
        btn_auto_q.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_auto_q.setStyleSheet(self._action_btn_style("#60A5FA"))
        btn_auto_q.clicked.connect(lambda: self.dispatch_requested.emit("auto_queue"))
        lay.addWidget(btn_auto_q)

        lay.addWidget(self._section_header("2. 3D 미니 텃밭 & 상점 납품", "수확한 작물과 어류를 판매해 골드를 확보하세요", "#34D399"))

        farm_card = QFrame()
        farm_card.setStyleSheet(
            "QFrame { background: rgba(13, 20, 36, 0.86); border: 1px solid rgba(255,255,255,0.09); border-radius: 12px; }"
        )
        fl = QVBoxLayout(farm_card)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(8)

        self.lbl_farm_status = QLabel()
        self.lbl_farm_status.setStyleSheet("color: #E2E8F0; font-size: 13px; font-weight: 700; border: none; background: transparent;")
        fl.addWidget(self.lbl_farm_status)

        farm_row = QHBoxLayout()
        farm_row.setSpacing(8)
        for txt, col, cb in [
            ("💧 농장 물주기", "#38BDF8", self._on_water_farm),
            ("🌾 작물 수확", "#34D399", self._on_harvest_farm),
            ("💰 작물 납품 (+28G)", "#FBBF24", self._on_sell_crops),
            ("🐟 어류 납품 (+32~85G)", "#FB923C", self._on_sell_fish),
        ]:
            btn = QPushButton(txt)
            btn.setMinimumHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._action_btn_style(col))
            btn.clicked.connect(cb)
            farm_row.addWidget(btn)
        fl.addLayout(farm_row)
        lay.addWidget(farm_card)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _build_tab_bag_consumables(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._SCROLL_CSS)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(9)

        lay.addWidget(self._section_header("1. 4대 전투 무장 장착 & 제작", "전투 스타일에 맞춰 근접 · 도검 · 장궁 · 중화기를 전환하세요", "#FBBF24"))

        self._weapon_btns_bag: dict[str, QPushButton] = {}
        wep_row = QHBoxLayout()
        wep_row.setSpacing(8)
        for w_key, w_spec in WEAPON_SPECS.items():
            btn_w = QPushButton(w_spec["short"])
            btn_w.setMinimumHeight(44)
            btn_w.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_w.setToolTip(w_spec["desc"])
            btn_w.setStyleSheet(self._small_btn_style("#64748B"))
            btn_w.clicked.connect(lambda _c, k=w_key: self._on_weapon_clicked(k))
            self._weapon_btns_bag[w_key] = btn_w
            wep_row.addWidget(btn_w)
        lay.addLayout(wep_row)

        lay.addWidget(self._section_header("2. 수집 전리품 도감", "원정과 디펜스에서 획득한 희귀 광물 · 어종 · 몬스터 코어", "#38BDF8"))

        self.lbl_bag_items = QLabel()
        self.lbl_bag_items.setWordWrap(True)
        self.lbl_bag_items.setStyleSheet(
            "background: rgba(7, 11, 21, 0.85); color: #F8FAFC; border: 1px solid rgba(255, 255, 255, 0.08); "
            "border-radius: 11px; padding: 10px 14px; font-size: 13px; line-height: 1.5;"
        )
        lay.addWidget(self.lbl_bag_items)

        lay.addWidget(self._section_header("3. 전술 소모품 즉시 발동 & 연금 제작", "전투 중 단축키 [5:포션] [6:가속] 또는 아래 카드로 즉시 사용", "#34D399"))

        cons_grid = QGridLayout()
        cons_grid.setSpacing(8)
        self._consumable_use_btns: dict[str, QPushButton] = {}
        for idx, (c_key, c_spec) in enumerate(CONSUMABLE_SPECS.items()):
            tile = QFrame()
            tile.setStyleSheet(
                "QFrame { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(255, 255, 255, 0.09); border-radius: 11px; }"
            )
            h_tile = QHBoxLayout(tile)
            h_tile.setContentsMargins(6, 5, 6, 5)
            h_tile.setSpacing(6)

            cnt = self.rpg.consumables.get(c_key, 0)
            s_name = self._SHORT_CONS.get(c_key, c_spec["name"][:6])
            btn_use = QPushButton(f"{s_name} · x{cnt}")
            btn_use.setMinimumHeight(38)
            btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_use.setToolTip(f"{c_spec['name']}: {c_spec['desc']}")
            btn_use.setStyleSheet(self._action_btn_style("#2DD4BF"))
            btn_use.clicked.connect(lambda _c, k=c_key: self._on_use_consumable(k))
            self._consumable_use_btns[c_key] = btn_use

            btn_craft = QPushButton(f"+연금 ({c_spec['gold']}G)")
            btn_craft.setMinimumHeight(38)
            btn_craft.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_craft.setToolTip(f"{c_spec['name']} 연금 제작 ({c_spec['gold']}G)")
            btn_craft.setStyleSheet(self._small_btn_style("#A78BFA"))
            btn_craft.clicked.connect(lambda _c, k=c_key: self._on_craft_consumable(k))

            h_tile.addWidget(btn_use, 1)
            h_tile.addWidget(btn_craft)
            cons_grid.addWidget(tile, idx // 2, idx % 2)

        lay.addLayout(cons_grid)
        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _build_tab_craft_cooking(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._SCROLL_CSS)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(7)

        lay.addWidget(self._section_header("1. 대장간 무기 제련 & 생활 도구 승급", "+1~+15 4단계 3D 외형 진화 및 채집 희귀 드랍률 향상", "#F87171"))

        forge_row = QHBoxLayout()
        forge_row.setSpacing(8)
        self.btn_forge_wep = QPushButton("🗡️ 무기 강화 (+1~+15 · 3D 외형 진화)")
        self.btn_forge_wep.setMinimumHeight(44)
        self.btn_forge_wep.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forge_wep.setToolTip("광석 + 골드로 무기 강화 (+1~+15 / 4단계 외형 진화)")
        self.btn_forge_wep.setStyleSheet(self._action_btn_style("#F87171"))
        self.btn_forge_wep.clicked.connect(self._on_enhance_weapon)

        self.btn_forge_tool = QPushButton("⛏️ 채집 도구 승급 (희귀 드랍률 UP)")
        self.btn_forge_tool.setMinimumHeight(44)
        self.btn_forge_tool.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forge_tool.setToolTip("곡괭이/낚싯대/물뿌리개 동시 승급")
        self.btn_forge_tool.setStyleSheet(self._action_btn_style("#818CF8"))
        self.btn_forge_tool.clicked.connect(self._on_upgrade_tools)
        forge_row.addWidget(self.btn_forge_wep)
        forge_row.addWidget(self.btn_forge_tool)
        lay.addLayout(forge_row)

        lay.addWidget(self._section_header("2. 전투 버프 도시락 주방", "영웅 또는 트리 위기 시 자동 섭취 (HP 회복 + 공격·공속 증폭)", "#FB923C"))

        self._bento_btns: dict[str, QPushButton] = {}
        bento_grid = QGridLayout()
        bento_grid.setSpacing(7)
        for idx, (b_key, b_spec) in enumerate(BENTO_RECIPES.items()):
            cnt = self.rpg.bentos.get(b_key, 0)
            btn_b = QPushButton(f"{self._SHORT_BENTOS.get(b_key, b_spec['name'])} · x{cnt}")
            btn_b.setMinimumHeight(42)
            btn_b.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_b.setToolTip(
                f"{b_spec['name']} (작물 {b_spec['crops']} + 일반어 {b_spec['fish_common']} + 희귀어 {b_spec['fish_rare']}) — {b_spec['desc']}"
            )
            btn_b.setStyleSheet(self._action_btn_style("#FB923C"))
            btn_b.clicked.connect(lambda _c, k=b_key: self._on_cook_bento(k))
            self._bento_btns[b_key] = btn_b
            bento_grid.addWidget(btn_b, idx // 2, idx % 2)
        lay.addLayout(bento_grid)

        lay.addWidget(self._section_header("3. 성소 방어 포탑 연구 & 전장 패드 증축", "성벽 요새 + 5대 상성 방어타워 (전장 5패드와 실시간 연동)", "#38BDF8"))

        self._turret_btns: dict[str, QPushButton] = {}
        tur_grid = QGridLayout()
        tur_grid.setSpacing(7)
        turret_accents = {
            "barricade": "#FBBF24",
            "ballista": "#38BDF8",
            "cannon": "#FB923C",
            "frost": "#22D3EE",
            "arc": "#A78BFA",
            "sniper": "#E879F9",
        }
        for idx, (t_key, t_spec) in enumerate(TURRET_SPECS.items()):
            lv = self.rpg.turrets.get(t_key, 0)
            btn_t = QPushButton(f"{self._SHORT_TURRETS.get(t_key, t_spec['name'])} · Lv.{lv}")
            btn_t.setMinimumHeight(42)
            btn_t.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_t.setToolTip(
                f"{t_spec['name']} 증축 ({t_spec['base_gold']}G / 일반 {t_spec['ore_common']} / 희귀 {t_spec['ore_rare']}) — {t_spec['desc']}"
            )
            btn_t.setStyleSheet(self._action_btn_style(turret_accents.get(t_key, "#38BDF8")))
            btn_t.clicked.connect(lambda _c, k=t_key: self._on_upgrade_turret(k))
            self._turret_btns[t_key] = btn_t
            tur_grid.addWidget(btn_t, idx // 2, idx % 2)
        lay.addLayout(tur_grid)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _build_tab_defense(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(self._SCROLL_CSS)
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(9)

        lay.addWidget(self._section_header("1. 출격 무장 빠른 전환", "전투 중에도 숫자키 [1~4] 또는 아래 버튼으로 즉시 교체", "#FBBF24"))

        self._weapon_btns_def: dict[str, QPushButton] = {}
        wep_def_row = QHBoxLayout()
        wep_def_row.setSpacing(8)
        for w_key, w_spec in WEAPON_SPECS.items():
            btn_wd = QPushButton(w_spec["short"])
            btn_wd.setMinimumHeight(42)
            btn_wd.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_wd.setToolTip(w_spec["desc"])
            btn_wd.setStyleSheet(self._small_btn_style("#64748B"))
            btn_wd.clicked.connect(lambda _c, k=w_key: self._on_weapon_clicked(k))
            self._weapon_btns_def[w_key] = btn_wd
            wep_def_row.addWidget(btn_wd)
        lay.addLayout(wep_def_row)

        self.lbl_gear_check = QLabel()
        self.lbl_gear_check.setWordWrap(True)
        self.lbl_gear_check.setStyleSheet(
            "background: rgba(7, 11, 21, 0.88); color: #FDE047; border: 1px solid rgba(251, 191, 36, 0.32); "
            "border-left: 3px solid #FBBF24; border-radius: 11px; padding: 10px 14px; font-size: 13px; font-weight: 700; line-height: 1.45;"
        )
        lay.addWidget(self.lbl_gear_check)

        self.lbl_last_battle_report = QLabel()
        self.lbl_last_battle_report.setWordWrap(True)
        self.lbl_last_battle_report.setStyleSheet(
            "background: rgba(7, 11, 21, 0.85); color: #BAE6FD; border: 1px solid rgba(56, 189, 248, 0.28); "
            "border-left: 3px solid #38BDF8; border-radius: 11px; padding: 9px 14px; font-size: 12px; font-weight: 700; line-height: 1.45;"
        )
        self.lbl_last_battle_report.hide()
        lay.addWidget(self.lbl_last_battle_report)

        launch_row = QHBoxLayout()
        launch_row.setSpacing(10)
        btn_skirmish = QPushButton("🛡️ 바탕화면 수호전 출격 (Ctrl+E)  ·  침입자 소탕")
        btn_skirmish.setMinimumHeight(52)
        btn_skirmish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skirmish.setStyleSheet(self._action_btn_style("#A78BFA"))
        btn_skirmish.clicked.connect(self.skirmish_requested.emit)

        self.btn_next_wave = QPushButton(f"⚔️ Wave {self.rpg.highest_wave + 1} 디펜스 출격 (Ctrl+D)")
        self.btn_next_wave.setMinimumHeight(52)
        self.btn_next_wave.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_wave.setStyleSheet(self._action_btn_style("#F43F5E"))
        self.btn_next_wave.clicked.connect(lambda: self._launch_wave(self.rpg.highest_wave + 1))
        launch_row.addWidget(btn_skirmish)
        launch_row.addWidget(self.btn_next_wave)
        lay.addLayout(launch_row)

        lay.addWidget(self._section_header("2. 스테이지 선택 도전", "클리어한 최고 웨이브+1까지 도전 가능 (5웨이브마다 군단장 보스)", "#F472B6"))

        wave_grid = QHBoxLayout()
        wave_grid.setSpacing(8)
        self._stage_jump_btns.clear()
        for w_num, label in [
            (1, "⚔️ Stage 1"),
            (5, "👑 Boss W5"),
            (10, "👑 Boss W10"),
            (15, "👑 Boss W15"),
        ]:
            b = QPushButton(label)
            b.setMinimumHeight(40)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(self._small_btn_style("#F43F5E" if w_num >= 5 else "#38BDF8"))
            b.clicked.connect(lambda _c, wn=w_num: self._launch_wave(wn))
            self._stage_jump_btns[w_num] = b
            wave_grid.addWidget(b)
        lay.addLayout(wave_grid)

        btn_stop = QPushButton("🏳️ 현재 전투 / 디펜스 후퇴하고 평화 모드로 복귀 (ESC)")
        btn_stop.setMinimumHeight(40)
        btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_stop.setStyleSheet(self._small_btn_style("#64748B"))
        btn_stop.clicked.connect(self.stop_combat_requested.emit)
        lay.addWidget(btn_stop)

        lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def _launch_wave(self, wave_num: int) -> None:
        max_allowed = self.rpg.highest_wave + 1
        if wave_num > max_allowed:
            self.set_feedback(
                f"🔒 [Stage {wave_num} 잠김] 이전 웨이브를 먼저 클리어해 주세요! (현재 도전 가능: Wave 1 ~ Wave {max_allowed})"
            )
            return
        diag = self.rpg.diagnose_wave_readiness(wave_num)
        self.set_feedback(diag)
        self.wave_defense_requested.emit(wave_num)

    def _on_work_safe_clicked(self, checked: bool) -> None:
        self.rpg.work_safe_mode = bool(checked)
        self.rpg.save()
        self.refresh_labels()
        self.work_safe_toggled.emit(self.rpg.work_safe_mode)

    def _on_worldview_selected(self, wv_key: str) -> None:
        meta = WORLDVIEW_INFO.get(wv_key, WORLDVIEW_INFO["fantasy"])
        req_wave = int(meta.get("unlock_wave", 0))
        if self.rpg.highest_wave < req_wave and wv_key not in self.rpg.unlocked_worldviews:
            self.set_feedback(f"🔒 [{meta['title']}] 세계관은 Wave {req_wave} 보스 클리어 시 해금됩니다!")
            return
        self.rpg.worldview = wv_key
        self.rpg.save()
        self.refresh_labels()
        self.worldview_changed.emit(wv_key)
        self.set_feedback(f"🌌 [{meta['title']}] 세계관 적용! — {meta['desc']}")

    def _on_water_farm(self) -> None:
        msg = self.rpg.water_farm()
        self.refresh_labels()
        self.set_feedback(msg)
        self.state_modified.emit(msg)

    def _on_harvest_farm(self) -> None:
        ok, msg = self.rpg.harvest_farm()
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_sell_crops(self) -> None:
        ok, msg = self.rpg.sell_crops()
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_sell_fish(self) -> None:
        ok, msg = self.rpg.sell_fish()
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_cook_bento(self, bento_key: str) -> None:
        ok, msg = self.rpg.cook_bento(bento_key)
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_enhance_weapon(self) -> None:
        ok, msg = self.rpg.enhance_weapon()
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_upgrade_tools(self) -> None:
        ok, msg = self.rpg.upgrade_tools()
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_upgrade_turret(self, turret_key: str) -> None:
        ok, msg = self.rpg.upgrade_turret(turret_key)
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_craft_consumable(self, item_key: str) -> None:
        ok, msg = self.rpg.craft_consumable(item_key)
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.state_modified.emit(msg)

    def _on_use_consumable(self, item_key: str) -> None:
        ok, msg = self.rpg.use_consumable(item_key)
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.consumable_used.emit(item_key)
            self.state_modified.emit(msg)

    def _on_weapon_clicked(self, wep_key: str) -> None:
        ok, msg = self.rpg.equip_or_craft_weapon(wep_key)
        self.refresh_labels()
        self.set_feedback(msg)
        if ok:
            self.weapon_changed.emit(self.rpg.equipped_weapon)
            self.state_modified.emit(msg)

    def open_section_tab(self, tab_idx: int, pet_rect: Optional[QRect] = None) -> None:
        self.tabs.setCurrentIndex(max(0, min(self.tabs.count() - 1, int(tab_idx))))
        if pet_rect is not None:
            self.show_beside_pet(pet_rect)
        else:
            self.refresh_labels()
            self.show()
            self.raise_()
            self.activateWindow()

    def open_bag_tab(self, pet_rect: Optional[QRect] = None) -> None:
        self.open_section_tab(1, pet_rect)

    def set_feedback(self, text: str) -> None:
        self.lbl_feedback.setText(text)

    def refresh_ui(self) -> None:
        self.refresh_labels()

    def refresh_labels(self) -> None:
        self.rpg.tick_farm_growth()
        inv = self.rpg.inventory
        t = self.rpg.turrets
        cur_wep_spec = WEAPON_SPECS.get(self.rpg.equipped_weapon, WEAPON_SPECS["fist"])

        self.btn_work_safe.setChecked(self.rpg.work_safe_mode)
        self.btn_work_safe.setText("💼 클릭 투과 ON" if self.rpg.work_safe_mode else "💼 클릭 투과 OFF")

        for wv_k, btn_wv in getattr(self, "_worldview_btns", {}).items():
            btn_wv.setStyleSheet(self._segmented_btn_style(active=(wv_k == self.rpg.worldview)))

        tb = self.rpg.typing_bonuses()
        cur_k = int(tb["curLevelProgress"])
        req_k = max(1, int(tb["curLevelReq"]))
        pct_k = min(100, int(round((cur_k / req_k) * 100)))
        fever_tag = " <span style='color:#FB923C;'>🔥피버ON</span>" if tb["feverActive"] else ""
        summary_html = (
            f"<span style='color:#38BDF8; font-weight:800;'>⌨️ Lv.{self.rpg.pet_level}</span> "
            f"<b>{tb['rankTitle']}</b> "
            f"<span style='color:#94A3B8;'>({cur_k:,}/{req_k:,}타 · </span>"
            f"<span style='color:#FBBF24; font-weight:800;'>{pct_k}%</span><span style='color:#94A3B8;'>)</span>"
            f" &nbsp;<span style='color:#334155;'>|</span>&nbsp; "
            f"오늘 <b>{tb['todayKeystrokes']:,}타</b> <span style='color:#94A3B8;'>({tb['liveCpm']}타/분)</span>{fever_tag}<br>"
            f"⚔️ <b>{cur_wep_spec['short']}+{self.rpg.weapon_enhance}</b> "
            f"<span style='color:#38BDF8;'>(ATK <b>{self.rpg.hero_atk}</b>)</span>"
            f" &nbsp;<span style='color:#334155;'>|</span>&nbsp; "
            f"💰 <span style='color:#FBBF24; font-weight:800;'>{self.rpg.gold:,}G</span>"
            f" &nbsp;<span style='color:#334155;'>|</span>&nbsp; "
            f"🏆 <b>W{self.rpg.highest_wave}</b>"
            f" &nbsp;<span style='color:#334155;'>|</span>&nbsp; "
            f"🪨<b>{inv.get('ore_common',0)}</b> &nbsp;"
            f"💎<b>{inv.get('ore_rare',0)}</b> &nbsp;"
            f"🌟<b>{inv.get('ore_legendary',0)}</b> &nbsp;"
            f"🌾<b>{inv.get('crops',0)}</b> &nbsp;"
            f"🪵<b>{inv.get('wood',0)}</b> &nbsp;"
            f"🐟<b>{inv.get('fish_common',0)}</b> &nbsp;"
            f"🐠<b>{inv.get('fish_rare',0)}</b> &nbsp;"
            f"👾<b>{inv.get('invader_core',0)}</b>"
        )
        self.lbl_hero_summary.setText(summary_html)

        for btn_dict in (getattr(self, "_weapon_btns_bag", {}), getattr(self, "_weapon_btns_def", {})):
            for w_key, btn_w in btn_dict.items():
                w_spec = WEAPON_SPECS[w_key]
                w_lbl = self._SHORT_WEAPONS.get(w_key, w_spec["short"])
                is_equipped = self.rpg.equipped_weapon == w_key
                is_unlocked = w_key in self.rpg.unlocked_weapons or w_key == "fist"
                if is_equipped:
                    btn_w.setText(f"✓ {w_lbl} (장착중)")
                    btn_w.setStyleSheet(self._small_btn_style("#38BDF8", active=True))
                elif is_unlocked:
                    btn_w.setText(w_lbl)
                    btn_w.setStyleSheet(self._small_btn_style("#34D399", active=False))
                else:
                    btn_w.setText(f"🔒 {w_lbl} · {w_spec['gold']}G")
                    btn_w.setStyleSheet(self._small_btn_style("#64748B", active=False))

        if hasattr(self, "btn_forge_wep"):
            k = self.rpg.weapon_enhance
            if k >= 15:
                self.btn_forge_wep.setText("🗡️ 무기 제련 MAX (+15 신화 달성)")
            else:
                g_c = 50 * ((k + 1) ** 2)
                oc_c = 2 * (k + 1)
                or_c = 0 if k < 4 else (k - 2)
                cost_tag = f"{g_c:,}G · 🪨{oc_c}" + (f" · 💎{or_c}" if or_c > 0 else "") + (" · 🌟1" if k >= 10 else "")
                self.btn_forge_wep.setText(f"🗡️ 무기 제련 +{k}➔+{k+1}  ({cost_tag})")

        if hasattr(self, "btn_forge_tool"):
            pt = self.rpg.pickaxe_tier
            if pt >= 5:
                self.btn_forge_tool.setText("⛏️ 생활 도구 Lv.5 MAX (드랍률 최고)")
            else:
                self.btn_forge_tool.setText(f"⛏️ 채집 도구 Lv.{pt}➔Lv.{pt+1}  ({120*pt}G · 🪨{3*pt})")

        growth_pct = int(float(self.rpg.farm.get("growth", 0.0)) * 100)
        q_str = " ➔ ".join(self.rpg.dispatch_queue) if self.rpg.dispatch_queue else "대기 중"
        self.lbl_farm_status.setText(
            f"🌱 텃밭 성장률: {growth_pct}% {'(🌾 수확 가능!)' if growth_pct >= 100 else ''}   |   📋 원정 대기열: {q_str}"
        )

        next_w = self.rpg.highest_wave + 1
        self.lbl_gear_check.setText(self.rpg.diagnose_wave_readiness(next_w))
        if hasattr(self, "lbl_last_battle_report"):
            rep = self.rpg.last_defense_report
            if isinstance(rep, dict) and rep.get("recommendations"):
                top_recs = "\n".join(f"• {r.get('text', r)}" for r in rep["recommendations"][:3])
                self.lbl_last_battle_report.setText(
                    f"📊 [직전 전투 분석 · Wave {rep.get('wave', next_w)}] "
                    f"실측 {rep.get('actualDps', 0)} DPS / 요구 {rep.get('reqDps', 0)} DPS\n{top_recs}"
                )
                self.lbl_last_battle_report.show()
            else:
                self.lbl_last_battle_report.hide()
        if hasattr(self, "btn_next_wave"):
            self.btn_next_wave.setText(f"⚔️ Wave {next_w} 디펜스 출격 (Ctrl+D)")

        for w_num, btn_st in getattr(self, "_stage_jump_btns", {}).items():
            unlocked = w_num <= (self.rpg.highest_wave + 1)
            base_lbl = f"⚔️ Stage {w_num}" if w_num == 1 else f"👑 Boss W{w_num}"
            if unlocked:
                btn_st.setText(base_lbl)
                btn_st.setStyleSheet(self._small_btn_style("#F43F5E" if w_num >= 5 else "#38BDF8", active=(w_num == next_w)))
            else:
                btn_st.setText(f"🔒 {base_lbl}")
                btn_st.setStyleSheet(self._small_btn_style("#475569", active=False))

        if hasattr(self, "_consumable_use_btns"):
            for c_key, btn in self._consumable_use_btns.items():
                c_spec = CONSUMABLE_SPECS[c_key]
                cnt = self.rpg.consumables.get(c_key, 0)
                btn.setText(f"{self._SHORT_CONS.get(c_key, c_spec['name'][:6])} · x{cnt}")

        if hasattr(self, "_bento_btns"):
            for b_key, btn_b in self._bento_btns.items():
                b_spec = BENTO_RECIPES[b_key]
                cnt = self.rpg.bentos.get(b_key, 0)
                ing = f"🌾{b_spec['crops']}" + (f" 🐟{b_spec['fish_common']}" if b_spec["fish_common"] else "") + (f" 🐠{b_spec['fish_rare']}" if b_spec["fish_rare"] else "")
                btn_b.setText(f"{self._SHORT_BENTOS.get(b_key, b_key)} x{cnt}  ({ing})")

        if hasattr(self, "_turret_btns"):
            for t_key, btn_t in self._turret_btns.items():
                t_spec = TURRET_SPECS[t_key]
                lv = t.get(t_key, 0)
                if lv >= 5:
                    btn_t.setText(f"{self._SHORT_TURRETS.get(t_key, t_key)} Lv.5 MAX")
                else:
                    m = lv + 1
                    g_cost = int(t_spec["base_gold"]) * m
                    btn_t.setText(f"{self._SHORT_TURRETS.get(t_key, t_key)} Lv.{lv}➔{m}  ({g_cost}G)")

        if hasattr(self, "lbl_bag_items"):
            items_sorted = sorted(
                self.rpg.collected_items.items(),
                key=lambda kv: (
                    0 if kv[1].get("tier") == "Legendary" else (1 if kv[1].get("tier") == "Rare" else 2),
                    -int(kv[1].get("count", 0)),
                ),
            )
            badge_strs = []
            for item_name, meta in items_sorted[:18]:
                ic = meta.get("icon", "🎁")
                cnt = int(meta.get("count", 1))
                tier = meta.get("tier", "Common")
                color = "#FACC15" if tier == "Legendary" else ("#C084FC" if tier == "Rare" else "#94A3B8")
                badge_strs.append(f"<span style='color:{color};'>{ic} {item_name} x{cnt}</span>")
            self.lbl_bag_items.setText(" &nbsp;&nbsp;·&nbsp;&nbsp; ".join(badge_strs) if badge_strs else "🎁 <i>획득 전리품 없음</i>")

    def show_beside_pet(self, pet_rect: QRect) -> None:
        self.refresh_labels()
        screen = QGuiApplication.screenAt(pet_rect.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        x = pet_rect.left() - self.width() - 16
        if x < avail.left() + 20:
            x = min(avail.right() - self.width() - 20, pet_rect.right() + 16)
        x = max(avail.left() + 20, min(avail.right() - self.width() - 20, x))
        y = max(avail.top() + 20, min(avail.bottom() - self.height() - 20, (avail.height() - self.height()) // 2 + avail.top()))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), 18.0, 18.0)

        # Deep Obsidian Cupertino Dark-Glass surface
        grad = QLinearGradient(0, 0, 0, float(rect.height()))
        grad.setColorAt(0.0, QColor(15, 23, 42, 244))
        grad.setColorAt(0.50, QColor(10, 15, 29, 246))
        grad.setColorAt(1.0, QColor(6, 10, 20, 248))
        p.fillPath(path, grad)

        # Crisp 1px Specular Glass Rim + soft Neumorphic top inner highlight
        p.setPen(QPen(QColor(255, 255, 255, 36), 1.1))
        p.drawPath(path)

        inner = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(float(inner.x()), float(inner.y()), float(inner.width()), float(inner.height()), 17.0, 17.0)
        p.setPen(QPen(QColor(56, 189, 248, 28), 1.0))
        p.drawPath(inner_path)
        p.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    @staticmethod
    def _pill_btn_style(accent: str) -> str:
        return (
            f"QPushButton {{ background: rgba(15, 23, 42, 0.85); color: #E2E8F0; "
            f"border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 17px; padding: 7px 15px; "
            f"font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; font-size: 13px; font-weight: 800; }}"
            f"QPushButton:checked {{ background: rgba(56, 189, 248, 0.22); color: #38BDF8; border-color: {accent}; }}"
            f"QPushButton:hover {{ background: rgba(30, 41, 59, 0.95); border-color: {accent}; color: #FFFFFF; }}"
        )

    @staticmethod
    def _segmented_btn_style(active: bool = False) -> str:
        if active:
            return (
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                "stop:0 rgba(56, 189, 248, 0.28), stop:1 rgba(14, 165, 233, 0.16)); "
                "color: #F8FAFC; border: 1px solid rgba(56, 189, 248, 0.65); border-radius: 8px; "
                "padding: 5px 12px; font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; "
                "font-size: 13px; font-weight: 800; }"
            )
        return (
            "QPushButton { background: transparent; color: #94A3B8; border: 1px solid transparent; "
            "border-radius: 8px; padding: 5px 12px; font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; "
            "font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.05); color: #E2E8F0; }"
        )

    @staticmethod
    def _action_btn_style(accent: str) -> str:
        return (
            "QPushButton { "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(23, 33, 53, 0.90), stop:1 rgba(13, 20, 36, 0.94)); "
            "color: #F8FAFC; "
            "border: 1px solid rgba(255, 255, 255, 0.10); "
            f"border-left: 3px solid {accent}; "
            "border-radius: 10px; "
            "padding: 8px 13px; "
            "font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; "
            "font-size: 13px; font-weight: 800; text-align: left; "
            "}"
            "QPushButton:hover { "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(30, 43, 68, 0.96), stop:1 rgba(19, 29, 50, 0.98)); "
            f"border: 1px solid {accent}; "
            f"border-left: 3px solid {accent}; "
            "color: #FFFFFF; "
            "}"
            "QPushButton:pressed { background: rgba(10, 15, 28, 0.98); }"
        )

    @staticmethod
    def _small_btn_style(accent: str, active: bool = False) -> str:
        if active:
            return (
                "QPushButton { "
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(56, 189, 248, 0.25), stop:1 rgba(14, 165, 233, 0.14)); "
                f"color: #FFFFFF; border: 1px solid {accent}; border-radius: 9px; padding: 6px 11px; "
                "font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; font-size: 13px; font-weight: 800; }"
            )
        return (
            "QPushButton { "
            "background: rgba(17, 25, 42, 0.88); color: #E2E8F0; "
            "border: 1px solid rgba(255, 255, 255, 0.10); "
            f"border-bottom: 2px solid {accent}; "
            "border-radius: 9px; padding: 6px 11px; "
            "font-family: 'Pretendard','Malgun Gothic','Segoe UI',sans-serif; font-size: 13px; font-weight: 700; }"
            f"QPushButton:hover {{ background: rgba(28, 40, 64, 0.95); border-color: {accent}; color: #FFFFFF; }}"
        )
