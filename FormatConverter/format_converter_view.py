"""
格式转换工具的视图层 - 处理界面呈现和用户交互
"""
import os
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget,
                             QTableWidgetItem, QFileDialog, QTextEdit, QProgressBar,
                             QGroupBox, QGridLayout, QHeaderView, QSplitter, QFrame,
                             QCheckBox)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt6.QtGui import QFont
from typing import Dict, List, Union, Optional

from utils.logger import LogManager
logger = LogManager.get_logger("FC", level="info")

from FormatConverter.format_converter_model import FormatConverterModel
from FormatConverter.format_converter_controller import FormatConverterController

# 导入样式接口
from style.style_interface import get_style, get_log_style


class DirectoryConfigPanel(QWidget):
    """目录配置面板"""

    directory_changed = pyqtSignal(str, str)  # 目录类型，路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 目录配置组
        dir_group = QGroupBox("目录配置")
        dir_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        dir_layout = QGridLayout(dir_group)

        # 源文件目录
        dir_layout.addWidget(QLabel("源文件目录:"), 0, 0)
        self.source_dir_edit = QLineEdit()
        self.source_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.source_dir_edit, 0, 1)
        source_btn = QPushButton("浏览...")
        source_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        source_btn.clicked.connect(lambda: self.browse_directory("source_dir"))
        dir_layout.addWidget(source_btn, 0, 2)

        # 图像文件目录
        dir_layout.addWidget(QLabel("图像文件目录:"), 1, 0)
        self.image_dir_edit = QLineEdit()
        self.image_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.image_dir_edit, 1, 1)
        image_btn = QPushButton("浏览...")
        image_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        image_btn.clicked.connect(lambda: self.browse_directory("image_dir"))
        dir_layout.addWidget(image_btn, 1, 2)

        # 输出目录
        dir_layout.addWidget(QLabel("输出目录:"), 2, 0)
        self.target_dir_edit = QLineEdit()
        self.target_dir_edit.setStyleSheet(get_style("INPUT_STYLE"))
        dir_layout.addWidget(self.target_dir_edit, 2, 1)
        target_btn = QPushButton("浏览...")
        target_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        target_btn.clicked.connect(lambda: self.browse_directory("target_dir"))
        dir_layout.addWidget(target_btn, 2, 2)

        layout.addWidget(dir_group)

        # 转换模式组
        mode_group = QGroupBox("转换模式")
        mode_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        mode_layout = QVBoxLayout(mode_group)

        # 转换方向
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("转换方向:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setStyleSheet(get_style("COMBO_BOX_STYLE"))
        self.mode_combo.addItems([
            "YOLO → labelme",
            "labelme → YOLO"
        ])
        direction_layout.addWidget(self.mode_combo)
        direction_layout.addStretch()
        mode_layout.addLayout(direction_layout)

        # YOLO classes.txt优先级设置（仅在YOLO格式下显示）
        self.classes_priority_layout = QHBoxLayout()
        self.use_classes_txt = QCheckBox("优先使用classes.txt文件")
        self.use_classes_txt.setChecked(True)
        self.use_classes_txt.stateChanged.connect(self.on_classes_priority_changed)
        self.classes_priority_layout.addWidget(self.use_classes_txt)

        self.classes_path_edit = QLineEdit()
        self.classes_path_edit.setStyleSheet(get_style("INPUT_STYLE"))
        self.classes_path_edit.setPlaceholderText("自动从源目录查找")
        self.classes_path_edit.setEnabled(False)
        self.classes_priority_layout.addWidget(self.classes_path_edit)

        classes_browse_btn = QPushButton("浏览...")
        classes_browse_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        classes_browse_btn.clicked.connect(self.browse_classes_txt)
        self.classes_priority_layout.addWidget(classes_browse_btn)

        mode_layout.addLayout(self.classes_priority_layout)

        # 初始隐藏classes.txt相关控件
        self.update_classes_visibility()

        layout.addWidget(mode_group)
        layout.addStretch()

    def browse_directory(self, dir_type: str):
        """浏览选择目录"""
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)

        current_path = ""
        if dir_type == "source_dir":
            current_path = self.source_dir_edit.text()
        elif dir_type == "image_dir":
            current_path = self.image_dir_edit.text()
        elif dir_type == "target_dir":
            current_path = self.target_dir_edit.text()

        if current_path and os.path.exists(current_path):
            dialog.setDirectory(current_path)

        if dialog.exec():
            selected_dir = dialog.selectedFiles()[0]
            if dir_type == "source_dir":
                self.source_dir_edit.setText(selected_dir)
            elif dir_type == "image_dir":
                self.image_dir_edit.setText(selected_dir)
            elif dir_type == "target_dir":
                self.target_dir_edit.setText(selected_dir)
            self.directory_changed.emit(dir_type, selected_dir)

    def browse_classes_txt(self):
        """浏览选择classes.txt文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择classes.txt文件", "", "Text Files (*.txt)")
        if file_path:
            self.classes_path_edit.setText(file_path)

    def on_conversion_mode_changed(self):
        """转换模式改变时更新UI"""
        self.update_classes_visibility()

    def on_classes_priority_changed(self, state):
        """classes.txt优先级改变时处理"""
        is_checked = state == Qt.CheckState.Checked.value
        self.classes_path_edit.setEnabled(is_checked)

        # 发送配置更新信号
        parent_view = self.parent().parent().parent()
        if hasattr(parent_view, 'config_changed'):
            current_config = self.get_config()
            parent_view.config_changed.emit(current_config)

    def update_classes_visibility(self):
        """根据转换模式更新classes.txt相关控件的可见性"""
        mode_text = self.mode_combo.currentText()
        is_yolo_mode = "YOLO → labelme" in mode_text

        for i in range(self.classes_priority_layout.count()):
            widget = self.classes_priority_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_yolo_mode)

    def get_config(self) -> Dict[str, str]:
        """获取当前配置"""
        mode_text = self.mode_combo.currentText()
        conversion_mode = "yolo_to_labelme" if "YOLO → labelme" in mode_text else "labelme_to_yolo"

        config = {
            "source_dir": self.source_dir_edit.text(),
            "image_dir": self.image_dir_edit.text(),
            "target_dir": self.target_dir_edit.text(),
            "conversion_mode": conversion_mode,
            "use_classes_txt": self.use_classes_txt.isChecked()
        }

        # 仅在YOLO模式下添加classes.txt路径
        if conversion_mode == "yolo_to_labelme":
            config["classes_txt_path"] = self.classes_path_edit.text()

        return config

    def update_config(self, config: Dict[str, str]):
        """更新配置显示"""
        if "source_dir" in config:
            self.source_dir_edit.setText(config["source_dir"])
        if "image_dir" in config:
            self.image_dir_edit.setText(config["image_dir"])
        if "target_dir" in config:
            self.target_dir_edit.setText(config["target_dir"])
        if "conversion_mode" in config:
            index = 0 if config["conversion_mode"] == "yolo_to_labelme" else 1
            self.mode_combo.setCurrentIndex(index)
            self.update_classes_visibility()
        if "use_classes_txt" in config:
            self.use_classes_txt.setChecked(config["use_classes_txt"])
        if "classes_txt_path" in config:
            self.classes_path_edit.setText(config["classes_txt_path"])


class LabelMappingPanel(QWidget):
    """标签映射配置面板"""

    discover_labels_requested = pyqtSignal()
    mapping_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_labels = {"yolo": [], "labelme": []}
        self.classes_labels = {}
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标签发现组
        discover_group = QGroupBox("标签发现")
        discover_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        discover_layout = QHBoxLayout(discover_group)

        self.discover_btn = QPushButton("自动发现标签")
        self.discover_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.discover_btn.clicked.connect(self.discover_labels_requested)
        discover_layout.addWidget(self.discover_btn)

        self.import_btn = QPushButton("导入映射")
        self.import_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.import_btn.clicked.connect(self.import_mapping)
        discover_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("导出映射")
        self.export_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.export_btn.clicked.connect(self.export_mapping)
        discover_layout.addWidget(self.export_btn)

        discover_layout.addStretch()
        layout.addWidget(discover_group)

        # 标签映射表
        mapping_group = QGroupBox("标签映射配置")
        mapping_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        mapping_layout = QVBoxLayout(mapping_group)

        self.mapping_table = QTableWidget()

        # 设置表格样式
        self.mapping_table.setStyleSheet("""
            QTableWidget {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                selection-background-color: #3daee9;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 5px;
                border: 1px solid #ccc;
                font-weight: bold;
            }
        """)

        # 设置表格属性
        header = self.mapping_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mapping_table.setAlternatingRowColors(True)

        # 连接信号
        self.mapping_table.cellChanged.connect(self.on_mapping_changed)

        mapping_layout.addWidget(self.mapping_table)
        layout.addWidget(mapping_group)

    def update_labels(self, labels: Dict[str, List[Union[str, int]]], classes_labels: Dict[str, List] = None):
        """更新发现的标签"""
        self.current_labels = labels
        self.classes_labels = classes_labels or {}
        self.populate_mapping_table()

    def populate_mapping_table(self):
        """填充映射表"""
        # 根据当前转换模式确定源标签和目标标签
        parent_view = self.parent().parent().parent()  # 获取主视图
        if hasattr(parent_view, 'directory_panel'):
            config = parent_view.directory_panel.get_config()
            conversion_mode = config.get("conversion_mode", "yolo_to_labelme")
            use_classes = config.get("use_classes_txt", True)
        else:
            conversion_mode = "yolo_to_labelme"
            use_classes = True

        if conversion_mode == "yolo_to_labelme":
            # YOLO转换模式
            if use_classes and self.classes_labels:
                # 优先使用classes.txt中的标签
                source_labels = self.classes_labels.get("yolo", [])
                original_labels = self.classes_labels.get("labelme", [])
            else:
                source_labels = self.current_labels.get("yolo", [])
                original_labels = [str(label) for label in source_labels]
        else:
            # labelme转换模式
            source_labels = self.current_labels.get("labelme", [])
            original_labels = source_labels

        # 设置表格列数和行数
        if conversion_mode == "yolo_to_labelme" and use_classes and self.classes_labels:
            self.mapping_table.setColumnCount(3)
            self.mapping_table.setHorizontalHeaderLabels(["YOLO类别ID", "原始标签", "labelme标签"])
        else:
            self.mapping_table.setColumnCount(2)
            if conversion_mode == "yolo_to_labelme":
                self.mapping_table.setHorizontalHeaderLabels(["YOLO类别ID", "labelme标签"])
            else:
                self.mapping_table.setHorizontalHeaderLabels(["labelme标签", "YOLO类别ID"])

        self.mapping_table.setRowCount(len(source_labels))

        # 填充数据
        for i, source_label in enumerate(source_labels):
            # 源标签（只读）
            source_item = QTableWidgetItem(str(source_label))
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(i, 0, source_item)

            # 如果有原始标签列（使用classes.txt时）
            if conversion_mode == "yolo_to_labelme" and use_classes and self.classes_labels:
                # 原始标签（只读）
                original_label = original_labels[i] if i < len(original_labels) else ""
                original_item = QTableWidgetItem(original_label)
                original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.mapping_table.setItem(i, 1, original_item)

                # 目标标签（可编辑）
                target_col = 2
            else:
                # 目标标签（可编辑）
                target_col = 1

            # 目标标签（可编辑）
            # 目标标签预填为原始标签
            if conversion_mode == "yolo_to_labelme" and use_classes and self.classes_labels and i < len(original_labels):
                default_label = original_labels[i]
            else:
                default_label = str(source_label)
            target_item = QTableWidgetItem(default_label)
            if conversion_mode == "yolo_to_labelme":
                if use_classes and self.classes_labels and i < len(original_labels):
                    target_item.setToolTip(original_labels[i])
                else:
                    target_item.setToolTip(f"标签_{source_label}")
            else:
                target_item.setToolTip("0")
            self.mapping_table.setItem(i, target_col, target_item)

    def get_mapping(self) -> Dict[Union[str, int], Union[str, int]]:
        """获取当前映射配置"""
        mapping = {}
        for i in range(self.mapping_table.rowCount()):
            source_item = self.mapping_table.item(i, 0)

            # 确定目标标签的列索引
            parent_view = self.parent().parent().parent()
            if hasattr(parent_view, 'directory_panel'):
                config = parent_view.directory_panel.get_config()
                conversion_mode = config.get("conversion_mode", "yolo_to_labelme")
                use_classes = config.get("use_classes_txt", True)
            else:
                conversion_mode = "yolo_to_labelme"
                use_classes = True

            if conversion_mode == "yolo_to_labelme" and use_classes and self.classes_labels:
                target_col = 2
            else:
                target_col = 1

            target_item = self.mapping_table.item(i, target_col)

            if source_item and target_item:
                source_value = source_item.text()
                target_value = target_item.text()

                if source_value and target_value:
                    try:
                        if conversion_mode == "yolo_to_labelme":
                            # YOLO ID -> labelme 标签
                            mapping[int(source_value)] = target_value
                        else:
                            # labelme 标签 -> YOLO ID
                            mapping[source_value] = int(target_value)
                    except ValueError:
                        logger.warning(f"映射值转换错误: {source_value} -> {target_value}")

        return mapping

    def update_mapping(self, mapping: Dict[Union[str, int], Union[str, int]]):
        """更新映射显示"""
        for i in range(self.mapping_table.rowCount()):
            source_item = self.mapping_table.item(i, 0)

            # 确定目标标签的列索引
            parent_view = self.parent().parent().parent()
            if hasattr(parent_view, 'directory_panel'):
                config = parent_view.directory_panel.get_config()
                conversion_mode = config.get("conversion_mode", "yolo_to_labelme")
                use_classes = config.get("use_classes_txt", True)
            else:
                conversion_mode = "yolo_to_labelme"
                use_classes = True

            if conversion_mode == "yolo_to_labelme" and use_classes and self.classes_labels:
                target_col = 2
            else:
                target_col = 1

            target_item = self.mapping_table.item(i, target_col)

            if source_item and target_item:
                source_value = source_item.text()
                try:
                    # 根据类型转换
                    if source_value.isdigit():
                        key = int(source_value)
                    else:
                        key = source_value

                    if key in mapping:
                        target_item.setText(str(mapping[key]))
                except:
                    pass

    @pyqtSlot()
    def on_mapping_changed(self):
        """映射改变时触发"""
        mapping = self.get_mapping()
        self.mapping_changed.emit(mapping)

    def import_mapping(self):
        """导入映射文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入标签映射", "", "JSON Files (*.json)")

        if file_path:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                self.update_mapping(mapping)
                logger.success(f"映射导入成功: {file_path}")
            except Exception as e:
                logger.error(f"导入映射失败: {e}")

    def export_mapping(self):
        """导出映射文件"""
        mapping = self.get_mapping()
        if not mapping:
            logger.warning("没有可导出的映射数据")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出标签映射", "label_mapping.json", "JSON Files (*.json)")

        if file_path:
            try:
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, ensure_ascii=False, indent=4)
                logger.success(f"映射导出成功: {file_path}")
            except Exception as e:
                logger.error(f"导出映射失败: {e}")


