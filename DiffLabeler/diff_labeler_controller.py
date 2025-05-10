"""
差分标注工具的控制器层 - 连接模型和视图
处理用户交互逻辑并更新视图
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

# 导入自定义日志记录器替代标准logging
from utils.logger import default_logger as logger


class ProcessingWorker(QThread):
    """处理任务的工作线程"""

    # 定义信号
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(int, int, list)  # 成功数、失败数、错误列表

    def __init__(self, model: DiffLabelerModel, by_sequence: bool = False):
        super().__init__()
        self.model = model
        self.by_sequence = by_sequence  # 是否按序列处理

    def run(self):
        """执行批处理任务"""
        try:
            logger.info("开始批量处理...")

            def update_progress(progress):
                self.progress_updated.emit(progress)

            if self.by_sequence:
                logger.info("使用序列模式处理图像...")
                processed, failed, errors = self.model.batch_process_by_sequence(update_progress)
            else:
                logger.info("使用标准模式处理图像...")
                processed, failed, errors = self.model.batch_process(update_progress)
            self.processing_finished.emit(processed, failed, errors)

            # 记录处理日志
            if errors:
                logger.warning(f"处理完成。成功: {processed}, 失败: {failed}")
                for error in errors[:5]:  # 只显示前5个错误
                    logger.error(f"错误: {error}")
                if len(errors) > 5:
                    logger.warning(f"... 共有 {len(errors)} 个错误")
            else:
                logger.success(f"处理完成。成功处理 {processed} 个图像")

        except Exception as e:
            logger.error(f"处理过程中发生错误: {e}")
            self.processing_finished.emit(0, 0, [str(e)])


class DiffLabelerController(QObject):
    """差分标注工具的控制器"""

    def __init__(self, model: DiffLabelerModel, view: 'DiffLabelerView'):
        super().__init__()
        self.model = model
        self.view = view

        # 连接视图信号到控制器槽
        self.view.config_changed.connect(self.update_config)
        self.view.process_requested.connect(self.start_processing)
        self.view.preview_requested.connect(self.generate_preview)

        # 连接配置保存和加载的视图信号
        self.view.save_config_requested.connect(self.save_config)
        self.view.load_config_requested.connect(self.load_config)
        self.view.sequence_process_requested.connect(self.start_sequence_processing)

        # 工作线程
        self.worker = None

    @pyqtSlot(dict)
    def update_config(self, config: Dict):
        """更新模型配置"""
        self.model.set_config(config)
        logger.info("配置已更新")

    @pyqtSlot(str)
    def save_config(self, config_path: str = None):
        """保存当前配置"""
        # 首先更新模型配置
        config = self.view.get_current_config()
        self.model.set_config(config)

        # 然后保存配置
        success = self.model.save_config(config_path)
        if success:
            logger.debug(f"配置已保存至: {config_path or self.model.config_file}")
        else:
            logger.error("配置保存失败")

    @pyqtSlot(str)
    def load_config(self, config_path: str = None):
        """加载配置"""
        success = self.model.load_config(config_path)
        if success:
            # 更新视图显示
            self.view.update_from_config({
                "bg_dir": self.model.bg_dir,
                "sample_dir": self.model.sample_dir,
                "output_dir": self.model.output_dir,
                "min_diff_area": self.model.min_diff_area,
                "diff_threshold": self.model.diff_threshold,
                "default_label": self.model.default_label,
                "bbox_padding": self.model.bbox_padding,
                "min_merge_iou": self.model.min_merge_iou
            })

            # logger.success(f"已从 {config_path or self.model.config_file} 加载配置")
        else:
            logger.error("配置加载失败")

    @pyqtSlot()
    def start_processing(self):
        """开始标准批处理任务"""
        self._start_processing_task(by_sequence=False)

    @pyqtSlot()
    def start_sequence_processing(self):
        """开始按序列批处理任务"""
        self._start_processing_task(by_sequence=True)

    def _start_processing_task(self, by_sequence: bool = False):
        """通用处理任务启动函数"""
        try:  # 新增异常捕获
            # 检查配置
            config = self.view.get_current_config()
            if not config["bg_dir"] or not config["sample_dir"] or not config["output_dir"]:
                logger.error("错误: 请设置所有必要的目录")
                return

            # 更新模型配置
            self.model.set_config(config)

            # 创建并启动工作线程
            self.worker = ProcessingWorker(self.model, by_sequence)
            self.worker.progress_updated.connect(self.view.set_progress)
            self.worker.processing_finished.connect(self.on_processing_finished)

            # 禁用处理按钮
            self.view.process_button.setEnabled(False)
            if hasattr(self.view, 'sequence_process_button'):
                self.view.sequence_process_button.setEnabled(False)

            # 启动工作线程
            self.worker.start()
        except Exception as e:  # 新增
            logger.critical(f"启动处理任务时发生严重错误: {e}", exc_info=True)

    @pyqtSlot(str, str)
    def generate_preview(self, bg_filename: str, sample_filename: str):
        """生成预览"""
        # 检查配置
        config = self.view.get_current_config()
        if not config["bg_dir"] or not config["sample_dir"]:
            logger.error("错误: 请设置背景图和样本图目录")
            return

        # 更新模型配置
        self.model.set_config(config)

        # 构建文件路径
        bg_path = os.path.join(config["bg_dir"], bg_filename)
        sample_path = os.path.join(config["sample_dir"], sample_filename)

        # 检查文件是否存在
        if not os.path.exists(bg_path):
            logger.error(f"错误: 背景图文件不存在 - {bg_path}")
            return

        if not os.path.exists(sample_path):
            logger.error(f"错误: 样本图文件不存在 - {sample_path}")
            return

        try:
            # 读取图像 - 使用中文路径兼容方式
            bg_img = cv2.imdecode(np.fromfile(bg_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            sample_img = cv2.imdecode(np.fromfile(sample_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            hd_img = sample_img.copy()

            if bg_img is None or sample_img is None:
                logger.error("错误: 图像读取失败")
                return

            # 计算差异和边界框
            diff_mask, bboxes = self.model.compute_image_diff(bg_path, sample_path)

            if diff_mask is None:
                logger.error("错误: 差异计算失败")
                return

            # 在差异图上绘制边界框
            diff_with_boxes = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)

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

            # 更新预览图像
            self.view.update_preview(bg_img, sample_img, diff_with_boxes, hd_img)

            # 记录找到的对象数
            logger.debug(f"找到 {len(bboxes)} 个对象")

        except Exception as e:
            logger.error(f"预览生成失败: {e}")

    @pyqtSlot(int, int, list)
    def on_processing_finished(self, processed: int, failed: int, errors: List[str]):
        """处理完成的回调"""
        # 重新启用处理按钮
        self.view.process_button.setEnabled(True)
        if hasattr(self.view, 'sequence_process_button'):
            self.view.sequence_process_button.setEnabled(True)

        # 更新进度条
        self.view.set_progress(100)
