#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_view.py
自动标注辅助工具 - 视图层

该模块负责标注辅助工具的界面展示
"""

import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QSlider, QComboBox, QSpinBox, QCheckBox, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont

# 导入样式接口
from config.style_interface import get_style, get_theme, StatusAnimator


class AutoLabelerView(QWidget):
    """自动标注工具视图类"""
    
    # 信号定义
    start_signal = pyqtSignal()
    pause_signal = pyqtSignal()
    stop_signal = pyqtSignal()
    mode_changed_signal = pyqtSignal(int)
    auto_next_changed_signal = pyqtSignal(bool)
    delay_draw_changed_signal = pyqtSignal(int)
    delay_next_changed_signal = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自动标注辅助工具")
        self.resize(500, 350)
        
        # 组件初始化
        self._init_ui()
        self._setup_connections()
        
        # 状态动画器
        self.status_animator = StatusAnimator(self.status_label)
        
        # 统计更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_duration_label)
        self.stats_timer.start(1000)  # 每秒更新一次
    
    def _init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== 控制面板 =====
        control_group = QGroupBox("控制面板")
        control_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        control_layout = QVBoxLayout(control_group)
        
        # 状态指示器
        status_frame = QFrame()
        status_frame.setStyleSheet(get_style('STATUS_FRAME_STYLE'))
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始监控")
        self.start_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        self.start_button.setMinimumWidth(100)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.pause_button.setMinimumWidth(80)
        self.pause_button.setEnabled(False)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.stop_button.setMinimumWidth(80)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        
        # 模式选择
        mode_layout = QHBoxLayout()
        
        mode_label = QLabel("操作模式:")
        mode_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(get_style('COMBO_BOX_STYLE'))
        self.mode_combo.addItem("仅自动绘制 (W)")
        self.mode_combo.addItem("绘制并下一张 (W+D)")
        
        self.auto_next_check = QCheckBox("单独绘制后自动下一张")
        self.auto_next_check.setStyleSheet(get_style('CHECK_BOX_STYLE'))
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addWidget(self.auto_next_check)
        mode_layout.addStretch(1)
        
        # 延迟设置
        delay_layout = QHBoxLayout()
        
        draw_delay_label = QLabel("绘制延迟:")
        draw_delay_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.draw_delay_spin = QSpinBox()
        self.draw_delay_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.draw_delay_spin.setRange(100, 2000)
        self.draw_delay_spin.setSingleStep(50)
        self.draw_delay_spin.setValue(300)
        self.draw_delay_spin.setSuffix(" ms")
        
        next_delay_label = QLabel("下一张延迟:")
        next_delay_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.next_delay_spin = QSpinBox()
        self.next_delay_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.next_delay_spin.setRange(100, 2000)
        self.next_delay_spin.setSingleStep(50)
        self.next_delay_spin.setValue(500)
        self.next_delay_spin.setSuffix(" ms")
        
        delay_layout.addWidget(draw_delay_label)
        delay_layout.addWidget(self.draw_delay_spin)
        delay_layout.addWidget(next_delay_label)
        delay_layout.addWidget(self.next_delay_spin)
        delay_layout.addStretch(1)
        
        # 添加到控制面板
        control_layout.addWidget(status_frame)
        control_layout.addLayout(button_layout)
        control_layout.addLayout(mode_layout)
        control_layout.addLayout(delay_layout)
        
        # ===== 统计信息 =====
        stats_group = QGroupBox("统计信息")
        stats_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        stats_layout = QVBoxLayout(stats_group)
        
        # 当前会话统计
        session_layout = QHBoxLayout()
        
        self.box_count_label = QLabel("本次已绘制: 0 个框")
        self.box_count_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.image_count_label = QLabel("本次已处理: 0 张图片")
        self.image_count_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.duration_label = QLabel("用时: 00:00:00")
        self.duration_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        session_layout.addWidget(self.box_count_label)
        session_layout.addWidget(self.image_count_label)
        session_layout.addWidget(self.duration_label)
        session_layout.addStretch(1)
        
        # 效率统计
        efficiency_layout = QHBoxLayout()
        
        self.box_rate_label = QLabel("框速率: 0.0 框/分钟")
        self.box_rate_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.image_rate_label = QLabel("图片速率: 0.0 图/分钟")
        self.image_rate_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        efficiency_layout.addWidget(self.box_rate_label)
        efficiency_layout.addWidget(self.image_rate_label)
        efficiency_layout.addStretch(1)
        
        # 总计统计
        total_layout = QHBoxLayout()
        
        self.total_box_label = QLabel("总计绘制: 0 个框")
        self.total_box_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        self.total_image_label = QLabel("总计处理: 0 张图片")
        self.total_image_label.setStyleSheet(get_style('LABEL_STYLE'))
        
        total_layout.addWidget(self.total_box_label)
        total_layout.addWidget(self.total_image_label)
        total_layout.addStretch(1)
        
        # 添加到统计面板
        stats_layout.addLayout(session_layout)
        stats_layout.addLayout(efficiency_layout)
        stats_layout.addLayout(total_layout)
        
        # 添加到主布局
        main_layout.addWidget(control_group, 3)
        main_layout.addWidget(stats_group, 2)
        
        self.setLayout(main_layout)
    
    def _setup_connections(self):
        """设置信号与槽的连接"""
        self.start_button.clicked.connect(self._on_start_clicked)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.mode_combo.currentIndexChanged.connect(self.mode_changed_signal.emit)
        self.auto_next_check.toggled.connect(self.auto_next_changed_signal.emit)
        self.draw_delay_spin.valueChanged.connect(self.delay_draw_changed_signal.emit)
        self.next_delay_spin.valueChanged.connect(self.delay_next_changed_signal.emit)
    
    def _on_start_clicked(self):
        """开始按钮点击处理"""
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.start_signal.emit()
    
    def _on_pause_clicked(self):
        """暂停按钮点击处理"""
        if self.pause_button.text() == "暂停":
            self.pause_button.setText("继续")
            self.pause_signal.emit()
        else:
            self.pause_button.setText("暂停")
            self.start_signal.emit()
    
    def _on_stop_clicked(self):
        """停止按钮点击处理"""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.stop_button.setEnabled(False)
        self.stop_signal.emit()
    
    def update_state(self, state):
        """更新界面状态"""
        from auto_labeler_model import AutoLabelerState
        
        if state == AutoLabelerState.IDLE:
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.pause_button.setText("暂停")
            self.stop_button.setEnabled(False)
        elif state == AutoLabelerState.MONITORING:
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.pause_button.setText("暂停")
            self.stop_button.setEnabled(True)
        elif state == AutoLabelerState.DRAWING:
            # 绘制状态不改变按钮状态
            pass
        elif state == AutoLabelerState.PAUSED:
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            self.pause_button.setText("继续")
            self.stop_button.setEnabled(True)
    
    def update_status(self, message, status_type="normal"):
        """更新状态信息"""
        if not message:
            self.status_animator.stop()
            self.status_label.setText("就绪")
            return
            
        # 根据状态类型显示不同颜色
        if status_type == "success":
            color = get_theme("success")
        elif status_type == "warning":
            color = get_theme("warning")
        elif status_type == "error":
            color = get_theme("error")
        elif status_type == "info":
            color = get_theme("info")
        else:
            color = get_theme("text")
            
        # 启动状态动画
        self.status_animator.start(message, color)
    
    def update_statistics(self, stats):
        """更新统计信息"""
        # 更新计数
        self.box_count_label.setText(f"本次已绘制: {stats['session_boxes']} 个框")
        self.image_count_label.setText(f"本次已处理: {stats['session_images']} 张图片")
        
        # 更新速率
        self.box_rate_label.setText(f"框速率: {stats['boxes_per_minute']:.1f} 框/分钟")
        self.image_rate_label.setText(f"图片速率: {stats['images_per_minute']:.1f} 图/分钟")
        
        # 更新总计
        self.total_box_label.setText(f"总计绘制: {stats['total_boxes']} 个框")
        self.total_image_label.setText(f"总计处理: {stats['total_images']} 张图片")
        
        # 更新时长
        self._update_duration_label(stats['duration'])
    
    def _update_duration_label(self, duration=None):
        """更新时长标签"""
        if duration is None:
            # 如果没有提供时长，则使用上次更新的时长加上1秒
            text = self.duration_label.text()
            if text.startswith("用时: "):
                time_str = text[4:]
                h, m, s = map(int, time_str.split(':'))
                duration = h * 3600 + m * 60 + s + 1
            else:
                return
        
        # 格式化时长
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        self.duration_label.setText(f"用时: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        self.stop_signal.emit()
        self.stats_timer.stop()
        event.accept()


# 独立运行时的测试代码
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyleSheet(get_style('APP_STYLE'))
    
    window = AutoLabelerView()
    window.show()
    
    # 模拟统计数据更新
    def update_test_stats():
        window.update_statistics({
            'total_boxes': 100,
            'total_images': 50,
            'session_boxes': 20,
            'session_images': 10,
            'duration': 300,
            'boxes_per_minute': 4.0,
            'images_per_minute': 2.0
        })
        window.update_status("测试状态消息", "success")
    
    QTimer.singleShot(1000, update_test_stats)
    
    sys.exit(app.exec())