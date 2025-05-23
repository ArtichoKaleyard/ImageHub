"""
粘贴板图像自动缩放器 - 现代化样式配置文件
包含毛玻璃效果、动画、流动状态栏以及深色模式支持
"""
import platform
from PyQt6.QtCore import QSettings, QTimer


# 系统主题检测
def is_dark_mode():
    """检测系统是否处于深色模式"""
    if platform.system() == "Windows":
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0
        except:
            return False
    elif platform.system() == "Darwin":  # macOS
        try:
            settings = QSettings("Apple", "")
            settings.beginGroup("NSGlobalDomain")
            theme = settings.value("AppleInterfaceStyle", "")
            return theme == "Dark"
        except:
            return False
    return False


# 应用程序标题
APP_TITLE = "应用程序标题"

# 窗口初始大小
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 500

# 检测系统主题
DARK_MODE = is_dark_mode()

# 颜色主题
LIGHT_THEME = {
    # 主色调（降低饱和度，向水蓝色方向调整）
    "primary": "#1565C0",  # 原#2962FF → 降低亮度+饱和度
    "primary_light": "#5E92F3",  # 原#768FFF → 加入灰调
    "primary_dark": "#003C8F",  # 原#0039CB → 加深并降低饱和度
    # 次要色调（改为更柔和的蓝绿色）
    "secondary": "#00838F",  # 原#00B0FF → 降低亮度增加绿色
    "secondary_light": "#4FB3BF",  # 原#69E2FF → 增加灰调
    "secondary_dark": "#005662",  # 原#0081CB → 大幅加深并偏绿
    # 强调色（改为柔和的青瓷色）
    "accent": "#26A69A",  # 原#00E5FF → 降低亮度增加绿调

    # 背景色
    "background": "#F5F7FA",
    "card_background": "#FFFFFF",
    "backdrop": "rgba(255, 255, 255, 0.7)",  # 毛玻璃背景

    # 文本色
    "text": "#263238",  # 深灰色
    "text_light": "#607D8B",  # 蓝灰色
    "text_secondary": "#78909C",

    # 状态颜色
    "success": "#00C853",
    "warning": "#FFD600",
    "error": "#FF1744",
    "critical": "#D32F2F",
    "info": "#2196F3",

    # 边框颜色
    "border": "#E0E0E0",
    "divider": "#EEEEEE",

    # 毛玻璃效果颜色
    "blur_background": "rgba(255, 255, 255, 0.65)",
    "shadow": "rgba(0, 0, 0, 0.15)"
}

DARK_THEME = {
    # 主色调（改为深空蓝，降低亮度）
    "primary": "#0D47A1",  # 原#2979FF → 加深至深夜蓝
    "primary_light": "#5472D3",  # 原#75A7FF → 降低亮度加灰
    "primary_dark": "#002171",  # 原#004ECB → 加深至接近黑色
    # 次要色调（改为暗夜蓝绿）
    "secondary": "#006978",  # 原#00B0FF → 大幅降低亮度
    "secondary_light": "#4F8D9C",  # 原#69E2FF → 增加灰调
    "secondary_dark": "#003D44",  # 原#0081CB → 加深至深海色
    # 强调色（改为暗翡翠色）
    "accent": "#00796B",  # 原#00E5FF → 大幅降低亮度

    # 背景色
    "background": "#121212",  # 深黑色
    "card_background": "#1E1E1E",
    "backdrop": "rgba(18, 18, 18, 0.7)",  # 毛玻璃背景

    # 文本色
    "text": "#ECEFF1",  # 浅灰白色
    "text_light": "#B0BEC5",  # 浅蓝灰色
    "text_secondary": "#78909C",

    # 状态颜色
    "success": "#00E676",
    "warning": "#CCBB00",
    "error": "#FF5252",
    "critical": "#ff0000",
    "info": "#40C4FF",

    # 边框颜色
    "border": "#333333",
    "divider": "#2C2C2C",

    # 毛玻璃效果颜色
    # 使用完全匹配的基色，但保持透明度
    "blur_background": "rgba(18, 18, 18, 0.85)",  # 与background完全一致的基色
    "shadow": "rgba(0, 0, 0, 0.3)"
}

# 使用当前系统主题
THEME = DARK_THEME if DARK_MODE else LIGHT_THEME

