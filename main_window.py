# main_window.py

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout

from ClipboardImageScaler.clipboard_image_scaler_gui import ClipboardImageScalerGUI
from AutoRename.auto_rename_gui import ImageRenamerGUI
from ImageProcessingValidator.verify_image_gui import ImageVerifierGUI
from config.style_config import APP_STYLE, Q_TAB_WIDGET_STYLE
from config.style_interface import get_style

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图像处理工具集")
        self.setGeometry(200, 200, get_style('WINDOW_WIDTH'), get_style('WINDOW_HEIGHT'))   #ignore
        self.setStyleSheet(APP_STYLE)

        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 标签页控件
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(Q_TAB_WIDGET_STYLE)  # 应用自定义样式
        tab_widget.setDocumentMode(False)              # 禁用文档模式
        tab_widget.setTabsClosable(False)             # 禁用关闭按钮

        # 添加图像缩放器标签页
        tab_widget.addTab(ClipboardImageScalerGUI(), "图像缩放工具")
        tab_widget.addTab(ImageRenamerGUI(), "图片重命名工具")
        tab_widget.addTab(ImageVerifierGUI(), "图片验证工具")

        # 布局设置
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # 去除主布局边距
        layout.addWidget(tab_widget)

        # 可选：设置标签位置与形状
        tab_widget.setTabPosition(QTabWidget.TabPosition.North)  # 标签在顶部
        tab_widget.setTabShape(QTabWidget.TabShape.Rounded)       # 圆角标签

