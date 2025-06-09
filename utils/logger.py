"""
日志记录器模块，提供统一的日志记录功能。
支持GUI和控制台日志输出，基于统一样式接口实现样式。
支持PyQt6 MVC架构，解决跨线程UI更新问题。

使用方法:
    from utils.logger import Logger, LogManager

    # 创建日志记录器
    logger = Logger(log_to_console=True, level="info")
    # 或者使用日志管理器获取命名日志记录器
    logger = LogManager.get_logger("app_name")

    # 设置日志级别
    logger.set_level("debug")  # 可选: debug, info, success, warning, error, critical

    # 添加GUI日志区域 (QTextEdit)
    logger.set_gui_log_widget(log_text_edit)

    # 记录不同级别的日志
    logger.info("应用程序已启动")
    logger.success("操作完成")
    logger.warning("文件已存在，将被覆盖")
    logger.error("无法连接到服务器")
    logger.critical("系统崩溃")
    logger.debug("变量x的值为: 42")
"""

import datetime
import html
import threading
from typing import Dict, List, Optional, Callable, Any, Union
from style.style_interface import format_console_log, format_log_html

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt, Q_ARG
except ImportError:
    # 兼容性导入，如果没有PyQt6，则尝试导入PyQt5
    try:
        from PyQt5.QtCore import QObject, pyqtSignal, QMetaObject, Qt, Q_ARG
    except ImportError:
        # 如果都没有，创建虚拟类以保持代码结构
        class QObject:
            pass

        class pyqtSignal:
            def __init__(self, *args):
                pass

            def connect(self, *args):
                pass

            def emit(self, *args):
                pass

        class QMetaObject:
            @staticmethod
            def invokeMethod(*args, **kwargs):
                pass

        class Qt:
            AutoConnection = 0
            QueuedConnection = 1

        def Q_ARG(type_name, value):
            return value


class LogSignaler(QObject):
    """日志信号发射器，用于跨线程安全地更新GUI"""
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()


class Logger:
    """日志记录器，支持控制台和GUI日志输出"""

    # 日志级别对应数值，用于比较
    LEVELS = {
        "debug": 10,
        "info": 20,
        "success": 25,
        "warning": 30,
        "error": 40,
        "critical": 50  # 新增critical级别
    }

    def __init__(self, log_to_console: bool = True, log_to_gui: bool = True, level: str = "info", name: str = None):
        """
        初始化日志记录器

        Args:
            log_to_console: 是否输出到控制台
            log_to_gui: 是否输出到GUI
            level: 日志级别，可选 debug, info, success, warning, error, critical
            name: 日志记录器名称，用于识别不同实例
        """
        self._log_to_console = log_to_console
        self._log_to_gui = log_to_gui
        self._gui_callbacks = []  # 直接GUI回调列表
        self._qt_callbacks = []   # 基于Qt信号的GUI回调
        self._signaler = LogSignaler()  # 信号发射器
        self._main_thread_id = threading.get_ident()  # 记录创建日志记录器的线程ID
        self._name = name or f"logger_{id(self)}"

        # 临时设置状态
        self._temp_log_to_console = None
        self._temp_log_to_gui = None
        self._level = self.LEVELS.get(level.lower(), self.LEVELS["info"])

    def set_level(self, level: str):
        """设置日志级别"""
        level_value = self.LEVELS.get(level.lower())
        if level_value is None:
            raise ValueError(f"不支持的日志级别: {level}. 可选值: {list(self.LEVELS.keys())}")
        self._level = level_value
        return self

    def get_level(self) -> str:
        """获取当前日志级别"""
        for name, value in self.LEVELS.items():
            if value == self._level:
                return name
        return "info"

    def set_gui_log_widget(self, text_edit, thread_safe: bool = True):
        """
        设置GUI日志控件

        Args:
            text_edit: QTextEdit或兼容对象，必须有append方法
            thread_safe: 是否使用线程安全模式（推荐开启）
        """
        if not hasattr(text_edit, 'append'):
            raise ValueError("GUI日志控件必须有append方法")

        if thread_safe:
            # 使用Qt信号槽机制实现线程安全的日志更新
            if text_edit not in self._qt_callbacks:
                callback = lambda html: self._safe_append_to_widget(text_edit, html)
                self._qt_callbacks.append((text_edit, callback))
                self._signaler.log_signal.connect(callback)
        else:
            # 使用传统方式（不安全的跨线程调用）
            if text_edit not in self._gui_callbacks:
                self._gui_callbacks.append(text_edit.append)

        return self

    def _safe_append_to_widget(self, widget, html_text):
        """使用Qt的invokeMethod实现线程安全的日志更新"""
        try:
            # 如果在创建日志记录器的线程中，直接调用
            if threading.get_ident() == self._main_thread_id:
                widget.append(html_text)
            else:
                # 如果在其他线程中，使用Qt的跨线程机制
                QMetaObject.invokeMethod(
                    widget,
                    "append",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, html_text)
                )
        except Exception as e:
            print(f"GUI日志更新失败: {e}")

    def remove_gui_log_widget(self, text_edit):
        """
        移除GUI日志控件

        Args:
            text_edit: 要移除的QTextEdit控件
        """
        # 移除直接回调
        if text_edit in self._gui_callbacks:
            self._gui_callbacks.remove(text_edit.append)

        # 移除Qt信号回调
        for widget, callback in list(self._qt_callbacks):
            if widget == text_edit:
                self._signaler.log_signal.disconnect(callback)
                self._qt_callbacks.remove((widget, callback))

        return self

    def console_only(self):
        """临时设置仅输出到控制台"""
        self._temp_log_to_console = True
        self._temp_log_to_gui = False
        return self

    def gui_only(self):
        """临时设置仅输出到GUI"""
        self._temp_log_to_console = False
        self._temp_log_to_gui = True
        return self

    def _log(self, message: str, level: str = "info"):
        """
        记录日志内部方法

        Args:
            message: 日志消息
            level: 日志级别
        """
        level = level.lower()
        level_value = self.LEVELS.get(level, self.LEVELS["info"])

        # 如果当前日志级别高于设定级别，则不输出
        if level_value < self._level:
            return

        # 确定当前的输出目标
        to_console = self._temp_log_to_console if self._temp_log_to_console is not None else self._log_to_console
        to_gui = self._temp_log_to_gui if self._temp_log_to_gui is not None else self._log_to_gui

        # 重置临时设置
        self._temp_log_to_console = None
        self._temp_log_to_gui = None

        # 添加模块名前缀
        name_prefix = f"[{self._name}] " if self._name else ""
        full_message = f"{name_prefix}{message}"

        # 生成时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 输出到控制台
        if to_console:
            console_log = format_console_log(timestamp, full_message, level)
            print(console_log)

        # 输出到GUI
        if to_gui:
            # 在构建 html_log 前转义特殊字符
            safe_message = html.escape(full_message)
            html_log = format_log_html(timestamp, safe_message, level)

            # 使用信号机制更新Qt界面
            self._signaler.log_signal.emit(html_log)

            # 兼容老版本的直接回调方式
            for callback in self._gui_callbacks:
                try:
                    callback(html_log)
                except Exception as e:
                    print(f"GUI日志输出失败: {e}")

    def info(self, message: str):
        """记录信息日志"""
        self._log(message, "info")
        return self

    def success(self, message: str):
        """记录成功日志"""
        self._log(message, "success")
        return self

    def warning(self, message: str):
        """记录警告日志"""
        self._log(message, "warning")
        return self

    def error(self, message: str):
        """记录错误日志"""
        self._log(message, "error")
        return self

    def critical(self, message: str):
        """记录致命错误日志"""
        self._log(message, "critical")
        return self

    def debug(self, message: str):
        """记录调试日志"""
        self._log(message, "debug")
        return self

    def log(self, message: str, level: str = "info"):
        """
        通用日志记录方法

        Args:
            message: 日志消息
            level: 日志级别
        """
        self._log(message, level)
        return self