class ProcessPanel(QWidget):
    """处理面板"""

    conversion_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    save_config_requested = pyqtSignal(str)
    load_config_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 控制按钮组
        control_group = QGroupBox("操作控制")
        control_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        control_layout = QHBoxLayout(control_group)

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        self.convert_btn.clicked.connect(self.conversion_requested)
        control_layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton("停止转换")
        self.cancel_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.cancel_btn.clicked.connect(self.cancel_requested)
        control_layout.addWidget(self.cancel_btn)

        control_layout.addStretch()

        # 配置文件操作
        self.save_config_btn = QPushButton("保存配置")
        self.save_config_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.save_config_btn.clicked.connect(self.save_config)
        control_layout.addWidget(self.save_config_btn)

        self.load_config_btn = QPushButton("加载配置")
        self.load_config_btn.setStyleSheet(get_style("SECONDARY_BUTTON_STYLE"))
        self.load_config_btn.clicked.connect(self.load_config)
        control_layout.addWidget(self.load_config_btn)

        layout.addWidget(control_group)

        # 进度组
        progress_group = QGroupBox("转换进度")
        progress_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(get_style("PRIMARY_BUTTON_STYLE"))
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        # 日志组
        log_group = QGroupBox("转换日志")
        log_group.setStyleSheet(get_style("GROUP_BOX_STYLE"))
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(get_log_style("LOG_AREA_STYLE"))
        self.log_text.document().setMaximumBlockCount(1000)

        # 设置字体
        font = self.log_text.font()
        font.setFamily("Consolas")
        font.setPointSize(9)
        self.log_text.setFont(font)

        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group, stretch=1)

    def save_config(self):
        """保存配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置", "fc_config.json", "JSON Files (*.json)")
        if file_path:
            self.save_config_requested.emit(file_path)

    def load_config(self):
        """加载配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载配置", "", "JSON Files (*.json)")
        if file_path:
            self.load_config_requested.emit(file_path)

    def set_progress(self, value: int):
        """设置进度值"""
        self.progress_bar.setValue(value)


