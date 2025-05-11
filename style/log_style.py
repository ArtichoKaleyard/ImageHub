"""
日志样式模块，提供统一的日志样式管理和格式化功能。
支持GUI日志显示和控制台日志输出，自动适配深浅色主题。

使用方法:
    from config.log_style import format_log_html, format_console_log, LOG_COLORS, set_theme

    # 设置主题 (可选)
    set_theme("dark")  # 或 "light", "auto"

    # GUI日志格式化
    html_log = format_log_html("14:30:22", "图像已成功保存", "success")
    log_text_edit.append(html_log)  # 添加到QTextEdit

    # 控制台日志格式化
    console_log = format_console_log("14:30:22", "图像已成功保存", "success")
    print(console_log)  # 在控制台显示带颜色的日志

    # 从应用程序主题同步颜色 (推荐)
    sync_from_app_theme()
"""
import os
import platform
import sys
import importlib.util

# 直接导入style_config模块，避免循环依赖
_style_config_imported = False
_style_config = None


def _import_style_config():
    """动态导入style_config模块，避免循环依赖"""
    global _style_config_imported, _style_config
    try:
        # 尝试使用importlib动态导入style_config模块
        spec = importlib.util.find_spec('style.style_config')
        if spec is not None:
            _style_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_style_config)
            _style_config_imported = True
            return True
        return False
    except (ImportError, AttributeError):
        return False


# 主题定义
class ThemeColors:
    """主题颜色定义"""

    # 浅色主题
    LIGHT = {
        "success": "#00C853",
        "warning": "#FFD600",
        "error": "#FF1744",
        "critical": "#D32F2F",
        "info": "#2196F3",
        "debug": "#607D8B",
        "timestamp": "#78909C",
        "text": "#263238",
        "text_secondary": "#78909C",
        "background": "#FFFFFF",
        "border": "#E0E0E0"
    }

    # 深色主题
    DARK = {
        "success": "#00E676",
        "warning": "#FFEA00",
        "error": "#FF5252",
        "critical": "#ff0000",
        "info": "#40C4FF",
        "debug": "#B0BEC5",
        "timestamp": "#90A4AE",
        "text": "#ECEFF1",
        "text_secondary": "#B0BEC5",
        "background": "#263238",
        "border": "#455A64"
    }


# 当前主题模式
CURRENT_THEME = "auto"
# 当前活动主题颜色
LOG_COLORS = {}


def _detect_system_theme():
    """检测系统主题是深色还是浅色

    Returns:
        str: "dark" 或 "light"
    """
    # 如果已导入style_config模块，使用其提供的信息
    if _style_config_imported and hasattr(_style_config, 'DARK_MODE'):
        return "dark" if _style_config.DARK_MODE else "light"

    # 尝试检测系统主题
    try:
        # macOS
        if platform.system() == "Darwin":
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, check=False
            )
            return "dark" if result.stdout.strip() == "Dark" else "light"

        # Windows 10+
        elif platform.system() == "Windows":
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if value == 1 else "dark"
            except:
                pass

        # Linux (检查一些常见的环境变量)
        elif platform.system() == "Linux":
            # 检查GNOME
            if os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME":
                try:
                    import subprocess
                    result = subprocess.run(
                        ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                        capture_output=True, text=True, check=False
                    )
                    return "dark" if "dark" in result.stdout.lower() else "light"
                except:
                    pass
    except:
        pass

    # 默认为浅色主题
    return "light"


def sync_from_app_theme():
    """
    从应用程序主题同步颜色设置

    将日志颜色与主应用程序主题保持一致
    如果主应用程序主题不可用，则不进行更改
    """
    # 尝试导入style_config模块
    if not _style_config_imported and not _import_style_config():
        return False

    global LOG_COLORS

    # 同步主题模式
    set_theme("dark" if _style_config.DARK_MODE else "light")

    # 从主应用程序主题获取颜色
    try:
        # 映射主应用程序颜色到日志颜色
        if hasattr(_style_config, 'THEME'):
            theme = _style_config.THEME

            # 直接映射关系
            color_mapping = {
                "success": "success",
                "warning": "warning",
                "error": "error",
                "info": "info",
                "debug": "text_secondary",
                "timestamp": "text_secondary",
                "text": "text",
                "text_secondary": "text_secondary",
                "background": "card_background",
                "border": "border"
            }

            # 更新日志颜色
            for log_color, app_color in color_mapping.items():
                if app_color in theme:
                    LOG_COLORS[log_color] = theme[app_color]

        # 更新日志区域样式
        global LOG_AREA_STYLE
        LOG_AREA_STYLE = _get_log_area_style()

        return True
    except Exception as e:
        # 如果获取主题颜色失败，保留原有颜色
        print(f"同步主题失败: {e}")
        return False


