"""
差分标注工具的模型层 - 负责核心逻辑处理
包括图像差分、目标检测、边界框计算和标注文件生成
"""
import time
import threading
import os
import cv2
import json
import numpy as np
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Optional, Any
import re

# 导入自定义日志记录器
from utils.logger import LogManager
# 创建视图层日志记录器
logger = LogManager.get_logger("DL", level="info")

@dataclass
class BoundingBox:
    """边界框数据类"""
    label_id: int
    x_center: float  # 归一化的中心x坐标 (相对于图像宽度)
    y_center: float  # 归一化的中心y坐标 (相对于图像高度)
    width: float     # 归一化的宽度 (相对于图像宽度)
    height: float    # 归一化的高度 (相对于图像高度)

    def to_yolo_format(self) -> str:
        """转换为YOLO格式的字符串"""
        return f"{self.label_id} {self.x_center:.6f} {self.y_center:.6f} {self.width:.6f} {self.height:.6f}"

    def get_absolute_coords(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """获取绝对坐标 (x1, y1, x2, y2)"""
        x1 = int((self.x_center - self.width / 2) * img_width)
        y1 = int((self.y_center - self.height / 2) * img_height)
        x2 = int((self.x_center + self.width / 2) * img_width)
        y2 = int((self.y_center + self.height / 2) * img_height)
        return x1, y1, x2, y2

    def get_area(self) -> float:
        """获取归一化面积"""
        return self.width * self.height

    def iou(self, other: 'BoundingBox') -> float:
        """计算两个边界框的交并比(IoU)"""
        # 计算交集区域
        x_left = max(self.x_center - self.width / 2, other.x_center - other.width / 2)
        y_top = max(self.y_center - self.height / 2, other.y_center - other.height / 2)
        x_right = min(self.x_center + self.width / 2, other.x_center + other.width / 2)
        y_bottom = min(self.y_center + self.height / 2, other.y_center + other.height / 2)

        # 检查是否有交集
        if x_right < x_left or y_bottom < y_top:
            return 0.0

        # 计算交集面积
        intersection_area = (x_right - x_left) * (y_bottom - y_top)

        # 计算并集面积
        self_area = self.width * self.height
        other_area = other.width * other.height
        union_area = self_area + other_area - intersection_area

        # 返回IoU
        return intersection_area / union_area


class DiffLabelerModel:
    """差分标注工具的模型层"""

    def __init__(self):
        # 默认配置
        self.bg_dir = ""            # 背景图片目录
        self.sample_dir = ""        # 样本图片目录
        self.output_dir = ""        # 标注输出目录
        self.min_diff_area = 100    # 最小差异区域大小 (像素)
        self.diff_threshold = 30    # 差异检测阈值
        self.default_label = 0      # 默认标签ID
        self.bbox_padding = 0       # 边界框额外填充量(像素)
        self.min_merge_iou = 0.3    # 边界框合并阈值
        self.config_file = "config\\DI_config.json"  # 配置文件路径

    def set_config(self, config: Dict):
        """设置配置参数"""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"未知的配置参数: {key}")

    def save_config(self, config_path: str = None) -> bool:
        """
        保存当前配置到文件

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径

        Returns:
            bool: 是否保存成功
        """
        if config_path is None:
            config_path = self.config_file

        try:
            # 准备要保存的配置
            config_data = {
                "bg_dir": self.bg_dir,
                "sample_dir": self.sample_dir,
                "output_dir": self.output_dir,
                "min_diff_area": self.min_diff_area,
                "diff_threshold": self.diff_threshold,
                "default_label": self.default_label,
                "bbox_padding": self.bbox_padding,
                "min_merge_iou": self.min_merge_iou
            }

            # 写入JSON文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def load_config(self, config_path: str = None) -> bool:
        """
        从文件加载配置

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径

        Returns:
            bool: 是否加载成功
        """
        if config_path is None:
            config_path = self.config_file

        if not os.path.exists(config_path):
            logger.warning("配置文件不存在")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            self.set_config(config_data)
            return True

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False

    def compute_image_diff(self, bg_path: str, sample_path: str) -> Tuple[np.ndarray, List[BoundingBox]]:
        """
        计算背景图和样本图的差异，生成边界框

        Args:
            bg_path: 背景图路径
            sample_path: 样本图路径

        Returns:
            diff_mask: 差异掩码图
            bounding_boxes: 检测到的边界框列表
        """
        try:
            # 读取图像 - 使用中文路径兼容方式
            bg_img = cv2.imdecode(np.fromfile(bg_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            sample_img = cv2.imdecode(np.fromfile(sample_path, dtype=np.uint8), cv2.IMREAD_COLOR)

            if bg_img is None or sample_img is None:
                logger.error("图像读取失败")
                return None, []

            # 确保两图大小一致
            if bg_img.shape != sample_img.shape:
                sample_img = cv2.resize(sample_img, (bg_img.shape[1], bg_img.shape[0]))

            # 计算绝对差异
            diff = cv2.absdiff(bg_img, sample_img)

            # 分别处理每个颜色通道
            b_diff, g_diff, r_diff = cv2.split(diff)

            # 对每个通道应用阈值
            _, b_mask = cv2.threshold(b_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)
            _, g_mask = cv2.threshold(g_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)
            _, r_mask = cv2.threshold(r_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)

            # 合并通道掩码
            mask = cv2.bitwise_or(cv2.bitwise_or(b_mask, g_mask), r_mask)

            # 形态学操作来去除噪点并连接相近区域
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # 寻找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # 图像尺寸用于归一化
            img_height, img_width = mask.shape

            # 生成边界框
            bounding_boxes = []
            for contour in contours:
                area = cv2.contourArea(contour)

                # 过滤小区域
                if area < self.min_diff_area:
                    continue

                # 获取轮廓的边界框
                x, y, w, h = cv2.boundingRect(contour)

                # 应用边界框填充（增加边界框尺寸）
                padding = self.bbox_padding
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(img_width - x, w + 2 * padding)
                h = min(img_height - y, h + 2 * padding)

                # 计算归一化的中心坐标和尺寸
                x_center = (x + w / 2) / img_width
                y_center = (y + h / 2) / img_height
                width = w / img_width
                height = h / img_height

                # 创建边界框对象
                bbox = BoundingBox(
                    label_id=self.default_label,
                    x_center=x_center,
                    y_center=y_center,
                    width=width,
                    height=height
                )

                bounding_boxes.append(bbox)

            # 如果启用了边界框合并功能且有多个边界框
            if self.min_merge_iou > 0 and len(bounding_boxes) > 1:
                bounding_boxes = self.merge_overlapping_boxes(bounding_boxes, img_width, img_height)

            return mask, bounding_boxes

        except Exception as e:
            logger.error(f"计算图像差异失败: {e}")
            return None, []

    def merge_overlapping_boxes(self, boxes: List[BoundingBox], img_width: int, img_height: int) -> List[BoundingBox]:
        """
        合并重叠的边界框

        Args:
            boxes: 边界框列表
            img_width: 图像宽度
            img_height: 图像高度

        Returns:
            合并后的边界框列表
        """
        if not boxes:
            return []

        # 对边界框按面积从大到小排序
        boxes.sort(key=lambda box: box.get_area(), reverse=True)

        result = []
        merged_indices = set()

        for i in range(len(boxes)):
            if i in merged_indices:
                continue

            current_box = boxes[i]
            merged_boxes = [current_box]

            # 查找与当前框重叠度高的框
            for j in range(i + 1, len(boxes)):
                if j in merged_indices:
                    continue

                iou = current_box.iou(boxes[j])
                if iou > self.min_merge_iou:
                    merged_boxes.append(boxes[j])
                    merged_indices.add(j)

            # 如果有需要合并的框
            if len(merged_boxes) > 1:
                # 计算合并后的边界框
                merged_box = self.create_merged_box(merged_boxes, img_width, img_height)
                result.append(merged_box)
            else:
                result.append(current_box)

        return result

    def create_merged_box(self, boxes: List[BoundingBox], img_width: int, img_height: int) -> BoundingBox:
        """
        从多个边界框创建一个合并的边界框

        Args:
            boxes: 要合并的边界框列表
            img_width: 图像宽度
            img_height: 图像高度

        Returns:
            合并后的边界框
        """
        # 获取所有框的绝对坐标
        all_coords = [box.get_absolute_coords(img_width, img_height) for box in boxes]

        # 找出最小和最大坐标
        min_x = min(coords[0] for coords in all_coords)
        min_y = min(coords[1] for coords in all_coords)
        max_x = max(coords[2] for coords in all_coords)
        max_y = max(coords[3] for coords in all_coords)

        # 计算归一化的中心坐标和尺寸
        width = (max_x - min_x) / img_width
        height = (max_y - min_y) / img_height
        x_center = (min_x + (max_x - min_x) / 2) / img_width
        y_center = (min_y + (max_y - min_y) / 2) / img_height

        # 创建新的边界框
        return BoundingBox(
            label_id=boxes[0].label_id,  # 使用第一个框的标签
            x_center=x_center,
            y_center=y_center,
            width=width,
            height=height
        )

    def process_image_pair(self, bg_filename: str, sample_filename: str) -> Tuple[bool, str]:
        """
        处理一对背景图和样本图，生成标注文件

        Args:
            bg_filename: 背景图文件名
            sample_filename: 样本图文件名

        Returns:
            success: 是否成功
            message: 处理结果信息
        """
        bg_path = os.path.join(self.bg_dir, bg_filename)
        sample_path = os.path.join(self.sample_dir, sample_filename)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 计算输出文件名 (与样本图同名但扩展名为.txt)
        base_name = os.path.splitext(sample_filename)[0]
        output_path = os.path.join(self.output_dir, f"{base_name}.txt")

        # 检查文件是否存在
        if not os.path.exists(bg_path):
            return False, f"背景图不存在: {bg_path}"
        if not os.path.exists(sample_path):
            return False, f"样本图不存在: {sample_path}"

        # 计算差异并获取边界框
        diff_mask, bboxes = self.compute_image_diff(bg_path, sample_path)

        if diff_mask is None:
            return False, f"处理图像失败: {sample_filename}"

        # 写入标注文件
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for bbox in bboxes:
                    f.write(bbox.to_yolo_format() + '\n')

            return True, f"成功处理 {sample_filename}, 检测到 {len(bboxes)} 个对象"

        except Exception as e:
            logger.error(f"写入标注文件时出错: {e}")
            return False, f"写入标注文件失败: {e}"

    def extract_base_name(self, filename: str) -> str:
        """
        提取文件的基本名称（移除后缀和扩展名）

        Args:
            filename: 原始文件名

        Returns:
            不包含后缀的基本名称
        """
        # 先移除扩展名
        base_name = os.path.splitext(filename)[0]

        # 使用正则表达式移除常见后缀模式
        patterns = [
            r'_标记$', r'_样本$', r'_edited$', r'_marked$', r'_sample$',
            r'[-_]v\d+$',  # 如 image_v1, image-v2
            r'[-_]\d+$',   # 如 image_1, image-2
            r'[-_]后$',     # 如 image_后
            r'[-_]修改$',    # 如 image_修改
        ]

        result = base_name
        for pattern in patterns:
            result = re.sub(pattern, '', result)

        return result

    def find_matching_bg(self, sample_filename: str, bg_files: List[str]) -> Optional[str]:
        """
        根据样本文件名查找匹配的背景图

        Args:
            sample_filename: 样本文件名
            bg_files: 背景图文件列表

        Returns:
            匹配的背景图文件名，如果没有找到则返回None
        """
        # 提取样本的基本名称（不含后缀）
        sample_base = self.extract_base_name(sample_filename)
        logger.debug(f"样本 {sample_filename} 的基本名称: {sample_base}")

        # 首先尝试完全匹配
        for bg_file in bg_files:
            bg_base = self.extract_base_name(bg_file)
            if bg_base == sample_base:
                logger.info(f"找到完全匹配: {bg_file} -> {sample_filename}")
                return bg_file

        # 如果没有完全匹配，尝试模糊匹配（检查样本名是否包含背景名）
        for bg_file in bg_files:
            bg_base = self.extract_base_name(bg_file)
            if bg_base in sample_base:
                logger.info(f"找到模糊匹配: {bg_file} -> {sample_filename}")
                return bg_file

        # 如果没有模糊匹配，尝试检查背景名是否包含样本名
        for bg_file in bg_files:
            bg_base = self.extract_base_name(bg_file)
            if sample_base in bg_base:
                logger.info(f"找到反向模糊匹配: {bg_file} -> {sample_filename}")
                return bg_file

        # 没有找到匹配
        return None

    def batch_process(self, progress_callback=None, max_workers: int = 16) -> Tuple[int, int, List[str], float]:
        """
        批量处理图像，使用多线程加速

        Args:
            progress_callback: 进度回调函数
            max_workers: 最大工作线程数

        Returns:
            processed_count: 成功处理的数量
            failed_count: 失败的数量
            error_list: 错误信息列表
            elapsed_time: 总耗时(秒)
        """
        # 记录开始时间
        start_time = time.time()

        if not os.path.exists(self.bg_dir) or not os.path.exists(self.sample_dir):
            logger.error("目录不存在")
            return 0, 0, ["源目录不存在"], 0.0

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 获取样本图列表
        sample_files = [f for f in os.listdir(self.sample_dir)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not sample_files:
            logger.warning("未找到图像文件")
            return 0, 0, ["未找到图像文件"], 0.0

        # 获取背景图列表一次，避免重复读取
        bg_files = [f for f in os.listdir(self.bg_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        processed_count = 0
        failed_count = 0
        error_list = []
        processed_lock = threading.Lock()  # 用于线程安全更新计数器

        def process_single_sample(sample_file):
            nonlocal processed_count, failed_count

            # 尝试寻找匹配的背景图
            bg_file = self.find_matching_bg(sample_file, bg_files)

            if not bg_file:
                error_msg = f"未找到对应的背景图: {sample_file}"
                with processed_lock:
                    failed_count += 1
                return False, error_msg

            try:
                # 处理图像对
                success, message = self.process_image_pair(bg_file, sample_file)

                with processed_lock:
                    if success:
                        processed_count += 1
                        logger.success(message)
                    else:
                        failed_count += 1
                        error_list.append(f"处理失败: {sample_file}")
                        logger.error(f"处理失败: {sample_file}")

                return success, message

            except Exception as e:
                error_msg = f"处理异常 {sample_file}: {str(e)}"
                with processed_lock:
                    failed_count += 1
                return False, error_msg

        # 使用线程池批量处理
        total_files = len(sample_files)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_sample = {
                executor.submit(process_single_sample, sample_file): sample_file
                for sample_file in sample_files
            }

            # 获取结果并更新进度
            for future in as_completed(future_to_sample):
                sample_file = future_to_sample[future]
                try:
                    success, message = future.result()
                    if not success:
                        error_list.append(message)
                        logger.error(message)
                except Exception as e:
                    error_msg = f"处理 {sample_file} 时发生异常: {str(e)}"
                    error_list.append(error_msg)
                    logger.error(error_msg)

                completed += 1
                if progress_callback:
                    progress = int(completed / total_files * 100)
                    if not progress_callback(progress):
                        break

        # 计算总耗时
        elapsed_time = time.time() - start_time
        logger.info(f"批处理完成，总耗时: {elapsed_time:.2f}秒")

        return processed_count, failed_count, error_list, elapsed_time

    def get_sample_sequence(self) -> Dict[str, List[str]]:
        """
        获取样本图序列，按基本名称分组

        Returns:
            Dict[str, List[str]]: 以基本名称为键，相关样本图列表为值的字典
        """
        if not os.path.exists(self.sample_dir):
            logger.error("样本目录不存在")
            return {}

        # 获取样本图列表
        sample_files = [f for f in os.listdir(self.sample_dir)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]

        # 按基本名称分组
        sequences = {}
        for sample_file in sample_files:
            base_name = self.extract_base_name(sample_file)
            if base_name not in sequences:
                sequences[base_name] = []
            sequences[base_name].append(sample_file)

        # 对每个序列按文件名排序
        for base_name in sequences:
            sequences[base_name].sort()

        return sequences

    def process_sample_sequence(self, base_name: str, sample_files: List[str], max_workers: int = 4) -> Tuple[
        int, int, List[str]]:
        """
        处理一个样本图序列，使用优化的多线程加速处理

        Args:
            base_name: 基本名称
            sample_files: 样本图文件列表
            max_workers: 最大工作线程数

        Returns:
            processed: 成功处理的图片数
            failed: 失败的图片数
            errors: 错误消息列表
        """
        # 获取背景图列表
        bg_files = [f for f in os.listdir(self.bg_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]

        if not bg_files:
            return 0, 0, ["背景目录中没有图片"]

        # 寻找匹配的背景图
        bg_match = None
        for bg_file in bg_files:
            bg_base = self.extract_base_name(bg_file)
            if bg_base == base_name:
                bg_match = bg_file
                logger.info(f"找到与序列 {base_name} 匹配的背景图: {bg_file}")
                break

        # 如果没有匹配，使用第一个背景图
        if bg_match is None:
            bg_match = bg_files[0]
            logger.warning(f"没有找到与序列 {base_name} 匹配的背景图，使用默认背景 {bg_match}")

        # 预先加载背景图像，避免重复加载
        bg_path = os.path.join(self.bg_dir, bg_match)
        try:
            bg_img = cv2.imdecode(np.fromfile(bg_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if bg_img is None:
                return 0, 0, [f"背景图 {bg_match} 加载失败"]

            # 获取图像尺寸供后续使用
            img_height, img_width = bg_img.shape[:2]
        except Exception as e:
            return 0, 0, [f"背景图 {bg_match} 加载异常: {str(e)}"]

        # 处理结果统计
        processed = 0
        failed = 0
        errors = []

        # 线程安全计数器
        lock = threading.Lock()

        # 创建针对序列优化的处理函数
        def process_single_image(sample_file):
            nonlocal processed, failed

            try:
                sample_path = os.path.join(self.sample_dir, sample_file)

                # 检查输出文件
                base_name = os.path.splitext(sample_file)[0]
                output_path = os.path.join(self.output_dir, f"{base_name}.txt")

                # 加载样本图像
                sample_img = cv2.imdecode(np.fromfile(sample_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if sample_img is None:
                    return False, f"样本图 {sample_file} 加载失败"

                # 确保尺寸匹配
                if sample_img.shape[:2] != bg_img.shape[:2]:
                    sample_img = cv2.resize(sample_img, (bg_img.shape[1], bg_img.shape[0]))

                # 计算差异
                diff = cv2.absdiff(bg_img, sample_img)

                # 分别处理每个颜色通道
                b_diff, g_diff, r_diff = cv2.split(diff)

                # 对每个通道应用阈值
                _, b_mask = cv2.threshold(b_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)
                _, g_mask = cv2.threshold(g_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)
                _, r_mask = cv2.threshold(r_diff, self.diff_threshold, 255, cv2.THRESH_BINARY)

                # 合并通道掩码
                mask = cv2.bitwise_or(cv2.bitwise_or(b_mask, g_mask), r_mask)

                # 形态学操作
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

                # 寻找轮廓
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # 生成边界框
                bounding_boxes = []
                for contour in contours:
                    area = cv2.contourArea(contour)

                    # 过滤小区域
                    if area < self.min_diff_area:
                        continue

                    # 获取边界框并应用填充
                    x, y, w, h = cv2.boundingRect(contour)
                    padding = self.bbox_padding
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(img_width - x, w + 2 * padding)
                    h = min(img_height - y, h + 2 * padding)

                    # 计算归一化的中心坐标和尺寸
                    x_center = (x + w / 2) / img_width
                    y_center = (y + h / 2) / img_height
                    width = w / img_width
                    height = h / img_height

                    # 创建边界框对象
                    bbox = BoundingBox(
                        label_id=self.default_label,
                        x_center=x_center,
                        y_center=y_center,
                        width=width,
                        height=height
                    )

                    bounding_boxes.append(bbox)

                # 合并重叠边界框
                if self.min_merge_iou > 0 and len(bounding_boxes) > 1:
                    bounding_boxes = self.merge_overlapping_boxes(bounding_boxes, img_width, img_height)

                # 写入标注文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    for bbox in bounding_boxes:
                        f.write(bbox.to_yolo_format() + '\n')

                # 更新统计信息
                with lock:
                    processed += 1

                return True, f"成功处理 {sample_file}, 检测到 {len(bounding_boxes)} 个对象"

            except Exception as e:
                with lock:
                    failed += 1
                return False, f"处理 {sample_file} 时发生异常: {str(e)}"

        # 使用线程池处理样本图
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_sample = {
                executor.submit(process_single_image, sample_file): sample_file
                for sample_file in sample_files
            }

            # 获取结果
            for future in as_completed(future_to_sample):
                sample_file = future_to_sample[future]
                try:
                    success, message = future.result()
                    if not success:
                        with lock:
                            errors.append(message)
                        logger.error(message)
                    else:
                        logger.success(message)
                except Exception as e:
                    with lock:
                        failed += 1
                    error_msg = f"处理 {sample_file} 时发生异常: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        return processed, failed, errors

    def batch_process_by_sequence(self, progress_callback=None, max_workers: int = 4) -> Tuple[
        int, int, List[str], float]:
        """
        按序列批量处理样本图，以一对多关系处理差分

        Args:
            progress_callback: 进度回调函数
            max_workers: 最大工作线程数

        Returns:
            processed: 成功处理的图片数
            failed: 失败的图片数
            errors: 错误消息列表
            elapsed_time: 总耗时(秒)
        """
        # 记录开始时间
        start_time = time.time()

        if not os.path.exists(self.bg_dir) or not os.path.exists(self.sample_dir):
            return 0, 0, ["背景或样本目录不存在"], 0.0

        # 获取样本图序列
        sequences = self.get_sample_sequence()

        if not sequences:
            return 0, 0, ["没有找到样本图序列"], 0.0

        # 总处理结果统计
        total_processed = 0
        total_failed = 0
        total_errors = []

        # 记录每个序列的处理时间
        sequence_times = {}

        # 并行处理多个序列
        if len(sequences) > 1 and max_workers > 1:
            # 分配线程给序列
            seq_workers = max(1, max_workers // min(len(sequences), max_workers // 2))
            logger.info(f"使用并行序列处理模式，每个序列分配 {seq_workers} 个线程")

            total_sequences = len(sequences)
            sequences_processed = 0

            with ThreadPoolExecutor(max_workers=min(len(sequences), max_workers // 2)) as executor:
                # 为每个序列创建处理任务
                future_to_sequence = {}
                for base_name, sample_files in sequences.items():
                    future = executor.submit(
                        self.process_sample_sequence,
                        base_name,
                        sample_files,
                        seq_workers
                    )
                    future_to_sequence[future] = base_name

                # 获取结果
                for future in as_completed(future_to_sequence):
                    base_name = future_to_sequence[future]
                    seq_start_time = time.time()

                    try:
                        processed, failed, errors = future.result()

                        total_processed += processed
                        total_failed += failed
                        total_errors.extend(errors)

                        # 记录序列处理时间
                        seq_elapsed = time.time() - seq_start_time
                        sequence_times[base_name] = seq_elapsed
                        logger.debug(f"序列 {base_name} 处理完成，耗时: {seq_elapsed:.5f}秒")

                    except Exception as e:
                        total_failed += len(sequences[base_name])
                        error_msg = f"处理序列 {base_name} 时发生异常: {str(e)}"
                        total_errors.append(error_msg)
                        logger.error(error_msg)

                    sequences_processed += 1
                    if progress_callback:
                        progress = int(sequences_processed / total_sequences * 100)
                        progress_callback(progress)
        else:
            # 顺序处理序列
            logger.info("使用顺序序列处理模式")
            total_sequences = len(sequences)
            sequences_processed = 0

            for base_name, sample_files in sequences.items():
                logger.info(f"处理序列: {base_name} (共 {len(sample_files)} 张图片)")

                seq_start_time = time.time()
                processed, failed, errors = self.process_sample_sequence(base_name, sample_files, max_workers)

                # 记录序列处理时间
                seq_elapsed = time.time() - seq_start_time
                sequence_times[base_name] = seq_elapsed
                logger.debug(f"序列 {base_name} 处理完成，耗时: {seq_elapsed:.5f}秒")

                total_processed += processed
                total_failed += failed
                total_errors.extend(errors)

                sequences_processed += 1
                if progress_callback:
                    progress = int(sequences_processed / total_sequences * 100)
                    progress_callback(progress)

        # 计算总耗时
        elapsed_time = time.time() - start_time
        logger.info(f"批处理完成，总耗时: {elapsed_time:.2f}秒")

        # 输出序列处理时间统计
        if len(sequences) > 1:
            logger.debug("各序列处理时间统计:")
            for base_name, seq_time in sequence_times.items():
                logger.debug(f"  - {base_name}: {seq_time:.5f}秒 (包含 {len(sequences[base_name])} 张图片)")

        return total_processed, total_failed, total_errors, elapsed_time