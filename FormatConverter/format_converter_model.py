"""
格式转换工具的模型层 - 处理YOLO与labelme格式的双向转换
支持rectangle和point两种形状类型
"""
import os
import json
import cv2
import numpy as np
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any, Union
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from utils.logger import LogManager
logger = LogManager.get_logger("FC", level="info")


@dataclass
class ConversionTask:
    """转换任务数据类"""
    source_file: str
    target_file: str
    image_file: str
    label_mapping: Dict[Union[str, int], Union[str, int]]


@dataclass
class ConversionResult:
    """转换结果数据类"""
    success: bool
    source_file: str
    target_file: str
    message: str
    objects_count: int = 0


class YOLOShape:
    """YOLO格式的形状数据"""
    def __init__(self, class_id: int, x_center: float = None, y_center: float = None,
                 width: float = None, height: float = None, polygon_points: List[float] = None):
        self.class_id = class_id
        self.x_center = x_center
        self.y_center = y_center
        self.width = width
        self.height = height
        self.polygon_points = polygon_points  # 多边形归一化坐标点列表 [x1, y1, x2, y2, ...]

    @property
    def is_point(self) -> bool:
        """判断是否为点类型"""
        return self.polygon_points is None and (self.width is None or self.height is None)

    @property
    def is_polygon(self) -> bool:
        """判断是否为多边形类型"""
        return self.polygon_points is not None

    def to_yolo_string(self) -> str:
        """转换为YOLO格式字符串"""
        if self.is_polygon:
            # 多边形格式: class_id x1 y1 x2 y2 ... xn yn
            points_str = ' '.join(f"{coord:.6f}" for coord in self.polygon_points)
            return f"{self.class_id} {points_str}"
        elif self.is_point:
            # 点格式: class_id x y
            return f"{self.class_id} {self.x_center:.6f} {self.y_center:.6f}"
        else:
            # 矩形格式: class_id x_center y_center width height
            return f"{self.class_id} {self.x_center:.6f} {self.y_center:.6f} {self.width:.6f} {self.height:.6f}"


class LabelmeShape:
    """Labelme格式的形状数据"""
    def __init__(self, label: str, points: List[List[float]], shape_type: str = "rectangle"):
        self.label = label
        self.points = points
        self.shape_type = shape_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "label": self.label,
            "points": self.points,
            "group_id": None,
            "description": "",
            "shape_type": self.shape_type,
            "flags": {},
            "attributes": {},
            "kie_linking": []
        }


