# image_verifier_adapter.py

import json
import os
import re
import time
import threading
from typing import List, Dict, Tuple, Set, Callable, Optional, Any, Union

# 导入核心处理模块
from ImageProcessingValidator.image_verifier_core import ImageVerifier, NamingPattern

from utils.logger import Logger, LogManager

# 条件导入PyQt6，如果不可用则不导入
try:
    from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


    # 创建假的QObject类，使代码可以在没有PyQt的情况下编译
    class QObject:
        pass


    def pyqtSignal(*args, **kwargs):
        return None


    def pyqtSlot(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


    class QRunnable:
        pass


    QThreadPool = None


class VerifierSignals(QObject):
    """
    定义验证过程中的信号
    """
    # 进度信号: 当前值, 总数, 百分比
    progress_updated = pyqtSignal(int, int, int)

    # 日志信号: 消息字符串
    log_message = pyqtSignal(str)

    # 完成信号: 结果摘要字典
    finished = pyqtSignal(dict)

    # 错误信号: 错误消息
    error = pyqtSignal(str)


class VerifierWorker(QRunnable):
    """
    使用QRunnable在Qt线程池中运行验证任务
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.signals = VerifierSignals()
        self.abort = False
        self.logger = LogManager.get_logger("IV")

    @pyqtSlot()
    def run(self):
        """
        在单独线程中执行验证任务
        """
        try:
            self.logger.debug("验证线程开始运行")

            # 调用ImageVerifierAdapter执行验证
            adapter = ImageVerifierAdapter()
            adapter.set_gui_signals(self.signals)
            result = adapter.verify_image_processing(**self.config)

            # 发出完成信号
            if not self.abort:
                self.signals.finished.emit(result)
                self.logger.debug("验证线程完成")

        except Exception as e:
            error_msg = f"验证线程发生错误: {str(e)}"
            self.logger.error(error_msg)
            # 发出错误信号
            self.signals.error.emit(error_msg)

    def stop(self):
        """
        设置中止标志
        """
        self.logger.warning("用户请求停止验证")
        self.abort = True


class ImageVerifierAdapter:
    """
    图片验证器适配器，桥接核心逻辑与GUI/CLI接口
    """

    def __init__(self):
        self.verifier = None
        self.signals = None
        self._is_gui_mode = False
        self.logger = LogManager.get_logger("IV")

        # 初始化后缀类型判断标志
        self.is_pure_serial = False
        self.is_pure_basename = False

    def set_gui_signals(self, signals: VerifierSignals):
        """
        设置GUI信号，切换到GUI模式
        """
        self.signals = signals
        self._is_gui_mode = True

    def _log_handler(self, message: str):
        """
        处理日志输出，根据模式选择适当的输出方法
        """
        if self._is_gui_mode and self.signals:
            self.signals.log_message.emit(message)
        else:
            self.logger.info(message)  # 使用统一的日志记录器

    def _progress_handler(self, current: int, total: int, percent: int):
        """
        处理进度更新，根据模式选择适当的更新方法
        """
        if self._is_gui_mode and self.signals:
            self.signals.progress_updated.emit(current, total, percent)

    def verify_image_processing(
            self,
            source_folder: str,
            target_folder: str,
            missing_folder: str,
            suffix_type: str = "range",  # "range", "numeric", 或 "custom"
            suffix_range: Tuple[int, int] = (1, 9),
            min_digits: int = 1,
            max_digits: int = None,
            expected_count_per_image: int = None,
            suffix_delimiter: str = "_",
            expected_extension: str = ".png",
            source_extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png'),
            custom_pattern: str = None,
            verify_naming: bool = True,
            verify_completeness: bool = True,
            max_workers: int = None,
    ) -> Dict:
        start_time = time.time()

        # 初始化所有要用到的变量，避免 "local variable referenced before assignment" 错误
        expected_suffixes = None
        expected_count = None
        naming_format = None
        self.is_pure_serial = False
        self.is_pure_basename = False

        self.logger.info(f"开始验证图片处理情况... (最大并行线程数: {max_workers if max_workers else '自动'})")
        self.logger.info(f"原始图片文件夹: {source_folder}")
        self.logger.info(f"处理后图片文件夹: {target_folder}")
        self.logger.info(f"未处理图片输出文件夹: {missing_folder}")

        # 设置默认 expected_extension 为后缀
        if expected_extension and not expected_extension.startswith("."):
            expected_extension = "." + expected_extension

        # 构建命名模式
        if suffix_type == "range":
            self.logger.info("后缀类型: 范围")
            self.logger.info(f"后缀范围: {suffix_range[0]} - {suffix_range[1]}")
            naming_pattern = NamingPattern.create_range_suffix_pattern(
                suffix_delimiter, expected_extension, suffix_range
            )
            expected_suffixes = [str(i) for i in range(suffix_range[0], suffix_range[1] + 1)]
            expected_count = len(expected_suffixes)
            naming_format = f"[base]{suffix_delimiter}[{suffix_range[0]}-{suffix_range[1]}]{expected_extension}"

        elif suffix_type == "numeric":
            self.logger.info("后缀类型: 数字")
            self.logger.info(f"最小位数: {min_digits}")
            self.logger.info(f"最大位数: {max_digits if max_digits else '不限'}")
            naming_pattern = NamingPattern.create_numeric_suffix_pattern(
                suffix_delimiter, expected_extension, min_digits, max_digits
            )
            self.logger.info(f"使用模式: {naming_pattern.pattern}")
            expected_suffixes = None  # 数字格式无法直接判断完整后缀集
            expected_count = expected_count_per_image
            naming_format = f"[base]{suffix_delimiter}[数字{'+' + str(max_digits) if max_digits else ''}位]{expected_extension}"

        elif suffix_type == "custom":
            self.logger.info("后缀类型: 自定义")
            if not custom_pattern:
                raise ValueError("未指定 custom_pattern，无法使用自定义模式")

            self.logger.info(f"自定义模式: {custom_pattern}")
            naming_pattern = NamingPattern.create_custom_pattern(custom_pattern)

            # 解析正则表达式中是否存在 base_name 或 suffix 组
            has_base = '?P<base_name>' in custom_pattern
            has_suffix = '?P<suffix>' in custom_pattern

            self.logger.debug(f"命名模式解析: base_name={'存在' if has_base else '不存在'}, "
                              f"suffix={'存在' if has_suffix else '不存在'}")

            if not has_base and has_suffix:
                # 原名不存，只有 suffix（类似纯序号命名: ^\d+\.png$）
                self.is_pure_serial = True
                expected_suffixes = []
                # 不能在这里访问 self.verifier.source_images（还没创建）
                # expected_count = len(self.verifier.source_images)  # 假设期望数量 = 原始文件数
                naming_format = f"纯数字序号格式（{custom_pattern}）"

            elif has_base and not has_suffix:
                # 原名存在，没有 suffix（如一对一映射处理后的文件）
                self.is_pure_basename = True
                expected_suffixes = ['']
                expected_count = 1
                naming_format = f"[base]{expected_extension}"

            else:
                # 普通自定义模式，提取所有的 suffixes（前提 suffix 组存在）
                # 示例: ^prefix_(?P<suffix>abc|123)\.(png|jpg)$  -> ['abc', '123']
                expected_suffixes = self._detect_all_suffixes(target_folder, naming_pattern)
                expected_count = len(expected_suffixes)
                naming_format = f"自定义匹配规则（使用{expected_count}种不同后缀）"
        else:
            error_msg = f"不支持的后缀类型: {suffix_type}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # 创建验证器实例
        self.verifier = ImageVerifier(
            source_folder,
            target_folder,
            missing_folder,
            max_workers,
            is_pure_serial=self.is_pure_serial
        )
        self.verifier.set_callbacks(
            progress_callback=self._progress_handler,
            log_callback=self._log_handler
        )

        # 扫描原始图片文件
        self.verifier.scan_source_images(source_extensions)

        # 添加对 is_pure_serial 情况的 expected_count 补充
        if self.is_pure_serial:
            expected_count = len(self.verifier.source_images)

        # 扫描处理后图片文件
        try:
            self.verifier.scan_processed_images(naming_pattern)
        except Exception as e:
            self.logger.error(f"扫描处理文件时发生错误: {str(e)}")

        # 如果 expected_suffixes 未设置，则从 processed_images 自动生成
        if expected_suffixes is None:
            self.logger.warning("未检测到明确的 expected_suffixes，尝试从处理后的图片自动推断...")
            all_suffixes = set()
            for suffixes in self.verifier.processed_images.values():
                all_suffixes.update(suffixes)
            expected_suffixes = sorted(list(all_suffixes))
            expected_count = len(expected_suffixes)
            self.logger.info(
                f"自动推断结果：处理文件中包含以下 {len(expected_suffixes)} 个后缀 -> {', '.join(expected_suffixes)}")

        # 验证处理完整性
        if verify_completeness:
            if self.is_pure_serial:
                # 纯序号模式走数量比对
                processed_total = sum(
                    len(s) for s in self.verifier.processed_images.values()) if self.verifier.processed_images else 0
                self.logger.info(f"数量比对：找到 {processed_total} 个处理图片（预期至少 {expected_count} 个）")
                if processed_total >= expected_count:
                    self.logger.success("纯序号模式验证通过！")
                else:
                    self.logger.warning("纯序号模式：处理文件数少于原始文件数")
            else:
                # 验证与 base_name 配套的后缀是否完整
                if expected_suffixes:
                    self.verifier.verify_completeness(expected_suffixes)
                else:
                    self.logger.warning("expected_suffixes 为空，无法进行完整验证")

        else:
            self.logger.info("跳过处理完整性验证")

        # 构建 summary 数据并打印
        self.verifier.print_summary(
            expected_count=expected_count,
            naming_format=naming_format or "未知模式",
            is_pure_serial=self.is_pure_serial,
            is_pure_basename=self.is_pure_basename,
            processed_count=len(self.verifier.processed_images) if hasattr(self.verifier, 'processed_images') else 0
        )

        # 总耗时
        total_time = time.time() - start_time
        self.logger.info(f"总计耗时: {total_time:.2f}秒")

        # 返回结果
        return self.verifier.get_summary(expected_count, naming_format)

    def _detect_all_suffixes(self, target_folder: str, naming_pattern: re.Pattern) -> List[str]:
        """
        自动检测目标文件夹中所有匹配的 suffix 名称（适用于 custom 模式）
        """
        suffixes = set()

        if not os.path.exists(target_folder):
            self.logger.warning(f"目标文件夹不存在: {target_folder}，跳过后缀检测")
            return []

        for filename in os.listdir(target_folder):
            match = naming_pattern.match(filename)
            if match:
                suffix = match.groupdict().get("suffix")
                if suffix is not None:
                    suffixes.add(suffix)

        return sorted(suffixes)


def cli_mode(config_key="numeric_config"):
    """
    从 JSON 文件中读取配置并执行验证
    支持 'range_config', 'numeric_config', 'custom_config'
    """
    # 获取CLI专用的日志记录器
    logger = LogManager.get_logger("IV")

    # 读取配置文件
    try:
        with open("../config/IPV_config.json", "r", encoding="utf-8") as f:
            configs = json.load(f)
    except FileNotFoundError:
        logger.error("配置文件 IPV_config.json 未找到，请检查文件是否存在。")
        return
    except json.JSONDecodeError:
        logger.error("配置文件格式错误，请检查 JSON 格式。")
        return

    config = configs.get(config_key)
    if not config:
        logger.error(f"配置段 '{config_key}' 不存在于配置文件中。")
        return

    # 类型转换：将 JSON 中的数组转换为 Python 元组
    if "suffix_range" in config:
        config["suffix_range"] = tuple(config["suffix_range"])
    if "source_extensions" in config:
        config["source_extensions"] = tuple(config["source_extensions"])

    # 创建适配器实例
    adapter = ImageVerifierAdapter()
    logger.info(f"使用配置段 '{config_key}' 开始测试 CLI 模式...")
    logger.info("当前配置:")
    for k, v in config.items():
        logger.info(f"  {k}: {v}")

    try:
        # 执行验证
        start_time = time.time()
        result = adapter.verify_image_processing(**config)
        duration = time.time() - start_time

        # 显示结果摘要
        logger.info("验证完成，结果摘要:")
        logger.info(f"完全未处理图片数: {len(result['missing_images'])}")
        logger.info(f"处理不完整图片数: {len(result['incomplete_images'])}")
        logger.info(f"命名错误图片数: {len(result['naming_errors'])}")
        logger.info(f"总耗时: {duration:.2f}秒")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    cli_mode()
