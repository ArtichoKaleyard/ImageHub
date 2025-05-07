#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_controller.py
自动标注辅助工具 - 控制器层

该模块负责连接模型和视图，处理用户交互和事件
"""

import sys
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
        self._is_running = False
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

        self._is_running = True

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
        try:
            from pynput.mouse import Button
            return {
                Button.left: Qt.MouseButton.LeftButton,
                Button.right: Qt.MouseButton.RightButton,
                Button.middle: Qt.MouseButton.MiddleButton
            }.get(button)
        except ImportError:
            return None

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
        if self._is_running:
            if self._mouse_listener:
                self._mouse_listener.stop()
            if self._keyboard_listener:
                self._keyboard_listener.stop()
            self._is_running = False

    def is_running(self):
        """检查监听器是否正在运行"""
        return self._is_running


class AutoLabelerController:
    """自动标注控制器类"""

    def __init__(self, model=None, view=None, application=None, parent_window=None):
        """
        初始化控制器
        """
        # 使用 Logger 类
        from Logger.logger import Logger
        self.logger = Logger(log_to_console=True, log_to_gui=True)

        # 连接模型和视图
        self.model = model
        self.view = view
        self.app = application or QApplication.instance()
        self.parent_window = parent_window

        # 快捷键设置
        self.draw_shortcut = "W"
        self.next_shortcut = "D"

        # 标记控制器是否已初始化完成
        self._initialized = False

        # 初始化全局事件过滤器
        self.event_filter = None
        self._init_event_filter()

        # 初始化键盘控制器
        self.keyboard = KeyboardController() if KeyboardController else None
        if not self.keyboard:
            self.logger.warning("键盘模拟功能受限，请安装pynput库获得完整功能")
            if self.view:
                self.view.update_status("键盘模拟功能受限，请安装pynput库", "warning")

        # 连接信号与槽
        self._setup_connections()

        self._initialized = True
        self.logger.info("自动标注辅助工具控制器层初始化完成")

    def _init_event_filter(self):
        """初始化全局事件过滤器"""
        self.event_filter = EventFilter()

        # 确保跨线程信号安全
        if self.model:
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

    def _setup_connections(self):
        """设置信号与槽的连接"""
        if self.model:
            # 键盘命令连接
            self.model.send_key_signal.connect(self._send_key_event)

            # 连接点击检测延迟设置
            if hasattr(self.view, 'click_delay_spin'):
                self.view.click_delay_spin.valueChanged.connect(
                    lambda ms: self.model.set_delay_click_detection(ms)
                )

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
            try:
                key_code = getattr(Qt.Key, f"Key_{key}")
                key_event = QKeyEvent(QEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier)
                QApplication.sendEvent(self.view, key_event)

                # 模拟按键释放
                release_event = QKeyEvent(QEvent.Type.KeyRelease, key_code, Qt.KeyboardModifier.NoModifier)
                QApplication.sendEvent(self.view, release_event)
            except (AttributeError, TypeError) as e:
                self.logger.error(f"发送按键事件失败: {e}")

    def is_initialized(self):
        """检查控制器是否已初始化完成"""
        return self._initialized

    def cleanup(self):
        """清理资源"""
        if self.event_filter:
            self.event_filter.stop()

    def set_shortcuts(self, draw_shortcut, next_shortcut):
        """设置快捷键"""
        self.draw_shortcut = draw_shortcut.upper()
        self.next_shortcut = next_shortcut.upper()
        self.logger.info(f"设置快捷键 - 绘制: {self.draw_shortcut}, 下一张: {self.next_shortcut}")


class AutoLabelerWidget(QObject):
    """自动标注工具组件类，用于集成到其他界面"""

    def __init__(self, view=None, parent=None):
        super().__init__(parent)
        from AutoLabeler.auto_labeler_model import AutoLabelerModel
        from AutoLabeler.auto_labeler_view import AutoLabelerView

        # 创建或使用传入的视图
        self.view = view or AutoLabelerView(parent)

        # 确保模型存在
        self.model = self.view.model or AutoLabelerModel()
        if not self.view.model:
            self.view.model = self.model

        # 创建控制器
        self.controller = AutoLabelerController(
            model=self.model,
            view=self.view
        )

        # 确保视图知道控制器
        self.view.controller = self.controller

    def get_widget(self):
        """获取可以添加到布局的小部件"""
        return self.view

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'controller') and self.controller:
            self.controller.cleanup()


# 独立运行时的入口函数
def main():
    """主函数"""
    # 创建应用
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格以获得更好的跨平台体验

    # 创建组件
    from AutoLabeler.auto_labeler_view import AutoLabelerView
    view = AutoLabelerView()
    auto_labeler = AutoLabelerWidget(view)

    # 显示视图
    view.show()

    # 清理并退出
    result = app.exec()
    auto_labeler.cleanup()
    sys.exit(result)


if __name__ == "__main__":
    main()