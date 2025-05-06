import datetime
import errno
import os
import re
import sys
import threading
import time
from queue import Queue

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTextEdit, QFileDialog,
    QMessageBox, QStatusBar, QGroupBox, QFontDialog
)
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from style.style_config import APP_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, GROUP_BOX_STYLE, INPUT_STYLE, \
    STATUS_BAR_STYLE, THEME

"""
图片自动重命名工具 GUI 版本
功能：监控指定文件夹中的图片文件，自动重命名为 原文件名_序号.扩展名 格式
"""

# 标签映射字典：将中文标签映射为英文标签
TAG_MAPPING = {
    '系统': 'SYSTEM',
    '初始化': 'INIT',
    '跳过': 'SKIP',
    '发现': 'FOUND',
    '警告': 'WARN',
    '操作': 'ACTION',
    '错误': 'ERROR',
    '重命名': 'RENAME',
    '删除': 'DELETE',
    '状态': 'STATUS',
    '提示': 'HINT',
    '限制': 'LIMIT'
}

# 日志标签颜色映射
TAG_COLOR_MAPPING = {
    'SYSTEM': '#5555FF',  # 系统消息蓝色
    'INIT': '#5555FF',  # 初始化消息蓝色
    'SKIP': '#FFA500',  # 跳过消息橙色
    'FOUND': '#008000',  # 发现消息绿色
    'WARN': '#FFA500',  # 警告消息橙色
    'ACTION': '#008000',  # 操作消息绿色
    'ERROR': '#FF0000',  # 错误消息红色
    'RENAME': '#008000',  # 重命名消息绿色
    'DELETE': '#FFA500',  # 删除消息橙色
    'STATUS': '#5555FF',  # 状态消息蓝色
    'HINT': '#FFA500',  # 提示消息橙色
    'LIMIT': '#FFA500'  # 限制消息橙色
}

# 标签固定宽度
TAG_WIDTH = 8


def format_tag(tag):
    """
    格式化日志标签，保持与命令行版本一致的格式

    参数:
        tag (str): 日志标签（中文）

    返回:
        str: 格式化后的标签和时间戳
    """
    # 将中文标签转换为英文
    eng_tag = TAG_MAPPING.get(tag, tag)

    # 计算居中位置
    if len(eng_tag) >= TAG_WIDTH:
        # 如果标签长度超过固定宽度，则截断
        padded_tag = eng_tag[:TAG_WIDTH]
    else:
        # 计算需要的空格数
        spaces_needed = TAG_WIDTH - len(eng_tag)
        left_spaces = spaces_needed // 2
        right_spaces = spaces_needed - left_spaces

        # 构建居中的标签
        padded_tag = ' ' * left_spaces + eng_tag + ' ' * right_spaces

    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    return f"[{padded_tag}] [{current_time}]"


def show_windows_notification(title, message, duration=5):
    """
    显示Windows系统通知

    参数:
        title (str): 通知标题
        message (str): 通知内容
        duration (int): 通知持续时间(秒)
    """

    def run_toast_in_subprocess():
        # 创建一个临时Python脚本用于显示通知
        temp_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_toast.py")
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write('''
import sys
from win10toast import ToastNotifier

title = sys.argv[1]
message = sys.argv[2]
try:
    duration = int(sys.argv[3])
except IndexError:
    duration = 5  # 默认值

# 重定向标准输出和错误输出到null设备
import os
null_device = open(os.devnull, 'w')
sys.stdout = null_device
sys.stderr = null_device

# 显示通知
toaster = ToastNotifier()
toaster.show_toast(
    title, 
    message,
    duration=duration,
    threaded=False
)
            ''')

        # 运行脚本并隐藏输出
        os.system(f'start /B "" python "{temp_script}" "{title}" "{message}" >nul 2>&1')

        # 等待一段时间后删除临时脚本
        def delete_temp_file():
            time.sleep(5)
            try:
                if os.path.exists(temp_script):
                    os.remove(temp_script)
            except:
                pass

        threading.Thread(target=delete_temp_file, daemon=True).start()

    # 使用单独进程运行通知
    run_toast_in_subprocess()


