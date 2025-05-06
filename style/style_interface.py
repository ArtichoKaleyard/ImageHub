"""
增强版样式接口模块，提供统一的样式、主题与日志样式访问方法。
整合了style_config.py和log_style.py的功能，作为统一入口点。

使用方法:
    from style.style_interface import (
        # 基础样式接口
        get_style, get_theme, StatusAnimator, is_dark_mode,
        # 日志样式接口
        get_log_style, format_log_html, format_console_log, set_log_theme, sync_log_theme
    )

    # 获取应用程序主样式
    app.setStyleSheet(get_style('APP_STYLE'))

    # 获取当前使用的主题颜色
    primary_color = get_theme('primary')

    # 创建状态栏动画
    status_animator = StatusAnimator(status_label)
    status_animator.start("保存成功!", get_theme('success'))

    # 设置日志主题（会自动与应用主题同步，但可以单独设置）
    set_log_theme("dark")  # 或 "light", "auto"

    # 同步日志主题与应用主题
    sync_log_theme()

    # 获取日志区域样式
    log_text_edit.setStyleSheet(get_log_style("LOG_AREA_STYLE"))

    # 格式化日志
    html_log = format_log_html("14:30:22", "图像已成功保存", "success")
    log_text_edit.append(html_log)

    console_log = format_console_log("14:30:22", "图像已成功保存", "success")
    print(console_log)
"""
import style.style_config as config
from style.log_style import (
    # 日志格式化函数
    format_log_html, format_console_log, log,
    # 日志主题管理
    set_theme as _set_log_theme,
    sync_from_app_theme as _sync_log_theme,
    # 日志样式
    LOG_AREA_STYLE, LOG_COLORS,
    # 控制台颜色
    ConsoleColors
)


def get_style(style_name: str) -> str:
    """
    获取指定名称的样式

    Args:
        style_name: 样式名称(字符串)，见下方样式列表

    Returns:
        字符串形式的样式定义，直接用于setStyleSheet()方法

    样式列表:
        - APP_STYLE: 应用程序全局样式
        - PRIMARY_BUTTON_STYLE: 主按钮样式
        - SECONDARY_BUTTON_STYLE: 次要按钮样式
        - INPUT_STYLE: 输入框和数字输入框样式
        - GROUP_BOX_STYLE: 分组框样式，带毛玻璃效果
        - COMBO_BOX_STYLE: 下拉菜单样式
        - CHECK_BOX_STYLE: 复选框样式
        - STATUS_BAR_STYLE: 状态栏样式
        - STATUS_FRAME_STYLE: 状态框样式
        - IMAGE_LABEL_STYLE: 图像标签样式，带边框
        - INFO_LABEL_STYLE: 信息标签样式，较小字体
        - LABEL_STYLE: 标准标签样式
        - SCROLLBAR_STYLE: 滚动条样式
        - Q_TAB_WIDGET_STYLE: 标签页样式
        - LOG_AREA_STYLE: 日志区域样式
    """
    # 特殊处理日志区域样式
    if style_name == 'LOG_AREA_STYLE':
        return LOG_AREA_STYLE

    if hasattr(config, style_name):
        return getattr(config, style_name)
    else:
        raise ValueError(f"样式 '{style_name}' 不存在")


def get_log_style(style_name: str) -> str:
    """
    获取日志相关的样式

    Args:
        style_name: 样式名称(字符串)
            - LOG_AREA_STYLE: 日志区域样式

    Returns:
        字符串形式的样式定义
    """
    if style_name == 'LOG_AREA_STYLE':
        return LOG_AREA_STYLE
    else:
        raise ValueError(f"日志样式 '{style_name}' 不存在")


