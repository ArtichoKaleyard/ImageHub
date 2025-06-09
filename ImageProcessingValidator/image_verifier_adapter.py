# image_verifier_adapter.py

import json
import os
import time
import threading
from typing import List, Dict, Tuple, Set, Callable, Optional, Any, Union

# 导入核心处理模块
from ImageProcessingValidator.image_verifier_core import ImageVerifier, NamingPattern

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

    @pyqtSlot()
    def run(self):
        """
        在单独线程中执行验证任务
        """
        try:
            # 调用ImageVerifierAdapter执行验证
            adapter = ImageVerifierAdapter()
            adapter.set_gui_signals(self.signals)
            result = adapter.verify_image_processing(**self.config)

            # 发出完成信号
            if not self.abort:
                self.signals.finished.emit(result)

        except Exception as e:
            # 发出错误信号
            self.signals.error.emit(str(e))

    def stop(self):
        """
        设置中止标志
        """
        self.abort = True


class ImageVerifierAdapter:
    """
    图片验证器适配器，桥接核心逻辑与GUI/CLI接口
    """

    def __init__(self):
        self.verifier = None
        self.signals = None
        self._is_gui_mode = False

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
            print(message)

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
            suffix_type: str = "range",  # "range", "numeric", "custom"
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
        self._log_handler(f"开始验证图片处理情况... (最大并行线程数: {max_workers if max_workers else '自动'})")
        self._log_handler(f"原始图片文件夹: {source_folder}")
        self._log_handler(f"处理后图片文件夹: {target_folder}")
        self._log_handler(f"未处理图片输出文件夹: {missing_folder}")

        # 初始化 processed_images 为默认空字典
        processed_images = {}

        # 根据 suffix_type 创建不同的命名模式
        if suffix_type == "range":
            self._log_handler(f"后缀类型: 范围")
            self._log_handler(f"后缀范围: {suffix_range[0]}-{suffix_range[1]}")
            naming_pattern = NamingPattern.create_range_suffix_pattern(
                suffix_delimiter, expected_extension, suffix_range
            )
            expected_suffixes = [str(i) for i in range(suffix_range[0], suffix_range[1] + 1)]
            expected_count = suffix_range[1] - suffix_range[0] + 1
            naming_format = f"[原名]{suffix_delimiter}[{suffix_range[0]}-{suffix_range[1]}]{expected_extension}"

        elif suffix_type == "numeric":
            self._log_handler(f"后缀类型: 数字")
            self._log_handler(f"最小位数: {min_digits}")
            self._log_handler(f"最大位数: {max_digits if max_digits else '不限'}")
            naming_pattern = NamingPattern.create_numeric_suffix_pattern(
                suffix_delimiter, expected_extension, min_digits, max_digits
            )
            naming_format = f"[原名]{suffix_delimiter}[数字{min_digits}{'-' + str(max_digits) if max_digits else '+'}位]{expected_extension}"
            expected_suffixes = None
            expected_count = None

        elif suffix_type == "custom":
            self._log_handler(f"后缀类型: 自定义")
            self._log_handler(f"自定义模式: {custom_pattern}")
            naming_pattern = NamingPattern.create_custom_pattern(custom_pattern)

            # 新增命名模式类型判断
            self.is_pure_serial = False
            self.is_pure_basename = False

            # 解析正则表达式组
            has_base = '?P<base_name>' in custom_pattern
            has_suffix = '?P<suffix>' in custom_pattern
            if not has_base and has_suffix:

                # 纯序号模式 (例如：^\d+\.txt$)
                self.is_pure_serial = True
                expected_count = len(self.verifier.source_files)  # 默认期望与原文件数量一致
                self._log_handler(f"纯序号模式检测：将执行数量验证（预期数量: {expected_count}）")
                naming_format = f"纯序号格式（无法对应原始文件）"
                self._log_handler("警告：无法验证文件名对应关系，仅验证处理后的文件总数")

            elif has_base and not has_suffix:
                # 纯原名模式 (例如：^.+\.txt$)
                self.is_pure_basename = True
                expected_suffixes = ['']
                expected_count = 1
                naming_format = "原名格式（一对一处理）"
        else:
            raise ValueError(f"不支持的后缀类型: {suffix_type}")

        self._log_handler(f"后缀分隔符: '{suffix_delimiter}'")
        self._log_handler(f"处理后图片格式: {expected_extension}")
        self._log_handler(f"原始图片格式: {', '.join(source_extensions)}")
        self._log_handler("-" * 50)

        # 创建验证器实例并设置回调
        self.verifier = ImageVerifier(source_folder, target_folder, missing_folder, max_workers)
        self.verifier.set_callbacks(
            progress_callback=self._progress_handler,
            log_callback=self._log_handler
        )

        # 扫描原始图片
        self.verifier.scan_source_images(source_extensions)

        # 扫描处理后图片
        try:
            processed_images = self.verifier.scan_processed_images(naming_pattern)
        except Exception as e:
            self._log_handler(f"扫描处理后图片时发生错误: {str(e)}")
            processed_images = {}

        # 如果未指定期望的后缀（数字或自定义模式），则从处理结果中提取
        if expected_suffixes is None and processed_images:
            all_suffixes = set()
            for suffixes in processed_images.values():
                all_suffixes.update(suffixes)
            expected_suffixes = sorted(list(all_suffixes))
            expected_count = len(expected_suffixes)
            self._log_handler(f"从处理结果中提取的后缀列表: {', '.join(expected_suffixes)}")
            self._log_handler(f"期望的处理版本数量: {expected_count}")

        # 如果是 numeric 模式且未指定 expected_count_per_image，则尝试基于 expected_suffixes 推断
        if suffix_type == "numeric" and expected_count_per_image is None:
            if expected_suffixes:
                self._log_handler(
                    "未指定每个基础图片应生成的处理版本数量，尝试从实际处理结果中推断...")
                expected_count_per_image = expected_count
                self._log_handler(f"推断得每个基础图片应生成的处理版本数量: {expected_count_per_image}")
            else:
                self._log_handler("无法推断每个基础图片应生成的处理版本数量，未找到任何处理后的图片。")
                expected_count_per_image = 0

        # 验证处理完整性
        if verify_completeness:
            if self.is_pure_serial:
                # 纯序号模式走数量验证分支
                processed_count = self.verifier.processed_count
                is_valid = processed_count >= expected_count

                # 记录缺失数量（如果允许部分缺失需调整逻辑）
                self.verifier.missing_images = list(self.verifier.source_files.keys())[
                                               :expected_count - processed_count]

                self._log_handler(f"数量验证结果：找到 {processed_count} 个处理文件（需要至少 {expected_count} 个）")
            else:
                # 原文件名匹配验证逻辑
                if expected_suffixes is not None:
                    self.verifier.verify_completeness(expected_suffixes)

        else:
            self._log_handler("\n跳过处理完整性验证.")

        # 打印结果摘要
        # 传递新增的模式标记参数
        self.verifier.print_summary(
            expected_count,
            naming_format,
            is_pure_serial=self.is_pure_serial,
            is_pure_basename=self.is_pure_basename,
            processed_count=len(self.verifier.processed_images) if hasattr(self.verifier, 'processed_images') else 0
        )

        # 计算总耗时
        total_time = time.time() - start_time
        self._log_handler(f"\n总计耗时: {total_time:.2f}秒")

        # 返回验证结果
        return {
            "missing_images": self.verifier.missing_images,
            "incomplete_images": self.verifier.incomplete_images,
            "naming_errors": self.verifier.naming_errors if verify_naming else []
        }