def set_theme(theme="auto"):
    """设置日志样式主题

    Args:
        theme: 主题名称 ("light", "dark", "auto")
    """
    global CURRENT_THEME, LOG_COLORS

    if theme not in ["light", "dark", "auto"]:
        theme = "auto"

    CURRENT_THEME = theme

    # 如果是自动模式，检测系统主题
    active_theme = theme
    if theme == "auto":
        active_theme = _detect_system_theme()

    # 设置活动主题颜色
    LOG_COLORS = ThemeColors.DARK if active_theme == "dark" else ThemeColors.LIGHT

    # 更新日志区域样式
    global LOG_AREA_STYLE
    LOG_AREA_STYLE = _get_log_area_style()


def _get_log_area_style():
    """根据当前主题获取日志区域样式

    Returns:
        str: QTextEdit样式表
    """
    return f"""
    QTextEdit {{
        background-color: {LOG_COLORS["background"]};
        color: {LOG_COLORS["text"]};
        border: 1px solid {LOG_COLORS["border"]};
        border-radius: 6px;
        padding: 5px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10pt;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {LOG_COLORS["text_secondary"]};
        min-height: 20px;
        border-radius: 4px;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    """


# 日志标签样式
LOG_TAG_STYLE = {
    "font": "font-family: 'Courier New', monospace; font-size: 9pt;",
    "padding": "padding: 1px 0px;",
    "border_radius": "border-radius: 3px;",
    "margin": "margin: 0 4px;",
    "align": "text-align: center;",
    "width": "width: 72px; display: inline-block;",  # 调整为固定宽度
    "white-space": "white-space: pre;"  # 新增，保留空格
}

# 日志HTML格式模板
LOG_HTML_TEMPLATE = """
<div style='font-family: "Courier New", monospace; color:{text_color}; white-space: pre-wrap;'>\
<span style='color:{timestamp_color}'>[{timestamp}]</span>\
<span style='color:{tag_color}; {tag_style}'>{tag}</span>\
{message}\
</div>
"""

# 初始化为默认主题（在模块导入时调用）
set_theme("auto")
# 尝试导入style_config并同步主题
_import_style_config()
if _style_config_imported:
    sync_from_app_theme()


# 控制台颜色代码
class ConsoleColors:
    """控制台ANSI颜色代码"""
    # 是否启用彩色输出
    ENABLED = True

    # 基础颜色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # 修饰
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # 重置
    RESET = '\033[0m'

    @classmethod
    def init(cls):
        """初始化控制台颜色支持"""
        # Windows命令提示符需要特殊处理
        if platform.system() == "Windows":
            try:
                # 尝试在Windows上启用ANSI转义序列
                os.system('color')
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except:
                # 如果失败，禁用彩色输出
                cls.ENABLED = False

    @classmethod
    def colorize(cls, text, color, style=None):
        """为文本添加颜色

        Args:
            text: 要着色的文本
            color: 颜色代码
            style: 可选样式（如BOLD）

        Returns:
            着色后的文本
        """
        if not cls.ENABLED:
            return text

        prefix = color
        if style:
            prefix = style + color

        return f"{prefix}{text}{cls.RESET}"


# 初始化控制台颜色支持
ConsoleColors.init()

# 日志级别到控制台颜色的映射
CONSOLE_COLOR_MAP = {
    "success": ConsoleColors.GREEN,
    "warning": ConsoleColors.YELLOW,
    "error": ConsoleColors.RED,
    "critical": ConsoleColors.BRIGHT_RED,
    "info": ConsoleColors.BLUE,
    "debug": ConsoleColors.BRIGHT_BLACK,
    "normal": ConsoleColors.WHITE
}


def format_log_html(timestamp: str, message: str, level: str = "info") -> str:
    """
    格式化日志消息为HTML格式(用于GUI显示)

    Args:
        timestamp: 时间戳字符串
        message: 日志消息内容
        level: 日志级别 ("success", "warning", "error", "info", "debug", "normal")

    Returns:
        格式化后的HTML字符串
    """
    # 获取标签映射和颜色
    TAG_MAPPING = {
        'success': 'SUCCESS',
        'warning': 'WARN',
        'error': 'ERROR',
        'critical': 'CRIT',
        'info': 'INFO',
        'debug': 'DEBUG',
        'normal': 'STATUS'
    }

    # 转换标签
    level_upper = TAG_MAPPING.get(level, 'INFO')

    # 处理标签内容
    TAG_WIDTH = 9
    if len(level_upper) > TAG_WIDTH - 2:
        tag = f"[{level_upper[:TAG_WIDTH - 2]}]"
    else:
        total_spaces = TAG_WIDTH - len(level_upper) - 2
        left_spaces = total_spaces // 2
        right_spaces = total_spaces - left_spaces
        tag = f"[{' ' * left_spaces}{level_upper}{' ' * right_spaces}]"

    # 获取颜色
    tag_color = LOG_COLORS.get(level, LOG_COLORS["info"])

    return LOG_HTML_TEMPLATE.format(
        text_color=LOG_COLORS["text"],
        timestamp_color=LOG_COLORS["timestamp"],
        tag_color=tag_color,
        tag_style='; '.join(LOG_TAG_STYLE.values()),
        tag=tag,
        timestamp=timestamp,
        message=message
    )


