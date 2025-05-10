"""
差分标注工具的视图层 - 处理界面呈现和用户交互
"""
import os
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSpinBox, QSizePolicy, QDoubleSpinBox,
                             QFileDialog, QTextEdit, QProgressBar, QComboBox, QSplitter,
                             QGroupBox, QScrollArea, QGridLayout, QFrame, QSlider)
from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QPixmap, QImage
from typing import Dict, Optional
import numpy as np

# 导入自定义日志记录器
from utils.logger import default_logger as logger

# 导入 Model 和 Controller
from DiffLabeler.diff_labeler_model import DiffLabelerModel
from DiffLabeler.diff_labeler_controller import DiffLabelerController, ProcessingWorker

# 导入样式接口
from style.style_interface import get_style, get_theme, LOG_LEVEL_COLORS, is_dark_mode, get_log_style


class ImagePreviewWidget(QWidget):
    """图像预览控件"""
    original_images: Dict[str, Optional[np.ndarray]]  # 类型提示

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_images = {
            "bg": None, "sample": None, "diff": None, "result": None
        }
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 主布局使用水平布局，固定比例3:7
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # 左侧面板：小图预览 (30%)
        left_panel = QWidget()
        left_panel.setMinimumWidth(200)  # 设置合理的最小宽度
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)  # 清除内部边距

        # 右侧面板：结果图 (70%)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)  # 清除内部边距

        # 创建预览标签
        self.preview_labels = {}
        titles = {"bg": "背景图", "sample": "样本图", "diff": "差异图"}

        for key, title in titles.items():
            group = QGroupBox(title)
            group.setMinimumSize(200, 150)  # 设置合理的最小尺寸
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel("无预览")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Ignored
            )
            label.setScaledContents(False)  # 关键：禁用自动缩放

            group_layout.addWidget(label)
            left_layout.addWidget(group)
            self.preview_labels[key] = label

        # 结果图
        result_group = QGroupBox("检测结果（放大）")
        result_group.setMinimumSize(400, 300)  # 设置合理的最小尺寸
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(0, 0, 0, 0)

        self.result_label = QLabel("无预览")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        self.result_label.setScaledContents(False)  # 关键：禁用自动缩放

        result_layout.addWidget(self.result_label)
        right_layout.addWidget(result_group)

        # 添加到主布局
        main_layout.addWidget(left_panel, stretch=3)
        main_layout.addWidget(right_panel, stretch=7)

    def resizeEvent(self, event):
        """窗口大小变化时重新缩放图像"""
        super().resizeEvent(event)
        self.rescale_images()

    def rescale_images(self):
        """根据当前控件尺寸重新缩放图像"""
        if not all(img is not None for img in self.original_images.values()):
            return

        # 获取各标签的可用绘制区域（减去边距）
        def get_available_size(label):
            return label.size() - QSize(10, 10)  # 减去少量边距

        # 更新预览图
        for key in ["bg", "sample", "diff"]:
            if self.original_images[key] is not None:
                label = self.preview_labels[key]
                available = get_available_size(label)

                qimg = self._convert_cv_to_qimage(self.original_images[key])
                scaled = QPixmap.fromImage(qimg).scaled(
                    available,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(scaled)

        # 更新结果图
        if self.original_images["result"] is not None:
            available = get_available_size(self.result_label)
            qimg = self._convert_cv_to_qimage(self.original_images["result"])
            scaled = QPixmap.fromImage(qimg).scaled(
                available,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.result_label.setPixmap(scaled)

    def _convert_cv_to_qimage(self, cv_img):
        """将OpenCV图像转换为QImage"""
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        return QImage(cv_img[..., ::-1].copy().data,
                      width, height, bytes_per_line,
                      QImage.Format.Format_RGB888)

    def update_preview(self, bg_img, sample_img, diff_img, result_img):
        """更新预览图像"""
        # 只存储原始图像数据
        self.original_images = {
            "bg": bg_img, "sample": sample_img,
            "diff": diff_img, "result": result_img
        }
        # 触发一次缩放
        self.rescale_images()


class ConfigPanel(QWidget):
    """配置面板"""

    # 定义信号
    directory_changed = pyqtSignal(str, str)  # 参数：目录类型，路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 目录配置部分
        dir_group = QGroupBox("目录配置")
        dir_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        dir_layout = QGridLayout(dir_group)

        # 背景图目录
        dir_layout.addWidget(QLabel("背景图目录:"), 0, 0)
        self.bg_dir_edit = QLineEdit()
        self.bg_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.bg_dir_edit, 0, 1)
        self.bg_dir_btn = QPushButton("浏览...")
        self.bg_dir_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.bg_dir_btn.clicked.connect(lambda: self.browse_directory("bg_dir"))
        dir_layout.addWidget(self.bg_dir_btn, 0, 2)

        # 样本图目录
        dir_layout.addWidget(QLabel("样本图目录:"), 1, 0)
        self.sample_dir_edit = QLineEdit()
        self.sample_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.sample_dir_edit, 1, 1)
        self.sample_dir_btn = QPushButton("浏览...")
        self.sample_dir_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.sample_dir_btn.clicked.connect(lambda: self.browse_directory("sample_dir"))
        dir_layout.addWidget(self.sample_dir_btn, 1, 2)

        # 输出目录
        dir_layout.addWidget(QLabel("输出目录:"), 2, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.output_dir_edit, 2, 1)
        self.output_dir_btn = QPushButton("浏览...")
        self.output_dir_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.output_dir_btn.clicked.connect(lambda: self.browse_directory("output_dir"))
        dir_layout.addWidget(self.output_dir_btn, 2, 2)

        layout.addWidget(dir_group)

        # 参数配置部分
        param_group = QGroupBox("参数配置")
        param_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        param_layout = QVBoxLayout(param_group)

        # 第一行：两个数字输入框并列
        row1 = QHBoxLayout()

        # 最小差异区域
        min_diff_area_layout = QVBoxLayout()
        min_diff_area_layout.addWidget(QLabel("最小差异区域"))
        self.min_diff_area_spin = QSpinBox()
        self.min_diff_area_spin.setRange(1, 10000)
        self.min_diff_area_spin.setValue(100)
        self.min_diff_area_spin.setToolTip("考虑为目标的最小面积 (像素)")
        self.min_diff_area_spin.setStyleSheet(get_style("INPUT_STYLE"))
        min_diff_area_layout.addWidget(self.min_diff_area_spin)
        row1.addLayout(min_diff_area_layout)

        # 默认标签ID
        default_label_layout = QVBoxLayout()
        default_label_layout.addWidget(QLabel("默认标签ID"))
        self.default_label_spin = QSpinBox()
        self.default_label_spin.setRange(0, 999)
        self.default_label_spin.setValue(0)
        self.default_label_spin.setToolTip("YOLO格式的标签ID")
        self.default_label_spin.setStyleSheet(get_style("INPUT_STYLE"))
        default_label_layout.addWidget(self.default_label_spin)
        row1.addLayout(default_label_layout)

        param_layout.addLayout(row1)

        # 差异检测阈值 (滑动条)
        diff_threshold_layout = QVBoxLayout()
        diff_threshold_layout.addWidget(QLabel("差异检测阈值"))
        slider_layout = QHBoxLayout()
        self.diff_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.diff_threshold_slider.setRange(1, 255)
        self.diff_threshold_slider.setValue(30)
        self.diff_threshold_slider.setTickInterval(10)
        self.diff_threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.diff_threshold_slider.setToolTip("检测差异的像素阈值 (1-255)")
        slider_layout.addWidget(self.diff_threshold_slider)
        self.diff_threshold_value = QLabel("30")
        self.diff_threshold_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.diff_threshold_value.setMinimumWidth(40)
        slider_layout.addWidget(self.diff_threshold_value)
        self.diff_threshold_slider.valueChanged.connect(lambda v: self.diff_threshold_value.setText(str(v)))
        diff_threshold_layout.addLayout(slider_layout)
        param_layout.addLayout(diff_threshold_layout)

        # 边界框填充 (滑动条)
        bbox_padding_layout = QVBoxLayout()
        bbox_padding_layout.addWidget(QLabel("边界框填充"))
        slider_layout = QHBoxLayout()
        self.bbox_padding_slider = QSlider(Qt.Orientation.Horizontal)
        self.bbox_padding_slider.setRange(0, 50)
        self.bbox_padding_slider.setValue(0)
        self.bbox_padding_slider.setTickInterval(5)
        self.bbox_padding_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bbox_padding_slider.setToolTip("边界框周围额外填充像素")
        slider_layout.addWidget(self.bbox_padding_slider)
        self.bbox_padding_value = QLabel("0")
        self.bbox_padding_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bbox_padding_value.setMinimumWidth(40)
        slider_layout.addWidget(self.bbox_padding_value)
        self.bbox_padding_slider.valueChanged.connect(lambda v: self.bbox_padding_value.setText(str(v)))
        bbox_padding_layout.addLayout(slider_layout)
        param_layout.addLayout(bbox_padding_layout)

        # 边界框合并阈值 (滑动条)
        min_merge_iou_layout = QVBoxLayout()
        min_merge_iou_layout.addWidget(QLabel("边界框合并阈值"))
        slider_layout = QHBoxLayout()
        self.min_merge_iou_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_merge_iou_slider.setRange(0, 100)  # 0-100对应0.0-1.0
        self.min_merge_iou_slider.setValue(30)  # 默认0.3
        self.min_merge_iou_slider.setTickInterval(5)
        self.min_merge_iou_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.min_merge_iou_slider.setToolTip("边界框合并的IoU阈值 (0-1)")
        slider_layout.addWidget(self.min_merge_iou_slider)
        self.min_merge_iou_value = QLabel("0.30")
        self.min_merge_iou_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.min_merge_iou_value.setMinimumWidth(40)
        slider_layout.addWidget(self.min_merge_iou_value)
        self.min_merge_iou_slider.valueChanged.connect(lambda v: self.min_merge_iou_value.setText(f"{v / 100:.2f}"))
        min_merge_iou_layout.addLayout(slider_layout)
        param_layout.addLayout(min_merge_iou_layout)

        layout.addWidget(param_group)

        # 配置文件操作部分
        config_group = QGroupBox("配置文件")
        config_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        config_layout = QHBoxLayout(config_group)

        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        config_layout.addWidget(self.save_config_btn)
        config_layout.addWidget(self.load_config_btn)

        layout.addWidget(config_group)

        # 添加弹性空间
        layout.addStretch()

    def browse_directory(self, dir_type):
        """浏览并选择目录"""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)

        # 获取当前路径作为初始目录
        current_path = ""
        if dir_type == "bg_dir":
            current_path = self.bg_dir_edit.text()
        elif dir_type == "sample_dir":
            current_path = self.sample_dir_edit.text()
        elif dir_type == "output_dir":
            current_path = self.output_dir_edit.text()

        if current_path and os.path.exists(current_path):
            dialog.setDirectory(current_path)

        if dialog.exec():
            selected_dir = dialog.selectedFiles()[0]

            # 更新对应的输入框
            if dir_type == "bg_dir":
                self.bg_dir_edit.setText(selected_dir)
            elif dir_type == "sample_dir":
                self.sample_dir_edit.setText(selected_dir)
            elif dir_type == "output_dir":
                self.output_dir_edit.setText(selected_dir)

            # 发出信号
            self.directory_changed.emit(dir_type, selected_dir)

    def get_config(self):
        """获取当前配置"""
        return {
            "bg_dir": self.bg_dir_edit.text(),
            "sample_dir": self.sample_dir_edit.text(),
            "output_dir": self.output_dir_edit.text(),
            "diff_threshold": self.diff_threshold_slider.value(),
            "min_diff_area": self.min_diff_area_spin.value(),
            "default_label": self.default_label_spin.value(),
            "bbox_padding": self.bbox_padding_slider.value(),
            "min_merge_iou": self.min_merge_iou_slider.value() / 100.0  # 转换为0.0-1.0
        }

    def update_config(self, config):
        """根据配置更新UI"""
        if "bg_dir" in config:
            self.bg_dir_edit.setText(config["bg_dir"])
        if "sample_dir" in config:
            self.sample_dir_edit.setText(config["sample_dir"])
        if "output_dir" in config:
            self.output_dir_edit.setText(config["output_dir"])
        if "diff_threshold" in config:
            self.diff_threshold_slider.setValue(config["diff_threshold"])
            self.diff_threshold_value.setText(str(config["diff_threshold"]))
        if "min_diff_area" in config:
            self.min_diff_area_spin.setValue(config["min_diff_area"])
        if "default_label" in config:
            self.default_label_spin.setValue(config["default_label"])
        if "bbox_padding" in config:
            self.bbox_padding_slider.setValue(config["bbox_padding"])
            self.bbox_padding_value.setText(str(config["bbox_padding"]))
        if "min_merge_iou" in config:
            iou_value = int(config["min_merge_iou"] * 100)
            self.min_merge_iou_slider.setValue(iou_value)
            self.min_merge_iou_value.setText(f"{config['min_merge_iou']:.2f}")