# 字体设置
FONTS = {
    "default": {
        "family": "Microsoft YaHei UI",  # 更现代的字体
        "size": 10
    },
    "title": {
        "family": "Microsoft YaHei UI",
        "size": 11,
    },
    "small": {
        "family": "Microsoft YaHei UI",
        "size": 9
    }
}

# 动画时间 (毫秒)
ANIMATION_SPEED = {
    "normal": 150,
    "slow": 300,
    "fast": 80,
}

# 基础字体样式
FONT_STYLE = f"""
    font-family: "{FONTS["default"]["family"]}";
"""

TITLE_FONT_STYLE = f"""
    font-family: "{FONTS["title"]["family"]}";
    font-size: {FONTS["title"]["size"]}pt;
    font-weight: normal;
"""

SMALL_FONT_STYLE = f"""
    font-family: "{FONTS["small"]["family"]}";
    font-size: {FONTS["small"]["size"]}pt;
"""

# ---------------------- 标签样式 ----------------------
Q_TAB_WIDGET_STYLE = f"""
    /* 设置整个标签栏的背景色（不同于内容区域） */
    QTabBar {{
        background-color: {THEME["background"]};  /* 与背景色一致 */
    }}
    /* 关键样式：使标签栏整体向右偏移，左侧留出空间 */
    QTabWidget::tab-bar {{
        left: 5px; /* 向右移动标签栏，左侧留出5px */
    }}
    /* 未选中标签样式 */
    QTabBar::tab {{
        background-color: {THEME["card_background"]};  /* 默认标题栏颜色 */
        color: {THEME["text"]};                         /* 文字颜色 */
        padding: 6px 12px;                             /* 内边距 */
        border: 1px solid {THEME["border"]};  /* 添加边框 */
        border-top-left-radius: 6px;                    /* 圆角 */
        border-top-right-radius: 6px;                   /* 圆角 */
        margin: 0px 2px;                                /* 标签水平间距 */
        font-weight: bold;                              /* 加粗字体 */
        {TITLE_FONT_STYLE}
    }}

    /* 悬停状态 */
    QTabBar::tab:hover {{
        color: {THEME["primary_light"]};                         /* 文字颜色 */
        background-color: {THEME["backdrop"]};     /* 悬停颜色 */
    }}

    /* 选中标签样式 */
    QTabBar::tab:selected {{
        border: 1px solid {THEME["border"]};  /* 添加边框 */
        background-color: {THEME["background"]};        /* 与内容区域一致 */
        color: {THEME["text"]};                         /* 文字颜色 */
        border-bottom-color: transparent;               /* 去掉底部边框，避免冲突 */
        font-weight: bold;                              /* 加粗字体 */
    }}

    /* 内容区域样式 */
    QTabWidget::pane {{
        border: 2px solid {THEME["border"]};            /* 保留顶部边框 */
        border-left: none;                              /* 去掉左侧边框 */
        border-right: none;                             /* 去掉右侧边框 */
        border-bottom: none;                            /* 去掉底部边框 */
        border-top-color: {THEME["border"]};   /* 与边框颜色一致 */
        border-radius: 6px;                             /* 圆角 */
        background-color: {THEME["background"]};        /* 内容区域背景色 */
        margin-top: -2px;                               /* 与标签栏无缝衔接 */
    }}
"""

# ---------------------- 按钮样式 ----------------------

# 主按钮样式 - 带光泽感和悬停动画
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {THEME["primary"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 15px;
        font-weight: bold;
        min-height: 20px;
        min-width: 80px;
        outline: none;
        {FONT_STYLE}
    }}
    QPushButton:hover {{
        background-color: {THEME["primary_light"]};
    }}
    QPushButton:pressed {{
        background-color: {THEME["primary_dark"]};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        background-color: rgba(150, 150, 150, 0.3);
        color: rgba(255, 255, 255, 0.5);
    }}
"""

# 同样修改SECONDARY_BUTTON_STYLE
SECONDARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {THEME["secondary"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 15px;
        font-weight: bold;
        min-height: 20px;
        min-width: 80px;
        outline: none;
        {FONT_STYLE}
    }}
    QPushButton:hover {{
        background-color: {THEME["secondary_light"]};
    }}
    QPushButton:pressed {{
        background-color: {THEME["secondary_dark"]};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        background-color: rgba(150, 150, 150, 0.3);
        color: rgba(255, 255, 255, 0.5);
    }}
"""

# ---------------------- 输入框样式 ----------------------

