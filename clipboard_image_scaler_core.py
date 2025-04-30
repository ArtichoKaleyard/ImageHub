"""
粘贴板图像自动缩放器 - 核心模块
该模块负责检测粘贴板中的图像，并根据设定的参数自动缩放
"""

import threading
import numpy as np
import cv2
from PIL import Image, ImageGrab
import win32clipboard
import win32con
from io import BytesIO


class ClipboardImageScalerCore:
    def __init__(self, callback=None):
        """
        初始化粘贴板图像缩放器核心

        参数:
        callback -- 用于通知UI更新的回调函数
        """
        # 目标尺寸（默认1920x1080）
        self.target_width = 1920
        self.target_height = 1080

        # 配置参数
        self.tolerance = 0.6  # 纵横比容差
        self.resize_method = cv2.INTER_LANCZOS4  # 默认缩放算法
        self.auto_adjust_larger_size = True  # 是否自动调整大于目标尺寸的图像
        self.auto_copy_back = True  # 自动复制回粘贴板

        # 状态变量
        self.monitoring = False
        self.last_image = None
        self.scaled_image = None
        self.last_clipboard_seq = 0  # 用于检测粘贴板变化的序号

        # 监控线程
        self.monitor_thread = None

        # 用于UI更新的回调函数
        self.callback = callback

    def set_target_size(self, width, height):
        """
        设置目标尺寸

        参数:
        width -- 目标宽度
        height -- 目标高度

        返回:
        设置是否成功
        """
        self.target_width = width
        self.target_height = height
        return True

    def set_auto_adjust_larger_size(self, enabled):
        """
                设置是否自动调整大于目标尺寸的图像
        """
        self.auto_adjust_larger_size = enabled
        return True

    def set_tolerance(self, tolerance):
        """
        设置纵横比容差

        参数:
        tolerance -- 容差值（0-1之间）

        返回:
        设置是否成功
        """
        if 0 <= tolerance <= 1:
            self.tolerance = tolerance
            return True
        return False

    def set_resize_method(self, method_name):
        """
        设置缩放算法

        参数:
        method_name -- 算法名称

        返回:
        设置是否成功
        """
        methods = {
            "最近邻": cv2.INTER_NEAREST,
            "双线性": cv2.INTER_LINEAR,
            "双三次": cv2.INTER_CUBIC,
            "Lanczos": cv2.INTER_LANCZOS4
        }
        if method_name in methods:
            self.resize_method = methods[method_name]
            return True
        return False

    def set_auto_copy(self, enabled):
        """
        设置是否自动复制回粘贴板

        参数:
        enabled -- 是否启用

        返回:
        设置是否成功
        """
        self.auto_copy_back = enabled
        return True

    def start_monitoring(self):
        """
        开始监控粘贴板图像变化

        返回:
        是否成功启动监控
        """
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_clipboard)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            return True
        return False

    def stop_monitoring(self):
        """
        停止监控粘贴板

        返回:
        是否成功停止监控
        """
        if self.monitoring:
            self.monitoring = False
            return True
        return False

    def monitor_clipboard(self):
        """监控粘贴板变化"""
        # 设置初始粘贴板序列号
        self.last_clipboard_seq = win32clipboard.GetClipboardSequenceNumber()

        while self.monitoring:
            try:
                # 获取当前粘贴板序列号
                current_seq = win32clipboard.GetClipboardSequenceNumber()

                # 如果粘贴板内容发生变化
                if current_seq != self.last_clipboard_seq:
                    # 更新序列号
                    self.last_clipboard_seq = current_seq

                    # 尝试获取粘贴板图像
                    img = ImageGrab.grabclipboard()

                    # 如果检测到图像
                    if isinstance(img, Image.Image):
                        # 更新状态
                        if self.callback:
                            self.callback("status", "检测到新图像，正在处理...")

                        # 转换为OpenCV格式
                        self.last_image = self.pil_to_cv2(img)

                        # 处理图像
                        self.process_image()

            except Exception as e:
                if self.callback:
                    self.callback("error", f"粘贴板读取错误: {str(e)}")
                pass

            # 线程休眠一小段时间，避免CPU过度使用
            threading.Event().wait(0.1)

    def pil_to_cv2(self, pil_image):
        """
        将PIL图像转换为OpenCV格式

        参数:
        pil_image -- PIL格式图像

        返回:
        OpenCV格式图像
        """
        # 确保图像为RGB模式
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # 转换为numpy数组
        open_cv_image = np.array(pil_image)

        # 转换RGB为BGR（OpenCV使用BGR）
        open_cv_image = open_cv_image[:, :, ::-1].copy()

        return open_cv_image

    def cv2_to_pil(self, cv_image):
        """
        将OpenCV图像转换为PIL格式

        参数:
        cv_image -- OpenCV格式图像

        返回:
        PIL格式图像
        """
        # 转换BGR为RGB（PIL使用RGB）
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

        # 创建PIL图像
        pil_image = Image.fromarray(rgb_image)

        return pil_image

    def process_image(self):
        if self.last_image is None:
            return False

        height, width = self.last_image.shape[:2]
        if self.callback:
            self.callback("original_image", self.last_image)
            self.callback("original_info", f"{width}x{height}")

        current_target_width = self.target_width
        current_target_height = self.target_height

        # # 添加调试信息
        # print(f"Original size: {width}x{height}")
        # print(f"Target size: {self.target_width}x{self.target_height}")
        # print(f"Auto adjust larger size: {self.auto_adjust_larger_size}")

        # 修改：移除 self.target_height == 1080 限制
        if self.auto_adjust_larger_size:
            if height > 1080 or width > 1920:
                current_target_height = 1440
                current_target_width = 2560
                if self.callback:
                    self.callback("status",
                                  f"检测到图像尺寸 {width}x{height} > 1080p，调整目标尺寸为 {current_target_width}x{current_target_height}")

        # print(f"Current target size: {current_target_width}x{current_target_height}")

        current_ratio = width / height
        target_ratio = current_target_width / current_target_height
        ratio_difference = abs(current_ratio - target_ratio) / target_ratio
        size_difference = (abs(width - current_target_width) / current_target_width +
                           abs(height - current_target_height) / current_target_height) / 2

        if ratio_difference <= self.tolerance and size_difference > 0.05:
            if current_ratio > target_ratio:
                new_width = current_target_width
                new_height = int(new_width / current_ratio)
            else:
                new_height = current_target_height
                new_width = int(new_height * current_ratio)

            # print(f"New size: {new_width}x{new_height}")

            self.scaled_image = cv2.resize(self.last_image, (new_width, new_height), interpolation=self.resize_method)
            if self.callback:
                self.callback("scaled_image", self.scaled_image)
                self.callback("scaled_info", f"{new_width}x{new_height}")
                self.callback("status",
                              f"图像已缩放 {width}x{height} -> {new_width}x{new_height} (目标: {current_target_width}x{current_target_height})")
            if self.auto_copy_back:
                self.copy_to_clipboard()
            return True
        else:
            self.scaled_image = None
            if self.callback:
                self.callback("scaled_image", None)
                self.callback("scaled_info", "无需缩放")
            return False

    def copy_to_clipboard(self):
        """
        将缩放后的图像复制到粘贴板

        返回:
        复制是否成功
        """
        if self.scaled_image is not None:
            try:
                # 转换OpenCV图像为PIL格式
                pil_image = self.cv2_to_pil(self.scaled_image)
                # 将PIL图像复制到粘贴板
                output = BytesIO()
                pil_image.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]  # BMP文件头为14字节
                output.close()
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                win32clipboard.CloseClipboard()

                # 更新剪贴板序列号以避免重复处理
                self.last_clipboard_seq = win32clipboard.GetClipboardSequenceNumber()
                if self.callback:
                    self.callback("status", "图像已复制到粘贴板")
                return True
            except Exception as e:
                if self.callback:
                    self.callback("error", f"复制到粘贴板失败: {str(e)}")
                return False
        else:
            if self.callback:
                self.callback("status", "没有可复制的缩放图像")
            return False