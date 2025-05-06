#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_controller.py
自动标注辅助工具 - 控制器层

该模块负责连接模型和视图，处理用户交互和事件
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QObject, QEvent, Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from auto_labeler_model import AutoLabelerModel, AutoLabelerMode, AutoLabelerState
from auto_labeler_view import AutoLabelerView

# 导入样式接口
from config.style_interface import get_style

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

    def __init__(self, application=None, parent_window=None):
        """
        初始化控制器

        Args:
            application: QApplication实例，用于全局事件过滤
            parent_window: 父窗口，用于设置事件过滤器
        """
        # 获取或配置日志记录器
        self.logger = logging.getLogger("AutoLabeler")

        # 创建模型和视图
        self.model = AutoLabelerModel()
        self.view = AutoLabelerView(parent=parent_window)

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
        # 视图到模型的连接
        self.view.start_signal.connect(self.model.start_monitoring)
        self.view.pause_signal.connect(self.model.pause_monitoring)
        self.view.stop_signal.connect(self.model.stop_monitoring)
        self.view.mode_changed_signal.connect(self._on_mode_changed)
        self.view.auto_next_changed_signal.connect(self.model.set_auto_next)
        self.view.delay_draw_changed_signal.connect(self.model.set_delay_draw)
        self.view.delay_next_changed_signal.connect(self.model.set_delay_next)

        # 模型到视图的连接
        self.model.state_changed.connect(self.view.update_state)
        self.model.status_changed.connect(self.view.update_status)
        self.model.statistics_updated.connect(self.view.update_statistics)

        # 事件过滤器连接
        self.event_filter.mouse_press_signal.connect(self.model.handle_mouse_press)
        self.event_filter.mouse_release_signal.connect(self.model.handle_mouse_release)
        self.event_filter.key_press_signal.connect(self.model.handle_key_press)

        # 键盘命令连接
        self.model.send_key_signal.connect(self._send_key_event)

    def _on_mode_changed(self, index):
        """处理模式变化"""
        if index == 0:
            self.model.set_mode(AutoLabelerMode.DRAW_ONLY)
        elif index == 1:
            self.model.set_mode(AutoLabelerMode.DRAW_AND_NEXT)

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
            QApplication.sendEvent(self.target_window, key_event)

            # 模拟按键释放
            release_event = QKeyEvent(QEvent.Type.KeyRelease, key_code, Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(self.target_window, release_event)

    def show(self):
        """显示视图"""
        self.view.show()


class AutoLabelerWidget(QMainWindow):
    """独立运行时的主窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("自动标注辅助工具")
        self.resize(500, 400)

        # 创建控制器
        self.controller = AutoLabelerController(QApplication.instance(), self)

        # 设置主窗口部件
        self.setCentralWidget(self.controller.view)

        # 应用样式
        self.setStyleSheet(get_style('APP_STYLE'))

    def closeEvent(self, event):
        """关闭窗口事件重写"""
        self.controller.event_filter.stop()
        super().closeEvent(event)


# 独立运行时的入口
def main():
    """主函数"""
    # 配置日志 - 只在根模块中配置一次
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格以获得更好的跨平台体验

    # 创建并显示主窗口
    window = AutoLabelerWidget()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()