class FormatConverterView(QWidget):
    """格式转换工具的视图"""

    # 定义信号
    config_changed = pyqtSignal(dict)
    conversion_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    save_config_requested = pyqtSignal(str)
    load_config_requested = pyqtSignal(str)
    discover_labels_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 先创建基础UI
        self.setup_base_ui()

        # 设置日志输出到GUI
        logger.set_gui_log_widget(self.process_panel.log_text)
        logger.info("正在初始化格式转换工具...")

        # 初始化模型和控制器
        self.model = FormatConverterModel()
        self.controller = FormatConverterController(self.model, self)

        # 完成UI连接
        self.setup_ui_connections()

        # 加载默认配置
        self.controller.load_config()
        logger.success("格式转换工具初始化完成")

    def setup_base_ui(self):
        """初始化基础UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(get_style("Q_TAB_WIDGET_STYLE"))

        # 创建各个面板
        self.directory_panel = DirectoryConfigPanel()
        self.mapping_panel = LabelMappingPanel()
        self.process_panel = ProcessPanel()

        # 添加标签页
        self.tab_widget.addTab(self.directory_panel, "目录配置")
        self.tab_widget.addTab(self.mapping_panel, "标签映射")
        self.tab_widget.addTab(self.process_panel, "执行转换")

        main_layout.addWidget(self.tab_widget)

        # 应用主样式
        self.setStyleSheet(get_style("APP_STYLE"))

    def setup_ui_connections(self):
        """设置UI信号连接"""
        # 目录配置面板
        self.directory_panel.directory_changed.connect(self.on_directory_changed)
        self.directory_panel.mode_combo.currentTextChanged.connect(self.on_conversion_mode_changed)

        # 标签映射面板
        self.mapping_panel.discover_labels_requested.connect(self.discover_labels_requested)
        self.mapping_panel.mapping_changed.connect(self.on_mapping_changed)

        # 处理面板
        self.process_panel.conversion_requested.connect(self.conversion_requested)
        self.process_panel.cancel_requested.connect(self.cancel_requested)
        self.process_panel.save_config_requested.connect(self.save_config_requested)
        self.process_panel.load_config_requested.connect(self.load_config_requested)

    def on_directory_changed(self, dir_type: str, path: str):
        """目录变更处理"""
        logger.info(f"{dir_type} 目录已更新: {path}")
        current_config = self.get_current_config()
        self.config_changed.emit(current_config)

    def on_conversion_mode_changed(self, mode_text: str):
        """转换模式变更处理"""
        logger.info(f"转换模式已变更: {mode_text}")
        self.directory_panel.on_conversion_mode_changed()
        # 重新填充映射表
        self.mapping_panel.populate_mapping_table()
        current_config = self.get_current_config()
        self.config_changed.emit(current_config)

    def on_mapping_changed(self, mapping: Dict):
        """映射变更处理"""
        current_config = self.get_current_config()
        current_config["label_mapping"] = mapping
        self.config_changed.emit(current_config)

    def get_current_config(self) -> Dict:
        """获取当前完整配置"""
        config = self.directory_panel.get_config()
        config["label_mapping"] = self.mapping_panel.get_mapping()
        return config

    def update_from_config(self, config: Dict):
        """从配置更新UI"""
        self.directory_panel.update_config(config)
        if "label_mapping" in config:
            self.mapping_panel.update_mapping(config["label_mapping"])

    def set_progress(self, value: int):
        """更新进度条"""
        self.process_panel.set_progress(value)

    @pyqtSlot(bool, str)
    def on_config_saved(self, success: bool, path: str):
        """配置保存结果处理"""
        if success:
            logger.success(f"配置已保存: {path}")
        else:
            logger.error(f"保存配置失败: {path}")

    @pyqtSlot(bool, str, dict)
    def on_config_loaded(self, success: bool, path: str, config: dict):
        """配置加载结果处理"""
        if success:
            logger.success(f"配置已加载: {path}")
            self.update_from_config(config)
        else:
            logger.error(f"加载配置失败: {path}")

    @pyqtSlot(dict)
    def on_labels_discovered(self, labels: Dict):
        """标签发现结果处理"""
        # 从controller的discover_labels方法获取classes_labels
        if hasattr(self.controller, 'last_classes_labels'):
            classes_labels = self.controller.last_classes_labels
        else:
            classes_labels = {}

        self.mapping_panel.update_labels(labels, classes_labels)
        total = len(labels.get("yolo", [])) + len(labels.get("labelme", []))
        logger.info(f"发现标签: YOLO({len(labels.get('yolo', []))}) + labelme({len(labels.get('labelme', []))})")

    @pyqtSlot(str, bool)
    def show_status_message(self, message: str, is_error: bool = False):
        """显示状态消息"""
        pass  # 日志已通过logger处理

    @pyqtSlot()
    def on_conversion_started(self):
        """转换开始时的UI响应"""
        self.process_panel.convert_btn.setEnabled(False)
        self.tab_widget.setTabEnabled(0, False)
        self.tab_widget.setTabEnabled(1, False)
        # 切换到处理页面
        self.tab_widget.setCurrentIndex(2)
        logger.info("开始批量转换...")

    @pyqtSlot(int, int, list)
    def on_conversion_finished(self, success_count: int, failure_count: int, error_list: list):
        """转换完成时的UI响应"""
        self.process_panel.convert_btn.setEnabled(True)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, True)

        if failure_count > 0:
            logger.warning(f"批量转换完成，成功 {success_count} 个，失败 {failure_count} 个")
            for error in error_list[:5]:  # 只显示前5个错误
                logger.error(error)
            if len(error_list) > 5:
                logger.info(f"... 还有 {len(error_list) - 5} 个错误")
        else:
            logger.success(f"批量转换完成，共成功转换 {success_count} 个文件")


def main():
    """作为独立应用运行"""
    app = QApplication(sys.argv)
    logger.set_level("info")
    logger.info("启动格式转换工具...")
    window = FormatConverterView()
    window.show()
    logger.info("应用程序就绪")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
