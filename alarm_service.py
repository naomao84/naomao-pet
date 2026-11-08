"""
Alarm Service for Ppong-ppong-i Desktop Pet:
- Parses Korean natural language alarm / timer commands from chat.
- Manages scheduled alarms, one-shot timers, and snoozes.
- Persists alarms across sessions in 'pet_alarms.json'.
- Emits Qt signals when alarm time is reached to display the 3D Visual Alarm Dialog.
"""

from __future__ import annotations
import datetime
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


ALARM_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_alarms.json")


class AlarmItem:
    def __init__(
        self,
        alarm_id: str,
        trigger_timestamp: float,
        label: str,
        raw_text: str = "",
        is_snoozed: bool = False,
    ) -> None:
        self.alarm_id = alarm_id
        self.trigger_timestamp = trigger_timestamp
        self.label = label
        self.raw_text = raw_text
        self.is_snoozed = is_snoozed
        self.triggered = False

    @property
    def target_time_str(self) -> str:
        dt = datetime.datetime.fromtimestamp(self.trigger_timestamp)
        return dt.strftime("%H:%M:%S")

    @property
    def target_datetime_str(self) -> str:
        dt = datetime.datetime.fromtimestamp(self.trigger_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.trigger_timestamp - time.time())

    @property
    def remaining_str(self) -> str:
        rem = int(self.remaining_seconds)
        hours = rem // 3600
        mins = (rem % 3600) // 60
        secs = rem % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "alarm_id": self.alarm_id,
            "trigger_timestamp": self.trigger_timestamp,
            "label": self.label,
            "raw_text": self.raw_text,
            "is_snoozed": self.is_snoozed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlarmItem":
        return cls(
            alarm_id=data.get("alarm_id", f"alarm_{int(time.time()*1000)}"),
            trigger_timestamp=float(data.get("trigger_timestamp", time.time() + 60)),
            label=data.get("label", "알람 시간이에요!"),
            raw_text=data.get("raw_text", ""),
            is_snoozed=bool(data.get("is_snoozed", False)),
        )


