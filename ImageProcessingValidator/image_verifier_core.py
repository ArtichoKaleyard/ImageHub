import os
import re
import shutil
import threading
import concurrent.futures
import time
from collections import defaultdict
from typing import List, Tuple, Dict, Set, Optional, Callable, Union, Pattern
from queue import Queue
from utils.logger import Logger, LogManager


class ImageVerifier:
    """图片处理验证工具，提供模块化的验证功能，支持多线程处理"""

    def __init__(self, source_folder: str, target_folder: str, missing_folder: str, max_workers: int = None):
        """
        初始化验证工具

        参数:
        source_folder: 原始图片所在文件夹
        target_folder: 处理后图片所在文件夹
        missing_folder: 未处理图片将被复制到的文件夹
        max_workers: 最大工作线程数，默认为None（使用系统CPU核心数）
        """
        # 初始化日志记录器
        self.logger = LogManager.get_logger("IV")

        self.source_folder = source_folder
        self.target_folder = target_folder
        self.missing_folder = missing_folder
        self.max_workers = max_workers if max_workers is not None else os.cpu_count()

        # 回调函数初始化
        self._progress_callback = None
        self._log_callback = None

        # 创建输出文件夹
        if not os.path.exists(missing_folder):
            os.makedirs(missing_folder)
            self.logger.info(f"创建输出文件夹: {missing_folder}")
        else:
            self.logger.info(f"输出文件夹已存在: {missing_folder}")

        # 初始化结果存储
        self.source_images = []  # 原始图片列表 [(base_name, filename), ...]
        self.processed_images = defaultdict(list)  # 处理后图片字典 {base_name: [suffixes]}
        self.naming_errors = []  # 命名不规范的图片列表
        self.missing_images = []  # 完全未处理的图片列表
        self.incomplete_images = []  # 处理不完整的图片列表 [(filename, missing_suffixes), ...]

        # 线程安全锁
        self._lock = threading.RLock()

        # 进度追踪
        self.total_files = 0
        self.processed_files = 0
        self.progress_percent = 0


    def set_callbacks(self, progress_callback: callable = None, log_callback: callable = None):
        """
        设置回调函数

        参数:
        progress_callback: 进度更新回调函数，接收(current, total, percent)参数
        log_callback: 日志输出回调函数，接收(message)参数
        """
        self._progress_callback = progress_callback
        self._log_callback = log_callback

    def _log(self, message: str):
        """输出日志（支持回调）"""
        if self._log_callback:
            self._log_callback(message)
        else:
            self.logger.info(message)  # 默认使用日志记录器

    def _update_progress(self):
        """更新进度（支持回调）"""
        if self._progress_callback:
            self._progress_callback(self.processed_files, self.total_files, self.progress_percent)

    def scan_source_images(self, source_extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png')) -> List[
        Tuple[str, str]]:
        """
        扫描原始图片文件夹，获取所有符合扩展名的图片

        参数:
        source_extensions: 原始图片的扩展名列表

        返回:
        包含(基础名称，文件名)的元组列表
        """
        self.logger.info("开始扫描原始图片...")
        start_time = time.time()

        # 获取文件列表
        all_files = os.listdir(self.source_folder)
        self.source_images = []

        # 使用线程池并行处理文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for filename in all_files:
                if filename.lower().endswith(source_extensions):
                    futures.append(executor.submit(self._process_source_file, filename))

            # 显示进度
            self.total_files = len(futures)
            self.processed_files = 0
            self.progress_percent = 0
            self._update_progress()
            self._monitor_progress(futures, "扫描原始图片")

            # 等待所有任务完成
            concurrent.futures.wait(futures)

        elapsed_time = time.time() - start_time
        self.logger.info(f"找到 {len(self.source_images)} 张原始图片. 耗时: {elapsed_time:.2f}秒")
        return self.source_images

    def _process_source_file(self, filename: str):
        """处理单个源文件（线程安全）"""
        base_name = os.path.splitext(filename)[0]
        with self._lock:
            self.source_images.append((base_name, filename))
            self.processed_files += 1
            self.progress_percent = int((self.processed_files / self.total_files) * 100)
            self._update_progress()

    def scan_processed_images(self, naming_pattern: Pattern) -> Dict[str, List[str]]:
        """
        扫描处理后图片文件夹，按照命名模式匹配图片并分组

        参数:
        naming_pattern: 正则表达式模式，用于匹配文件名并提取基础名称和后缀

        返回:
        以基础名称为键，后缀列表为值的字典
        """
        self.logger.info("开始扫描处理后图片...")
        start_time = time.time()

        all_files = os.listdir(self.target_folder)
        self.processed_images = defaultdict(list)
        self.naming_errors = []

        # 使用线程池并行处理文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for filename in all_files:
                futures.append(executor.submit(self._process_target_file, filename, naming_pattern))

            # 显示进度
            self.processed_files = 0
            self.total_files = len(futures)
            self.progress_percent = 0
            self._update_progress()
            self._monitor_progress(futures, "扫描处理后图片")

            # 等待所有任务完成
            concurrent.futures.wait(futures)

        total_processed = sum(len(suffixes) for suffixes in self.processed_images.values())
        elapsed_time = time.time() - start_time
        self.logger.info(
            f"找到 {total_processed} 张处理后图片, 覆盖 {len(self.processed_images)} 个基础名称. 耗时: {elapsed_time:.2f}秒")
        return self.processed_images

    def _process_target_file(self, filename: str, naming_pattern: Pattern):
        """处理单个目标文件（线程安全）"""
        # 尝试匹配命名模式
        match = naming_pattern.match(filename)

        with self._lock:
            if match:
                group_dict = match.groupdict()
                if 'base_name' not in group_dict:
                    self.naming_errors.append(filename)
                    return
                base_name = group_dict['base_name']
                suffix = group_dict.get('suffix', '')  # 允许无后缀
                self.processed_images[base_name].append(suffix)
            else:
                self.naming_errors.append(filename)

            self.processed_files += 1
            self.progress_percent = int((self.processed_files / self.total_files) * 100)
            self._update_progress()

    def verify_completeness(self, expected_suffixes: List[str]) -> Tuple[List[str], List[Tuple[str, Set[str]]]]:
        """
        验证处理完整性，检查每张原始图片是否都有预期数量的处理版本

        参数:
        expected_suffixes: 期望的后缀列表

        返回:
        完全未处理的图片列表和处理不完整的图片列表
        """
        self.logger.info("开始检查处理完整性...")
        start_time = time.time()

        self.missing_images = []
        self.incomplete_images = []
        missing_queue = Queue()  # 用于存储需要复制的文件信息

        # 使用线程池并行验证
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for base_name, original_filename in self.source_images:
                futures.append(executor.submit(
                    self._verify_image_completeness,
                    base_name,
                    original_filename,
                    set(expected_suffixes),
                    missing_queue
                ))

            # 显示进度
            self.processed_files = 0
            self.total_files = len(futures)
            self.progress_percent = 0
            self._update_progress()
            self._monitor_progress(futures, "验证处理完整性")

            # 等待所有任务完成
            concurrent.futures.wait(futures)

        # 启动复制线程池
        self._copy_missing_files(missing_queue)

        elapsed_time = time.time() - start_time
        self.logger.info(f"完成处理完整性验证. 耗时: {elapsed_time:.2f}秒")
        return self.missing_images, self.incomplete_images

    def _verify_image_completeness(self, base_name: str, original_filename: str,
                                   expected_suffixes: Set[str], missing_queue: Queue):
        """验证单个图像的完整性（线程安全）"""
        need_to_copy = False

        with self._lock:
            if base_name not in self.processed_images:
                # 原始图片完全没有处理
                self.missing_images.append(original_filename)
                need_to_copy = True
            elif set(self.processed_images[base_name]) != expected_suffixes:
                # 原始图片处理不完整
                existing_suffixes = set(self.processed_images[base_name])
                missing_suffixes = expected_suffixes - existing_suffixes
                excess_suffixes = existing_suffixes - expected_suffixes

                if missing_suffixes:  # 只在缺少后缀时才算不完整
                    self.incomplete_images.append((original_filename, missing_suffixes))
                    need_to_copy = True

                # 如果有多余的后缀，在日志中记录但不算作错误
                if excess_suffixes:
                    self._log(f"警告: {original_filename} 有多余的后缀: {', '.join(sorted(excess_suffixes))}")

            self.processed_files += 1
            self.progress_percent = int((self.processed_files / self.total_files) * 100)
            self._update_progress()

        # 如果需要复制，将任务添加到队列
        if need_to_copy:
            missing_queue.put(original_filename)

    def _copy_missing_files(self, missing_queue: Queue):
        """并行复制缺失的文件"""
        copy_tasks = []
        while not missing_queue.empty():
            copy_tasks.append(missing_queue.get())

        if not copy_tasks:
            return

        self.logger.info(f"开始复制 {len(copy_tasks)} 个缺失或不完整的文件...")

        # 使用线程池并行复制文件
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for filename in copy_tasks:
                futures.append(executor.submit(
                    shutil.copy,
                    os.path.join(self.source_folder, filename),
                    os.path.join(self.missing_folder, filename)
                ))

            # 等待所有复制任务完成
            concurrent.futures.wait(futures)

        self.logger.info("文件复制完成.")

    def _monitor_progress(self, futures, task_name):
        """在后台监控任务进度"""

        def progress_reporter():
            last_percent = -1
            while not all(future.done() for future in futures):
                with self._lock:
                    current_percent = self.progress_percent

                if current_percent != last_percent:
                    self.logger.info(f"{task_name}进度: {current_percent}% ({self.processed_files}/{self.total_files})")
                    last_percent = current_percent
                time.sleep(0.5)

            self.logger.info(f"{task_name}进度: 100% ({self.total_files}/{self.total_files})")

        # 启动进度报告线程
        threading.Thread(target=progress_reporter, daemon=True).start()

    def get_summary(self, expected_count: int, naming_format: str) -> dict:
        """获取验证结果摘要数据"""
        return {
            "missing_images": self.missing_images,
            "incomplete_images": self.incomplete_images,
            "naming_errors": self.naming_errors,
            "expected_count": expected_count,
            "naming_format": naming_format
        }

    def print_summary(self, expected_count, naming_format,
                      is_pure_serial=False, is_pure_basename=False,
                      processed_count=0):
        """打印验证结果摘要"""
        self.logger.info("=" * 50)
        self.logger.info("验证结果摘要:")
        self.logger.info("=" * 50)

        # 1. 显示完全未处理的图片
        self.logger.info("1. 完全未处理的图片:")
        if self.missing_images:
            for img in self.missing_images[:10]:  # 只显示前10个
                self.logger.info(f"  - {img}")
            if len(self.missing_images) > 10:
                self.logger.info(f"  ... 以及 {len(self.missing_images) - 10} 个更多 ...")
            self.logger.info(f"  共 {len(self.missing_images)} 张图片未处理，已复制到 '{self.missing_folder}'")
        else:
            self.logger.info("  所有原始图片都已进行处理，没有完全遗漏的图片。")

        # 2. 显示处理不完整的图片
        self.logger.info("2. 处理不完整的图片:")
        if self.incomplete_images:
            for img, missing_suffixes in self.incomplete_images[:10]:  # 只显示前10个
                self.logger.info(f"  - {img} (缺少版本: {', '.join(sorted(missing_suffixes))})")
            if len(self.incomplete_images) > 10:
                self.logger.info(f"  ... 以及 {len(self.incomplete_images) - 10} 个更多 ...")
            self.logger.info(f"  共 {len(self.incomplete_images)} 张图片处理不完整，已复制到 '{self.missing_folder}'")
        else:
            self.logger.info(f"  所有已处理的图片都有完整的{expected_count}个版本，没有处理不完整的图片。")

        # 3. 显示命名不规范的图片
        self.logger.info("3. 命名不规范的图片:")
        if self.naming_errors:
            for img in self.naming_errors[:10]:  # 只显示前10个
                self.logger.info(f"  - {img}")
            if len(self.naming_errors) > 10:
                self.logger.info(f"  ... 以及 {len(self.naming_errors) - 10} 个更多 ...")
            self.logger.info(f"  共 {len(self.naming_errors)} 张图片命名不规范")
        else:
            self.logger.info(f"  所有处理后的图片命名均符合规范: {naming_format}")

        # 总结
        self.logger.info("=" * 50)
        self.logger.info("验证总结:")
        total_issues = len(self.missing_images) + len(self.incomplete_images) + len(self.naming_errors)
        if total_issues == 0:
            self.logger.success("太棒了！所有图片都已正确处理且命名规范。")
        else:
            self.logger.warning(f"发现 {total_issues} 个问题，详见上述报告。")
        self.logger.info("=" * 50)

        if is_pure_serial:
            self.logger.warning("[!] 纯序号模式注意:")
            self.logger.info(f" - 实际找到处理文件: {processed_count} 个")
            self.logger.info(f" - 期望总数验证: {'通过' if processed_count >= expected_count else '不通过'}")
            self.logger.info(" - 文件对应关系无法验证，缺失文件列表仅供参考")

        if is_pure_basename:
            self.logger.success("[√] 已验证所有原文件的1对1对应关系")


