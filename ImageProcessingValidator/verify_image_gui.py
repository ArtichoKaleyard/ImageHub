import sys
import os
import json
from typing import Dict, Any

from PyQt6.QtCore import Qt, QSettings, QThreadPool, QUrl
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox,
    QFileDialog, QTabWidget, QTextEdit, QSpinBox, QProgressBar,
    QGroupBox, QFormLayout, QMessageBox, QStatusBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# 导入适配器
from ImageProcessingValidator.image_verifier_adapter import VerifierWorker

# 导入样式接口
from style.style_interface import get_style, get_theme, DEFAULT_WINDOW_SIZE


class ImageVerifierGUI(QMainWindow):
    """图片验证工具的图形用户界面"""

    def __init__(self):
        super().__init__()

        # 设置应用程序
        self.setWindowTitle("图片处理验证工具")
        self.resize(*DEFAULT_WINDOW_SIZE)

        # 应用全局样式
        self.setStyleSheet(get_style('APP_STYLE'))

        # 初始化线程池
        self.threadpool = QThreadPool()
        self.verifier_worker = None

        # 应用设置
        self.settings = QSettings("ImageVerifier", "ImageVerifierApp")

        # 初始化界面布局
        self._setup_ui()

        # 加载配置
        self._load_config()

        # 显示初始状态
        self.status_bar.showMessage("就绪")

    def _setup_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(get_style('Q_TAB_WIDGET_STYLE'))
        main_layout.addWidget(self.tab_widget)

        # 添加基本配置选项卡
        self._create_basic_config_tab()

        # 添加高级配置选项卡
        self._create_advanced_config_tab()

        # 添加验证输出选项卡（进度和日志）
        self._create_output_tab()

        # 创建按钮区域
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        # 添加操作按钮
        self.start_button = QPushButton("开始验证")
        self.start_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        self.start_button.clicked.connect(self.start_verification)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("停止验证")
        self.stop_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.stop_button.clicked.connect(self.stop_verification)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.save_config_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_config_button)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(get_style('STATUS_BAR_STYLE'))
        main_layout.addWidget(self.status_bar)

    def _create_output_tab(self):
        """创建验证输出选项卡（包含进度和日志）"""
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)

        # 添加进度条
        progress_layout = QHBoxLayout()
        output_layout.addLayout(progress_layout)

        progress_label = QLabel("验证进度:")
        progress_label.setStyleSheet(get_style('LABEL_STYLE'))
        progress_layout.addWidget(progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(get_style('SCROLLBAR_STYLE'))
        progress_layout.addWidget(self.progress_bar)

        # 添加日志输出区域
        log_group = QGroupBox("验证日志")
        log_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        log_layout = QVBoxLayout(log_group)
        output_layout.addWidget(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet(get_style('INPUT_STYLE'))
        log_layout.addWidget(self.log_output)

        # 添加到选项卡
        self.tab_widget.addTab(output_tab, "验证输出")

        # 保存输出选项卡的索引，用于自动切换
        self.output_tab_index = self.tab_widget.count() - 1

    def _create_basic_config_tab(self):
        """创建基本配置选项卡"""
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        # 文件夹配置组
        folder_group = QGroupBox("文件夹配置")
        folder_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        folder_layout = QFormLayout(folder_group)
        basic_layout.addWidget(folder_group)

        # 源文件夹
        source_layout = QHBoxLayout()
        self.source_folder_edit = QLineEdit()
        self.source_folder_edit.setStyleSheet(get_style('INPUT_STYLE'))
        source_layout.addWidget(self.source_folder_edit)
        self.source_folder_button = QPushButton("浏览...")
        self.source_folder_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        self.source_folder_button.clicked.connect(lambda: self._browse_folder(self.source_folder_edit))
        source_layout.addWidget(self.source_folder_button)

        source_label = QLabel("原始图片文件夹:")
        source_label.setStyleSheet(get_style('LABEL_STYLE'))
        folder_layout.addRow(source_label, source_layout)

        # 目标文件夹
        target_layout = QHBoxLayout()
        self.target_folder_edit = QLineEdit()
        self.target_folder_edit.setStyleSheet(get_style('INPUT_STYLE'))
        target_layout.addWidget(self.target_folder_edit)
        self.target_folder_button = QPushButton("浏览...")
        self.target_folder_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        self.target_folder_button.clicked.connect(lambda: self._browse_folder(self.target_folder_edit))
        target_layout.addWidget(self.target_folder_button)

        target_label = QLabel("处理后图片文件夹:")
        target_label.setStyleSheet(get_style('LABEL_STYLE'))
        folder_layout.addRow(target_label, target_layout)

        # 缺失文件夹
        missing_layout = QHBoxLayout()
        self.missing_folder_edit = QLineEdit()
        self.missing_folder_edit.setStyleSheet(get_style('INPUT_STYLE'))
        missing_layout.addWidget(self.missing_folder_edit)
        self.missing_folder_button = QPushButton("浏览...")
        self.missing_folder_button.setStyleSheet(get_style('PRIMARY_BUTTON_STYLE'))
        self.missing_folder_button.clicked.connect(lambda: self._browse_folder(self.missing_folder_edit))
        missing_layout.addWidget(self.missing_folder_button)

        missing_label = QLabel("未处理图片输出文件夹:")
        missing_label.setStyleSheet(get_style('LABEL_STYLE'))
        folder_layout.addRow(missing_label, missing_layout)

        # 创建一个水平布局用于包含命名和后缀配置
        naming_suffix_layout = QHBoxLayout()
        basic_layout.addLayout(naming_suffix_layout)

        # 命名模式配置组
        naming_group = QGroupBox("命名模式配置")
        naming_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        naming_layout = QFormLayout(naming_group)
        naming_suffix_layout.addWidget(naming_group, 2)  # 比例2

        # 后缀类型
        self.suffix_type_combo = QComboBox()
        self.suffix_type_combo.setStyleSheet(get_style('COMBO_BOX_STYLE'))
        self.suffix_type_combo.addItems(["range", "numeric", "custom"])
        self.suffix_type_combo.currentTextChanged.connect(self._update_suffix_editability)

        suffix_type_label = QLabel("后缀类型:")
        suffix_type_label.setStyleSheet(get_style('LABEL_STYLE'))
        naming_layout.addRow(suffix_type_label, self.suffix_type_combo)

        # 分隔符
        self.suffix_delimiter_edit = QLineEdit("_")
        self.suffix_delimiter_edit.setStyleSheet(get_style('INPUT_STYLE'))

        delimiter_label = QLabel("后缀分隔符:")
        delimiter_label.setStyleSheet(get_style('LABEL_STYLE'))
        naming_layout.addRow(delimiter_label, self.suffix_delimiter_edit)

        # 源文件扩展名
        self.source_extensions_edit = QLineEdit(".jpg, .jpeg, .png")
        self.source_extensions_edit.setStyleSheet(get_style('INPUT_STYLE'))

        source_ext_label = QLabel("原始图片格式:")
        source_ext_label.setStyleSheet(get_style('LABEL_STYLE'))
        naming_layout.addRow(source_ext_label, self.source_extensions_edit)

        # 期望的扩展名
        self.expected_extension_edit = QLineEdit(".png")
        self.expected_extension_edit.setStyleSheet(get_style('INPUT_STYLE'))

        expected_ext_label = QLabel("处理后图片格式:")
        expected_ext_label.setStyleSheet(get_style('LABEL_STYLE'))
        naming_layout.addRow(expected_ext_label, self.expected_extension_edit)

        # 检查选项 - 靠左显示
        verify_layout1 = QHBoxLayout()
        self.verify_naming_check = QCheckBox("验证命名规范性")
        self.verify_naming_check.setStyleSheet(get_style('CHECK_BOX_STYLE'))
        self.verify_naming_check.setChecked(True)
        verify_layout1.addWidget(self.verify_naming_check)
        verify_layout1.addStretch()  # 添加弹性空间让复选框靠左
        naming_layout.addRow(verify_layout1)

        verify_layout2 = QHBoxLayout()
        self.verify_completeness_check = QCheckBox("验证处理完整性")
        self.verify_completeness_check.setStyleSheet(get_style('CHECK_BOX_STYLE'))
        self.verify_completeness_check.setChecked(True)
        verify_layout2.addWidget(self.verify_completeness_check)
        verify_layout2.addStretch()  # 添加弹性空间让复选框靠左
        naming_layout.addRow(verify_layout2)

        # 后缀配置组
        self.suffix_config_group = QGroupBox("后缀配置")
        self.suffix_config_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        self.suffix_config_layout = QFormLayout(self.suffix_config_group)
        naming_suffix_layout.addWidget(self.suffix_config_group, 3)  # 比例3

        # Range模式配置
        self.range_min_spin = QSpinBox()
        self.range_min_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.range_min_spin.setRange(1, 999)
        self.range_min_spin.setValue(1)

        range_min_label = QLabel("后缀最小值:")
        range_min_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(range_min_label, self.range_min_spin)

        self.range_max_spin = QSpinBox()
        self.range_max_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.range_max_spin.setRange(1, 999)
        self.range_max_spin.setValue(10)

        range_max_label = QLabel("后缀最大值:")
        range_max_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(range_max_label, self.range_max_spin)

        # Numeric模式配置
        self.min_digits_spin = QSpinBox()
        self.min_digits_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.min_digits_spin.setRange(1, 10)
        self.min_digits_spin.setValue(1)

        min_digits_label = QLabel("最小位数:")
        min_digits_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(min_digits_label, self.min_digits_spin)

        self.max_digits_spin = QSpinBox()
        self.max_digits_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.max_digits_spin.setRange(0, 10)
        self.max_digits_spin.setValue(0)
        self.max_digits_spin.setSpecialValueText("不限制")

        max_digits_label = QLabel("最大位数:")
        max_digits_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(max_digits_label, self.max_digits_spin)

        self.expected_count_spin = QSpinBox()
        self.expected_count_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.expected_count_spin.setRange(0, 999)
        self.expected_count_spin.setValue(0)
        self.expected_count_spin.setSpecialValueText("自动检测")

        expected_count_label = QLabel("每图预期数量:")
        expected_count_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(expected_count_label, self.expected_count_spin)

        # Custom模式配置
        self.custom_pattern_edit = QLineEdit()
        self.custom_pattern_edit.setStyleSheet(get_style('INPUT_STYLE'))
        self.custom_pattern_edit.setPlaceholderText("^(?P<base_name>.+)_(?P<suffix>\\d+)\\.png$")

        custom_pattern_label = QLabel("自定义模式:")
        custom_pattern_label.setStyleSheet(get_style('LABEL_STYLE'))
        self.suffix_config_layout.addRow(custom_pattern_label, self.custom_pattern_edit)

        # 初始化控件状态
        self._update_suffix_editability(self.suffix_type_combo.currentText())

        # 添加到选项卡
        self.tab_widget.addTab(basic_tab, "基本配置")

    def _update_suffix_editability(self, suffix_type):
        """根据后缀类型更新控件的可编辑性"""
        # Range模式
        range_enabled = suffix_type == "range"
        self.range_min_spin.setEnabled(range_enabled)
        self.range_max_spin.setEnabled(range_enabled)

        # Numeric模式
        numeric_enabled = suffix_type == "numeric"
        self.min_digits_spin.setEnabled(numeric_enabled)
        self.max_digits_spin.setEnabled(numeric_enabled)
        self.expected_count_spin.setEnabled(numeric_enabled)

        # Custom模式
        custom_enabled = suffix_type == "custom"
        self.custom_pattern_edit.setEnabled(custom_enabled)

    def _create_advanced_config_tab(self):
        """创建高级配置选项卡"""
        advanced_tab = QWidget()
        advanced_layout = QHBoxLayout(advanced_tab)  # 改为水平布局

        # 左侧垂直布局，包含性能配置组和配置预设组
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(left_panel)

        # 性能配置组
        performance_group = QGroupBox("性能配置")
        performance_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        performance_layout = QFormLayout(performance_group)
        left_layout.addWidget(performance_group)

        # 工作线程数
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setStyleSheet(get_style('INPUT_STYLE'))
        self.max_workers_spin.setRange(0, 32)
        self.max_workers_spin.setValue(0)
        self.max_workers_spin.setSpecialValueText("自动")

        workers_label = QLabel("最大工作线程数:")
        workers_label.setStyleSheet(get_style('LABEL_STYLE'))
        performance_layout.addRow(workers_label, self.max_workers_spin)

        # 配置预设组
        preset_group = QGroupBox("配置预设")
        preset_group.setStyleSheet(get_style('GROUP_BOX_STYLE'))
        preset_layout = QVBoxLayout(preset_group)  # 保持垂直布局
        left_layout.addWidget(preset_group)

        # 预设选择下拉框
        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet(get_style('COMBO_BOX_STYLE'))
        self.preset_combo.addItems(["range_config", "numeric_config", "custom_config"])
        preset_layout.addWidget(self.preset_combo)  # 直接垂直添加

        # 加载预设按钮
        self.load_preset_button = QPushButton("加载预设")
        self.load_preset_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.load_preset_button.clicked.connect(self._load_preset)
        preset_layout.addWidget(self.load_preset_button)  # 直接垂直添加

        # 保存预设按钮
        self.save_preset_button = QPushButton("保存为预设")
        self.save_preset_button.setStyleSheet(get_style('SECONDARY_BUTTON_STYLE'))
        self.save_preset_button.clicked.connect(self._save_preset)
        preset_layout.addWidget(self.save_preset_button)  # 直接垂直添加

        # 右侧帮助区域
        help_view = QWebEngineView()
        help_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)  # 禁用右键菜单
        try:
            # 读取 HTML 文件
            help_path = os.path.join("./ImageProcessingValidator/help.html")
            if os.path.exists(help_path):
                # 使用 file:// 协议加载本地文件
                url = QUrl.fromLocalFile(os.path.abspath(help_path))
                help_view.load(url)
            else:
                help_view.setHtml(f"<h2 style='color: {get_theme('error')}'>帮助文档未找到</h2>")
        except Exception as e:
            help_view.setHtml(f"<h2 style='color: {get_theme('error')}'>帮助文档未找到</h2> {str(e)}")

        advanced_layout.addWidget(help_view)

        # 添加到选项卡
        self.tab_widget.addTab(advanced_tab, "高级配置")

    def _update_suffix_ui(self, suffix_type: str):
        """根据选择的后缀类型更新界面"""
        # 隐藏所有特定配置
        self.range_min_spin.setVisible(False)
        self.range_max_spin.setVisible(False)
        self.min_digits_spin.setVisible(False)
        self.max_digits_spin.setVisible(False)
        self.expected_count_spin.setVisible(False)
        self.custom_pattern_edit.setVisible(False)

        # 根据选择显示相应配置
        if suffix_type == "range":
            self.range_min_spin.setVisible(True)
            self.range_max_spin.setVisible(True)
        elif suffix_type == "numeric":
            self.min_digits_spin.setVisible(True)
            self.max_digits_spin.setVisible(True)
            self.expected_count_spin.setVisible(True)
        elif suffix_type == "custom":
            self.custom_pattern_edit.setVisible(True)

    def _browse_folder(self, line_edit: QLineEdit):
        """打开文件夹选择对话框"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", line_edit.text())
        if folder:
            line_edit.setText(folder)

    def _get_config_from_ui(self) -> Dict[str, Any]:
        """从界面收集配置参数"""
        suffix_type = self.suffix_type_combo.currentText()

        # 基本配置
        config = {
            "source_folder": self.source_folder_edit.text(),
            "target_folder": self.target_folder_edit.text(),
            "missing_folder": self.missing_folder_edit.text(),
            "suffix_type": suffix_type,
            "suffix_delimiter": self.suffix_delimiter_edit.text(),
            "expected_extension": self.expected_extension_edit.text(),
            "source_extensions": tuple(ext.strip() for ext in self.source_extensions_edit.text().split(",")),
            "verify_naming": self.verify_naming_check.isChecked(),
            "verify_completeness": self.verify_completeness_check.isChecked(),
            "max_workers": self.max_workers_spin.value() if self.max_workers_spin.value() > 0 else None
        }

        # 后缀类型特定配置
        if suffix_type == "range":
            config.update({
                "suffix_range": (self.range_min_spin.value(), self.range_max_spin.value()),
                "min_digits": 1
            })
        elif suffix_type == "numeric":
            config.update({
                "min_digits": self.min_digits_spin.value(),
                "max_digits": self.max_digits_spin.value() if self.max_digits_spin.value() > 0 else None,
                "expected_count_per_image": self.expected_count_spin.value() if self.expected_count_spin.value() > 0 else None
            })
        elif suffix_type == "custom":
            config["custom_pattern"] = self.custom_pattern_edit.text()

        return config

    def _set_config_to_ui(self, config: Dict[str, Any]):
        """将配置应用到界面"""
        # 设置文件夹
        if "source_folder" in config:
            self.source_folder_edit.setText(config["source_folder"])
        if "target_folder" in config:
            self.target_folder_edit.setText(config["target_folder"])
        if "missing_folder" in config:
            self.missing_folder_edit.setText(config["missing_folder"])

        # 设置基本选项
        if "suffix_delimiter" in config:
            self.suffix_delimiter_edit.setText(config["suffix_delimiter"])
        if "expected_extension" in config:
            self.expected_extension_edit.setText(config["expected_extension"])
        if "source_extensions" in config:
            self.source_extensions_edit.setText(", ".join(config["source_extensions"]))
        if "verify_naming" in config:
            self.verify_naming_check.setChecked(config["verify_naming"])
        if "verify_completeness" in config:
            self.verify_completeness_check.setChecked(config["verify_completeness"])
        if "max_workers" in config and config["max_workers"] is not None:
            self.max_workers_spin.setValue(config["max_workers"])
        else:
            self.max_workers_spin.setValue(0)

        # 设置后缀类型
        if "suffix_type" in config:
            self.suffix_type_combo.setCurrentText(config["suffix_type"])

            # 设置特定类型的配置
            if config["suffix_type"] == "range" and "suffix_range" in config:
                self.range_min_spin.setValue(config["suffix_range"][0])
                self.range_max_spin.setValue(config["suffix_range"][1])
            elif config["suffix_type"] == "numeric":
                if "min_digits" in config:
                    self.min_digits_spin.setValue(config["min_digits"])
                if "max_digits" in config:
                    self.max_digits_spin.setValue(config["max_digits"] if config["max_digits"] is not None else 0)
                if "expected_count_per_image" in config:
                    self.expected_count_spin.setValue(
                        config["expected_count_per_image"] if config["expected_count_per_image"] is not None else 0)
            elif config["suffix_type"] == "custom" and "custom_pattern" in config:
                self.custom_pattern_edit.setText(config["custom_pattern"])

    def _load_config(self):
        """从配置文件加载配置"""
        try:
            with open("./config/IPV_config.json", "r", encoding="utf-8") as f:
                configs = json.load(f)
                if "range_config" in configs:  # 只加载默认配置
                    self._set_config_to_ui(configs["range_config"])
                    self.status_bar.showMessage("配置已加载")
        except (FileNotFoundError, json.JSONDecodeError):
            self.status_bar.showMessage("未找到配置文件或格式错误")

    def _load_preset(self):
        """加载选定的预设配置"""
        preset_key = self.preset_combo.currentText()
        try:
            with open("./config/IPV_config.json", "r", encoding="utf-8") as f:
                configs = json.load(f)
                if preset_key in configs:
                    self._set_config_to_ui(configs[preset_key])
                    self.status_bar.showMessage(f"预设 '{preset_key}' 已加载")
                else:
                    self.status_bar.showMessage(f"预设 '{preset_key}' 不存在")
        except (FileNotFoundError, json.JSONDecodeError):
            self.status_bar.showMessage("未找到配置文件或格式错误")

    def _save_preset(self):
        """将当前配置保存为预设"""
        preset_key = self.preset_combo.currentText()
        config = self._get_config_from_ui()

        try:
            # 读取现有配置
            try:
                with open("./config/IPV_config.json", "r", encoding="utf-8") as f:
                    configs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                configs = {}

            # 更新配置
            configs[preset_key] = config

            # 保存配置
            with open("./config/IPV_config.json", "w", encoding="utf-8") as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)  # type: ignore

            self.status_bar.showMessage(f"配置已保存为预设 '{preset_key}'")
        except Exception as e:
            self.status_bar.showMessage(f"保存配置失败: {str(e)}")

    def save_config(self):
        """保存当前配置"""
        self._save_preset()

    def start_verification(self):
        """开始验证过程"""
        # 获取配置
        config = self._get_config_from_ui()

        # 验证必要的路径是否存在
        for path_key in ["source_folder", "target_folder", "missing_folder"]:
            if not config[path_key] or not os.path.exists(config[path_key]):
                QMessageBox.warning(self, "路径错误", f"路径 '{config[path_key]}' 不存在或未设置")
                return

        # 清空日志和进度条
        self.log_output.clear()
        self.progress_bar.setValue(0)

        # 创建并配置验证工作线程
        self.verifier_worker = VerifierWorker(config)

        # 连接信号
        self.verifier_worker.signals.progress_updated.connect(self.update_progress)
        self.verifier_worker.signals.log_message.connect(self.append_log)
        self.verifier_worker.signals.finished.connect(self.verification_finished)
        self.verifier_worker.signals.error.connect(self.verification_error)

        # 更新UI状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_bar.showMessage("验证中...")

        # 切换到验证输出选项卡
        self.tab_widget.setCurrentIndex(self.output_tab_index)

        # 启动工作线程
        self.threadpool.start(self.verifier_worker)

    def stop_verification(self):
        """停止验证过程"""
        if self.verifier_worker:
            self.verifier_worker.stop()
            self.append_log("正在停止验证，请等待...")
            self.status_bar.showMessage("正在停止...")

    def update_progress(self, current: int, total: int, percent: int):
        """更新进度条"""
        self.progress_bar.setValue(percent)

    def append_log(self, message: str):
        """添加日志消息"""
        self.log_output.append(message)
        # 滚动到底部
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_output.setTextCursor(cursor)

    def verification_finished(self, result: Dict):
        """验证完成处理"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(100)

        # 显示摘要
        total_issues = len(result['missing_images']) + len(result['incomplete_images']) + len(result['naming_errors'])

        if total_issues == 0:
            self.status_bar.showMessage("验证完成: 完美!")
            QMessageBox.information(self, "验证完成", "太棒了！所有图片都已正确处理且命名规范。")
        else:
            self.status_bar.showMessage(f"验证完成: 发现 {total_issues} 个问题")
            QMessageBox.warning(
                self,
                "验证完成",
                f"验证已完成，但发现 {total_issues} 个问题:\n"
                f"- 完全未处理: {len(result['missing_images'])} 张图片\n"
                f"- 处理不完整: {len(result['incomplete_images'])} 张图片\n"
                f"- 命名不规范: {len(result['naming_errors'])} 张图片"
            )

    def verification_error(self, error_message: str):
        """验证过程中的错误处理"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("验证出错")

        # 显示错误信息
        self.append_log(f"错误: {error_message}")
        QMessageBox.critical(self, "验证错误", f"验证过程中发生错误:\n{error_message}")


def main():
    app = QApplication(sys.argv)
    window = ImageVerifierGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()