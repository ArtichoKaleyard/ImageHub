import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QCheckBox, QGroupBox, QFrame,
                             QMessageBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QPalette

import cv2
import numpy as np

from ClipboardImageScaler.clipboard_image_scaler_core import ClipboardImageScalerCore
from config.config import (THEME, APP_STYLE, ANIMATION_SPEED, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
                           INPUT_STYLE, GROUP_BOX_STYLE, COMBO_BOX_STYLE, CHECK_BOX_STYLE,
                           STATUS_BAR_STYLE, IMAGE_LABEL_STYLE, INFO_LABEL_STYLE, LABEL_STYLE,
                           STATUS_FRAME_STYLE, StatusAnimator, STATUS_COLORS)


class ClipboardImageScalerGUI(QWidget):
    def __init__(self):
        """初始化图像缩放器GUI"""
        super().__init__()

        # 主窗口属性
        self.setWindowTitle("粘贴板图像自动缩放器")
        self.setGeometry(100, 100, 900, 500)
        self.setStyleSheet(APP_STYLE)

        # 初始化核心逻辑类
        self.core = ClipboardImageScalerCore()

        # 连接信号到槽
        self.connect_signals()

        # 设置是否启用调整功能
        self.adjust_larger_check = None

        # 状态属性
        self.status_message = "就绪"

        # 存储历史图像及其面积和尺寸
        self.last_original_image = None
        self.last_scaled_image = None
        self.original_area = 0
        self.scaled_area = 0
        self.original_dimensions = (0, 0)  # 存储原始图像的宽高
        self.scaled_dimensions = (0, 0)  # 存储缩放后图像的宽高

        # 动画状态
        self.animating = False
        self.animations = []

        # 初始化UI
        self.init_ui()

        # 设置字体
        self.set_fonts()

        # 应用动画效果
        self.setup_animations()

        # 在所有初始化完成后，强制所有标签背景透明
        self.force_transparent_labels()

    def connect_signals(self):
        """连接核心类的信号到GUI槽函数"""
        self.core.status_signal.connect(self.on_status_update)
        self.core.error_signal.connect(self.on_error)
        self.core.original_image_signal.connect(self.on_original_image)
        self.core.original_info_signal.connect(self.on_original_info)
        self.core.scaled_image_signal.connect(self.on_scaled_image)
        self.core.scaled_info_signal.connect(self.on_scaled_info)

    # 新添加的槽函数
    @pyqtSlot(str)
    def on_status_update(self, message):
        self.status_label.setText(message)

    @pyqtSlot(str)
    def on_error(self, error_message):
        QMessageBox.critical(self, "错误", error_message)
        self.status_animator.start(f"错误: {error_message}", *STATUS_COLORS["error"])

    @pyqtSlot(object)
    def on_original_image(self, image):
        if image is not None:
            self.last_original_image = image.copy()
            height, width = image.shape[:2]
            self.original_dimensions = (width, height)
            self.original_area = width * height
            # 重新绘制两张图片，以保证比例关系正确
            self.redraw_preview_images()

    @pyqtSlot(str)
    def on_original_info(self, info):
        self.original_info_label.setText(f"原始尺寸: {info}")

    @pyqtSlot(object)
    def on_scaled_image(self, image):
        if image is not None:
            self.last_scaled_image = image.copy()
            height, width = image.shape[:2]
            self.scaled_dimensions = (width, height)
            self.scaled_area = width * height
            # 重新绘制两张图片，以保证比例关系正确
            self.redraw_preview_images()
            self.copy_btn.setEnabled(True)
            # 显示成功状态
            self.status_animator.start("图像已成功调整", *STATUS_COLORS["success"])
        else:
            self.scaled_image_label.clear()
            self.copy_btn.setEnabled(False)

    @pyqtSlot(str)
    def on_scaled_info(self, info):
        self.scaled_info_label.setText(f"调整后尺寸: {info}")

    def force_transparent_labels(self):
        """确保所有标签背景透明"""
        for label in self.findChildren(QLabel):
            # 检查当前样式表是否包含背景色设置
            current_style = label.styleSheet()
            # 确保背景透明
            if "background-color" not in current_style:
                label.setStyleSheet(current_style + "background-color: transparent;")

    def set_fonts(self):
        """设置应用程序字体"""
        # 使用配置中的字体样式，而不是硬编码字体
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)

        # 为所有组框设置标题字体
        for group_box in self.findChildren(QGroupBox):
            group_box.setFont(title_font)

    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)  # 直接设置到 self（即 QWidget）
        main_layout.setSpacing(12)  # 增加组件间距

        # ---- 设置区域 ----
        settings_group = QGroupBox("设置")
        settings_group.setStyleSheet(GROUP_BOX_STYLE)
        settings_layout = QHBoxLayout(settings_group)

        # 目标尺寸设置
        target_group = QGroupBox("目标尺寸")
        target_group.setStyleSheet(GROUP_BOX_STYLE)
        target_layout = QVBoxLayout(target_group)

        width_layout = QHBoxLayout()
        width_label = QLabel("宽 度:")
        width_label.setStyleSheet(LABEL_STYLE)
        width_layout.addWidget(width_label)
        self.width_edit = QLineEdit(str(self.core.target_width))
        self.width_edit.setStyleSheet(INPUT_STYLE)
        width_layout.addWidget(self.width_edit)
        target_layout.addLayout(width_layout)

        height_layout = QHBoxLayout()
        height_label = QLabel("高 度:")
        height_label.setStyleSheet(LABEL_STYLE)
        height_layout.addWidget(height_label)
        self.height_edit = QLineEdit(str(self.core.target_height))
        self.height_edit.setStyleSheet(INPUT_STYLE)
        height_layout.addWidget(self.height_edit)
        target_layout.addLayout(height_layout)

        self.adjust_larger_check = QCheckBox("当原始尺寸超过1080p时临时调整到1440p")
        self.adjust_larger_check.setChecked(self.core.auto_adjust_larger_size)
        self.adjust_larger_check.setEnabled(self.core.target_height == 1080)
        self.adjust_larger_check.stateChanged.connect(self.on_auto_adjust_changed)
        self.adjust_larger_check.setStyleSheet(CHECK_BOX_STYLE)
        target_layout.addWidget(self.adjust_larger_check)

        self.apply_size_btn = QPushButton("应 用 尺 寸")
        self.apply_size_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.apply_size_btn.clicked.connect(self.apply_target_size)
        target_layout.addWidget(self.apply_size_btn)

        settings_layout.addWidget(target_group)

        # 选项设置
        options_group = QGroupBox("选项")
        options_group.setStyleSheet(GROUP_BOX_STYLE)
        options_layout = QVBoxLayout(options_group)

        tolerance_layout = QHBoxLayout()
        tolerance_label = QLabel("纵 横 比 容 差 (0.0-1.0):")
        tolerance_label.setStyleSheet(LABEL_STYLE)
        tolerance_layout.addWidget(tolerance_label)
        self.tolerance_edit = QLineEdit(str(self.core.tolerance))
        self.tolerance_edit.setStyleSheet(INPUT_STYLE)
        tolerance_layout.addWidget(self.tolerance_edit)
        options_layout.addLayout(tolerance_layout)

        algorithm_layout = QHBoxLayout()
        algorithm_label = QLabel("缩 放 算 法:")
        algorithm_label.setStyleSheet(LABEL_STYLE)
        algorithm_layout.addWidget(algorithm_label)
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.algorithm_combo.addItems(["最近邻", "双线性", "双三次", "Lanczos"])
        self.algorithm_combo.setCurrentText("Lanczos")
        algorithm_layout.addWidget(self.algorithm_combo)
        options_layout.addLayout(algorithm_layout)

        self.auto_copy_check = QCheckBox("自动将调整后的图像复制回粘贴板")
        self.auto_copy_check.setChecked(self.core.auto_copy_back)
        self.auto_copy_check.setStyleSheet(CHECK_BOX_STYLE)
        options_layout.addWidget(self.auto_copy_check)

        self.apply_options_btn = QPushButton("应 用 选 项")
        self.apply_options_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.apply_options_btn.clicked.connect(self.apply_options)
        options_layout.addWidget(self.apply_options_btn)

        settings_layout.addWidget(options_group)
        main_layout.addWidget(settings_group)

        # ---- 控制行区域 ----
        control_group = QGroupBox("操作控制")
        control_group.setStyleSheet(GROUP_BOX_STYLE)
        control_layout = QHBoxLayout(control_group)
        control_layout.setContentsMargins(4, 12, 4, 8)

        # 状态容器，添加ID属性以便样式表识别
        self.status_frame = QFrame()
        self.status_frame.setObjectName("StatusFrame")
        self.status_frame.setStyleSheet(STATUS_FRAME_STYLE)
        self.status_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        status_layout = QHBoxLayout(self.status_frame)
        self.status_label = QLabel("就 绪")
        self.status_label.setObjectName("StatusLabel")  # 添加ID以便样式表识别
        self.status_label.setStyleSheet(STATUS_BAR_STYLE)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        control_layout.addWidget(self.status_frame, stretch=1)

        # 创建状态动画控制器
        self.status_animator = StatusAnimator(self.status_label)

        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.start_btn = QPushButton("开 始 监 控")
        self.stop_btn = QPushButton("停 止 监 控")
        self.copy_btn = QPushButton("复 制 到 粘 贴 板")

        for btn in [self.start_btn, self.stop_btn, self.copy_btn]:
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(80)
            btn.setMinimumHeight(35)  # 增加按钮高度
            button_layout.addWidget(btn)

        self.start_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.stop_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.copy_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)

        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.copy_btn.clicked.connect(self.core.copy_to_clipboard)
        self.stop_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        control_layout.addWidget(button_container, stretch=1)
        main_layout.addWidget(control_group)

        # ---- 图像预览区域 ----
        preview_group = QGroupBox("图像预览")
        preview_group.setStyleSheet(GROUP_BOX_STYLE)
        preview_layout = QVBoxLayout(preview_group)

        # 使用 QHBoxLayout
        self.image_layout = QHBoxLayout()

        # 原始图像部分
        self.original_group = QGroupBox("原始图像")
        self.original_group.setStyleSheet(GROUP_BOX_STYLE)
        original_layout = QVBoxLayout(self.original_group)
        self.original_image_label = QLabel()
        self.original_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_image_label.setMinimumSize(300, 200)
        self.original_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original_image_label.setFrameStyle(QFrame.Shape.StyledPanel)
        self.original_image_label.setScaledContents(False)
        self.original_image_label.setStyleSheet(IMAGE_LABEL_STYLE)
        original_layout.addWidget(self.original_image_label)

        # 原始图像信息标签
        self.original_info_label = QLabel("原始尺寸: -")
        self.original_info_label.setStyleSheet(INFO_LABEL_STYLE)
        original_layout.addWidget(self.original_info_label)
        self.image_layout.addWidget(self.original_group)

        # 缩放图像部分
        self.scaled_group = QGroupBox("调整后图像")
        self.scaled_group.setStyleSheet(GROUP_BOX_STYLE)
        scaled_layout = QVBoxLayout(self.scaled_group)
        self.scaled_image_label = QLabel()
        self.scaled_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scaled_image_label.setMinimumSize(300, 200)
        self.scaled_image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.scaled_image_label.setFrameStyle(QFrame.Shape.StyledPanel)
        self.scaled_image_label.setScaledContents(False)
        self.scaled_image_label.setStyleSheet(IMAGE_LABEL_STYLE)
        scaled_layout.addWidget(self.scaled_image_label)

        # 缩放图像信息标签
        self.scaled_info_label = QLabel("调整后尺寸: -")
        self.scaled_info_label.setStyleSheet(INFO_LABEL_STYLE)
        scaled_layout.addWidget(self.scaled_info_label)
        self.image_layout.addWidget(self.scaled_group)

        preview_layout.addLayout(self.image_layout)
        main_layout.addWidget(preview_group)

    def setup_animations(self):
        """设置UI元素的动画效果"""
        # 保存所有可以动画的组件
        self.animatable_components = [
            self.original_group,
            self.scaled_group,
            self.status_frame
        ]

        # 动画预备位置 - 隐藏所有组件
        for component in self.animatable_components:
            component.setGraphicsEffect(None)  # 清除任何已有效果

        # 创建入场动画
        QTimer.singleShot(100, self.start_entrance_animations)

    def start_entrance_animations(self):
        """开始入场动画"""
        delay = 0

        # 逐个组件的入场动画
        for i, component in enumerate(self.animatable_components):
            rect = component.geometry()

            # 创建属性动画
            anim = QPropertyAnimation(component, b"geometry")
            anim.setDuration(ANIMATION_SPEED["normal"])
            anim.setStartValue(QRect(rect.x(), rect.y() - 20, rect.width(), 0))
            anim.setEndValue(rect)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            # 延迟启动
            QTimer.singleShot(delay, anim.start)
            self.animations.append(anim)  # 保存动画引用

            delay += ANIMATION_SPEED["fast"]  # 增加延迟时间

    def apply_target_size(self):
        """应用目标尺寸设置"""
        try:
            width = int(self.width_edit.text())
            height = int(self.height_edit.text())
            if self.core.set_target_size(width, height):
                self.core.set_auto_adjust_larger_size(self.adjust_larger_check.isChecked())
                self.update_status(f"目标尺寸已更新为 {width}x{height}")
                # 触发成功状态颜色
                self.status_animator.start(f"目标尺寸已更新为 {width}x{height}", *STATUS_COLORS["success"])
            self.update_adjust_checkbox_state()
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的数字")
            # 触发错误状态颜色
            self.status_animator.start("输入错误: 请输入有效的数字", *STATUS_COLORS["error"])

    def update_adjust_checkbox_state(self):
        """根据目标高度更新复选框状态"""
        target_height = self.core.target_height
        self.adjust_larger_check.setEnabled(target_height == 1080)

    def on_auto_adjust_changed(self, state):
        """自动调整复选框状态变更处理"""
        enabled = (state == Qt.CheckState.Checked)
        self.core.set_auto_adjust_larger_size(enabled)

    def apply_options(self):
        """应用选项设置"""
        try:
            tolerance = float(self.tolerance_edit.text())
            if not self.core.set_tolerance(tolerance):
                QMessageBox.critical(self, "错误", "容差值必须在0和1之间")
                self.status_animator.start("错误: 容差值必须在0和1之间", *STATUS_COLORS["error"])
                return

            algorithm = self.algorithm_combo.currentText()
            self.core.set_resize_method(algorithm)

            auto_copy = self.auto_copy_check.isChecked()
            self.core.set_auto_copy(auto_copy)

            self.status_animator.start("选项已应用", *STATUS_COLORS["success"])
        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的数字")
            self.status_animator.start("输入错误: 请输入有效的数字", *STATUS_COLORS["error"])

    def start_monitoring(self):
        """开始监控粘贴板"""
        if self.core.start():  # 直接调用核心类的start()方法
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_animator.start("正在监控粘贴板...", *STATUS_COLORS["normal"])

    def stop_monitoring(self):
        """停止监控粘贴板"""
        if self.core.stop():  # 直接调用核心类的stop()方法
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_animator.set_static_color("监控已停止", THEME["warning"])

    def update_status(self, message):
        """更新状态消息"""
        self.status_message = message
        self.status_label.setText(message)

    @pyqtSlot(str, object)
    def update_ui(self, update_type, data):
        """核心类的回调函数，用于更新UI"""
        if update_type == "status":
            self.status_label.setText(data)
        elif update_type == "error":
            QMessageBox.critical(self, "错误", data)
            self.status_animator.start(f"错误: {data}", *STATUS_COLORS["error"])
        elif update_type == "original_image":
            if data is not None:
                self.last_original_image = data.copy()
                height, width = data.shape[:2]
                self.original_dimensions = (width, height)
                self.original_area = width * height
                # 重新绘制两张图片，以保证比例关系正确
                self.redraw_preview_images()
        elif update_type == "original_info":
            self.original_info_label.setText(f"原始尺寸: {data}")
        elif update_type == "scaled_image":
            if data is not None:
                self.last_scaled_image = data.copy()
                height, width = data.shape[:2]
                self.scaled_dimensions = (width, height)
                self.scaled_area = width * height
                # 重新绘制两张图片，以保证比例关系正确
                self.redraw_preview_images()
                self.copy_btn.setEnabled(True)
                # 显示成功状态
                self.status_animator.start("图像已成功调整", *STATUS_COLORS["success"])
            else:
                self.scaled_image_label.clear()
                self.copy_btn.setEnabled(False)
        elif update_type == "scaled_info":
            self.scaled_info_label.setText(f"调整后尺寸: {data}")

    def redraw_preview_images(self):
        """重新绘制预览图像，确保比例正确"""
        if self.last_original_image is not None and self.last_scaled_image is not None:
            # 计算真实的尺寸比例
            org_w, org_h = self.original_dimensions
            scl_w, scl_h = self.scaled_dimensions

            # 计算缩放比例，基于两者的实际尺寸比例
            # 使用面积比来计算显示大小比例
            area_ratio = self.scaled_area / self.original_area if self.original_area > 0 else 1.0

            # 基于面积比例和可用空间，确定合适的显示比例
            if area_ratio < 1.0:  # 缩放后图像更小
                orig_size_ratio = 1.0
                scal_size_ratio = np.sqrt(area_ratio)
            else:  # 缩放后图像更大
                orig_size_ratio = 1.0 / np.sqrt(area_ratio)
                scal_size_ratio = 1.0

            # 确保无论自动调整是否触发，都保持比例正确
            self.update_image_preview(
                self.original_image_label,
                self.last_original_image,
                size_ratio=orig_size_ratio,
                force_redraw=True
            )

            # 立即更新缩放后的图像，并设置动画状态
            self.update_image_preview(
                self.scaled_image_label,
                self.last_scaled_image,
                size_ratio=scal_size_ratio,
                force_redraw=True
            )

    def complete_image_update(self, label, cv_image, size_ratio=1.0, force_redraw=False):
        """完成图像更新，同时结束动画状态"""
        self.update_image_preview(label, cv_image, size_ratio, force_redraw)
        self.animating = False

    def update_image_preview(self, label, cv_image, size_ratio=1.0, force_redraw=False):
        """更新图像预览标签，显示OpenCV图像

        Args:
            label: 要更新的QLabel
            cv_image: OpenCV格式的图像
            size_ratio: 显示大小的比例系数，用于差异化显示
            force_redraw: 是否强制重绘
        """
        if cv_image is None:
            label.clear()
            return

        height, width = cv_image.shape[:2]
        label_width = label.width()
        label_height = label.height()

        if label_width <= 0 or label_height <= 0:
            label_width = max(label_width, 300)
            label_height = max(label_height, 200)

        # 计算基础缩放比例，留出10%的边距
        safe_label_width = label_width * 0.9
        safe_label_height = label_height * 0.9
        width_ratio = safe_label_width / width
        height_ratio = safe_label_height / height
        base_scale_ratio = min(width_ratio, height_ratio)

        # 应用自定义大小比例，但要确保不会超出容器
        scale_ratio = base_scale_ratio * size_ratio

        # 再次检查是否会超出容器边界
        display_width = int(width * scale_ratio)
        display_height = int(height * scale_ratio)

        # 如果调整后的尺寸超出了安全区域，需要重新调整
        if display_width > safe_label_width or display_height > safe_label_height:
            # 重新计算比例
            new_width_ratio = safe_label_width / display_width
            new_height_ratio = safe_label_height / display_height
            adjustment_factor = min(new_width_ratio, new_height_ratio)
            display_width = int(display_width * adjustment_factor)
            display_height = int(display_height * adjustment_factor)

        # 确保尺寸至少为1
        display_width = max(1, display_width)
        display_height = max(1, display_height)

        # 调整图像尺寸
        display_image = cv2.resize(cv_image, (display_width, display_height),
                                   interpolation=cv2.INTER_AREA)

        # 转换为Qt图像格式
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # 更新标签
        pixmap = QPixmap.fromImage(qt_image)
        label.setPixmap(pixmap)

    def resizeEvent(self, event):
        """窗口大小改变时重绘图像"""
        super().resizeEvent(event)
        # 延迟重绘以提高响应性
        QTimer.singleShot(ANIMATION_SPEED["fast"], self.redraw_preview_images)


# 在应用程序初始化代码中添加全局调色板设置
def apply_global_palette():
    """应用全局调色板设置，确保复选框等控件正确显示"""
    palette = QApplication.palette()
    # 设置关键调色板角色
    palette.setColor(QPalette.ColorRole.WindowText, QColor(THEME["text"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))  # 对钩的颜色
    palette.setColor(QPalette.ColorRole.Highlight, QColor(THEME["primary"]))  # 选中背景色

    # 确保对钩正确显示
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))  # 对钩颜色

    # 设置复选框文本颜色
    palette.setColor(QPalette.ColorRole.Text, QColor(THEME["text"]))

    # 应用调色板
    QApplication.setPalette(palette)


# 在main函数中调用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_global_palette()  # 必须在窗口创建前调用
    QApplication.setStyle("Fusion")  # 使用Fusion样式引擎以确保跨平台一致性
    window = ClipboardImageScalerGUI()
    window.show()
    sys.exit(app.exec())