class PreviewPanel(QWidget):
    """预览面板"""

    # 定义信号
    preview_requested = pyqtSignal(str, str)  # 参数：背景图文件名，样本图文件名

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg_files = []
        self.sample_files = []
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 文件选择部分
        file_group = QGroupBox("文件选择")
        file_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        file_layout = QGridLayout(file_group)

        # 背景图选择
        file_layout.addWidget(QLabel("背景图:"), 0, 0)
        self.bg_combo = QComboBox()
        self.bg_combo.setMinimumWidth(250)
        self.bg_combo.setStyleSheet(get_style("COMBO_BOX_STYLE"))
        file_layout.addWidget(self.bg_combo, 0, 1)

        # 样本图选择
        file_layout.addWidget(QLabel("样本图:"), 1, 0)
        self.sample_combo = QComboBox()
        self.sample_combo.setMinimumWidth(250)
        self.sample_combo.setStyleSheet(get_style("COMBO_BOX_STYLE"))
        file_layout.addWidget(self.sample_combo, 1, 1)
        self.sample_combo.currentIndexChanged.connect(self.sample_changed)

        # 预览按钮
        self.preview_btn = QPushButton("生成预览")
        self.preview_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.preview_btn.clicked.connect(self.request_preview)
        file_layout.addWidget(self.preview_btn, 1, 2)

        layout.addWidget(file_group)

        # 使用QSplitter来更好地管理空间分配
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 预览显示部分
        self.preview_widget = ImagePreviewWidget()
        splitter.addWidget(self.preview_widget)

        # 添加一个空的占位widget来限制文件选择部分的高度
        placeholder = QWidget()
        placeholder.setMaximumHeight(0)
        splitter.addWidget(placeholder)

        # 设置splitter的拉伸因子，使预览widget获得所有额外空间
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        # 设置splitter手柄不可见，因为我们已经固定了文件选择部分的高度
        splitter.setHandleWidth(0)

        layout.addWidget(splitter, stretch=1)  # 关键：设置拉伸因子为1

    def update_bg_files(self, dir_path):
        """更新背景图文件列表"""
        self.bg_files = []
        self.bg_combo.clear()

        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    self.bg_files.append(file)

            self.bg_files.sort()
            self.bg_combo.addItems(self.bg_files)

    def update_sample_files(self, dir_path):
        """更新样本图文件列表"""
        self.sample_files = []
        self.sample_combo.clear()

        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    self.sample_files.append(file)

            self.sample_files.sort()
            self.sample_combo.addItems(self.sample_files)

    def request_preview(self):
        """请求生成预览"""
        if not self.bg_files or not self.sample_files:
            logger.warning("没有可用的背景图或样本图")
            return

        bg_file = self.bg_combo.currentText()
        sample_file = self.sample_combo.currentText()

        if bg_file and sample_file:
            self.preview_requested.emit(bg_file, sample_file)

    def sample_changed(self, index):
        """样本图变更时尝试自动匹配背景图并预览"""
        if index < 0 or not self.bg_files or not self.sample_files:
            return

        sample_file = self.sample_combo.currentText()
        if not sample_file:
            return

        # 尝试从样本文件名中提取基本名称
        base_name = self.extract_base_name(sample_file)
        logger.debug(f"样本 {sample_file} 的基本名称: {base_name}")

        # 尝试匹配背景图
        matched_index = -1
        for i, bg_file in enumerate(self.bg_files):
            bg_base = self.extract_base_name(bg_file)
            # 完全匹配
            if bg_base == base_name:
                matched_index = i
                logger.debug(f"找到完全匹配的背景图: {bg_file}")
                break
            # 部分匹配
            elif bg_base in base_name or base_name in bg_base:
                matched_index = i
                logger.debug(f"找到部分匹配的背景图: {bg_file}")
                break

        # 如果找到匹配的背景图，自动选择并预览
        if matched_index >= 0:
            self.bg_combo.setCurrentIndex(matched_index)
            self.request_preview()

    def extract_base_name(self, filename):
        """提取文件的基本名称（移除扩展名和常见后缀）"""
        import re

        # 先移除扩展名
        base_name = os.path.splitext(filename)[0]

        # 移除常见后缀
        patterns = [
            r'_标记$', r'_样本$', r'_edited$', r'_marked$', r'_sample$',
            r'[-_]v\d+$',  # 如 image_v1, image-v2
            r'[-_]\d+$',  # 如 image_1, image-2
            r'[-_]后$',  # 如 image_后
            r'[-_]修改$',  # 如 image_修改
        ]

        for pattern in patterns:
            base_name = re.sub(pattern, '', base_name)

        return base_name

    def clear_preview(self):
        """清除预览"""
        self.preview_widget.clear_preview()