def format_console_log(timestamp: str, message: str, level: str = "info") -> str:
    """
    格式化日志消息为控制台输出格式(带ANSI颜色代码)

    Args:
        timestamp: 时间戳字符串
        message: 日志消息内容
        level: 日志级别 ("success", "warning", "error", "info", "debug", "normal")

    Returns:
        格式化后的控制台日志字符串(带颜色)
    """
    # 获取标签映射
    TAG_MAPPING = {
        'success': 'SUCCESS',
        'warning': 'WARN',
        'error': 'ERROR',
        'critical': 'CRIT',
        'info': 'INFO',
        'debug': 'DEBUG',
        'normal': 'STATUS'
    }

    # 转换标签
    level_upper = TAG_MAPPING.get(level, 'INFO')

    # 处理标签内容
    TAG_WIDTH = 9
    if len(level_upper) > TAG_WIDTH - 2:
        tag = f"[{level_upper[:TAG_WIDTH - 2]}]"
    else:
        total_spaces = TAG_WIDTH - len(level_upper) - 2
        left_spaces = total_spaces // 2
        right_spaces = total_spaces - left_spaces
        tag = f"[{' ' * left_spaces}{level_upper}{' ' * right_spaces}]"

    # 获取控制台颜色
    color = CONSOLE_COLOR_MAP.get(level, ConsoleColors.WHITE)
    timestamp_color = ConsoleColors.BRIGHT_BLACK

    # 格式化带颜色的控制台日志
    formatted_timestamp = ConsoleColors.colorize(f"[{timestamp}]", timestamp_color)
    formatted_tag = ConsoleColors.colorize(tag, color, ConsoleColors.BOLD)

    return f"{formatted_timestamp} {formatted_tag} {message}"


# 简单日志记录函数
def log(message: str, level: str = "info", timestamp: str = None, to_console: bool = True, gui_callback=None):
    """
    记录日志到控制台和/或GUI

    Args:
        message: 日志消息
        level: 日志级别
        timestamp: 时间戳，如果为None则自动生成
        to_console: 是否输出到控制台
        gui_callback: GUI日志回调函数，接收HTML格式的日志
    """
    import datetime

    # 生成时间戳
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 输出到控制台
    if to_console:
        console_log = format_console_log(timestamp, message, level)
        print(console_log)

    # 输出到GUI
    if gui_callback is not None:
        html_log = format_log_html(timestamp, message, level)
        gui_callback(html_log)


# 日志级别测试功能
def test_log_styles():
    """测试日志样式"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    print("===== 当前主题: {} =====".format(
        CURRENT_THEME if CURRENT_THEME != "auto" else f"auto ({_detect_system_theme()})"
    ))

    # 显示主题来源
    if _style_config_imported:
        print("===== 主题来源: 从应用程序主题同步 =====")
    else:
        print("===== 主题来源: 内部定义 =====")

    print("\n===== 控制台日志样式测试 =====")
    print(format_console_log(timestamp, "这是一条信息日志", "info"))
    print(format_console_log(timestamp, "这是一条成功日志", "success"))
    print(format_console_log(timestamp, "这是一条警告日志", "warning"))
    print(format_console_log(timestamp, "这是一条错误日志", "error"))
    print(format_console_log(timestamp, "这是一条调试日志", "debug"))
    print(format_console_log(timestamp, "这是一条普通状态日志", "normal"))

    print("\n===== HTML日志样式示例 =====")
    print(format_log_html(timestamp, "这是一条HTML格式的信息日志", "info"))

    print("\n===== 主题切换测试 =====")
    current = CURRENT_THEME

    # 切换到浅色主题
    set_theme("light")
    print("浅色主题 - 成功日志示例:")
    print(format_console_log(timestamp, "这是浅色主题下的成功日志", "success"))

    # 切换到深色主题
    set_theme("dark")
    print("深色主题 - 成功日志示例:")
    print(format_console_log(timestamp, "这是深色主题下的成功日志", "success"))

    # 如果主应用程序主题可用，测试同步
    if _style_config_imported:
        print("\n===== 应用程序主题同步测试 =====")
        sync_from_app_theme()
        print("同步后 - 成功日志示例:")
        print(format_console_log(timestamp, "这是同步应用程序主题后的成功日志", "success"))

    # 恢复之前的主题
    set_theme(current)

    print("\n使用log()函数同时输出:")
    log("这是同时发送到控制台和GUI的日志", "success")


if __name__ == "__main__":
    # 测试日志样式
    test_log_styles()
