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
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
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
        "name": "🧱 강철 바리케이드",
        "base_gold": 80,
        "ore_common": 3,
        "ore_rare": 0,
        "wood": 2,
        "core": 0,
        "desc": "수호 코어 최대 HP +250 증가 및 적 공격 피해 8% 경감",
    },
    "ballista": {
        "name": "🏹 연발 발리스타",
        "base_gold": 140,
        "ore_common": 4,
        "ore_rare": 1,
        "wood": 2,
        "core": 0,
        "desc": "단일 표적 고속 물리 화살 자동 사격 포탑",
    },
    "frost": {
        "name": "❄️ 프로스트 크리스탈 타워",
        "base_gold": 220,
        "ore_common": 2,
        "ore_rare": 3,
        "wood": 0,
        "core": 1,
        "desc": "빙결 마법탄 발사 — 적 이동속도 48% 둔화 (Wave 10 필수)",
    },
    "arc": {
        "name": "⚡ 오리할콘 아크 캐논",
        "base_gold": 360,
        "ore_common": 0,
        "ore_rare": 3,
        "wood": 0,
        "core": 2,
        "desc": "최대 3기 동시 타격 연쇄 번개 광역 포탑 (Wave 15 필수)",
    },
}


class RPGWorldState:
    """Manages persistent RPG stats, inventory, farm growth, economy, and defense progression."""

    def __init__(self, data_dir: Path) -> None:
        self.save_path = data_dir / SAVE_FILE_NAME
        self.worldview: str = "fantasy"
        self.unlocked_worldviews: list[str] = ["fantasy", "cyberpunk", "scifi", "cozy"]
        self.work_safe_mode: bool = False
        self.basecamp_visible: bool = True

        self.pet_level: int = 1
        self.pet_xp: int = 0
        self.gold: int = 250

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
            "ballista": 0,
            "frost": 0,
            "arc": 0,
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
    def hero_atk(self) -> int:
        base_wep = 12 + self.weapon_tier * 10
        return int(round(15 + 4 * self.pet_level + base_wep * (1.0 + 0.14 * self.weapon_enhance)))

    @property
    def hero_max_hp(self) -> int:
        return int(round(140 + 30 * self.pet_level + self.weapon_enhance * 18))

    @property
    def tool_bonus_rare(self) -> float:
        avg_tool = (self.pickaxe_tier + self.rod_tier + self.watering_tier) / 3.0
        return min(0.25, (avg_tool - 1.0) * 0.06)

    def add_pet_xp(self, amount: int) -> bool:
        self.pet_xp += max(0, int(amount))
        new_lv = int(math.floor(math.sqrt(self.pet_xp / 25.0))) + 1
        leveled = new_lv > self.pet_level
        if leveled:
            self.pet_level = new_lv
        return leveled

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
        if self.gold < gold_cost:
            return False, f"강화 골드가 부족해요! (필요: {gold_cost}G / 보유: {self.gold}G) ➔ 농사/낚시 납품으로 골드를 모아보세요!"
        if self.inventory.get("ore_common", 0) < ore_c_cost:
            return False, f"일반 광석이 부족해요! (필요: {ore_c_cost}개) ➔ [⛏️ 바탕화면 채굴]을 지시해 광석을 캐보세요!"
        if self.inventory.get("ore_rare", 0) < ore_r_cost:
            return False, f"희귀 광석이 부족해요! (필요: {ore_r_cost}개) ➔ 채굴을 통해 미스릴/마나수정을 발굴하세요!"

        self.gold -= gold_cost
        self.inventory["ore_common"] -= ore_c_cost
        self.inventory["ore_rare"] -= ore_r_cost
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

        self.gold -= g_cost
        self.inventory["ore_common"] -= oc_cost
        self.inventory["ore_rare"] -= or_cost
        self.inventory["wood"] -= w_cost
        self.inventory["invader_core"] -= core_cost
        self.turrets[turret_key] = cur_lv + 1
        self.add_pet_xp(40)
        self.save()
        return True, f"🏰 [{spec['name']}] Lv.{cur_lv + 1} 건설/증축 완료! 웨이브 디펜스 전장에 배치됩니다!"

    def diagnose_wave_readiness(self, target_wave: int) -> str:
        """Returns a clear gear-check diagnosis linking Defense difficulty to Mining/Farming/Fishing."""
        total_bentos = sum(self.bentos.values())
        if target_wave >= 15:
            if self.weapon_enhance < 9 or self.turrets.get("arc", 0) < 1 or total_bentos < 1:
                return f"⚠️ [Wave {target_wave} 기어 체크 경고] 권장 스펙: 무기 +9강 이상(채굴), 아크 캐논 건설(채굴), 황제 도시락(농사+낚시)!"
        elif target_wave >= 10:
            if self.weapon_enhance < 6 or self.turrets.get("frost", 0) < 1 or total_bentos < 1:
                return f"⚠️ [Wave {target_wave} 보스 대비] 권장 스펙: 무기 +6강(채굴), 프로스트 타워(채굴), 황금 잉어 매운탕(농사+낚시)!"
        elif target_wave >= 5:
            if self.weapon_enhance < 3 or self.turrets.get("ballista", 0) < 1 or total_bentos < 1:
                return f"💡 [Wave {target_wave} 보스 팁] 무기 +3강(채굴), 발리스타 포탑(채굴+목재), 송어 스테이크(농사+낚시)를 준비하면 쉽게 돌파해요!"
        return f"✅ [Wave {target_wave} 출격 준비 완료] 현재 공격력 {self.hero_atk}, 보유 도시락 {total_bentos}개로 충분히 돌파 가능합니다!"

    def diagnose_wave_readiness_dict(self, target_wave: int) -> dict:
        """Returns structured combat power and specific causal progression advices."""
        turret_cp = sum(self.turrets.values()) * 35
        bento_cp = sum(self.bentos.values()) * 25
        player_cp = self.hero_atk * 4 + turret_cp + bento_cp
        rec_cp = 120 + target_wave * 55
        advices: list[str] = []
        if self.weapon_enhance < max(1, target_wave // 2):
            advices.append(f"[채굴 ➔ 대장간] 무기 강화가 부족합니다 (현재 +{self.weapon_enhance}강, 권장 +{max(1, target_wave // 2)}강)")
        if target_wave >= 5 and self.turrets.get("ballista", 0) < 1:
            advices.append("[채굴+농사 ➔ 포탑] 연발 발리스타 포탑을 건설하면 화력이 크게 증가합니다")
        if target_wave >= 10 and self.turrets.get("frost", 0) < 1:
            advices.append("[희귀광석+코어 ➔ 포탑] 프로스트 크리스탈 타워(적 감속)가 필요합니다")
        if sum(self.bentos.values()) < 1:
            advices.append("[농사+낚시 ➔ 요리] 전투 도시락을 요리해 두면 위기 시 자동 회복+공격력 버프가 발동됩니다")
        if not advices:
            advices.append(self.diagnose_wave_readiness(target_wave))
        return {
            "player_cp": player_cp,
            "rec_cp": rec_cp,
            "advices": advices,
            "summary": self.diagnose_wave_readiness(target_wave),
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
            "weaponEnhance": self.weapon_enhance,
            "weaponTier": self.weapon_tier,
            "pickaxeTier": self.pickaxe_tier,
            "rodTier": self.rod_tier,
            "wateringTier": self.watering_tier,
            "toolBonusRare": self.tool_bonus_rare,
            "turrets": dict(self.turrets),
            "bentos": dict(self.bentos),
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
                "worldview": self.worldview,
                "unlocked_worldviews": self.unlocked_worldviews,
                "work_safe_mode": self.work_safe_mode,
                "basecamp_visible": self.basecamp_visible,
                "pet_level": self.pet_level,
                "pet_xp": self.pet_xp,
                "gold": self.gold,
                "weapon_enhance": self.weapon_enhance,
                "pickaxe_tier": self.pickaxe_tier,
                "rod_tier": self.rod_tier,
                "watering_tier": self.watering_tier,
                "inventory": self.inventory,
                "bentos": self.bentos,
                "turrets": self.turrets,
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
            self.worldview = str(data.get("worldview", "fantasy"))
            self.unlocked_worldviews = list(data.get("unlocked_worldviews", ["fantasy", "cyberpunk", "scifi", "cozy"]))
            self.work_safe_mode = bool(data.get("work_safe_mode", False))
            self.basecamp_visible = bool(data.get("basecamp_visible", True))
            self.pet_level = int(data.get("pet_level", 1))
            self.pet_xp = int(data.get("pet_xp", 0))
            self.gold = int(data.get("gold", 250))
            self.weapon_enhance = int(data.get("weapon_enhance", 0))
            self.pickaxe_tier = int(data.get("pickaxe_tier", 1))
            self.rod_tier = int(data.get("rod_tier", 1))
            self.watering_tier = int(data.get("watering_tier", 1))
            if isinstance(data.get("inventory"), dict):
                self.inventory.update(data["inventory"])
            if isinstance(data.get("bentos"), dict):
                self.bentos.update(data["bentos"])
            if isinstance(data.get("turrets"), dict):
                self.turrets.update(data["turrets"])
            if isinstance(data.get("farm"), dict):
                self.farm.update(data["farm"])
            if isinstance(data.get("dispatch_queue"), list):
                self.dispatch_queue = [str(x) for x in data["dispatch_queue"][:5]]
            self.highest_wave = int(data.get("highest_wave", 0))
            self.total_enemies_defeated = int(data.get("total_enemies_defeated", 0))
            if isinstance(data.get("skill_xp"), dict):
                self.skill_xp.update(data["skill_xp"])
            self.tick_farm_growth()
        except Exception:
            pass


class RPGWorldHubDrawer(QWidget):
    """
    Glassmorphic Floating RPG World, Economy, Dispatch & Defense Command Center (Ctrl+R).
    Floats independently beside Ppong-ppong-i so 3D viewport is never clipped.
    """

    dispatch_requested = pyqtSignal(str)          # 'mining' | 'gardening' | 'fishing' | 'skirmish' | 'auto_queue'
    worldview_changed = pyqtSignal(str)           # 'fantasy' | 'cyberpunk' | 'scifi' | 'cozy'
    work_safe_toggled = pyqtSignal(bool)
    skirmish_requested = pyqtSignal()
    wave_defense_requested = pyqtSignal(int)      # wave_number
    stop_combat_requested = pyqtSignal()
    state_modified = pyqtSignal(str)              # feedback toast message

    def __init__(self, rpg_state: RPGWorldState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.rpg = rpg_state
        self.setWindowTitle("🦄 뽕뽕이 3D 월드 & 디펜스 사령부 (Ctrl+R)")
        self.setFixedSize(460, 560)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._drag_pos: Optional[QPoint] = None
        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.refresh_labels)
        self._refresh_timer.start()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(8)

        # Top Header Bar
        header = QHBoxLayout()
        title_lbl = QLabel("🏰 뽕뽕이 3D 월드 & 디펜스 사령부")
        title_lbl.setStyleSheet("color: #f8fafc; font-size: 14px; font-weight: 800;")
        header.addWidget(title_lbl)
        header.addStretch()

        self.btn_work_safe = QPushButton("💼 업무 집중(클릭투과): OFF")
        self.btn_work_safe.setCheckable(True)
        self.btn_work_safe.setChecked(self.rpg.work_safe_mode)
        self.btn_work_safe.clicked.connect(self._on_work_safe_clicked)
        self.btn_work_safe.setStyleSheet(self._pill_btn_style("#0ea5e9"))
        header.addWidget(self.btn_work_safe)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.hide)
        btn_close.setStyleSheet(
            "QPushButton { background: rgba(239,68,68,0.22); color: #fca5a5; border: 1px solid rgba(239,68,68,0.5); border-radius: 13px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(239,68,68,0.45); color: #ffffff; }"
        )
        header.addWidget(btn_close)
        root_layout.addLayout(header)

        # Hero Summary & Inventory Status Card
        self.lbl_hero_summary = QLabel()
        self.lbl_hero_summary.setWordWrap(True)
        self.lbl_hero_summary.setStyleSheet(
            "background: rgba(15, 23, 42, 0.85); color: #e2e8f0; border: 1px solid rgba(56, 189, 248, 0.35); "
            "border-radius: 10px; padding: 8px 10px; font-size: 11px; line-height: 1.4;"
        )
        root_layout.addWidget(self.lbl_hero_summary)

        # Worldview Selector Bar (4 Themes)
        wv_bar = QHBoxLayout()
        wv_bar.setSpacing(4)
        for wv_key, wv_meta in WORLDVIEW_INFO.items():
            btn_wv = QPushButton(wv_meta["title"])
            btn_wv.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_wv.setStyleSheet(self._small_btn_style("#334155"))
            btn_wv.clicked.connect(lambda _c, k=wv_key: self._on_worldview_selected(k))
            wv_bar.addWidget(btn_wv)
        root_layout.addLayout(wv_bar)

        # 3 Main Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid rgba(56, 189, 248, 0.28);
                background: rgba(15, 23, 42, 0.78);
                border-radius: 10px;
            }
            QTabBar::tab {
                background: rgba(30, 41, 59, 0.85);
                color: #94a3b8;
                padding: 7px 12px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #0284c7;
                color: #ffffff;
            }
            """
        )
        self.tabs.addTab(self._build_tab_dispatch_economy(), "📋 작업지시 · 농장 · 상점")
        self.tabs.addTab(self._build_tab_craft_cooking(), "🍳 요리 · 대장간 · 포탑")
        self.tabs.addTab(self._build_tab_defense(), "⚔️ 수호 · 웨이브 디펜스")
        root_layout.addWidget(self.tabs, 1)

        # Bottom Toast Feedback Label
        self.lbl_feedback = QLabel("💡 업무 중에는 [작업 지시]를 내려두고, 휴식 시간에 [웨이브 디펜스]를 즐겨보세요!")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setStyleSheet(
            "background: rgba(2, 6, 23, 0.9); color: #fde047; border: 1px solid rgba(250, 204, 21, 0.35); "
            "border-radius: 8px; padding: 6px 8px; font-size: 11px; font-weight: 600;"
        )
        root_layout.addWidget(self.lbl_feedback)
        self.refresh_labels()

    def _build_tab_dispatch_economy(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # 1. Task Dispatch Section
        sec1 = QLabel("📋 간헐적 업무 지시 (바탕화면 로밍 채굴 · 농사 · 낚시 오더)")
        sec1.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px;")
        lay.addWidget(sec1)

        row1 = QHBoxLayout()
        for label, key, col in [
            ("⛏️ 채굴 지시", "mining", "#0284c7"),
            ("🌱 농사 지시", "gardening", "#16a34a"),
            ("🎣 낚시 지시", "fishing", "#0d9488"),
            ("🛡️ 경비 수호", "skirmish", "#7c3aed"),
        ]:
            b = QPushButton(label)
            b.setStyleSheet(self._action_btn_style(col))
            b.clicked.connect(lambda _c, k=key: self.dispatch_requested.emit(k))
            row1.addWidget(b)
        lay.addLayout(row1)

        btn_auto_q = QPushButton("🔄 3슬롯 연속 작업 예약 큐 가동 ([채굴] ➔ [농사] ➔ [낚시] 자동 순환)")
        btn_auto_q.setStyleSheet(self._action_btn_style("#2563eb"))
        btn_auto_q.clicked.connect(lambda: self.dispatch_requested.emit("auto_queue"))
        lay.addWidget(btn_auto_q)

        # 2. Mini Farm Plot Section
        sec2 = QLabel("🌱 바탕화면 3D 텃밭 (오프라인 자동 성장 & 수확)")
        sec2.setStyleSheet("color: #4ade80; font-weight: 800; font-size: 12px; margin-top: 4px;")
        lay.addWidget(sec2)

        self.lbl_farm_status = QLabel()
        self.lbl_farm_status.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        lay.addWidget(self.lbl_farm_status)

        farm_row = QHBoxLayout()
        btn_water = QPushButton("💧 텃밭 물주기 (+성장 가속)")
        btn_water.setStyleSheet(self._action_btn_style("#0ea5e9"))
        btn_water.clicked.connect(self._on_water_farm)
        btn_harvest = QPushButton("🌾 다 자란 작물/목재 수확하기")
        btn_harvest.setStyleSheet(self._action_btn_style("#15803d"))
        btn_harvest.clicked.connect(self._on_harvest_farm)
        farm_row.addWidget(btn_water)
        farm_row.addWidget(btn_harvest)
        lay.addLayout(farm_row)

        # 3. Shop & Economy Section
        sec3 = QLabel("🏪 퐁퐁 상점 (수확 작물 & 물고기 납품 ➔ 강화/제작 골드 확보)")
        sec3.setStyleSheet("color: #facc15; font-weight: 800; font-size: 12px; margin-top: 4px;")
        lay.addWidget(sec3)

        shop_row = QHBoxLayout()
        btn_sell_crop = QPushButton("💰 농작물 상점 납품 (+골드)")
        btn_sell_crop.setStyleSheet(self._action_btn_style("#ca8a04"))
        btn_sell_crop.clicked.connect(self._on_sell_crops)
        btn_sell_fish = QPushButton("🐟 어획물 상점 납품 (+골드)")
        btn_sell_fish.setStyleSheet(self._action_btn_style("#d97706"))
        btn_sell_fish.clicked.connect(self._on_sell_fish)
        shop_row.addWidget(btn_sell_crop)
        shop_row.addWidget(btn_sell_fish)
        lay.addLayout(shop_row)

        lay.addStretch()
        return w

    def _build_tab_craft_cooking(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # 1. Blacksmith & Tools
        sec_forge = QLabel("🔨 대장간 무기 진화 & 생활 도구 승급 (채굴 광석 + 상점 골드 필수)")
        sec_forge.setStyleSheet("color: #f87171; font-weight: 800; font-size: 12px;")
        lay.addWidget(sec_forge)

        forge_row = QHBoxLayout()
        btn_wep = QPushButton("🗡️ 무기 강화 (+1~+15 / 4단계 외형 진화)")
        btn_wep.setStyleSheet(self._action_btn_style("#dc2626"))
        btn_wep.clicked.connect(self._on_enhance_weapon)
        btn_tool = QPushButton("⛏️ 곡괭이/낚싯대/물뿌리개 승급")
        btn_tool.setStyleSheet(self._action_btn_style("#4f46e5"))
        btn_tool.clicked.connect(self._on_upgrade_tools)
        forge_row.addWidget(btn_wep)
        forge_row.addWidget(btn_tool)
        lay.addLayout(forge_row)

        # 2. Battle Bento Kitchen
        sec_cook = QLabel("🍳 전투 도시락 공방 (농사 작물 + 낚시 어종 ➔ 디펜스 자동 회복/버프)")
        sec_cook.setStyleSheet("color: #fb923c; font-weight: 800; font-size: 12px; margin-top: 4px;")
        lay.addWidget(sec_cook)

        for b_key, b_spec in BENTO_RECIPES.items():
            btn_b = QPushButton(
                f"{b_spec['name']} 조리 (작물 {b_spec['crops']} + 일반어 {b_spec['fish_common']} + 희귀어 {b_spec['fish_rare']})"
            )
            btn_b.setToolTip(b_spec["desc"])
            btn_b.setStyleSheet(self._action_btn_style("#ea580c"))
            btn_b.clicked.connect(lambda _c, k=b_key: self._on_cook_bento(k))
            lay.addWidget(btn_b)

        # 3. Defense Turrets Construction
        sec_tur = QLabel("🏰 3D 디펜스 포탑 & 바리케이드 건설 (채굴 광석 + 목재 + 침입자 코어)")
        sec_tur.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px; margin-top: 4px;")
        lay.addWidget(sec_tur)

        for t_key, t_spec in TURRET_SPECS.items():
            btn_t = QPushButton(
                f"{t_spec['name']} 증축 (기본 {t_spec['base_gold']}G / 일반광석 {t_spec['ore_common']} / 희귀 {t_spec['ore_rare']})"
            )
            btn_t.setToolTip(t_spec["desc"])
            btn_t.setStyleSheet(self._action_btn_style("#0284c7"))
            btn_t.clicked.connect(lambda _c, k=t_key: self._on_upgrade_turret(k))
            lay.addWidget(btn_t)

        scroll.setWidget(w)
        return scroll

    def _build_tab_defense(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        sec1 = QLabel("🛡️ 간헐적 바탕화면 수호 (Skirmish Defense)")
        sec1.setStyleSheet("color: #a855f7; font-weight: 800; font-size: 12px;")
        lay.addWidget(sec1)

        btn_skirmish = QPushButton("👾 침입자 즉시 출현 & 바탕화면 수호 교전 시작 (Ctrl+E)")
        btn_skirmish.setStyleSheet(self._action_btn_style("#7c3aed"))
        btn_skirmish.clicked.connect(self.skirmish_requested.emit)
        lay.addWidget(btn_skirmish)

        sec2 = QLabel("🏰 3D 웨이브 디펜스 미니게임 (Desktop Siege Defense / Ctrl+D)")
        sec2.setStyleSheet("color: #facc15; font-weight: 800; font-size: 12px; margin-top: 6px;")
        lay.addWidget(sec2)

        self.lbl_gear_check = QLabel()
        self.lbl_gear_check.setWordWrap(True)
        self.lbl_gear_check.setStyleSheet(
            "background: rgba(30, 41, 59, 0.9); color: #fde047; border-radius: 8px; padding: 8px; font-size: 11px;"
        )
        lay.addWidget(self.lbl_gear_check)

        btn_next_wave = QPushButton("⚔️ 다음 웨이브 출격! (최고 기록 갱신 도전)")
        btn_next_wave.setStyleSheet(self._action_btn_style("#e11d48"))
        btn_next_wave.clicked.connect(lambda: self._launch_wave(self.rpg.highest_wave + 1))
        lay.addWidget(btn_next_wave)

        wave_grid = QHBoxLayout()
        for w_num, label in [
            (1, "Wave 1 (입문)"),
            (5, "👑 Wave 5 (보스)"),
            (10, "👑 Wave 10 (보스)"),
            (15, "👑 Wave 15 (보스)"),
        ]:
            b = QPushButton(label)
            b.setStyleSheet(self._small_btn_style("#be123c" if w_num >= 5 else "#0369a1"))
            b.clicked.connect(lambda _c, wn=w_num: self._launch_wave(wn))
            wave_grid.addWidget(b)
        lay.addLayout(wave_grid)

        btn_stop = QPushButton("⏹️ 전투 / 디펜스 모드 즉시 종료 (일상 복귀)")
        btn_stop.setStyleSheet(self._small_btn_style("#475569"))
        btn_stop.clicked.connect(self.stop_combat_requested.emit)
        lay.addWidget(btn_stop)

        lay.addStretch()
        return w

    def _launch_wave(self, wave_num: int) -> None:
        diag = self.rpg.diagnose_wave_readiness(wave_num)
        self.set_feedback(diag)
        self.wave_defense_requested.emit(wave_num)

    def _on_work_safe_clicked(self, checked: bool) -> None:
        self.rpg.work_safe_mode = bool(checked)
        self.rpg.save()
        self.refresh_labels()
        self.work_safe_toggled.emit(self.rpg.work_safe_mode)

    def _on_worldview_selected(self, wv_key: str) -> None:
        self.rpg.worldview = wv_key
        self.rpg.save()
        self.refresh_labels()
        self.worldview_changed.emit(wv_key)
        meta = WORLDVIEW_INFO.get(wv_key, WORLDVIEW_INFO["fantasy"])
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

    def set_feedback(self, text: str) -> None:
        self.lbl_feedback.setText(text)

    def refresh_ui(self) -> None:
        self.refresh_labels()

    def refresh_labels(self) -> None:
        self.rpg.tick_farm_growth()
        inv = self.rpg.inventory
        b = self.rpg.bentos
        t = self.rpg.turrets
        wv_title = WORLDVIEW_INFO.get(self.rpg.worldview, WORLDVIEW_INFO["fantasy"])["title"]

        self.btn_work_safe.setChecked(self.rpg.work_safe_mode)
        self.btn_work_safe.setText(
            "💼 업무 집중(클릭투과): ON" if self.rpg.work_safe_mode else "💼 업무 집중(클릭투과): OFF"
        )

        summary_html = (
            f"<b>[{wv_title}]</b> 🦄 <b>Lv.{self.rpg.pet_level}</b> (EXP {self.rpg.pet_xp}) | "
            f"⚔️ 공격력 <b>{self.rpg.hero_atk}</b> (무기 <b>+{self.rpg.weapon_enhance}강</b> / Tier {self.rpg.weapon_tier}) | "
            f"💰 <b>{self.rpg.gold} G</b> | 🏆 최고 <b>Wave {self.rpg.highest_wave}</b><br>"
            f"⛏️ 광석(일반 <b>{inv.get('ore_common',0)}</b> / 희귀 <b>{inv.get('ore_rare',0)}</b> / 전설 <b>{inv.get('ore_legendary',0)}</b>) | "
            f"🌾 작물 <b>{inv.get('crops',0)}</b> · 목재 <b>{inv.get('wood',0)}</b> | "
            f"🐟 물고기(일반 <b>{inv.get('fish_common',0)}</b> / 희귀 <b>{inv.get('fish_rare',0)}</b>) | "
            f"👾 코어 <b>{inv.get('invader_core',0)}</b><br>"
            f"🍱 보유 도시락(감자 <b>{b.get('potato_fish',0)}</b> / 송어 <b>{b.get('trout_steak',0)}</b> / 매운탕 <b>{b.get('carp_stew',0)}</b> / 황제 <b>{b.get('star_emperor',0)}</b>) | "
            f"🏰 포탑(방벽 Lv.{t.get('barricade',1)} / 발리스타 Lv.{t.get('ballista',0)} / 빙결 Lv.{t.get('frost',0)} / 아크포 Lv.{t.get('arc',0)})"
        )
        self.lbl_hero_summary.setText(summary_html)

        growth_pct = int(float(self.rpg.farm.get("growth", 0.0)) * 100)
        q_str = " ➔ ".join(self.rpg.dispatch_queue) if self.rpg.dispatch_queue else "대기 중 (자율 활동)"
        self.lbl_farm_status.setText(
            f"🌱 텃밭 성장률: {growth_pct}% ({'🌾수확 가능!' if growth_pct >= 100 else '성장 중'}) | 📋 예약 작업 큐: [{q_str}]"
        )

        next_w = self.rpg.highest_wave + 1
        self.lbl_gear_check.setText(self.rpg.diagnose_wave_readiness(next_w))

    def show_beside_pet(self, pet_rect: QRect) -> None:
        self.refresh_labels()
        x = pet_rect.left() - self.width() - 12
        if x < 20:
            x = pet_rect.right() + 12
        y = max(40, min(pet_rect.bottom() - self.height(), 600))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), 16.0, 16.0)
        p.fillPath(path, QColor(2, 6, 23, 238))
        p.setPen(QPen(QColor(56, 189, 248, 120), 1.5))
        p.drawPath(path)
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
            f"QPushButton {{ background: rgba(15,23,42,0.9); color: #f8fafc; border: 1px solid {accent}; "
            f"border-radius: 11px; padding: 4px 10px; font-size: 10px; font-weight: 700; }}"
            f"QPushButton:checked {{ background: {accent}; color: #020617; }}"
        )

    @staticmethod
    def _action_btn_style(bg: str) -> str:
        return (
            f"QPushButton {{ background: {bg}; color: #ffffff; border: 1px solid rgba(255,255,255,0.2); "
            f"border-radius: 7px; padding: 7px 10px; font-size: 11px; font-weight: 700; text-align: left; }}"
            f"QPushButton:hover {{ border: 1px solid #fde047; }}"
        )

    @staticmethod
    def _small_btn_style(bg: str) -> str:
        return (
            f"QPushButton {{ background: {bg}; color: #f8fafc; border: 1px solid rgba(255,255,255,0.18); "
            f"border-radius: 6px; padding: 5px 8px; font-size: 10px; font-weight: 700; }}"
            f"QPushButton:hover {{ border: 1px solid #38bdf8; }}"
        )