class FormatConverterModel:
    """格式转换模型"""

    def __init__(self):
        # 配置参数
        self.source_dir = ""          # 源文件目录
        self.target_dir = ""          # 目标文件目录
        self.image_dir = ""           # 图像文件目录
        self.conversion_mode = "yolo_to_labelme"  # 转换模式
        self.label_mapping = {}       # 标签映射表
        self.config_file = "config/FC_config.json"
        self.use_classes_txt = True   # 是否优先使用classes.txt
        self.classes_txt_path = ""    # classes.txt文件路径
        self.auto_generate_classes = True  # 是否自动生成classes.txt

        # 支持的图像格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

    def set_config(self, config: Dict[str, Any]):
        """设置配置参数"""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def save_config(self, config_path: str = None) -> bool:
        """保存配置到文件"""
        if config_path is None:
            config_path = self.config_file

        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            config_data = {
                "source_dir": self.source_dir,
                "target_dir": self.target_dir,
                "image_dir": self.image_dir,
                "conversion_mode": self.conversion_mode,
                "label_mapping": self.label_mapping,
                "use_classes_txt": self.use_classes_txt,
                "classes_txt_path": self.classes_txt_path,
                "auto_generate_classes": self.auto_generate_classes
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            logger.success(f"配置已保存到: {config_path}")
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def load_config(self, config_path: str = None) -> bool:
        """从文件加载配置"""
        if config_path is None:
            config_path = self.config_file

        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            self.set_config(config_data)
            logger.success(f"配置已加载: {config_path}")
            return True

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False

    def load_classes_txt(self, classes_path: str = None) -> Dict[str, List[Union[str, int]]]:
        """加载classes.txt文件"""
        if classes_path is None:
            # 如果未指定路径，尝试从源目录查找
            classes_path = os.path.join(self.source_dir, "classes.txt")
            if not os.path.exists(classes_path):
                logger.info(f"未在源目录找到classes.txt: {classes_path}")
                return {}

        if not os.path.exists(classes_path):
            logger.warning(f"classes.txt文件不存在: {classes_path}")
            return {}

        try:
            with open(classes_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            classes = []
            for i, line in enumerate(lines):
                line = line.strip()
                if line:  # 忽略空行
                    classes.append(line)

            # 保存路径供后续使用
            self.classes_txt_path = classes_path

            logger.success(f"成功加载classes.txt，共{len(classes)}个类别")
            return {"yolo": list(range(len(classes))), "labelme": classes}

        except Exception as e:
            logger.error(f"读取classes.txt失败: {e}")
            return {}

    def generate_classes_txt(self, output_dir: str = None, class_names: List[str] = None) -> bool:
        """
        生成classes.txt文件

        Args:
            output_dir: 输出目录,默认为target_dir
            class_names: 类别名称列表(按class_id顺序),如果为None则从label_mapping提取

        Returns:
            bool: 是否成功生成
        """
        if output_dir is None:
            output_dir = self.target_dir

        if class_names is None:
            # 从label_mapping中提取类别名称
            if not self.label_mapping:
                logger.warning("label_mapping为空,无法生成classes.txt")
                return False

            # label_mapping在labelme_to_yolo模式下的格式: {label_name: class_id}
            # 需要按class_id排序后提取label_name
            try:
                # 按class_id排序
                sorted_items = sorted(self.label_mapping.items(), key=lambda x: int(x[1]))
                class_names = [item[0] for item in sorted_items]

                logger.info(f"从label_mapping提取了{len(class_names)}个类别")
            except (ValueError, TypeError) as e:
                logger.error(f"label_mapping格式错误,无法生成classes.txt: {e}")
                return False

        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 生成classes.txt路径
            classes_path = os.path.join(output_dir, "classes.txt")

            # 写入文件
            with open(classes_path, 'w', encoding='utf-8') as f:
                for class_name in class_names:
                    f.write(f"{class_name}\n")

            logger.success(f"成功生成classes.txt: {classes_path},共{len(class_names)}个类别")
            self.classes_txt_path = classes_path
            return True

        except Exception as e:
            logger.error(f"生成classes.txt失败: {e}")
            return False

    def get_image_size(self, image_path: str) -> Tuple[int, int]:
        """获取图像尺寸 (width, height)"""
        try:
            # 使用cv2读取图像以支持中文路径
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"无法读取图像: {image_path}")
            height, width = img.shape[:2]
            return width, height
        except Exception as e:
            logger.error(f"获取图像尺寸失败 {image_path}: {e}")
            raise

    def find_corresponding_image(self, annotation_file: str) -> Optional[str]:
        """查找对应的图像文件"""
        base_name = os.path.splitext(os.path.basename(annotation_file))[0]

        # 在图像目录中查找同名图像文件
        for ext in self.image_extensions:
            image_path = os.path.join(self.image_dir, base_name + ext)
            if os.path.exists(image_path):
                return image_path

        logger.warning(f"未找到对应的图像文件: {base_name}")
        return None

        def load_yolo_annotation(self, yolo_file: str) -> List[YOLOShape]:
            """加载YOLO格式标注文件"""
        shapes = []
        try:
            with open(yolo_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split()
                    if len(parts) < 3:
                        logger.warning(f"YOLO文件第{line_num}行格式错误: {line}")
                        continue

                    try:
                        class_id = int(parts[0])

                        if len(parts) == 3:
                            # 点类型: class_id x y
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            shapes.append(YOLOShape(class_id, x_center, y_center))

                        elif len(parts) == 5:
                            # 矩形类型: class_id x_center y_center width height
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            shapes.append(YOLOShape(class_id, x_center, y_center, width, height))

                        elif len(parts) > 5 and (len(parts) - 1) % 2 == 0:
                            # 多边形类型: class_id x1 y1 x2 y2 ... xn yn
                            # 点数必须是偶数
                            polygon_points = [float(parts[i]) for i in range(1, len(parts))]
                            shapes.append(YOLOShape(class_id, polygon_points=polygon_points))

                        else:
                            logger.warning(f"YOLO文件第{line_num}行参数数量错误: {line}")

                    except ValueError as e:
                        logger.warning(f"YOLO文件第{line_num}行数值转换错误: {e}")

        except Exception as e:
            logger.error(f"读取YOLO文件失败 {yolo_file}: {e}")
            raise

        return shapes

    def load_labelme_annotation(self, labelme_file: str) -> List[LabelmeShape]:
        """加载labelme格式标注文件"""
        try:
            with open(labelme_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            shapes = []
            for shape_data in data.get('shapes', []):
                label = shape_data['label']
                points = shape_data['points']
                shape_type = shape_data.get('shape_type', 'rectangle')

                # 支持rectangle、point和polygon类型
                if shape_type in ['rectangle', 'point', 'polygon']:
                    shapes.append(LabelmeShape(label, points, shape_type))
                else:
                    logger.warning(f"跳过不支持的形状类型: {shape_type}")

            return shapes

        except Exception as e:
            logger.error(f"读取labelme文件失败 {labelme_file}: {e}")
            raise

    def yolo_to_labelme(self, yolo_file: str, output_file: str,
                        image_file: str, label_mapping: Dict[int, str]) -> ConversionResult:
        """YOLO格式转labelme格式"""
        try:
            # 加载YOLO标注
            yolo_shapes = self.load_yolo_annotation(yolo_file)

            # 获取图像尺寸
            img_width, img_height = self.get_image_size(image_file)

            # 转换为labelme格式
            labelme_shapes = []
            for yolo_shape in yolo_shapes:
                # 应用标签映射
                label = label_mapping.get(yolo_shape.class_id, str(yolo_shape.class_id))

                if yolo_shape.is_polygon:
                    # 多边形类型 - 将归一化坐标转换为像素坐标
                    points = []
                    for i in range(0, len(yolo_shape.polygon_points), 2):
                        x = yolo_shape.polygon_points[i] * img_width
                        y = yolo_shape.polygon_points[i + 1] * img_height
                        points.append([x, y])
                    shape_type = "polygon"

                elif yolo_shape.is_point:
                    # 点类型
                    x = yolo_shape.x_center * img_width
                    y = yolo_shape.y_center * img_height
                    points = [[x, y]]
                    shape_type = "point"

                else:
                    # 矩形类型 - 从中心点和宽高转换为四个角点
                    x_center = yolo_shape.x_center * img_width
                    y_center = yolo_shape.y_center * img_height
                    width = yolo_shape.width * img_width
                    height = yolo_shape.height * img_height

                    x1 = x_center - width / 2
                    y1 = y_center - height / 2
                    x2 = x_center + width / 2
                    y2 = y_center + height / 2

                    points = [[x1, y1], [x2, y2]]
                    shape_type = "rectangle"

                labelme_shapes.append(LabelmeShape(label, points, shape_type))

            # 构建labelme JSON数据
            labelme_data = {
                "version": "3.1.1",
                "flags": {},
                "shapes": [shape.to_dict() for shape in labelme_shapes],
                "imagePath": os.path.basename(image_file),
                "imageData": None,
                "imageHeight": img_height,
                "imageWidth": img_width
            }

            # 保存labelme文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(labelme_data, f, ensure_ascii=False, indent=2)

            return ConversionResult(
                success=True,
                source_file=yolo_file,
                target_file=output_file,
                message=f"成功转换 {len(labelme_shapes)} 个对象",
                objects_count=len(labelme_shapes)
            )

        except Exception as e:
            error_msg = f"YOLO转labelme失败: {e}"
            logger.error(error_msg)
            return ConversionResult(
                success=False,
                source_file=yolo_file,
                target_file=output_file,
                message=error_msg
            )

    def labelme_to_yolo(self, labelme_file: str, output_file: str,
                        label_mapping: Dict[str, int]) -> ConversionResult:
        """labelme格式转YOLO格式"""
        try:
            # 加载labelme标注
            with open(labelme_file, 'r', encoding='utf-8') as f:
                labelme_data = json.load(f)

            img_width = labelme_data['imageWidth']
            img_height = labelme_data['imageHeight']

            # 转换为YOLO格式
            yolo_shapes = []
            for shape_data in labelme_data.get('shapes', []):
                label = shape_data['label']
                points = shape_data['points']
                shape_type = shape_data.get('shape_type', 'rectangle')

                # 跳过不支持的形状类型
                if shape_type not in ['rectangle', 'point', 'polygon']:
                    logger.warning(f"跳过不支持的形状类型: {shape_type}")
                    continue

                # 应用标签映射
                class_id = label_mapping.get(label, 0)  # 默认为0

                if shape_type == 'point':
                    # 点类型
                    x = points[0][0] / img_width
                    y = points[0][1] / img_height
                    yolo_shapes.append(YOLOShape(class_id, x, y))

                elif shape_type == 'rectangle':
                    if len(points) == 2:
                        # 原始labelme格式
                        x1, y1 = points[0]
                        x2, y2 = points[1]
                    elif len(points) == 4:
                        # 四角点情况
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        x1, x2 = min(xs), max(xs)
                        y1, y2 = min(ys), max(ys)
                        logger.warning("检测到rectangle类型使用了四角点，已自动转换为两点表示")
                    else:
                        logger.warning(f"rectangle类型的点数异常: {points}")
                        continue

                    # 通用转换
                    x_center = (x1 + x2) / 2 / img_width
                    y_center = (y1 + y2) / 2 / img_height
                    width = (x2 - x1) / img_width
                    height = (y2 - y1) / img_height

                    yolo_shapes.append(YOLOShape(class_id, x_center, y_center, width, height))

                elif shape_type == 'polygon':
                    # 多边形类型 - 将像素坐标转换为归一化坐标
                    polygon_points = []
                    for point in points:
                        x_norm = point[0] / img_width
                        y_norm = point[1] / img_height
                        polygon_points.extend([x_norm, y_norm])

                    yolo_shapes.append(YOLOShape(class_id, polygon_points=polygon_points))

            # 保存YOLO文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                for shape in yolo_shapes:
                    f.write(shape.to_yolo_string() + '\n')

            return ConversionResult(
                success=True,
                source_file=labelme_file,
                target_file=output_file,
                message=f"成功转换 {len(yolo_shapes)} 个对象",
                objects_count=len(yolo_shapes)
            )

        except Exception as e:
            error_msg = f"labelme转YOLO失败: {e}"
            logger.error(error_msg)
            return ConversionResult(
                success=False,
                source_file=labelme_file,
                target_file=output_file,
                message=error_msg
            )

    def discover_labels(self) -> Dict[str, List[Union[str, int]]]:
        """自动发现源目录中的所有标签"""
        labels = {"yolo": [], "labelme": []}

        # 如果是YOLO格式且启用classes.txt优先级,先尝试加载classes.txt
        if self.conversion_mode == "yolo_to_labelme" and self.use_classes_txt:
            classes_labels = self.load_classes_txt()
            if classes_labels:
                logger.info("使用classes.txt中的标签")
                return classes_labels

        if not os.path.exists(self.source_dir):
            return {"yolo": [], "labelme": []}

        try:
            for file_name in os.listdir(self.source_dir):
                file_path = os.path.join(self.source_dir, file_name)

                if file_name.endswith('.txt') and file_name != 'classes.txt':
                    # YOLO格式文件
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    parts = line.split()
                                    if len(parts) >= 3:
                                        class_id = int(parts[0])
                                        if class_id not in labels["yolo"]:
                                            labels["yolo"].append(class_id)
                    except Exception as e:
                        logger.warning(f"读取YOLO文件失败 {file_path}: {e}")

                elif file_name.endswith('.json'):
                    # labelme格式文件
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            for shape in data.get('shapes', []):
                                label = shape.get('label', '')
                                if label and label not in labels["labelme"]:
                                    labels["labelme"].append(label)
                    except Exception as e:
                        logger.warning(f"读取labelme文件失败 {file_path}: {e}")

        except Exception as e:
            logger.error(f"发现标签时出错: {e}")

        # 转换为排序列表
        labels["yolo"] = sorted(labels["yolo"])
        labels["labelme"] = sorted(labels["labelme"])

        # 如果是labelme转YOLO模式,自动建立映射关系
        if self.conversion_mode == "labelme_to_yolo" and labels["labelme"]:
            # 检查是否已有映射,如果没有则自动创建
            if not self.label_mapping:
                # 按字母顺序为每个标签分配class_id
                self.label_mapping = {label: idx for idx, label in enumerate(labels["labelme"])}
                logger.info(f"自动创建label_mapping,共{len(self.label_mapping)}个类别")
                logger.debug(f"label_mapping: {self.label_mapping}")

        return labels

    def batch_convert(self, progress_callback=None, max_workers: int = 4) -> Tuple[int, int, List[str], float]:
        """批量转换"""
        start_time = time.time()

        if not os.path.exists(self.source_dir):
            return 0, 0, ["源目录不存在"], 0.0

        if not os.path.exists(self.image_dir):
            return 0, 0, ["图像目录不存在"], 0.0

        # 创建输出目录
        os.makedirs(self.target_dir, exist_ok=True)

        # 获取源文件列表
        if self.conversion_mode == "yolo_to_labelme":
            source_files = [f for f in os.listdir(self.source_dir) if f.endswith('.txt') and f != 'classes.txt']
            target_ext = '.json'
        else:
            source_files = [f for f in os.listdir(self.source_dir) if f.endswith('.json')]
            target_ext = '.txt'

        if not source_files:
            return 0, 0, ["源目录中没有找到相应格式的文件"], 0.0

        # **关键修复: 在转换前确保label_mapping已建立**
        if self.conversion_mode == "labelme_to_yolo" and not self.label_mapping:
            logger.info("label_mapping为空,开始自动发现标签...")
            discovered_labels = self.discover_labels()
            if not self.label_mapping:
                logger.warning("自动发现标签失败,将使用默认映射")

        # 准备转换任务
        tasks = []
        for source_file in source_files:
            source_path = os.path.join(self.source_dir, source_file)
            base_name = os.path.splitext(source_file)[0]
            target_path = os.path.join(self.target_dir, base_name + target_ext)

            # 查找对应的图像文件
            if self.conversion_mode == "yolo_to_labelme":
                image_path = self.find_corresponding_image(source_path)
                if image_path is None:
                    continue
            else:
                # labelme转YOLO不需要图像文件(尺寸信息在json中)
                image_path = None

            tasks.append(ConversionTask(
                source_file=source_path,
                target_file=target_path,
                image_file=image_path,
                label_mapping=self.label_mapping
            ))

        if not tasks:
            return 0, 0, ["没有找到可转换的文件（缺少对应图像）"], 0.0

        # 执行批量转换
        success_count = 0
        failed_count = 0
        errors = []
        completed = 0

        def convert_single_task(task: ConversionTask) -> ConversionResult:
            """转换单个任务"""
            if self.conversion_mode == "yolo_to_labelme":
                return self.yolo_to_labelme(
                    task.source_file,
                    task.target_file,
                    task.image_file,
                    task.label_mapping
                )
            else:
                return self.labelme_to_yolo(
                    task.source_file,
                    task.target_file,
                    task.label_mapping
                )

        # 使用线程池执行转换
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(convert_single_task, task): task for task in tasks}

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result.success:
                        success_count += 1
                        logger.success(f"转换成功: {os.path.basename(result.source_file)} -> {os.path.basename(result.target_file)}")
                    else:
                        failed_count += 1
                        errors.append(result.message)
                        logger.error(f"转换失败: {os.path.basename(result.source_file)} - {result.message}")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"处理任务异常 {os.path.basename(task.source_file)}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

                completed += 1
                if progress_callback:
                    progress = int(completed / len(tasks) * 100)
                    if not progress_callback(progress):
                        break  # 用户取消

        # 转换完成后,如果是labelme转YOLO模式且启用自动生成classes.txt
        if self.conversion_mode == "labelme_to_yolo" and self.auto_generate_classes and success_count > 0:
            logger.info("开始自动生成classes.txt...")
            if self.generate_classes_txt():
                logger.success("classes.txt生成成功")
            else:
                logger.warning("classes.txt生成失败")

        elapsed_time = time.time() - start_time
        logger.info(f"批量转换完成，耗时: {elapsed_time:.2f}秒")

        return success_count, failed_count, errors, elapsed_time
