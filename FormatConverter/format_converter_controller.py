"""
格式转换工具的控制器层 - 连接模型和视图
处理用户交互逻辑并更新视图
"""
import os
from PyQt6.QtCore import QObject, pyqtSlot, QThread, pyqtSignal
from typing import Dict, List, Optional, Union
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FormatConverter.format_converter_view import FormatConverterView

from FormatConverter.format_converter_model import FormatConverterModel
from utils.logger import LogManager

logger = LogManager.get_logger("FC", level="info")


class ConversionWorker(QThread):
    """转换任务的工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(int, int, list)  # 成功数、失败数、错误列表
    conversion_started = pyqtSignal()
    conversion_error = pyqtSignal(str)

    def __init__(self, model: FormatConverterModel):
        super().__init__()
        self.model = model
        self.is_cancelled = False

    def run(self):
        """执行转换任务"""
        try:
            self.conversion_started.emit()

            def update_progress(progress):
                if self.isInterruptionRequested():
                    self.is_cancelled = True
                    return False
                self.progress_updated.emit(progress)
                return True

            success, failed, errors, elapsed = self.model.batch_convert(update_progress)

            if not self.is_cancelled:
                self.conversion_finished.emit(success, failed, errors)

        except Exception as e:
            error_msg = f"转换过程中发生错误: {e}"
            logger.error(error_msg)
            self.conversion_error.emit(error_msg)
            self.conversion_finished.emit(0, 0, [str(e)])

    def cancel(self):
        """取消转换任务"""
        self.is_cancelled = True
        self.requestInterruption()


class FormatConverterController(QObject):
    """格式转换工具的控制器"""

    # 定义控制器信号
    config_saved = pyqtSignal(bool, str)
    config_loaded = pyqtSignal(bool, str, dict)
    status_message = pyqtSignal(str, bool)  # 消息，是否错误
    labels_discovered = pyqtSignal(dict)    # 发现的标签

    def __init__(self, model: FormatConverterModel, view: 'FormatConverterView'):
        super().__init__(parent=view)
        self.model = model
        self.view = view
        self.last_classes_labels = {}  # 保存最后一次加载的classes.txt标签

        # 连接视图信号到控制器槽
        self.view.config_changed.connect(self.update_config)
        self.view.conversion_requested.connect(self.start_conversion)
        self.view.cancel_requested.connect(self.cancel_conversion)
        self.view.save_config_requested.connect(self.save_config)
        self.view.load_config_requested.connect(self.load_config)
        self.view.discover_labels_requested.connect(self.discover_labels)

        # 连接控制器信号到视图槽
        self.config_saved.connect(self.view.on_config_saved)
        self.config_loaded.connect(self.view.on_config_loaded)
        self.status_message.connect(self.view.show_status_message)
        self.labels_discovered.connect(self.view.on_labels_discovered)

        # 工作线程
        self.worker = None

    @pyqtSlot(dict)
    def update_config(self, config: Dict):
        """更新模型配置"""
        self.model.set_config(config)
        self.status_message.emit("配置已更新", False)

    @pyqtSlot()
    def start_conversion(self):
        """开始转换任务"""
        try:
            # 检查必要配置
            config = self.view.get_current_config()
            if not all([config.get("source_dir"), config.get("target_dir"), config.get("image_dir")]):
                self.status_message.emit("请设置所有必要的目录", True)
                return

            # 更新模型配置
            self.model.set_config(config)

            # 如果已有工作线程在运行，先停止
            if self.worker and self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(1000)

            # 创建并启动工作线程
            self.worker = ConversionWorker(self.model)

            # 连接工作线程信号
            self.worker.progress_updated.connect(self.view.set_progress)
            self.worker.conversion_started.connect(self.view.on_conversion_started)
            self.worker.conversion_finished.connect(self.view.on_conversion_finished)
            self.worker.conversion_error.connect(lambda msg: self.status_message.emit(msg, True))

            # 启动工作线程
            self.worker.start()

        except Exception as e:
            error_msg = f"启动转换任务失败: {e}"
            logger.error(error_msg)
            self.status_message.emit(error_msg, True)

    @pyqtSlot()
    def cancel_conversion(self):
        """取消转换任务"""
        if self.worker and self.worker.isRunning():
            logger.info("取消转换任务...")
            self.worker.cancel()
            self.worker.wait(1000)
            if hasattr(self.view, 'on_conversion_finished'):
                self.view.on_conversion_finished(0, 0, [])
            self.status_message.emit("转换任务已取消", False)

    @pyqtSlot(str)
    def save_config(self, config_path: str = None):
        """保存配置"""
        config = self.view.get_current_config()
        self.model.set_config(config)

        success = self.model.save_config(config_path)
        self.config_saved.emit(success, config_path or self.model.config_file)

    @pyqtSlot(str)
    def load_config(self, config_path: str = None):
        """加载配置"""
        success = self.model.load_config(config_path)
        if success:
            config = {
                "source_dir": self.model.source_dir,
                "target_dir": self.model.target_dir,
                "image_dir": self.model.image_dir,
                "conversion_mode": self.model.conversion_mode,
                "label_mapping": self.model.label_mapping,
                "use_classes_txt": self.model.use_classes_txt,
                "classes_txt_path": self.model.classes_txt_path
            }
            self.config_loaded.emit(True, config_path or self.model.config_file, config)
        else:
            self.config_loaded.emit(False, config_path or "", {})

    @pyqtSlot()
    def discover_labels(self):
        """发现标签"""
        try:
            # 更新源目录配置
            config = self.view.get_current_config()
            self.model.set_config(config)

            # 发现标签
            labels = self.model.discover_labels()

            # 如果是YOLO格式且启用了classes.txt优先级，获取classes.txt标签
            classes_labels = {}
            if config.get("conversion_mode") == "yolo_to_labelme" and config.get("use_classes_txt", True):
                # 使用用户指定的classes.txt路径，如果为空则使用默认路径
                classes_txt_path = config.get("classes_txt_path", "")
                classes_labels = self.model.load_classes_txt(classes_txt_path if classes_txt_path else None)
                if classes_labels:
                    self.last_classes_labels = classes_labels
                    logger.info(f"使用classes.txt中的标签: {len(classes_labels.get('yolo', []))}个类别")

            self.labels_discovered.emit(labels)

            total_labels = len(labels.get("yolo", [])) + len(labels.get("labelme", []))
            self.status_message.emit(f"发现 {total_labels} 个标签", False)

        except Exception as e:
            error_msg = f"发现标签失败: {e}"
            logger.error(error_msg)
            self.status_message.emit(error_msg, True)
