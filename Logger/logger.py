"""
日志记录器模块，提供统一的日志记录功能。
支持GUI和控制台日志输出，基于统一样式接口实现样式。

使用方法:
    from config.Logger import Logger

    # 创建日志记录器
    Logger = Logger(log_to_console=True)

    # 添加GUI日志区域 (QTextEdit)
    Logger.set_gui_log_widget(log_text_edit)

    # 记录不同级别的日志
    Logger.info("应用程序已启动")
    Logger.success("操作完成")
    Logger.warning("文件已存在，将被覆盖")
    Logger.error("无法连接到服务器")
    Logger.debug("变量x的值为: 42")

    # 仅发送到控制台
    Logger.console_only().info("这条信息只会在控制台显示")

    # 仅发送到GUI
    Logger.gui_only().info("这条信息只会在GUI中显示")
"""
import datetime
from style.style_interface import format_console_log, format_log_html


class Logger:
    """日志记录器，支持控制台和GUI日志输出"""

    def __init__(self, log_to_console: bool = True, log_to_gui: bool = True):
        """
        初始化日志记录器

        Args:
            log_to_console: 是否输出到控制台
            log_to_gui: 是否输出到GUI
        """
        self._log_to_console = log_to_console
        self._log_to_gui = log_to_gui
        self._gui_callback = None
        # 临时设置状态
        self._temp_log_to_console = None
        self._temp_log_to_gui = None

    def set_gui_log_widget(self, text_edit):
        """
        设置GUI日志控件

        Args:
            text_edit: QTextEdit或兼容对象，必须有append方法
        """
        if hasattr(text_edit, 'append'):
            self._gui_callback = text_edit.append
        else:
            raise ValueError("GUI日志控件必须有append方法")
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
        # 确定当前的输出目标
        to_console = self._temp_log_to_console if self._temp_log_to_console is not None else self._log_to_console
        to_gui = self._temp_log_to_gui if self._temp_log_to_gui is not None else self._log_to_gui

        # 重置临时设置
        self._temp_log_to_console = None
        self._temp_log_to_gui = None

        # 生成时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 输出到控制台
        if to_console:
            console_log = format_console_log(timestamp, message, level)
            print(console_log)

        # 输出到GUI
        if to_gui and self._gui_callback is not None:
            html_log = format_log_html(timestamp, message, level)
            self._gui_callback(html_log)

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


# 创建一个默认的全局日志记录器实例
default_logger = Logger()


# 测试代码
def test_logger():
    """测试日志记录器"""
    logger = Logger()

    # 测试不同级别的日志
    logger.info("这是一条信息日志")
    logger.success("这是一条成功日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    logger.debug("这是一条调试日志")

    # 测试链式调用
    logger.info("链式调用").success("可以连续记录多条日志")

    # 测试仅控制台输出
    logger.console_only().info("这条日志只会在控制台显示")

    print("\n日志记录器测试完成!")


if __name__ == "__main__":
    test_logger()