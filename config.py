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
APP_TITLE = "粘贴板图像自动缩放器"

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
    "warning": "#FFEA00",
    "error": "#FF5252",
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
        "size": 12,
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

# ---------------------- 按钮样式 ----------------------

# 主按钮样式 - 带光泽感和悬停动画
PRIMARY_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {THEME["primary"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        min-height: 30px;
        min-width: 80px;
        outline: none;
    }}
    QPushButton:hover {{
        background-color: {THEME["primary_light"]};
        transition: background-color 0.2s;
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
        font-weight: bold;
        min-height: 30px;
        min-width: 80px;
        outline: none;
    }}
    QPushButton:hover {{
        background-color: {THEME["secondary_light"]};
        transition: background-color 0.2s;
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

# 带动画的输入框样式
INPUT_STYLE = f"""
    QLineEdit {{
        border: 2px solid {THEME["border"]};
        border-radius: 5px;
        padding: 6px 8px;
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        selection-background-color: {THEME["primary_light"]};
        selection-color: white;
        transition: border 0.3s ease;
    }}
    QLineEdit:hover {{
        border: 2px solid {THEME["primary_light"]};
    }}
    QLineEdit:focus {{
        border: 2px solid {THEME["primary"]};
        background-color: {THEME["background"]};
    }}
"""

# ---------------------- 组件样式 ----------------------

# 组框样式 - 半透明毛玻璃效果
GROUP_BOX_STYLE = f"""
    QGroupBox {{ 
        background-color: {THEME["blur_background"]};
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        margin-top: 20px;
        padding: 15px 10px 10px 10px;
        font-weight: bold;
        color: {THEME["text"]};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        top: 10px;
        padding: 0 5px;
        background-color: {THEME["background"]};  # 使用不透明背景
        color: {THEME["text"]};
    }}

    /* 添加这一块来处理GroupBox内的标签 */
    QGroupBox QLabel {{
        background-color: transparent;
    }}
"""

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
        image: none;
        width: 18px;
        height: 18px;
        background-color: {THEME["primary"]};
        clip-path: polygon(50% 75%, 25% 25%, 75% 25%);
    }}
    QComboBox QAbstractItemView {{
        border: 1px solid {THEME["border"]};
        border-radius: 5px;
        selection-background-color: {THEME["primary"]};
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
    }}
"""

# 复选框样式 - 动画效果
# 修改复选框样式 - 使用Qt原生渲染方式
CHECK_BOX_STYLE = f"""
    QCheckBox {{
        spacing: 8px;
        color: {THEME["text"]};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {THEME["border"]};
        border-radius: 4px;
        background: {THEME["card_background"]};
    }}

    QCheckBox::indicator:checked {{
        background-color: {THEME["primary"]};
        border-color: {THEME["primary_dark"]};
        /* 让Qt使用默认对钩 */
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
# 注意：流动效果需要在代码中使用QTimer来实现
STATUS_BAR_STYLE = f"""
    QLabel#StatusLabel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                     stop:0 {THEME["primary_dark"]}, 
                     stop:0.3 {THEME["primary"]},
                     stop:0.6 {THEME["primary"]}, 
                     stop:1 {THEME["secondary_dark"]});
        color: white;
        padding: 8px 12px;
        border-radius: 5px;
        font-weight: bold;
        margin: 2px;
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
        background-color: {THEME["blur_background"]};  # 使用半透明背景
        border: 1px solid {THEME["border"]};
        border-radius: 8px;
        padding: 2px;
    }}
"""

# 信息标签样式
# 检查并确保信息标签没有背景色
INFO_LABEL_STYLE = f"""
    QLabel {{
        color: {THEME["text_light"]};
        background-color: transparent;  # 确保这里是透明的
        padding: 4px;
        font-size: 9pt;
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

# 主应用程序样式
APP_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {THEME["background"]};
        color: {THEME["text"]};
    }}

    /* 加强QLabel透明度设置 */
    QLabel {{
        color: {THEME["text"]};
        background-color: transparent !important;  /* 添加!important强制优先级 */
    }}
    QSplitter::handle {{
        background-color: {THEME["border"]};
    }}
    QToolTip {{
        background-color: {THEME["card_background"]};
        color: {THEME["text"]};
        border: 1px solid {THEME["primary"]};
        padding: 5px;
        border-radius: 4px;
    }}

    /* 添加其他组件样式引用 */
    {SCROLLBAR_STYLE}
"""


# ---------------------- 状态动画类 ----------------------

class StatusAnimator:
    """状态栏动画控制器"""

    def __init__(self, status_label):
        self.label = status_label
        self.timer = QTimer()
        self.gradientPos = 0.0
        self.active = False
        self.direction = 1  # 1 = 向右, -1 = 向左
        self.timer.timeout.connect(self.update_gradient)

    def start(self, message, color_start=None, color_end=None):
        """开始动画"""
        if not color_start:
            color_start = THEME["info"]
        if not color_end:
            color_end = THEME["primary"]

        self.label.setText(message)
        self.active = True
        self.gradientPos = 0.0
        self.direction = 1
        self.update_colors(color_start, color_end)
        if not self.timer.isActive():
            self.timer.start(50)  # 每50ms更新一次

    def stop(self):
        """停止动画"""
        if self.timer.isActive():
            self.timer.stop()
        self.active = False
        # 重置为透明背景
        self.label.setStyleSheet(f"""
            background-color: transparent;
            color: {THEME["text"]};
            padding: 8px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin: 2px;
        """)

    def update_colors(self, color_start, color_end):
        """更新颜色"""
        self.color_start = color_start
        self.color_end = color_end

    def update_gradient(self):
        """更新渐变位置"""
        if not self.active:
            return

        # 更新位置
        self.gradientPos += 0.02 * self.direction
        if self.gradientPos >= 1.0:
            self.direction = -1
        elif self.gradientPos <= 0.0:
            self.direction = 1

        # 设置新的渐变
        stop1 = max(0.0, self.gradientPos - 0.3)
        stop2 = self.gradientPos
        stop3 = min(1.0, self.gradientPos + 0.3)

        self.label.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:{stop1} {self.color_start}, 
                        stop:{stop2} {self.color_end}, 
                        stop:{stop3} {self.color_start});
            color: white;
            padding: 8px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin: 2px;
        """)


# 状态消息配色方案
STATUS_COLORS = {
    "normal": (THEME["info"], THEME["primary"]),
    "success": (THEME["success"], THEME["secondary"]),
    "error": (THEME["error"], THEME["primary"]),
    "warning": (THEME["warning"], THEME["secondary"]),
}