class NamingPattern:
    """命名模式生成器，用于创建和应用自定义命名模式"""

    @staticmethod
    def create_numeric_suffix_pattern(
            delimiter: str = "_",
            extension: str = ".png",
            min_digits: int = 1,
            max_digits: int = None
    ) -> Pattern:
        """
        创建数字后缀的命名模式
        """
        logger = LogManager.get_logger("NamingPattern")
        logger.debug(f"创建数字后缀模式: delimiter={delimiter}, extension={extension}, "
                     f"min_digits={min_digits}, max_digits={max_digits}")

        # 构建正则表达式
        if max_digits is None:
            digit_part = r'\d+'  # 至少一位数字，不限制最大位数
        elif min_digits == max_digits:
            digit_part = r'\d{' + str(min_digits) + '}'  # 固定位数
        else:
            digit_part = r'\d{' + str(min_digits) + ',' + str(max_digits) + '}'  # 指定范围位数

        pattern_str = r'^(?P<base_name>.+)' + re.escape(delimiter) + r'(?P<suffix>' + digit_part + r')' + re.escape(
            extension) + r'$'
        return re.compile(pattern_str, re.IGNORECASE)

    @staticmethod
    def create_range_suffix_pattern(
            delimiter: str = "_",
            extension: str = ".png",
            suffix_range: Tuple[int, int] = (1, 9)
    ) -> Pattern:
        """
        创建指定范围内数字后缀的命名模式
        """
        logger = LogManager.get_logger("NamingPattern")
        logger.debug(f"创建范围后缀模式: delimiter={delimiter}, extension={extension}, "
                     f"suffix_range={suffix_range}")

        # 构建正则表达式
        # 将范围内的每个数字转换为字符串，并用'|'连接
        number_options = '|'.join([str(i) for i in range(suffix_range[0], suffix_range[1] + 1)])
        pattern_str = r'^(?P<base_name>.+)' + re.escape(
            delimiter) + r'(?P<suffix>' + f'({number_options})' + r')' + re.escape(extension) + r'$'
        return re.compile(pattern_str, re.IGNORECASE)

    @staticmethod
    def create_custom_pattern(pattern_template: str) -> Pattern:
        """
        创建自定义命名模式
        """
        logger = LogManager.get_logger("NamingPattern")
        logger.debug(f"创建自定义模式: {pattern_template}")

        # 不再强制要求同时包含两个命名组
        return re.compile(pattern_template, re.IGNORECASE)