# 输入框样式 - 移除了transition属性
INPUT_STYLE = f"""
    QLineEdit, QSpinBox {{
        border: 2px solid {THEME["border"]};
        border-radius: 6px;
        padding: 6px 8px;
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        selection-background-color: {THEME["primary_light"]};
        selection-color: white;
        {FONT_STYLE}
    }}
    QLineEdit:hover, QSpinBox:hover {{
        border: 2px solid {THEME["primary_light"]};
    }}
    QLineEdit:focus, QSpinBox:focus {{
        border: 2px solid {THEME["primary"]};
        background-color: {THEME["background"]};
    }}

    /* 调整 QSpinBox 上下按钮大小和样式 */
    QSpinBox::up-button {{
        background-color: {THEME["card_background"]};
        border: 1px solid {THEME["border"]};
        border-top-right-radius: 4px;
        margin: 1px 0px 1px 1px;
        width: 20px;  /* 调整宽度 */
        height: 12px; /* 调整高度 */
    }}
    QSpinBox::down-button {{
        background-color: {THEME["card_background"]};
        border: 1px solid {THEME["border"]};
        border-bottom-right-radius: 4px;
        margin: 1px 0px 1px 1px;
        width: 20px;
        height: 12px;
    }}

    /* 自定义上下箭头图标 */
    QSpinBox::up-arrow {{
        image: url(icons/arrow_up_icon.svg); /* 使用自定义图标 */
        width: 12px;
        height: 12px;
        margin: 0px 4px; /* 图标居中 */
    }}
    QSpinBox::down-arrow {{
        image: url(icons/arrow_down_icon.svg);
        width: 12px;
        height: 12px;
        margin: 0px 4px;
    }}

    /* 悬停和按下时的样式 */
    QSpinBox::up-button:hover {{
        background-color: {THEME["primary_light"]};
        border-color: {THEME["primary"]};
    }}
    QSpinBox::down-button:hover {{
        background-color: {THEME["primary_light"]};
        border-color: {THEME["primary"]};
    }}
    QSpinBox::up-button:pressed {{
        background-color: {THEME["primary_dark"]};
    }}
    QSpinBox::down-button:pressed {{
        background-color: {THEME["primary_dark"]};
    }}
"""

# ---------------------- 组件样式 ----------------------

# 组框样式 - 半透明毛玻璃效果
GROUP_BOX_STYLE = f"""
    QGroupBox {{ 
        background-color: {THEME["blur_background"]};
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        margin-top: 10px;
        padding: 2px 2px 2px 2px;
        font-weight: bold;
        color: {THEME["text"]};
        {TITLE_FONT_STYLE}
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        top: 0px;
        padding: 0 5px;
        background-color: {THEME["background"]};
        color: {THEME["text"]};
    }}
    
    /* 确保GroupBox内所有标签都透明 */
    QGroupBox QLabel {{
        background-color: transparent !important;
        color: {THEME["text"]};
        {FONT_STYLE}
    }}
"""

# 设置箭头图标
arrow_icon = "icons/chevron_down_light.svg" if DARK_MODE else "icons/chevron_down_dark.svg"

# 下拉菜单样式 - 现代化风格
COMBO_BOX_STYLE = f"""
    QComboBox {{
        border: 2px solid {THEME["border"]};
        border-radius: 5px;
        padding: 5px 8px;
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        min-height: 25px;
        selection-background-color: {THEME["primary"]};
        selection-color: white;
        {FONT_STYLE}
    }}
    QComboBox:hover {{
        border: 2px solid {THEME["primary_light"]};
    }}
    QComboBox:focus {{
        border: 2px solid {THEME["primary"]};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
        border-left: 1px solid {THEME["border"]};
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }}
    QComboBox::down-arrow {{
        image: url({arrow_icon});
        width: 18px;
        height: 18px;
    }}
    QComboBox QAbstractItemView {{
        border: 1px solid {THEME["border"]};
        border-radius: 5px;
        selection-background-color: {THEME["primary"]};
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        {FONT_STYLE}
    }}
"""

# 复选框样式 - 使用Qt原生渲染方式
CHECK_BOX_STYLE = f"""
    QCheckBox {{
        spacing: 8px;
        color: {THEME["text"]};
        {FONT_STYLE}
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {THEME["border"]};
        border-radius: 4px;
        background: {THEME["card_background"]};
    }}
    QCheckBox::indicator:checked {{
        image: url(icons/check_icon.svg);
        border-color: {THEME["primary_dark"]};
    }}
    QCheckBox::indicator:hover {{
        border-color: {THEME["primary"]};
    }}
    QCheckBox::indicator:disabled {{
        background: {THEME["divider"]};
        border-color: {THEME["border"]};
    }}
"""