class LogManager:
    """
    日志管理器，用于管理多个命名日志记录器实例
    使用内部单例模式，但创建的Logger实例彼此独立
    """
    _instance = None
    _loggers: Dict[str, Logger] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._loggers = {}
        return cls._instance

    @classmethod
    def get_logger(cls, name: str = None, **kwargs) -> Logger:
        """
        获取一个命名的日志记录器

        Args:
            name: 日志记录器名称，如果名称已存在则返回现有实例
            **kwargs: 创建Logger的其他参数

        Returns:
            Logger实例
        """
        # 如果没有指定名称，则返回一个新的未命名Logger实例
        if name is None:
            return Logger(**kwargs)

        # 如果已存在此名称的Logger，则返回现有实例
        if name in cls._instance._loggers if cls._instance else {}:
            return cls._instance._loggers[name]

        # 否则创建一个新的Logger并保存
        if cls._instance is None:
            cls._instance = cls()

        logger = Logger(name=name, **kwargs)
        cls._instance._loggers[name] = logger
        return logger

    @classmethod
    def remove_logger(cls, name: str) -> bool:
        """
        从管理器中移除指定名称的日志记录器

        Args:
            name: 日志记录器名称

        Returns:
            是否成功移除
        """
        if cls._instance and name in cls._instance._loggers:
            del cls._instance._loggers[name]
            return True
        return False


# 创建一个默认的全局日志记录器实例（默认只输出 info 及以上）
default_logger = Logger(level="info")


# 测试代码
def test_logger():
    """测试日志记录器"""
    print("=== 基本功能测试 ===")
    logger = Logger(level="debug")  # 调试模式，显示所有日志

    # 测试不同级别的日志
    logger.info("这是一条信息日志")
    logger.success("这是一条成功日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    logger.critical("这是一条致命错误日志")  # 新增的级别
    logger.debug("这是一条调试日志")

    # 测试链式调用
    logger.info("链式调用").success("可以连续记录多条日志")

    # 测试仅控制台输出
    logger.console_only().info("这条日志只会在控制台显示")

    print("\n=== 日志管理器测试 ===")
    # 测试日志管理器
    app_logger = LogManager.get_logger("app", level="info")
    db_logger = LogManager.get_logger("database", level="debug")

    app_logger.info("应用程序初始化")
    db_logger.debug("数据库连接参数: localhost:5432")

    # 测试获取相同名称的logger是否返回同一实例
    app_logger2 = LogManager.get_logger("app")
    print(f"是否为同一实例: {app_logger is app_logger2}")

    print("\n日志记录器测试完成!")


if __name__ == "__main__":
    test_logger()