def cli_mode(config_key="numeric_config"):
    """
    从 JSON 文件中读取配置并执行验证
    支持 'range_config', 'numeric_config', 'custom_config'
    """
    # 读取配置文件
    try:
        with open("../config/IPV_config.json", "r", encoding="utf-8") as f:
            configs = json.load(f)
    except FileNotFoundError:
        print("配置文件 IPV_config.json 未找到，请检查文件是否存在。")
        return
    except json.JSONDecodeError:
        print("配置文件格式错误，请检查 JSON 格式。")
        return
    config = configs.get(config_key)
    if not config:
        print(f"配置段 '{config_key}' 不存在于配置文件中。")
        return
    # 类型转换：将 JSON 中的数组转换为 Python 元组
    if "suffix_range" in config:
        config["suffix_range"] = tuple(config["suffix_range"])
    if "source_extensions" in config:
        config["source_extensions"] = tuple(config["source_extensions"])
    # 创建适配器实例
    adapter = ImageVerifierAdapter()
    print(f"使用配置段 '{config_key}' 开始测试 CLI 模式...")
    print("当前配置:")
    for k, v in config.items():
        print(f"  {k}: {v}")
    try:
        # 执行验证
        start_time = time.time()
        result = adapter.verify_image_processing(**config)
        duration = time.time() - start_time
        # 显示结果摘要
        print("\n验证完成，结果摘要:")
        print(f"完全未处理图片数: {len(result['missing_images'])}")
        print(f"处理不完整图片数: {len(result['incomplete_images'])}")
        print(f"命名错误图片数: {len(result['naming_errors'])}")
        print(f"总耗时: {duration:.2f}秒")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    # 运行测试
    cli_mode()