# 状态栏样式 - 流动效果
STATUS_BAR_STYLE = f"""
    QLabel#StatusLabel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                     stop:0 {THEME["primary"]}, 
                     stop:0.3 {THEME["primary_dark"]},
                     stop:0.7 {THEME["primary_dark"]}, 
                     stop:1 {THEME["primary"]});
        color: white;
        padding: 8px 12px;
        border-radius: 5px;
        font-weight: bold;
        margin: 2px;
        {FONT_STYLE}
    }}
"""

# 状态帧样式 - 立体阴影效果
STATUS_FRAME_STYLE = f"""
    QFrame#StatusFrame {{
        background-color: {THEME["blur_background"]};
        border-radius: 6px;
        border: 1px solid {THEME["border"]};
    }}
"""

# 图像标签样式 - 阴影边框
IMAGE_LABEL_STYLE = f"""
    QLabel {{
        background-color: {THEME["blur_background"]};
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        padding: 2px;
    }}
"""

# 信息标签样式
INFO_LABEL_STYLE = f"""
    QLabel {{
        color: {THEME["text_light"]};
        background-color: transparent !important;
        padding: 4px;
        {SMALL_FONT_STYLE}
    }}
"""

# 标准标签样式
LABEL_STYLE = f"""
    QLabel {{
        color: {THEME["text"]};
        background-color: transparent !important;
        {FONT_STYLE}
    }}
"""

