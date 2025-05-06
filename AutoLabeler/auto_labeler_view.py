# auto_labeler_view.py 修改版
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_view.py
自动标注辅助工具 - 视图层

该模块负责标注辅助工具的界面展示
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QSlider, QComboBox, QSpinBox, QCheckBox, QSizePolicy, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QFont

# 导入其他模块
from AutoLabeler.auto_labeler_model import AutoLabelerModel, AutoLabelerMode, AutoLabelerState

# 导入样式接口
try:
    from config.style_interface import get_style, get_theme, StatusAnimator
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
            'INPUT_STYLE': "QSpinBox { border: 1px solid #ddd; border-radius: 3px; padding: 2px; }",
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
        self.resize(500, 350)

        # 创建日志记录器
        self.logger = logging.getLogger("AutoLabeler")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.propagate = False

        # 创建模型实例
        self.model = AutoLabelerModel()

        # 组件初始化
        self._init_ui()
        self._setup_connections()

        # 状态动画器
        self.status_animator = StatusAnimator(self.status_label)

        # 统计更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._refresh_stats)
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
        self.auto_next_check.toggled.connect(self.auto_next_changed_signal.emit)
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
        self.auto_next_changed_signal.connect(self.model.set_auto_next)
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

        event.accept()

    def initialize(self):
        """初始化控制器和全局事件监听"""
        if not hasattr(self, 'controller'):
            self._setup_controller()
        return self.controller


# auto_labeler_controller.py 修改版
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_controller.py
自动标注辅助工具 - 控制器层

该模块负责连接模型和视图，处理用户交互和事件
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QEvent, Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QKeyEvent, QMouseEvent

# 导入第三方键盘控制库
try:
    from pynput.keyboard import Key, Controller as KeyboardController
except ImportError:
    logging.warning("未找到pynput库，将使用模拟键盘事件代替")
    KeyboardController = None


class EventFilter(QObject):
    """全局事件过滤器，通过pynput监听全局鼠标和键盘事件"""
    mouse_press_signal = pyqtSignal(QMouseEvent)
    mouse_release_signal = pyqtSignal(QMouseEvent)
    key_press_signal = pyqtSignal(QKeyEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mouse_listener = None
        self._keyboard_listener = None
        self._init_global_listeners()

    def _init_global_listeners(self):
        """初始化全局监听器"""
        try:
            from pynput import mouse, keyboard
        except ImportError:
            logging.error("缺少pynput库，无法启用全局监听")
            return

        # 启动鼠标监听
        self._mouse_listener = mouse.Listener(on_click=self._handle_mouse_click)
        self._mouse_listener.start()

        # 启动键盘监听
        self._keyboard_listener = keyboard.Listener(on_press=self._handle_key_press)
        self._keyboard_listener.start()

    def _handle_mouse_click(self, x, y, button, pressed):
        """处理全局鼠标点击事件"""
        # 将pynput按钮转换为Qt按钮
        qt_button = self._map_pynput_button(button)
        if qt_button is None:
            return

        # 构建虚拟的QMouseEvent（坐标可能需要调整）
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress if pressed else QEvent.Type.MouseButtonRelease,
            QPointF(x, y),  # 屏幕坐标
            qt_button,
            qt_button,  # 假设没有其他组合按键
            Qt.KeyboardModifier.NoModifier
        )

        # 发射信号（使用队列连接确保线程安全）
        if pressed:
            self.mouse_press_signal.emit(event)
        else:
            self.mouse_release_signal.emit(event)

    def _handle_key_press(self, key):
        """处理全局键盘按键事件"""
        try:
            # 尝试获取字符（普通键）
            char = key.char
        except AttributeError:
            # 处理特殊键（如方向键）
            char = str(key).split('.')[-1].lower()

        # 构建虚拟的QKeyEvent
        if char:
            qt_key = self._map_pynput_key(char)
            if qt_key:
                event = QKeyEvent(
                    QEvent.Type.KeyPress,
                    qt_key,
                    Qt.KeyboardModifier.NoModifier,
                    char
                )
                self.key_press_signal.emit(event)

    def _map_pynput_button(self, button):
        """映射pynput按钮到Qt按钮"""
        from pynput.mouse import Button
        return {
            Button.left: Qt.MouseButton.LeftButton,
            Button.right: Qt.MouseButton.RightButton,
            Button.middle: Qt.MouseButton.MiddleButton
        }.get(button)

    def _map_pynput_key(self, key):
        """映射pynput按键到Qt按键"""
        key_map = {
            'w': Qt.Key.Key_W,
            'd': Qt.Key.Key_D,
            'space': Qt.Key.Key_Space,
            'enter': Qt.Key.Key_Return,
            # 添加其他需要监听的按键
        }
        return key_map.get(key.lower())

    def stop(self):
        """停止监听器"""
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()


class AutoLabelerController:
    """自动标注控制器类"""

    def __init__(self, application=None, parent_window=None, model=None, view=None):
        """
        初始化控制器

        Args:
            application: QApplication实例，用于全局事件过滤
            parent_window: 父窗口，用于设置事件过滤器
            model: 自动标注模型实例
            view: 自动标注视图实例
        """
        # 获取或配置日志记录器
        self.logger = logging.getLogger("AutoLabeler")

        # 连接模型和视图
        self.model = model
        self.view = view

        # 初始化全局事件过滤器
        self.event_filter = EventFilter()

        # 确保跨线程信号安全
        self.event_filter.mouse_press_signal.connect(
            self.model.handle_mouse_press,
            Qt.ConnectionType.QueuedConnection
        )
        self.event_filter.mouse_release_signal.connect(
            self.model.handle_mouse_release,
            Qt.ConnectionType.QueuedConnection
        )
        self.event_filter.key_press_signal.connect(
            self.model.handle_key_press,
            Qt.ConnectionType.QueuedConnection
        )

        # 初始化键盘控制器
        self.keyboard = KeyboardController() if KeyboardController else None
        if not self.keyboard:
            self.model.logger.warning("键盘模拟功能受限，请安装pynput库获得完整功能")
            self.view.update_status("键盘模拟功能受限，请安装pynput库", "warning")

        # 连接信号与槽
        self._setup_connections()

        self.logger.info("自动标注控制器初始化完成")

    def _setup_connections(self):
        """设置信号与槽的连接"""
        # 键盘命令连接
        self.model.send_key_signal.connect(self._send_key_event)

    def _send_key_event(self, key):
        """
        发送键盘事件

        Args:
            key: 按键字符，如'W'、'D'等
        """
        self.logger.debug(f"发送键盘事件: {key}")

        if self.keyboard:
            # 使用pynput发送真实键盘事件
            self.keyboard.press(key.lower())
            self.keyboard.release(key.lower())
        else:
            # 模拟QKeyEvent事件
            key_code = getattr(Qt.Key, f"Key_{key}")
            key_event = QKeyEvent(QEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.view, key_event)

            # 模拟按键释放
            release_event = QKeyEvent(QEvent.Type.KeyRelease, key_code, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.view, release_event)


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