class ImageRenamer(FileSystemEventHandler):
    """
    图片重命名处理器类，负责监控文件系统事件并重命名新保存的图片
    """

    def __init__(self, watch_folder, max_images=10, log_func=None, show_notification_func=None):
        """
        初始化图片重命名处理器

        参数:
            watch_folder (str): 需要监控的文件夹路径
            max_images (int): 每个图像系列的最大图片数量
            log_func (callable): 日志输出函数
            show_notification_func (callable): 显示通知的函数
        """
        self.watch_folder = watch_folder
        self.max_images = max_images
        self.counter = {}  # 用于跟踪每个基础文件名已处理的文件数量
        self.file_queue = Queue()  # 处理队列
        self.process_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.process_thread.start()
        self.processing_files = set()  # 记录正在处理的文件，防止重复处理
        self.last_msg_was_time = False
        self.log_func = log_func or print
        self.show_notification_func = show_notification_func or (lambda title, msg: None)
        self._init_counter()  # 初始化计数器

    def _init_counter(self):
        """初始化计数器，扫描监控文件夹中的已有文件"""
        self.log_func(f"{format_tag('系统')}正在扫描文件夹: {self.watch_folder}")

        for filename in os.listdir(self.watch_folder):
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                # 尝试匹配已有的 basename_number.ext 格式
                match = re.match(r'(.+)_(\d+)\.([^.]+)$', filename)
                if match:
                    basename = match.group(1)
                    number = int(match.group(2))
                    if basename in self.counter:
                        self.counter[basename] = max(self.counter[basename], number)
                    else:
                        self.counter[basename] = number

        if self.counter:
            self.log_func(f"{format_tag('初始化')}已找到以下文件系列:")
            for basename, count in self.counter.items():
                self.log_func(f"  - {basename}: 已有{count}个文件")
        else:
            self.log_func(f"{format_tag('初始化')}文件夹中没有检测到已命名的图像系列")

    def on_created(self, event):
        """
        当新文件创建时调用

        参数:
            event: 文件系统事件
        """
        if not event.is_directory and not event.src_path.endswith(('.tmp', '.crdownload')):
            # 将文件添加到队列而不是立即处理
            self.file_queue.put(event.src_path)

    def is_file_accessible(self, file_path):
        """检查文件是否可访问（未被占用）"""
        try:
            with open(file_path, 'rb') as f:
                return True
        except (IOError, OSError):
            return False

    def _process_queue(self):
        """持续处理队列中的文件"""
        while True:
            file_path = self.file_queue.get()
            # 检查文件是否已在处理中
            if file_path in self.processing_files:
                self.file_queue.task_done()
                continue

            self.processing_files.add(file_path)
            # 等待文件写入完成
            time.sleep(1)

            # 处理文件
            try:
                if os.path.exists(file_path):  # 确认文件仍然存在
                    self._process_file(file_path)
            except Exception as e:
                self.log_func(f"{format_tag('错误')}处理文件时出错: {e}")
            finally:
                # 处理完成后从集合中移除
                self.processing_files.discard(file_path)
                self.file_queue.task_done()

    def _process_file(self, file_path):
        """
        处理新创建的文件

        参数:
            file_path (str): 需要处理的文件路径
        """
        # 确保是图片文件
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            return

        # 再次检查文件是否存在
        if not os.path.exists(file_path):
            self.log_func(f"{format_tag('跳过')}文件不存在，可能已被移动或删除: {file_path}")
            return

        # 获取文件信息
        dirname = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)

        # 检查文件名是否已经包含数字后缀
        if re.match(r'.+_\d+\.[^.]+$', filename):
            self.log_func(f"{format_tag('跳过')}文件 {filename} 已包含数字后缀")
            return

        # 检查新图像文件
        if name not in self.counter:
            self.counter[name] = 0
            self.log_func(f"{format_tag('发现')}检测到新的图像系列: {name}")

        # 增加计数器，但要考虑最大限制
        self.counter[name] += 1

        # 如果超过最大图片数量，则覆盖最后一个文件
        if self.counter[name] > self.max_images:
            self.log_func(f"{format_tag('警告')}{name} 系列已达到{self.max_images}张图片上限")
            self.log_func(f"{format_tag('操作')}将覆盖最后一个文件: {name}_{self.max_images}{ext}")
            self.counter[name] = self.max_images

        # 达到最大图片数量时发送Windows通知
        if self.counter[name] >= self.max_images:
            self.show_notification_func("图片重命名工具", f"{name} 系列已达到{self.max_images}张图片上限")

        new_filename = f"{name}_{self.counter[name]}{ext}"
        new_path = os.path.join(dirname, new_filename)

        # 检查文件是否可访问
        if not self.is_file_accessible(file_path):
            self.log_func(f"{format_tag('错误')}源文件被占用，跳过处理: {filename}")
            return

        # 删除旧文件
        if os.path.exists(new_path):
            retry = 3
            while retry > 0:
                try:
                    os.remove(new_path)
                    self.log_func(f"{format_tag('删除')}已删除现有文件: {new_filename}")
                    break
                except (OSError, IOError) as e:
                    retry -= 1
                    time.sleep(2)
            if retry == 0:
                self.log_func(f"{format_tag('错误')}无法删除目标文件: {new_filename}")
                return

        # 重命名文件，处理重试逻辑
        retry = 3
        while retry > 0:
            try:
                os.rename(file_path, new_path)
                self.log_func(
                    f"{format_tag('重命名')}{filename} → {new_filename} ({self.counter[name]}/{self.max_images})")
                break
            except (OSError, IOError) as e:
                if e.errno in (errno.EACCES, errno.EBUSY) or (hasattr(e, 'winerror') and e.winerror == 32):
                    retry -= 1
                    self.log_func(f"{format_tag('警告')}文件被占用，{2}秒后重试... 剩余尝试次数: {retry}")
                    time.sleep(2)
                else:
                    self.log_func(f"{format_tag('错误')}重命名文件时出错: {str(e)}")
                    break
        if retry == 0:
            self.log_func(f"{format_tag('错误')}多次尝试失败，跳过文件: {filename}")