# 滚动条样式
SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        border: none;
        background: {THEME["background"]};
        width: 10px;
        margin: 0px 0px 0px 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {THEME["primary_light"]};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {THEME["primary"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        border: none;
        background: {THEME["background"]};
        height: 10px;
        margin: 0px 0px 0px 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {THEME["primary_light"]};
        min-width: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {THEME["primary"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
"""

# 主应用程序样式 - 全局默认样式
APP_STYLE = f"""
    /* 基础应用程序样式 */
    QMainWindow, QWidget {{
        background-color: {THEME["background"]};
        color: {THEME["text"]};
        {FONT_STYLE}
    }}

    /* 独立样式保护日志区域 */
    QTextEdit {{
        font-family: "Courier New";
        font-size: 10pt;
        background-color: {THEME["card_background"]};  /* 使用主题背景色 */
        selection-background-color: {THEME["primary"]};
        border: 1px solid {THEME["border"]};
        border-radius: 6px;
    }}

    /* 确保所有标签默认透明 */
    QLabel {{
        color: {THEME["text"]};
        background-color: transparent !important;
        {FONT_STYLE}
    }}

    /* 分隔符样式 */
    QSplitter::handle {{
        background-color: {THEME["border"]};
    }}

    /* 工具提示样式 */
    QToolTip {{
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        border: 1px solid {THEME["primary"]};
        padding: 5px;
        border-radius: 4px;
        {FONT_STYLE}
    }}

    /* 包含全局滚动条样式 */
    {SCROLLBAR_STYLE}
"""

# 日志区域样式
LOG_AREA_STYLE = f"""
    QTextEdit {{
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        border: 1px solid {THEME["border"]};
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
        background: {THEME["primary_light"]};
        min-height: 20px;
        border-radius: 4px;
    }}
    
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
"""

# 日志消息颜色定义
LOG_COLORS = {
    "success": THEME["success"],
    "warning": THEME["warning"],
    "error": THEME["error"],
    "info": THEME["info"],
    "debug": THEME["text_light"],
    "timestamp": THEME["text_secondary"],
    "text": THEME["text"],
    "text_secondary": THEME["text_secondary"]
}

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


# ---------------------- 状态动画类 ----------------------

class StatusAnimator:
    """状态栏动画控制器 - 完整版流动效果"""

    def __init__(self, status_label):
        """初始化状态动画控制器
        Args:
            status_label: 要应用动画效果的QLabel
        """
        self.label = status_label
        self.timer = QTimer()
        self.reset_timer = QTimer()  # 添加重置定时器
        self.animation_pos = 0  # 动画位置标记 (0-100)
        self.direction = 1  # 动画方向 (1=正向, -1=反向)
        self.current_colors = None  # 当前使用的颜色元组
        self.message = ""  # 当前显示的消息
        # 设置定时器
        self.timer.timeout.connect(self.update_animation)
        self.timer.setInterval(10)  # 10ms更新一次
        # 设置重置定时器
        self.reset_timer.timeout.connect(self._auto_reset_to_ready)
        self.reset_timer.setSingleShot(True)  # 单次触发

    def start(self, message, color_start, color_end=None):
        """开始状态动画
        Args:
            message: 要显示的状态消息
            color_start: 起始颜色
            color_end: 结束颜色,如不指定则使用起始颜色
        """
        self.message = message
        self.label.setText(message)
        # 设置颜色
        if not color_end:
            color_end = color_start
        self.current_colors = (color_start, color_end)
        # 重置动画参数
        self.animation_pos = 0
        self.direction = 1
        # 应用初始渐变
        self._update_gradient()
        # 启动定时器
        if not self.timer.isActive():
            self.timer.start()
        # 停止任何之前的重置定时器
        if self.reset_timer.isActive():
            self.reset_timer.stop()

    def stop(self):
        """停止动画"""
        if self.timer.isActive():
            self.timer.stop()
        # 设置为灰色而不是白色
        self.set_static_color("已停止", "#808080")  # 使用灰色
        # 启动重置定时器
        self.reset_timer.start(3000)  # 3秒后重置为就绪状态

    def _auto_reset_to_ready(self):
        """自动重置为就绪状态"""
        self.set_static_color("就绪", "#2196F3")  # 使用info蓝色

    def update_animation(self):
        """更新动画状态"""
        # 更新位置
        self.animation_pos += (self.direction * 1)  # 每步移动1个单位
        # 检查边界并重置方向
        if self.animation_pos >= 100:
            self.animation_pos = 0
            # self.direction = -1
        elif self.animation_pos <= 0:
            self.animation_pos = 0
            self.direction = 1
        # 更新渐变效果
        self._update_gradient()

    def set_static_color(self, message, color):
        """设置静态颜色状态 - 不使用动画
        Args:
            message: 要显示的状态消息
            color: 要应用的颜色
        """
        self.message = message
        self.label.setText(message)
        # 停止任何正在运行的动画
        if self.timer.isActive():
            self.timer.stop()
        # 应用静态颜色样式
        static_style = f"""
            background-color: {color};
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin: 2px;
        """
        self.label.setStyleSheet(static_style)

    def _update_gradient(self):
        """更新标签的渐变背景"""
        if not self.current_colors:
            return
        color1, color2 = self.current_colors
        pos = self.animation_pos / 100.0  # 转换为0-1范围

        # 确保所有 stop 位置在 0.0 到 1.0 之间
        stop0 = max(0.0, pos - 0.1)
        stop1 = max(0.0, pos - 0.015)
        stop2 = min(1.0, pos + 0.011)

        # 构建渐变样式
        gradient_style = f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {color1},
                stop:{stop0} {color1},
                stop:{stop1} {color2},
                stop:{pos} {color2},
                stop:{stop2} {color1},
                stop:1 {color1}
            );
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin: 2px;
        """
        self.label.setStyleSheet(gradient_style)


def with_alpha(color_hex, alpha):
    """将十六进制颜色转换为带透明度的RGBA字符串

    Args:
        color_hex: 十六进制颜色字符串，例如 "#FF0000"
        alpha: 透明度值 (0.0-1.0)

    Returns:
        rgba格式的颜色字符串，例如 "rgba(255, 0, 0, 0.5)"
    """
    try:
        if color_hex.startswith("#"):
            color_hex = color_hex.lstrip("#")
            # 假设原颜色为6位，不考虑alpha通道
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        else:
            return color_hex  # 非十六进制颜色保持不变（如预定义的rgba）
    except:
        return color_hex


# 状态消息配色方案（带60%透明度）
STATUS_COLORS = {
    "normal": (with_alpha(THEME["primary"], 0.6), with_alpha(THEME["info"], 0.6)),
    "success": (with_alpha(THEME["secondary"], 0.6), with_alpha(THEME["success"], 0.6)),
    "error": (with_alpha(THEME["primary"], 0.6), with_alpha(THEME["error"], 0.6)),
    "warning": (with_alpha(THEME["secondary"], 0.6), with_alpha(THEME["warning"], 0.6)),
}