class ProcessPanel(QWidget):
    """处理面板"""

    # 定义信号
    process_requested = pyqtSignal()
    sequence_process_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 处理模式组
        mode_group = QGroupBox("处理模式")
        mode_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        mode_layout = QHBoxLayout(mode_group)

        # 处理按钮
        self.process_button = QPushButton("标准处理模式")
        self.process_button.setToolTip("逐一处理样本图，为每个样本图自动匹配背景图")
        self.process_button.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.process_button.clicked.connect(self.process_requested)

        self.sequence_process_button = QPushButton("序列处理模式")
        self.sequence_process_button.setToolTip("按样本图序列分组处理，每组使用同一背景图")
        self.sequence_process_button.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.sequence_process_button.clicked.connect(self.sequence_process_requested)

        mode_layout.addWidget(self.process_button)
        mode_layout.addWidget(self.sequence_process_button)

        layout.addWidget(mode_group)

        # 进度组
        progress_group = QGroupBox("处理进度")
        progress_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        progress_layout = QVBoxLayout(progress_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        # 日志组
        log_group = QGroupBox("处理日志")
        log_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        log_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        log_layout = QVBoxLayout(log_group)

        # 日志文本区域（应用日志样式）
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(get_log_style("LOG_AREA_STYLE"))
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_text.setMinimumHeight(100)

        log_layout.addWidget(self.log_text)

        # 将日志文本框连接到日志记录器
        logger.set_gui_log_widget(self.log_text)

        layout.addWidget(log_group, stretch=1)  # 关键：设置拉伸因子

        # 添加弹性空间
        layout.addStretch()

    def set_progress(self, value):
        """设置进度条值"""
        self.progress_bar.setValue(value)


class DiffLabelerView(QWidget):
    """差分标注工具的视图"""

    # 定义信号
    config_changed = pyqtSignal(dict)
    process_requested = pyqtSignal()
    sequence_process_requested = pyqtSignal()
    preview_requested = pyqtSignal(str, str)
    save_config_requested = pyqtSignal(str)
    load_config_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("差分标注工具")
        self.resize(900, 500)
        # 初始化模型和控制器
        self.model = DiffLabelerModel()
        self.controller = DiffLabelerController(self.model, self)
        self.init_ui()
        # 加载默认配置
        self.controller.load_config()

    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(get_style("Q_TAB_WIDGET_STYLE"))

        # 创建分页
        self.config_panel = ConfigPanel()
        self.preview_panel = PreviewPanel()
        self.process_panel = ProcessPanel()

        # 添加配置页
        self.tab_widget.addTab(self.config_panel, "标注配置")
        self.tab_widget.addTab(self.preview_panel, "标注预览")
        self.tab_widget.addTab(self.process_panel, "标注处理")

        # 将标签页控件添加到主布局
        main_layout.addWidget(self.tab_widget)

        # 连接配置面板信号
        self.config_panel.directory_changed.connect(self.directory_changed)
        self.config_panel.save_config_btn.clicked.connect(self.save_config)
        self.config_panel.load_config_btn.clicked.connect(self.load_config)

        # 连接预览面板信号
        self.preview_panel.preview_requested.connect(self.preview_requested)

        # 连接处理面板信号
        self.process_panel.process_requested.connect(self.process_requested)
        self.process_panel.sequence_process_requested.connect(self.sequence_process_requested)

        # 引用处理按钮，以便控制器可以禁用/启用
        self.process_button = self.process_panel.process_button
        self.sequence_process_button = self.process_panel.sequence_process_button

        # 应用主样式
        self.setStyleSheet(get_style("APP_STYLE"))

        # 记录启动日志
        logger.info("差分标注工具已启动")

    def directory_changed(self, dir_type, path):
        """目录变更处理"""
        # 更新相关UI
        if dir_type == "bg_dir":
            self.preview_panel.update_bg_files(path)
        elif dir_type == "sample_dir":
            self.preview_panel.update_sample_files(path)

        # 通知配置变更
        self.config_changed.emit(self.get_current_config())

    def update_preview(self, bg_img, sample_img, diff_img, result_img):
        """更新预览图像"""
        self.preview_panel.preview_widget.update_preview(bg_img, sample_img, diff_img, result_img)

        # 如果当前不在预览标签页，自动切换到预览页
        if self.tab_widget.currentIndex() != 1:  # 预览页索引是1
            self.tab_widget.setCurrentIndex(1)

    def get_current_config(self):
        """获取当前配置"""
        return self.config_panel.get_config()

    def update_from_config(self, config):
        """从配置更新UI"""
        self.config_panel.update_config(config)

        # 更新文件列表
        if "bg_dir" in config:
            self.preview_panel.update_bg_files(config["bg_dir"])
        if "sample_dir" in config:
            self.preview_panel.update_sample_files(config["sample_dir"])

    def set_progress(self, value):
        """设置进度条值"""
        self.process_panel.set_progress(value)

        # 如果当前不在处理标签页且进度不为0，自动切换到处理页
        if value > 0 and value < 100 and self.tab_widget.currentIndex() != 2:  # 处理页索引是2
            self.tab_widget.setCurrentIndex(2)

    def log_message(self, message):
        """记录日志消息"""
        logger.info(message)

    def save_config(self):
        """保存配置"""
        dialog = QFileDialog()
        dialog.setNameFilter("JSON Files (*.json)")
        dialog.setDefaultSuffix("json")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

        if dialog.exec():
            config_path = dialog.selectedFiles()[0]
            self.save_config_requested.emit(config_path)

    def load_config(self):
        """加载配置"""
        dialog = QFileDialog()
        dialog.setNameFilter("JSON Files (*.json)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if dialog.exec():
            config_path = dialog.selectedFiles()[0]
            self.load_config_requested.emit(config_path)


def main():
    """作为独立应用运行"""
    app = QApplication(sys.argv)
    window = DiffLabelerView()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # 作为独立应用运行
    main()