class AlarmManager(QObject):
    alarm_triggered = pyqtSignal(str, str, str)  # alarm_id, label, time_str
    alarms_changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._alarms: Dict[str, AlarmItem] = {}
        self._check_timer = QTimer(self)
        self._check_timer.setInterval(500)  # Check every 500ms
        self._check_timer.timeout.connect(self._check_alarms)
        self._check_timer.start()

        self._load_from_storage()

    def _load_from_storage(self) -> None:
        if not os.path.exists(ALARM_STORAGE_PATH):
            return
        try:
            with open(ALARM_STORAGE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = time.time()
            for d in data:
                item = AlarmItem.from_dict(d)
                # Keep future alarms, or alarms due within last 10s
                if item.trigger_timestamp > now - 10.0:
                    self._alarms[item.alarm_id] = item
        except Exception as e:
            sys_err = getattr(__import__("sys"), "stderr")
            sys_err.write(f"[AlarmManager] Error loading alarms: {e}\n")

    def _save_to_storage(self) -> None:
        try:
            data = [item.to_dict() for item in self._alarms.values()]
            with open(ALARM_STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            sys_err = getattr(__import__("sys"), "stderr")
            sys_err.write(f"[AlarmManager] Error saving alarms: {e}\n")

    def get_all_alarms(self) -> List[AlarmItem]:
        """Returns sorted list of alarms by trigger time."""
        return sorted(self._alarms.values(), key=lambda x: x.trigger_timestamp)

    def schedule_alarm(
        self, delay_seconds: float, label: str = "알람 시간이에요!", raw_text: str = ""
    ) -> AlarmItem:
        alarm_id = f"alarm_{int(time.time()*1000)}"
        trigger_time = time.time() + max(1.0, delay_seconds)
        item = AlarmItem(alarm_id, trigger_time, label, raw_text)
        self._alarms[alarm_id] = item
        self._save_to_storage()
        self.alarms_changed.emit()
        return item

    def schedule_absolute_alarm(
        self, target_dt: datetime.datetime, label: str = "알람 시간이에요!", raw_text: str = ""
    ) -> AlarmItem:
        delay = (target_dt - datetime.datetime.now()).total_seconds()
        if delay <= 0:
            delay += 86400.0  # If past today, schedule for tomorrow
        return self.schedule_alarm(delay, label, raw_text)

    def update_alarm(self, alarm_id: str, new_label: str, new_timestamp: float) -> bool:
        if alarm_id in self._alarms:
            item = self._alarms[alarm_id]
            item.label = new_label
            item.trigger_timestamp = new_timestamp
            self._save_to_storage()
            self.alarms_changed.emit()
            return True
        return False

    def cancel_alarm(self, alarm_id: str) -> bool:
        if alarm_id in self._alarms:
            del self._alarms[alarm_id]
            self._save_to_storage()
            self.alarms_changed.emit()
            return True
        return False

    def clear_all_alarms(self) -> None:
        self._alarms.clear()
        self._save_to_storage()
        self.alarms_changed.emit()

    def snooze_alarm(self, label: str, snooze_minutes: int = 5) -> AlarmItem:
        clean_lbl = label.replace("[다시 알림] ", "")
        item = self.schedule_alarm(
            snooze_minutes * 60, f"[다시 알림] {clean_lbl}", "snooze"
        )
        item.is_snoozed = True
        return item

    def _check_alarms(self) -> None:
        now = time.time()
        for alarm_id, item in list(self._alarms.items()):
            if not item.triggered and now >= item.trigger_timestamp:
                item.triggered = True
                del self._alarms[alarm_id]
                self._save_to_storage()
                self.alarm_triggered.emit(item.alarm_id, item.label, item.target_time_str)
                self.alarms_changed.emit()

    def try_parse_chat_alarm(self, text: str) -> Optional[Tuple[AlarmItem, str]]:
        """
        Parses user Korean chat prompt for alarm requests.
        Supports:
          - '10초 뒤에 알람 맞춰줘'
          - '5분 뒤 약 먹기'
          - '1분 뒤 라면 먹기'
          - '오후 5시 30분 회의 알람'
          - '오후 7시 운동'
          - '내일 오전 9시 스트레칭'
        """
        t = text.strip()
        low = t.lower()

        # Check for relative time pattern: (\d+)\s*(초|분|시간)\s*(뒤|후)
        rel_match = re.search(r"(\d+)\s*(초|분|시간)\s*(뒤|후)", t)
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2)
            seconds = amount
            if unit == "분":
                seconds *= 60
            elif unit == "시간":
                seconds *= 3600

            # Extract label
            label = t
            label = re.sub(r"(\d+)\s*(초|분|시간)\s*(뒤|후)에?", "", label)
            label = re.sub(r"(알람|타이머|알림|리마인더|맞춰줘|해줘|설정해줘|알려줘|등록해줘|부탁해)", "", label).strip()
            # Clean up residual words
            label = re.sub(r"\s+", " ", label).strip()
            if not label:
                label = "알람 시간이에요!"
            else:
                label = f"{label} 시간이에요!"

            item = self.schedule_alarm(seconds, label, t)
            msg = f"⏰ 알람 설정 완료! {amount}{unit} 뒤 ({item.target_time_str})에 [{item.label}]을(를) 3D 입체 팝업으로 알려드릴게요! ✨"
            return item, msg

        # Check for absolute time pattern: (오늘|내일)?\s*(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?
        abs_match = re.search(r"(오늘|내일)?\s*(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?", t)
        if abs_match:
            day_mod = abs_match.group(1)
            ampm = abs_match.group(2)
            hour = int(abs_match.group(3))
            minute = int(abs_match.group(4) or 0)

            if ampm == "오후" and hour < 12:
                hour += 12
            elif ampm == "오전" and hour == 12:
                hour = 0

            now = datetime.datetime.now()
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if day_mod == "내일":
                target_dt += datetime.timedelta(days=1)
            elif target_dt <= now:
                target_dt += datetime.timedelta(days=1)

            label = t
            label = re.sub(r"(오늘|내일)?\s*(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?에?", "", label)
            label = re.sub(r"(알람|타이머|알림|리마인더|맞춰줘|해줘|설정해줘|알려줘|등록해줘|부탁해)", "", label).strip()
            label = re.sub(r"\s+", " ", label).strip()
            if not label:
                label = "알람 시간이에요!"
            else:
                label = f"{label} 시간이에요!"

            item = self.schedule_absolute_alarm(target_dt, label, t)
            msg = f"⏰ 알람 설정 완료! {target_dt.strftime('%m월 %d일 %H:%M')}에 [{item.label}]을(를) 3D 입체 팝업으로 알려드릴게요! ✨"
            return item, msg

        return None