class Worker(QtCore.QObject):
    """
    工作线程类，负责在后台执行监控任务
    """
    log = pyqtSignal(str)  # 日志信号，用于向UI发送日志
    finished = pyqtSignal()  # 完成信号，用于通知UI任务已完成
    show_notification = pyqtSignal(str, str)  # 通知信号

    def __init__(self, folder_path, max_images):
        """
        初始化工作线程

        参数:
            folder_path (str): 需要监控的文件夹路径
            max_images (int): 每个图像系列的最大图片数量
        """
        super().__init__()
        self.folder_path = folder_path
        self.max_images = max_images
        self.running = False
        self.observer = None

    def start_monitoring(self):
        """开始监控指定文件夹"""
        if not os.path.exists(self.folder_path):
            self.log.emit(f"{format_tag('错误')}文件夹不存在: {self.folder_path}")
            return

        self.running = True
        self.log.emit(f"{format_tag('系统')}开始监控文件夹: {self.folder_path}")
        self.log.emit(f"{format_tag('系统')}每个图像系列最多处理: {self.max_images} 张图片")
        self.log.emit(f"{format_tag('提示')}按停止按钮停止监控")

        event_handler = ImageRenamer(self.folder_path, self.max_images, self.log.emit, self.show_notification.emit)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.folder_path, recursive=False)
        self.observer.start()

        # 连接信号并显示通知
        # self.worker = Worker(self.folder_path, self.max_images)
        # self.worker.show_notification.connect(self.show_notification_in_main_thread)
        # self.show_notification_in_main_thread("图片重命名工具", "已开始监控文件夹")

        try:
            while self.running:
                time.sleep(1)
        except Exception as e:
            self.log.emit(f"{format_tag('错误')}监控异常: {str(e)}")
        finally:
            self.observer.stop()
            self.observer.join()
            self.log.emit(f"{format_tag('系统')}监控已停止")
            self.finished.emit()

    def stop_monitoring(self):
        """停止监控任务"""
        self.running = False


