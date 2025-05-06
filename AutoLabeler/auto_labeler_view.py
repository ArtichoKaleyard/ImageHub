# auto_labeler_view.py 修改版
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_view.py
自动标注辅助工具 - 视图层

该模块负责标注辅助工具的界面展示
"""

import sys
import time
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame, QLineEdit, QTextEdit, QApplication
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt

# 导入其他模块
from AutoLabeler.auto_labeler_model import AutoLabelerModel, AutoLabelerMode, AutoLabelerState

# 导入新的日志记录器
from Logger.logger import Logger

# 导入样式接口
try:
    from style.style_interface import get_style, get_theme, StatusAnimator
    from style.log_style import LOG_COLORS, LOG_TAG_STYLE
except ImportError:
    # 默认样式函数，当无法导入时使用
    def get_style(style_name):
        styles = {
            'APP_STYLE': "QWidget { background-color: #f5f5f5; }",
            'GROUP_BOX_STYLE': "QGroupBox { font-weight: bold; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }",
            'STATUS_FRAME_STYLE': "QFrame { border: 1px solid #ddd; border-radius: 3px; background-color: #fff; }",
            'LABEL_STYLE': "QLabel { color: #333; }",
            'PRIMARY_BUTTON_STYLE': "QPushButton { background-color: #4CAF50; color: white; border-radius: 4px; padding: 5px; } QPushButton:hover { background-color: #45a049; }",
            'SECONDARY_BUTTON_STYLE': "QPushButton { background-color: #f1f1f1; border: 1px solid #ddd; border-radius: 4px; padding: 5px; }",
            'COMBO_BOX_STYLE': "QComboBox { border: 1px solid #ddd; border-radius: 3px; padding: 2px; }",
            'CHECK_BOX_STYLE': "QCheckBox { color: #333; }",
            'INPUT_STYLE': "QSpinBox, QLineEdit { border: 1px solid #ddd; border-radius: 3px; padding: 2px; }",
            'LOG_AREA_STYLE': "QTextEdit { border: 1px solid #ddd; border-radius: 3px; }",
        }
        return styles.get(style_name, "")


    def get_theme(color_name):
        colors = {
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'info': '#2196F3',
            'text': '#333333'
        }
        return colors.get(color_name, '#333333')


    # 简单的状态动画器
    class StatusAnimator:
        def __init__(self, label):
            self.label = label
            self.timer = QTimer()
            self.timer.timeout.connect(self._reset_style)

        def start(self, text, color):
            self.label.setText(text)
            self.label.setStyleSheet(f"QLabel {{ color: {color}; font-weight: bold; }}")
            self.timer.start(3000)  # 3秒后重置

        def stop(self):
            self.timer.stop()
            self._reset_style()

        def _reset_style(self):
            self.timer.stop()
            self.label.setStyleSheet("QLabel { color: #333; }")


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
        self.resize(650, 500)  # 调整窗口大小以适应新布局

        # 创建新的日志记录器
        self.logger = Logger(log_to_console=True, log_to_gui=True)

        # 兼容旧代码的 logger 接口
        self._setup_legacy_logger()

        # 创建模型实例
        self.model = AutoLabelerModel()

        # 组件初始化
        self._init_ui()
        self._setup_connections()

        # 状态动画器 - 使用白底黑字样式确保状态文本可见
        self.status_animator = StatusAnimator(self.status_label)

        # 统计更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._refresh_stats)
        self.stats_timer.start(1000)  # 每秒更新一次

        # 日志记录启动信息
        self.logger.info("自动标注辅助工具已启动")

    def _setup_legacy_logger(self):
        """设置兼容旧代码的logger接口"""
        # 创建标准Python logger，并将其输出重定向到我们的Logger
        legacy_logger = logging.getLogger("AutoLabeler")
        legacy_logger.setLevel(logging.INFO)

        # 移除所有旧的处理器
        for handler in legacy_logger.handlers[:]:
            legacy_logger.removeHandler(handler)

        # 添加自定义处理器，将日志转发到我们的Logger
        class LoggerAdapter(logging.Handler):
            def __init__(self, custom_logger):
                super().__init__()
                self.custom_logger = custom_logger

            def emit(self, record):
                log_level = record.levelname.lower()
                if log_level == 'critical':
                    log_level = 'error'
                elif log_level == 'warning':
                    log_level = 'warning'
                elif log_level == 'info':
                    log_level = 'info'
                elif log_level == 'debug':
                    log_level = 'debug'
                else:
                    log_level = 'info'

                # 调用对应的日志方法
                log_method = getattr(self.custom_logger, log_level, self.custom_logger.info)
                log_method(self.format(record))

        # 添加适配器
        handler = LoggerAdapter(self.logger)
        handler.setFormatter(logging.Formatter('%(message)s'))  # 简化格式，因为我们的Logger会添加时间戳
        legacy_logger.addHandler(handler)
        legacy_logger.propagate = False

    def _init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ===== 操作控制面板 =====
        operation_control_group = QGroupBox("操作控制")
        operation_control_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        operation_layout = QHBoxLayout(operation_control_group)

        # 状态指示器 - 左侧占一半
        status_frame = QFrame()
        status_frame.setStyleSheet(get_style('STATUS_FRAME_STYLE'))
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 5, 5, 5)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)

        # 按钮面板 - 右侧占一半
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("开始监控")
        self.start_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))

        self.pause_button = QPushButton("暂停")
        self.pause_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.pause_button.setEnabled(False)

        self.stop_button = QPushButton("停止")
        self.stop_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.stop_button.setEnabled(False)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)

        operation_layout.addWidget(status_frame, 1)  # 状态栏占一半
        operation_layout.addLayout(button_layout, 1)  # 按钮占一半

        # ===== 中间部分：控制面板和统计信息水平排布 =====
        middle_layout = QHBoxLayout()

        # ===== 控制面板 - 左侧 =====
        control_group = QGroupBox("控制面板")
        control_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        control_layout = QVBoxLayout(control_group)

        # 模式选择 - 独占一行
        mode_layout = QHBoxLayout()
        mode_label = QLabel("操作模式:")
        mode_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(get_style('COMBO_BOX_STYLE'))
        self.mode_combo.addItem("仅自动绘制 (W)")
        self.mode_combo.addItem("绘制并下一张 (W+D)")

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)

        # 延迟设置 - 两两一行
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

        # 快捷键设置 - 两两一行
        shortcut_layout = QHBoxLayout()

        draw_shortcut_label = QLabel("绘制快捷键:")
        draw_shortcut_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.draw_shortcut_edit = QLineEdit("W")
        self.draw_shortcut_edit.setStyleSheet(get_style('INPUT_STYLE'))
        self.draw_shortcut_edit.setMaxLength(1)

        next_shortcut_label = QLabel("下一张快捷键:")
        next_shortcut_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.next_shortcut_edit = QLineEdit("D")
        self.next_shortcut_edit.setStyleSheet(get_style('INPUT_STYLE'))
        self.next_shortcut_edit.setMaxLength(1)

        shortcut_layout.addWidget(draw_shortcut_label)
        shortcut_layout.addWidget(self.draw_shortcut_edit)
        shortcut_layout.addWidget(next_shortcut_label)
        shortcut_layout.addWidget(self.next_shortcut_edit)

        # 添加到控制面板
        control_layout.addLayout(mode_layout)
        control_layout.addLayout(delay_layout)
        control_layout.addLayout(shortcut_layout)
        control_layout.addStretch(1)  # 填充剩余空间

        # ===== 统计信息 - 右侧 =====
        stats_group = QGroupBox("统计信息")
        stats_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        stats_layout = QVBoxLayout(stats_group)

        # 当前会话统计
        session_layout = QHBoxLayout()

        self.box_count_label = QLabel("本次已绘制: 0 个框")
        self.box_count_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.image_count_label = QLabel("本次已处理: 0 张图片")
        self.image_count_label.setStyleSheet(get_style('LABEL_STYLE'))

        session_layout.addWidget(self.box_count_label)
        session_layout.addWidget(self.image_count_label)

        # 时长单独一行
        duration_layout = QHBoxLayout()

        self.duration_label = QLabel("用时: 00:00:00")
        self.duration_label.setStyleSheet(get_style('LABEL_STYLE'))

        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch(1)

        # 效率统计
        efficiency_layout = QHBoxLayout()

        self.box_rate_label = QLabel("框速率: 0.0 框/分钟")
        self.box_rate_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.image_rate_label = QLabel("图片速率: 0.0 图/分钟")
        self.image_rate_label.setStyleSheet(get_style('LABEL_STYLE'))

        efficiency_layout.addWidget(self.box_rate_label)
        efficiency_layout.addWidget(self.image_rate_label)

        # 总计统计
        total_layout = QHBoxLayout()

        self.total_box_label = QLabel("总计绘制: 0 个框")
        self.total_box_label.setStyleSheet(get_style('LABEL_STYLE'))

        self.total_image_label = QLabel("总计处理: 0 张图片")
        self.total_image_label.setStyleSheet(get_style('LABEL_STYLE'))

        total_layout.addWidget(self.total_box_label)
        total_layout.addWidget(self.total_image_label)

        # 添加到统计面板
        stats_layout.addLayout(session_layout)
        stats_layout.addLayout(duration_layout)
        stats_layout.addLayout(efficiency_layout)
        stats_layout.addLayout(total_layout)
        stats_layout.addStretch(1)  # 填充剩余空间

        # 将控制面板和统计信息添加到中间布局
        middle_layout.addWidget(control_group, 1)  # 各占一半
        middle_layout.addWidget(stats_group, 1)

        # 日志展示区域 - 底部，至少占据三分之一的空间
        log_group = QGroupBox("日志")
        log_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(get_style('LOG_AREA_STYLE'))
        log_layout.addWidget(self.log_text)

        # 设置Logger的GUI日志控件
        self.logger.set_gui_log_widget(self.log_text)

        # 添加到主布局
        main_layout.addWidget(operation_control_group)
        main_layout.addLayout(middle_layout, 2)  # 中间部分占2份
        main_layout.addWidget(log_group, 3)  # 日志区域占3份，确保至少三分之一

        self.setLayout(main_layout)

    def _setup_controller(self):
        """设置控制器"""
        from AutoLabeler.auto_labeler_controller import AutoLabelerController

        # 创建控制器
        self.controller = AutoLabelerController(
            application=QApplication.instance(),
            parent_window=self.parent(),
            model=self.model,
            view=self
        )

        # 将自身添加为控制器的视图
        self.controller.view = self

        self.logger.info("控制器初始化完成")

        return self.controller

    def _setup_connections(self):
        """设置信号与槽的连接"""
        self.start_button.clicked.connect(self._on_start_clicked)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.mode_combo.currentIndexChanged.connect(self.mode_changed_signal.emit)
        self.draw_delay_spin.valueChanged.connect(self.delay_draw_changed_signal.emit)
        self.next_delay_spin.valueChanged.connect(self.delay_next_changed_signal.emit)

        # 连接模型信号
        self.model.state_changed.connect(self.update_state)
        self.model.status_changed.connect(self.update_status)
        self.model.statistics_updated.connect(self.update_statistics)

        # 连接自身信号到模型
        self.start_signal.connect(self.model.start_monitoring)
        self.pause_signal.connect(self.model.pause_monitoring)
        self.stop_signal.connect(self.model.stop_monitoring)
        self.mode_changed_signal.connect(self._on_mode_changed)
        self.delay_draw_changed_signal.connect(self.model.set_delay_draw)
        self.delay_next_changed_signal.connect(self.model.set_delay_next)

    def _on_mode_changed(self, index):
        """处理模式变化"""
        if index == 0:
            self.model.set_mode(AutoLabelerMode.DRAW_ONLY)
        elif index == 1:
            self.model.set_mode(AutoLabelerMode.DRAW_AND_NEXT)

    def _on_start_clicked(self):
        """开始按钮点击处理"""
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        # 确保控制器已初始化
        if not hasattr(self, 'controller'):
            self._setup_controller()

        self.start_signal.emit()
        self.logger.success("开始监控")

    def _on_pause_clicked(self):
        """暂停按钮点击处理"""
        if self.pause_button.text() == "暂停":
            self.pause_button.setText("继续")
            self.pause_signal.emit()
            self.logger.info("监控已暂停")
        else:
            self.pause_button.setText("暂停")
            self.start_signal.emit()
            self.logger.info("监控已继续")

    def _on_stop_clicked(self):
        """停止按钮点击处理"""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.stop_button.setEnabled(False)
        self.stop_signal.emit()
        self.logger.info("监控已停止")

    def update_state(self, state):
        """更新界面状态"""
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

        # 根据状态类型记录对应级别的日志
        if status_type == "success":
            self.logger.success(message)
        elif status_type == "warning":
            self.logger.warning(message)
        elif status_type == "error":
            self.logger.error(message)
        elif status_type == "info" or status_type == "normal":
            self.logger.info(message)
        else:
            self.logger.info(message)

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
            return

        # 格式化时长
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        self.duration_label.setText(f"用时: {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _refresh_stats(self):
        """从模型刷新统计数据"""
        if hasattr(self, 'model'):
            stats = self.model.statistics
            if stats['start_time'] > 0:  # 只有当计时器正在运行时才更新
                self.update_statistics(stats)

    def closeEvent(self, event):
        """关闭窗口事件"""
        self.stop_signal.emit()
        self.stats_timer.stop()

        # 停止事件过滤器
        if hasattr(self, 'controller'):
            if hasattr(self.controller, 'event_filter'):
                self.controller.event_filter.stop()

        self.logger.info("应用程序已关闭")
        event.accept()

    def initialize(self):
        """初始化控制器和全局事件监听"""
        if not hasattr(self, 'controller'):
            self._setup_controller()
        return self.controller


# 主窗口和入口函数
def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 创建视图并初始化
    view = AutoLabelerView()
    controller = view.initialize()  # 初始化控制器
    view.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()