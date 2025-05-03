"""
示例：如何使用样式声明文件来应用样式
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QGroupBox, QLabel, QHBoxLayout, QComboBox, QCheckBox,
    QTabWidget, QSpinBox, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt

# 导入样式声明文件
from style_interface import get_style, get_theme, StatusAnimator, STATUS_COLORS


class StyleDemoWindow(QMainWindow):
    """样式演示窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("现代化样式演示")
        self.resize(800, 600)

        # 应用全局样式
        self.setStyleSheet(get_style('APP_STYLE'))

        # 创建主部件
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # 创建标签页小部件
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(get_style('Q_TAB_WIDGET_STYLE'))

        # 添加 "按钮" 标签页
        button_tab = QWidget()
        button_layout = QVBoxLayout(button_tab)

        # 主按钮
        primary_btn = QPushButton("主按钮")
        primary_btn.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        primary_btn.clicked.connect(lambda: self.show_status("点击了主按钮", "normal"))

        # 次要按钮
        secondary_btn = QPushButton("次要按钮")
        secondary_btn.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        secondary_btn.clicked.connect(lambda: self.show_status("点击了次要按钮", "success"))

        # 添加按钮到布局
        button_layout.addWidget(primary_btn)
        button_layout.addWidget(secondary_btn)
        button_layout.addStretch()

        # 添加 "输入框" 标签页
        input_tab = QWidget()
        input_layout = QVBoxLayout(input_tab)

        # 文本输入框
        text_input = QLineEdit()
        text_input.setPlaceholderText("请输入文本...")
        text_input.setStyleSheet(get_style('INPUT_STYLE'))

        # 数字输入框
        number_input = QSpinBox()
        number_input.setRange(0, 100)
        number_input.setValue(50)
        number_input.setStyleSheet(get_style('INPUT_STYLE'))

        # 添加输入框到布局
        input_layout.addWidget(QLabel("文本输入框:"))
        input_layout.addWidget(text_input)
        input_layout.addWidget(QLabel("数字输入框:"))
        input_layout.addWidget(number_input)
        input_layout.addStretch()

        # 添加 "组件" 标签页
        components_tab = QWidget()
        components_layout = QVBoxLayout(components_tab)

        # 组框
        group_box = QGroupBox("分组框")
        group_box.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        group_box_layout = QVBoxLayout(group_box)

        # 下拉菜单
        combo = QComboBox()
        combo.addItems(["选项1", "选项2", "选项3"])
        combo.setStyleSheet(get_style('COMBO_BOX_STYLE'))

        # 复选框
        checkbox = QCheckBox("启用选项")
        checkbox.setStyleSheet(get_style('CHECK_BOX_STYLE'))

        # 添加组件到组框
        group_box_layout.addWidget(combo)
        group_box_layout.addWidget(checkbox)

        # 信息标签
        info_label = QLabel("这是一个信息标签，使用较小的字体")
        info_label.setStyleSheet(get_style('INFO_LABEL_STYLE'))

        # 文本编辑器（继承全局样式）
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("这是一个文本编辑区域...")

        # 添加组件到布局
        components_layout.addWidget(group_box)
        components_layout.addWidget(info_label)
        components_layout.addWidget(text_edit)

        # 将标签页添加到标签页小部件
        tab_widget.addTab(button_tab, "按钮")
        tab_widget.addTab(input_tab, "输入框")
        tab_widget.addTab(components_tab, "组件")

        # 添加标签页到主布局
        main_layout.addWidget(tab_widget)

        # 创建状态栏
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_frame.setStyleSheet(get_style('STATUS_FRAME_STYLE'))
        status_layout = QHBoxLayout(status_frame)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setStyleSheet(get_style('STATUS_BAR_STYLE'))

        status_layout.addWidget(self.status_label)
        status_layout.setContentsMargins(10, 5, 10, 5)

        main_layout.addWidget(status_frame)

        # 创建状态动画控制器
        self.status_animator = StatusAnimator(self.status_label)

        # 默认状态消息
        self.show_status("欢迎使用现代化样式演示", "normal")

    def show_status(self, message, status_type):
        """显示状态消息

        Args:
            message: 状态消息文本
            status_type: 状态类型，可以是 'normal', 'success', 'error', 'warning'
        """
        if status_type in STATUS_COLORS:
            color_start, color_end = STATUS_COLORS[status_type]
            self.status_animator.start(message, color_start, color_end)
        else:
            # 默认状态
            self.status_animator.start(
                message,
                get_theme('primary'),
                get_theme('secondary')
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StyleDemoWindow()
    window.show()
    sys.exit(app.exec())