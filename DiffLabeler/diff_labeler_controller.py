"""
差分标注工具的控制器层 - 连接模型和视图
处理用户交互逻辑并更新视图
使用信号槽机制更新UI，提高代码解耦性
"""
import os
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSlot, QThread, pyqtSignal
from typing import Dict, List, Tuple, Optional
from typing import TYPE_CHECKING

# 避免循环导入：仅在类型检查时引入 DiffLabelerView
if TYPE_CHECKING:
    from DiffLabeler.diff_labeler_view import DiffLabelerView

from DiffLabeler.diff_labeler_model import DiffLabelerModel

# 导入自定义日志记录器
from utils.logger import LogManager
# 创建视图层日志记录器
logger = LogManager.get_logger("DL", level="info")


class ProcessingWorker(QThread):
    """处理任务的工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(int, int, list)  # 成功数、失败数、错误列表
    processing_started = pyqtSignal()  # 新增：处理开始信号
    processing_error = pyqtSignal(str)  # 新增：处理过程中的错误信号

    def __init__(self, model: DiffLabelerModel, by_sequence: bool = False):
        super().__init__()
        self.model = model
        self.by_sequence = by_sequence  # 是否按序列处理
        self.is_cancelled = False

    def run(self):
        """执行批处理任务"""
        try:
            # 发送处理开始信号
            self.processing_started.emit()

            def update_progress(progress):
                if self.isInterruptionRequested():
                    self.is_cancelled = True
                    return False  # 返回False表示中断处理
                self.progress_updated.emit(progress)
                return True

            if self.by_sequence:
                processed, failed, errors, _ = self.model.batch_process_by_sequence(update_progress)
            else:
                processed, failed, errors, _ = self.model.batch_process(update_progress)

            # 如果任务被取消，不发送完成信号
            if not self.is_cancelled:
                self.processing_finished.emit(processed, failed, errors)

        except Exception as e:
            error_msg = f"处理过程中发生错误: {e}"
            logger.error(error_msg)
            self.processing_error.emit(error_msg)
            self.processing_finished.emit(0, 0, [str(e)])

    def cancel(self):
        """取消处理任务"""
        self.is_cancelled = True
        self.requestInterruption()


class PreviewWorker(QThread):
    """预览生成的工作线程"""

    # 定义信号
    preview_ready = pyqtSignal(np.ndarray, np.ndarray, np.ndarray, np.ndarray, int)  # bg, sample, diff, hd_img, num_objects
    preview_error = pyqtSignal(str)  # 错误信息

    def __init__(self, model: DiffLabelerModel, bg_path: str, sample_path: str):
        super().__init__()
        self.model = model
        self.bg_path = bg_path
        self.sample_path = sample_path

    def run(self):
        """执行预览生成任务"""
        try:
            # 读取图像 - 使用中文路径兼容方式
            bg_img = cv2.imdecode(np.fromfile(self.bg_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            sample_img = cv2.imdecode(np.fromfile(self.sample_path, dtype=np.uint8), cv2.IMREAD_COLOR)

            if bg_img is None or sample_img is None:
                self.preview_error.emit("错误: 图像读取失败")
                return

            hd_img = sample_img.copy()

            # 计算差异和边界框
            diff_mask, bboxes = self.model.compute_image_diff(self.bg_path, self.sample_path)

            if diff_mask is None:
                self.preview_error.emit("错误: 差异计算失败")
                return

            img_height, img_width = diff_mask.shape
            for bbox in bboxes:
                # 计算像素坐标（使用原始图像尺寸）
                center_x = int(bbox.x_center * img_width)
                center_y = int(bbox.y_center * img_height)
                width = int(bbox.width * img_width)
                height = int(bbox.height * img_height)
                left = center_x - width // 2
                top = center_y - height // 2
                # 绘制边界框（使用更醒目的参数）
                color = (0, 255, 0)  # 绿色
                cv2.rectangle(hd_img, (left, top),
                              (left + width, top + height), color, 3)

                # 绘制文字背景
                label_text = f"{bbox.label_id}"
                (text_width, text_height), _ = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(hd_img,
                              (left, top - text_height - 10),
                              (left + text_width, top),
                              color, -1)

                # 绘制标签文字
                cv2.putText(hd_img, label_text, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

            # 发送预览就绪信号
            self.preview_ready.emit(bg_img, sample_img, diff_mask, hd_img, len(bboxes))

        except Exception as e:
            error_msg = f"预览生成失败: {e}"
            logger.error(error_msg)  # 这里保留错误日志
            self.preview_error.emit(error_msg)


class DiffLabelerController(QObject):
    """差分标注工具的控制器"""

    # 定义控制器信号
    config_saved = pyqtSignal(bool, str)  # 配置保存结果信号 (成功?, 路径)
    config_loaded = pyqtSignal(bool, str, dict)  # 配置加载结果信号 (成功?, 路径, 配置数据)
    status_message = pyqtSignal(str, bool)  # 状态消息信号 (消息, 是否错误)

    def __init__(self, model: DiffLabelerModel, view: 'DiffLabelerView'):
        super().__init__(parent=view)  # 绑定父对象生命周期
        self.model = model
        self.view = view

        # 连接视图信号到控制器槽
        self.view.config_changed.connect(self.update_config)
        self.view.process_requested.connect(self.start_processing)
        self.view.preview_requested.connect(self.generate_preview)
        self.view.cancel_requested.connect(self.cancel_processing)  # 新增：取消处理的信号连接

        # 连接配置保存和加载的视图信号
        self.view.save_config_requested.connect(self.save_config)
        self.view.load_config_requested.connect(self.load_config)
        self.view.sequence_process_requested.connect(self.start_sequence_processing)

        # 连接控制器信号到视图槽
        self.config_saved.connect(self.view.on_config_saved)
        self.config_loaded.connect(self.view.on_config_loaded)
        self.status_message.connect(self.view.show_status_message)

        # 工作线程
        self.worker = None
        self.preview_worker = None

    @pyqtSlot(dict)
    def update_config(self, config: Dict):
        """更新模型配置"""
        self.model.set_config(config)
        self.status_message.emit("配置已更新", False)

    @pyqtSlot(str)
    def save_config(self, config_path: str = None):
        """保存当前配置"""
        # 首先更新模型配置
        config = self.view.get_current_config()
        self.model.set_config(config)

        # 然后保存配置
        success = self.model.save_config(config_path)
        self.config_saved.emit(success, config_path or self.model.config_file)

    @pyqtSlot(str)
    def load_config(self, config_path: str = None):
        """加载配置"""
        success = self.model.load_config(config_path)
        if success:
            # 获取最新配置
            config = {
                "bg_dir": self.model.bg_dir,
                "sample_dir": self.model.sample_dir,
                "output_dir": self.model.output_dir,
                "min_diff_area": self.model.min_diff_area,
                "diff_threshold": self.model.diff_threshold,
                "default_label": self.model.default_label,
                "bbox_padding": self.model.bbox_padding,
                "min_merge_iou": self.model.min_merge_iou
            }
            # 发送配置加载成功信号
            self.config_loaded.emit(True, config_path or self.model.config_file, config)
        else:
            self.config_loaded.emit(False, config_path or "", {})

    @pyqtSlot()
    def start_processing(self):
        """开始标准批处理任务"""
        self._start_processing_task(by_sequence=False)

    @pyqtSlot()
    def start_sequence_processing(self):
        """开始按序列批处理任务"""
        self._start_processing_task(by_sequence=True)

    @pyqtSlot()
    def cancel_processing(self):
        """取消当前处理任务"""
        if self.worker and self.worker.isRunning():
            logger.info("取消处理任务...")
            self.worker.cancel()
            self.worker.wait(1000)  # 等待最多1秒
            # 手动调用 on_processing_finished 以恢复UI状态
            if hasattr(self.view, 'on_processing_finished'):
                self.view.on_processing_finished(0, 0, [])
            self.status_message.emit("处理任务已取消", False)

    def _start_processing_task(self, by_sequence: bool = False):
        try:
            # 如果已有工作线程在运行，先停止它
            if self.worker and self.worker.isRunning():
                self.worker.cancel()
                self.worker.wait(1000)  # 等待1秒

            # 检查配置
            config = self.view.get_current_config()
            if not config["bg_dir"] or not config["sample_dir"] or not config["output_dir"]:
                error_msg = "请设置所有必要的目录"
                self.status_message.emit(error_msg, True)
                return

            # 更新模型配置
            self.model.set_config(config)

            # 创建并启动工作线程
            self.worker = ProcessingWorker(self.model, by_sequence)

            # 连接工作线程信号到视图槽
            self.worker.progress_updated.connect(self.view.set_progress)
            self.worker.processing_started.connect(self.view.on_processing_started)
            self.worker.processing_finished.connect(self.view.on_processing_finished)
            self.worker.processing_error.connect(lambda msg: self.status_message.emit(msg, True))

            # 启动工作线程
            self.worker.start()

        except Exception as e:
            error_msg = f"启动处理任务时发生错误: {e}"
            logger.error(error_msg)  # 保留关键错误日志
            self.status_message.emit(error_msg, True)

    @pyqtSlot(str, str)
    def generate_preview(self, bg_filename: str, sample_filename: str):
        """生成预览"""
        try:
            # 检查配置
            config = self.view.get_current_config()
            if not config["bg_dir"] or not config["sample_dir"]:
                self.status_message.emit("请设置背景图和样本图目录", True)
                return

            # 更新模型配置
            self.model.set_config(config)

            # 构建文件路径
            bg_path = os.path.join(config["bg_dir"], bg_filename)
            sample_path = os.path.join(config["sample_dir"], sample_filename)

            # 检查文件是否存在
            if not os.path.exists(bg_path):
                self.status_message.emit(f"背景图文件不存在: {bg_path}", True)
                return

            if not os.path.exists(sample_path):
                self.status_message.emit(f"样本图文件不存在: {sample_path}", True)
                return

            # 如果已有预览工作线程在运行，先停止它
            if self.preview_worker and self.preview_worker.isRunning():
                self.preview_worker.wait()

            # 创建并启动预览工作线程
            self.preview_worker = PreviewWorker(self.model, bg_path, sample_path)

            # 连接预览工作线程信号
            self.preview_worker.preview_ready.connect(self.view.on_preview_ready)
            self.preview_worker.preview_error.connect(lambda msg: self.status_message.emit(msg, True))

            # 显示预览加载状态
            self.status_message.emit("正在生成预览...", False)

            # 启动预览工作线程
            self.preview_worker.start()

        except Exception as e:
            error_msg = f"预览生成失败: {e}"
            logger.error(error_msg)  # 保留关键错误日志
            self.status_message.emit(error_msg, True)