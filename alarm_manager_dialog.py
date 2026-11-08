"""
Alarm Manager HUD & Dialog for Ppong-ppong-i Desktop Pet:
- Displays all currently scheduled alarms and timers with live countdowns.
- Allows adding new relative/absolute alarms with quick presets (+1m, +5m, +10m, +30m, +1h).
- Allows editing existing alarm times and labels.
- Allows canceling individual alarms or clearing all alarms.
- Seamlessly synchronizes with AlarmManager and persists across app restarts.
"""

from __future__ import annotations
import datetime
import time
from typing import Optional
from PyQt6.QtCore import QPoint, QRect, Qt, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from alarm_service import AlarmItem, AlarmManager


class EditAlarmDialog(QDialog):
    """Sub-dialog to edit an existing alarm's time and label."""

    def __init__(self, item: AlarmItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("알람 수정")
        self.setFixedSize(360, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 12px;
            }
            QLabel {
                color: #cbd5e1;
                font-family: 'Malgun Gothic';
                font-size: 13px;
                font-weight: 600;
            }
            QLineEdit, QTimeEdit {
                background: #1e293b;
                color: #38bdf8;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton {
                background: #0284c7;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #38bdf8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title_lbl = QLabel("⏰ 알람 내용 및 시간 수정")
        title_lbl.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: 800;")
        layout.addWidget(title_lbl)

        # Label input
        layout.addWidget(QLabel("알람 내용:"))
        self.label_edit = QLineEdit(item.label, self)
        layout.addWidget(self.label_edit)

        # Time input
        layout.addWidget(QLabel("목표 시각:"))
        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm:ss")
        dt = datetime.datetime.fromtimestamp(item.trigger_timestamp)
        self.time_edit.setTime(QTime(dt.hour, dt.minute, dt.second))
        layout.addWidget(self.time_edit)

        # Buttons
        btn_box = QHBoxLayout()
        save_btn = QPushButton("저장 완료", self)
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("취소", self)
        cancel_btn.setStyleSheet("background: #475569;")
        cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        layout.addLayout(btn_box)

    def get_updated_data(self) -> tuple[str, float]:
        new_label = self.label_edit.text().strip() or "알람 시간이에요!"
        t = self.time_edit.time()
        now = datetime.datetime.now()
        target_dt = now.replace(hour=t.hour(), minute=t.minute(), second=t.second(), microsecond=0)
        if target_dt <= now:
            target_dt += datetime.timedelta(days=1)
        return new_label, target_dt.timestamp()


class AlarmManagerDialog(QDialog):
    """
    Primary Alarm Management HUD for Ppong-ppong-i Desktop Pet.
    """

    def __init__(self, alarm_manager: AlarmManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.alarm_manager = alarm_manager

        self.setWindowTitle("⏰ 미니펫 알람 관리자 (Alarm Manager)")
        self.setFixedSize(620, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f8fafc;
                border: 1.5px solid #38bdf8;
                border-radius: 16px;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'Malgun Gothic';
            }
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
                gridline-color: #1e293b;
                color: #f8fafc;
                font-size: 13px;
                selection-background-color: #1e3a8a;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #38bdf8;
                font-weight: 700;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #38bdf8;
            }
            QLineEdit, QTimeEdit {
                background: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTimeEdit:focus {
                border-color: #38bdf8;
            }
            QPushButton.quick-btn {
                background: #1e293b;
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton.quick-btn:hover {
                background: #0284c7;
                color: white;
            }
            QPushButton.action-btn {
                background: linear-gradient(135deg, #0284c7, #38bdf8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton.action-btn:hover {
                background: #38bdf8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header (Title + Live Clock)
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        main_title = QLabel("⏰ 미니펫 알람 및 타이머 매니저")
        main_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #38bdf8;")
        sub_title = QLabel("자연어 채팅 등록 알람 및 개별 타이머를 실시간으로 확인하고 관리합니다.")
        sub_title.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(main_title)
        title_box.addWidget(sub_title)
        header_box.addLayout(title_box)
        header_box.addStretch()

        self.live_clock_lbl = QLabel("")
        self.live_clock_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #f472b6; background: #1e293b; padding: 6px 12px; border-radius: 8px;")
        header_box.addWidget(self.live_clock_lbl)
        layout.addLayout(header_box)

        # 2. Quick Add Bar
        quick_box = QHBoxLayout()
        quick_box.addWidget(QLabel("⚡ 간편 등록:"))
        for amount, unit, txt in [(1, 60, "+1분"), (5, 300, "+5분"), (10, 600, "+10분"), (30, 1800, "+30분"), (60, 3600, "+1시간")]:
            btn = QPushButton(txt, self)
            btn.setProperty("class", "quick-btn")
            btn.clicked.connect(lambda _c, s=unit, t=txt: self._quick_add_alarm(s, t))
            quick_box.addWidget(btn)
        quick_box.addStretch()
        layout.addLayout(quick_box)

        # Direct Input Row
        input_row = QHBoxLayout()
        self.new_time_edit = QTimeEdit(self)
        self.new_time_edit.setDisplayFormat("HH:mm")
        now_dt = datetime.datetime.now() + datetime.timedelta(minutes=15)
        self.new_time_edit.setTime(QTime(now_dt.hour, now_dt.minute))
        self.new_time_edit.setFixedWidth(85)

        self.new_label_edit = QLineEdit(self)
        self.new_label_edit.setPlaceholderText("알람 내용 입력 (예: 팀 주간 회의, 눈 스트레칭, 약 챙겨먹기)")

        add_btn = QPushButton("✨ 알람 추가", self)
        add_btn.setProperty("class", "action-btn")
        add_btn.clicked.connect(self._add_custom_alarm)

        input_row.addWidget(QLabel("시각:"))
        input_row.addWidget(self.new_time_edit)
        input_row.addWidget(QLabel("내용:"))
        input_row.addWidget(self.new_label_edit)
        input_row.addWidget(add_btn)
        layout.addLayout(input_row)

        # 3. Alarms Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["⏰ 목표 시각", "📝 알람 내용", "⏳ 남은 시간", "🛠️ 관리"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # 4. Footer Actions
        footer_box = QHBoxLayout()
        clear_btn = QPushButton("🗑️ 전체 알람 삭제", self)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.2);
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
            }
        """)
        clear_btn.clicked.connect(self._clear_all)

        close_btn = QPushButton("닫기", self)
        close_btn.setStyleSheet("background: #334155; color: white; border-radius: 8px; padding: 6px 16px; font-weight: bold;")
        close_btn.clicked.connect(self.close)

        footer_box.addWidget(clear_btn)
        footer_box.addStretch()
        footer_box.addWidget(close_btn)
        layout.addLayout(footer_box)

        # Live Update Timer (1 sec tick for countdowns & live clock)
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self._refresh_countdown_and_clock)
        self.update_timer.start()

        self.alarm_manager.alarms_changed.connect(self.populate_table)
        self.populate_table()
        self._refresh_countdown_and_clock()

    def _refresh_countdown_and_clock(self) -> None:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.live_clock_lbl.setText(f"🕒 {now_str}")

        # Update remaining times in table
        for r in range(self.table.rowCount()):
            item_id = self.table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            for alm in self.alarm_manager.get_all_alarms():
                if alm.alarm_id == item_id:
                    rem_item = self.table.item(r, 2)
                    if rem_item:
                        rem_item.setText(alm.remaining_str)
                    break

    def populate_table(self) -> None:
        alarms = self.alarm_manager.get_all_alarms()
        self.table.setRowCount(len(alarms))

        for row, alm in enumerate(alarms):
            # Target Time
            time_item = QTableWidgetItem(alm.target_time_str)
            time_item.setData(Qt.ItemDataRole.UserRole, alm.alarm_id)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setForeground(QColor("#38bdf8"))
            self.table.setItem(row, 0, time_item)

            # Label
            lbl_text = alm.label
            if alm.is_snoozed:
                lbl_text = f"💤 {lbl_text}"
            label_item = QTableWidgetItem(lbl_text)
            self.table.setItem(row, 1, label_item)

            # Remaining Countdown
            rem_item = QTableWidgetItem(alm.remaining_str)
            rem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rem_item.setForeground(QColor("#f472b6"))
            self.table.setItem(row, 2, rem_item)

            # Action Buttons (Edit + Delete)
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            edit_btn = QPushButton("✏️ 수정")
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: #1e3a8a;
                    color: #93c5fd;
                    border: none;
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #2563eb;
                    color: white;
                }
            """)
            edit_btn.clicked.connect(lambda _c, a=alm: self._open_edit_dialog(a))

            del_btn = QPushButton("🗑️ 삭제")
            del_btn.setStyleSheet("""
                QPushButton {
                    background: #7f1d1d;
                    color: #fca5a5;
                    border: none;
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #dc2626;
                    color: white;
                }
            """)
            del_btn.clicked.connect(lambda _c, a_id=alm.alarm_id: self._delete_alarm(a_id))

            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 3, btn_widget)

    def _quick_add_alarm(self, seconds: int, text_label: str) -> None:
        desc = self.new_label_edit.text().strip() or f"{text_label} 타이머"
        self.alarm_manager.schedule_alarm(seconds, desc, f"quick_{seconds}")
        self.new_label_edit.clear()

    def _add_custom_alarm(self) -> None:
        t = self.new_time_edit.time()
        label = self.new_label_edit.text().strip() or "알람 시간이에요!"
        now = datetime.datetime.now()
        target_dt = now.replace(hour=t.hour(), minute=t.minute(), second=0, microsecond=0)
        if target_dt <= now:
            target_dt += datetime.timedelta(days=1)
        self.alarm_manager.schedule_absolute_alarm(target_dt, label, "manual_ui")
        self.new_label_edit.clear()

    def _open_edit_dialog(self, item: AlarmItem) -> None:
        dlg = EditAlarmDialog(item, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_label, new_ts = dlg.get_updated_data()
            self.alarm_manager.update_alarm(item.alarm_id, new_label, new_ts)

    def _delete_alarm(self, alarm_id: str) -> None:
        self.alarm_manager.cancel_alarm(alarm_id)

    def _clear_all(self) -> None:
        if self.alarm_manager.get_all_alarms():
            reply = QMessageBox.question(
                self,
                "전체 알람 삭제",
                "등록된 모든 알람을 삭제하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.alarm_manager.clear_all_alarms()

