"""
样式接口模块，提供统一的样式与主题访问方法。
具体实现位于 style_config.py，本模块仅用于暴露接口。

使用方法:
    from modern_style_declarations import get_style, get_theme, StatusAnimator

    # 获取应用程序主样式
    app.setStyleSheet(get_style('APP_STYLE'))

    # 获取按钮样式
    my_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))

    # 获取当前使用的主题颜色
    primary_color = get_theme('primary')

    # 创建状态栏动画
    status_animator = StatusAnimator(status_label)
    status_animator.start("保存成功!", get_theme('success'))
"""
import config.style_config as config


def get_style(style_name: str) -> str | int:
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
    """
    if hasattr(config, style_name):
        return getattr(config, style_name)
    else:
        raise ValueError(f"样式 '{style_name}' 不存在")


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


def is_dark_mode():
    """
    检测系统是否处于深色模式

    Returns:
        bool: 如果系统使用深色模式则返回True，否则返回False
    """
    return config.DARK_MODE


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

# 日志区域样式
LOG_AREA_STYLE = config.LOG_AREA_STYLE

# 日志颜色方案
LOG_COLORS = config.LOG_COLORS

# 日志标签样式
LOG_TAG_STYLE = config.LOG_TAG_STYLE

# 日志HTML模板
LOG_HTML_TEMPLATE = config.LOG_HTML_TEMPLATE

def format_log_html(timestamp: str, message: str, level: str = "info") -> str:
    """
    格式化日志消息为HTML
    
    Args:
        timestamp: 时间戳字符串
        message: 日志消息内容
        level: 日志级别 ("success", "warning", "error", "info", "normal")
    
    Returns:
        格式化后的HTML字符串
    """
    # 获取标签映射和颜色
    TAG_MAPPING = {
        'success': 'SUCCESS',
        'warning': 'WARN',
        'error': 'ERROR',
        'info': 'INFO',
        'normal': 'STATUS'
    }
    
    # 转换标签
    level_upper = TAG_MAPPING.get(level, 'INFO')
    
    # 处理标签内容
    TAG_WIDTH = 9
    if len(level_upper) > TAG_WIDTH - 2:
        tag = f"[{level_upper[:TAG_WIDTH-2]}]"
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