def get_theme(color_name: str) -> str:
    """
    获取当前主题中的颜色

    Args:
        color_name: 颜色名称(字符串)，见下方颜色列表

    Returns:
        颜色值，如 "#1565C0"

    颜色列表:
        - primary: 主色调
        - primary_light: 浅主色调
        - primary_dark: 深主色调
        - secondary: 次要色调
        - secondary_light: 浅次要色调
        - secondary_dark: 深次要色调
        - accent: 强调色
        - background: 背景色
        - card_background: 卡片背景色
        - backdrop: 半透明背景色
        - text: 文本色
        - text_light: 浅文本色
        - text_secondary: 次要文本色
        - success: 成功状态色
        - warning: 警告状态色
        - error: 错误状态色
        - info: 信息状态色
        - border: 边框色
        - divider: 分隔线色
        - blur_background: 毛玻璃效果背景色
        - shadow: 阴影色
    """
    if color_name in config.THEME:
        return config.THEME[color_name]
    else:
        raise ValueError(f"颜色 '{color_name}' 不存在")


def get_log_theme(color_name: str) -> str:
    """
    获取当前日志主题中的颜色

    Args:
        color_name: 颜色名称(字符串)
            - success: 成功状态色
            - warning: 警告状态色
            - error: 错误状态色
            - info: 信息状态色
            - debug: 调试状态色
            - timestamp: 时间戳色
            - text: 文本色
            - text_secondary: 次要文本色
            - background: 背景色
            - border: 边框色

    Returns:
        颜色值，如 "#00C853"
    """
    if color_name in LOG_COLORS:
        return LOG_COLORS[color_name]
    else:
        raise ValueError(f"日志颜色 '{color_name}' 不存在")


def is_dark_mode() -> bool:
    """
    检测系统是否处于深色模式

    Returns:
        bool: 如果系统使用深色模式则返回True，否则返回False
    """
    return config.DARK_MODE


def set_log_theme(theme="auto"):
    """
    设置日志样式主题，不影响应用主题

    Args:
        theme: 主题名称 ("light", "dark", "auto")
    """
    _set_log_theme(theme)


def sync_log_theme():
    """
    从应用程序主题同步日志颜色设置

    将日志颜色与主应用程序主题保持一致
    如果主应用程序主题不可用，则不进行更改

    Returns:
        bool: 同步成功返回True，否则返回False
    """
    return _sync_log_theme()


# 导出StatusAnimator类便于直接使用
class StatusAnimator(config.StatusAnimator):
    """
    状态栏动画控制器

    用于创建流动动画效果的状态提示

    使用方法:
        # 创建实例
        animator = StatusAnimator(status_label)

        # 启动动画
        animator.start(
            message="操作成功!",    # 显示的消息
            color_start="#00C853",  # 起始颜色
            color_end="#26A69A"     # 结束颜色(可选)
        )

        # 静态颜色显示
        animator.set_static_color("警告信息", "#FFD600")

        # 停止动画
        animator.stop()
    """
    pass

# 应用标题常量
APP_TITLE = config.APP_TITLE

# 窗口默认尺寸
DEFAULT_WINDOW_SIZE = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

# 动画速度常量
ANIMATION_SPEED = {
    "normal": config.ANIMATION_SPEED["normal"],
    "slow": config.ANIMATION_SPEED["slow"],
    "fast": config.ANIMATION_SPEED["fast"]
}

# 状态消息颜色方案
STATUS_COLORS = {
    "normal": config.STATUS_COLORS["normal"],
    "success": config.STATUS_COLORS["success"],
    "error": config.STATUS_COLORS["error"],
    "warning": config.STATUS_COLORS["warning"]
}

# 导出日志颜色常量
LOG_LEVEL_COLORS = {
    "success": LOG_COLORS["success"],
    "warning": LOG_COLORS["warning"],
    "error": LOG_COLORS["error"],
    "info": LOG_COLORS["info"],
    "debug": LOG_COLORS["debug"],
    "normal": LOG_COLORS["text"]
}

# 为向后兼容保留原始导出
format_log_html = format_log_html
format_console_log = format_console_log