class ImageRenamerGUI(QWidget):
    """
    图片重命名工具的图形用户界面类
    """

    def __init__(self):
        """初始化GUI界面"""
        super().__init__()
        self.running_time = 0  # 运行时间计数器
        self.timer = None  # 计时器
        self.worker = None  # 工作线程
        self.worker_thread = None  # QThread对象
        self.initUI()  # 初始化UI

    def initUI(self):
        """初始化用户界面"""
        self.setStyleSheet(APP_STYLE)
        layout = QVBoxLayout(self)

        # 文件夹选择区域
        folder_group = QGroupBox("监控设置")
        folder_group.setStyleSheet(GROUP_BOX_STYLE)
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setStyleSheet(INPUT_STYLE)
        self.browse_button = QPushButton("浏 览")
        self.browse_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(QLabel("监控文件夹:"))
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.browse_button)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)

        # 参数设置区域
        param_group = QGroupBox("参数设置")
        param_group.setStyleSheet(GROUP_BOX_STYLE)
        param_layout = QHBoxLayout()
        self.max_images_spin = QSpinBox()
        self.max_images_spin.setStyleSheet(INPUT_STYLE)
        self.max_images_spin.setRange(1, 100)
        self.max_images_spin.setValue(10)
        param_layout.addWidget(QLabel("最大文件数:"))
        param_layout.addWidget(self.max_images_spin)
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("开 始 监 控")
        self.start_button.setObjectName("start_button")
        self.start_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button = QPushButton("停 止 监 控")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)

        # 添加字体选择按钮
        self.font_button = QPushButton("设置字体")
        self.font_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.font_button.clicked.connect(self.select_font)
        btn_layout.addWidget(self.font_button)

        layout.addLayout(btn_layout)

        # 日志区域
        log_group = QGroupBox("运行日志")
        log_group.setStyleSheet(GROUP_BOX_STYLE)
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        # 设置等宽字体，确保标签显示一致
        font = QtGui.QFont("Courier New", 10)
        font.setFixedPitch(True)  # 确保是等宽字体
        self.log_text.setFont(font)

        # 设置样式表
        self.log_text.setStyleSheet(f"""
            font-family: "Courier New";
            font-size: 10pt;
            background-color: {THEME["card_background"]};
            padding: 5px;
            border: 1px solid {THEME["border"]};
            border-radius: 6px;
        """)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 状态栏
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet(STATUS_BAR_STYLE)
        layout.addWidget(self.statusBar)

        # 设置窗口标题和大小
        self.setWindowTitle("自动图片重命名工具")
        self.resize(700, 500)

    def show_notification_in_main_thread(self, title, message):
        """在主线程中显示通知"""
        show_windows_notification(title, message)

    def select_font(self):
        """打开字体选择对话框，允许用户自定义日志字体"""
        current_font = self.log_text.font()
        font, ok = QFontDialog.getFont(current_font, self, "选择日志字体")
        if ok:
            # 确保选择的是等宽字体
            font.setFixedPitch(True)
            self.log_text.setFont(font)
            self.log_text.setStyleSheet(f"""
                font-family: "{font.family()}";
                font-size: {font.pointSize()}pt;
                background-color: {THEME["card_background"]};
                padding: 5px;
                border: 1px solid {THEME["border"]};
                border-radius: 6px;
            """)

    def browse_folder(self):
        """打开文件夹选择对话框"""
        folder = QFileDialog.getExistingDirectory(self, "选择监控文件夹")
        if folder:
            self.folder_input.setText(folder)

    def start_monitoring(self):
        """开始监控任务"""
        folder = self.folder_input.text().strip()
        max_images = self.max_images_spin.value()
        if not folder or not os.path.exists(folder):
            QMessageBox.critical(self, "错误", "请选择有效的文件夹路径")
            return
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # 重置计时并启动计时器
        self.running_time = 0
        self.statusBar.showMessage(f"运行时间: 0s")
        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_status_bar)
        self.timer.start(1000)  # 每秒更新一次

        # 创建和启动工作线程
        self.worker = Worker(folder, max_images)
        self.worker_thread = QtCore.QThread(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker.show_notification.connect(self.show_notification_in_main_thread)
        self.worker_thread.started.connect(self.worker.start_monitoring)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_monitoring_finished)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.log.connect(self.update_log)
        self.worker_thread.start()

    def stop_monitoring(self):
        """停止监控任务"""
        if self.worker:
            self.worker.stop_monitoring()
        if self.timer:
            self.timer.stop()

    def on_monitoring_finished(self):
        """监控任务完成时的回调函数"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.timer:
            self.timer.stop()

    def update_status_bar(self):
        """更新状态栏显示的运行时间"""
        self.running_time += 1
        time_str = self.format_time(self.running_time)
        self.statusBar.showMessage(f"运行时间: {time_str}")

    def format_time(self, seconds):
        """
        格式化时间显示

        参数:
            seconds (int): 总秒数

        返回:
            str: 格式化后的时间字符串
        """
        h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
        if h > 0:
            return f"{h}h {m:02d}m {s:02d}s"
        elif m > 0:
            return f"{m}m {s:02d}s"
        else:
            return f"{s}s"

    def closeEvent(self, event):
        """
        处理窗口关闭事件

        参数:
            event: 关闭事件
        """
        # 在关闭窗口时停止监控和计时器
        if self.worker:
            self.worker.stop_monitoring()
        if self.timer:
            self.timer.stop()
        event.accept()

    def update_log(self, message):
        """
        更新日志显示

        参数:
            message (str): 日志消息
        """
        # 修改解析方式，适应当前格式
        tag_match = re.match(r'\[([^]]+)] \[([^]]+)](.+)', message)

        if tag_match:
            tag_raw = tag_match.group(1)  # 提取原始标签（包含空格）
            tag = tag_raw.strip()  # 清除两侧空格获取实际标签
            time_str = tag_match.group(2)  # 提取时间
            rest = tag_match.group(3)  # 提取剩余内容

            # 创建一个新的文本文档片段
            doc = self.log_text.document()
            cursor = QtGui.QTextCursor(doc)
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

            # 设置标签颜色
            tag_format = QtGui.QTextCharFormat()
            tag_color = TAG_COLOR_MAPPING.get(tag, "#000000")
            tag_format.setForeground(QtGui.QColor(tag_color))

            # 插入带颜色的标签，保持原始格式（包括空格）
            cursor.insertText(f"[{tag_raw}]", tag_format)

            # 设置时间和内容颜色
            time_format = QtGui.QTextCharFormat()
            time_format.setForeground(QtGui.QColor(THEME["text"]))  # 使用主题定义的文本颜色
            cursor.insertText(f" [{time_str}]{rest}\n", time_format)

            # 滚动到底部
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
        else:
            # 对于格式不匹配的消息，使用默认颜色
            cursor = self.log_text.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)

            default_format = QtGui.QTextCharFormat()
            default_format.setForeground(QtGui.QColor(THEME["text"]))
            cursor.insertText(f"{message}\n", default_format)

            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageRenamerGUI()
    window.show()
    sys.exit(app.exec())