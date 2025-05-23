#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_labeler_model.py
自动标注辅助工具 - 模型层

该模块负责管理标注辅助工具的核心逻辑和状态
"""

import sys
import time
import logging
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtCore import Qt


class AutoLabelerMode(Enum):
    """自动标注模式枚举"""
    DRAW_ONLY = 0  # 仅自动开启绘制模式
    NEXT_ONLY = 1  # 仅自动跳转下一张
    DRAW_AND_NEXT = 2  # 绘制完成后自动进入下一张


class AutoLabelerState(Enum):
    """自动标注状态枚举"""
    IDLE = 0  # 空闲状态
    MONITORING = 1  # 监控状态
    DRAWING = 2  # 绘制中状态
    PAUSED = 3  # 暂停状态


class AutoLabelerModel(QObject):
    """自动标注工具模型类"""

    # 信号定义
    status_changed = pyqtSignal(str, str)  # 状态信息更新信号(消息, 颜色类型)
    statistics_updated = pyqtSignal(dict)  # 统计数据更新信号
    state_changed = pyqtSignal(AutoLabelerState)  # 状态变化信号
    send_key_signal = pyqtSignal(str)  # 按键发送信号

    def __init__(self):
        super().__init__()
        # 导入自定义日志记录器
        from utils.logger import LogManager
        # 创建视图层日志记录器
        self.logger = LogManager.get_logger("AL", level="info")

        # 状态与配置
        self._state = AutoLabelerState.IDLE
        self._mode = AutoLabelerMode.DRAW_ONLY
        self._delay_draw = 300  # 绘制后等待时间(毫秒)
        self._delay_next = 500  # 下一张等待时间(毫秒)
        self._delay_click_detection = 200  # 点击检测延迟(毫秒)

        # 鼠标事件相关
        self._mouse_pressed = False
        self._press_time = 0  # 记录鼠标按下的时间戳
        self._release_time = 0  # 记录鼠标释放的时间戳
        self._draw_detected = False

        # 统计数据
        self._stats = {
            'total_boxes': 0,  # 总共绘制的框数量
            'total_images': 0,  # 总共处理的图片数量
            'session_boxes': 0,  # 本次会话绘制的框数量
            'session_images': 0,  # 本次会话处理的图片数量
            'start_time': 0,  # 会话开始时间
            'paused_duration': 0,  # 暂停的总时长
            'pause_time': 0,  # 上次暂停的时间点
        }

        # 初始化定时器
        self._auto_draw_timer = QTimer()
        self._auto_draw_timer.setSingleShot(True)
        self._auto_draw_timer.timeout.connect(self._send_draw_key)

        self._auto_next_timer = QTimer()
        self._auto_next_timer.setSingleShot(True)
        self._auto_next_timer.timeout.connect(self._send_next_key)

        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)

        # 统计更新定时器
        self._stats_timer = QTimer()
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.setInterval(1000)  # 每秒更新一次

        # 新增定时器：用于延时切换回"监控中"状态
        self._reset_state_timer = QTimer()
        self._reset_state_timer.setSingleShot(True)
        self._reset_state_timer.timeout.connect(self._reset_to_monitoring)

        self.logger.info("自动标注模型初始化完成")

    @property
    def state(self):
        """获取当前状态"""
        return self._state

    @property
    def mode(self):
        """获取当前模式"""
        return self._mode

    @property
    def delay_draw(self):
        """获取绘制延迟时间"""
        return self._delay_draw

    @property
    def delay_next(self):
        """获取下一张延迟时间"""
        return self._delay_next

    @property
    def delay_click_detection(self):
        """获取点击检测延迟时间"""
        return self._delay_click_detection

    @property
    def statistics(self):
        """获取统计信息"""
        stats = self._stats.copy()

        # 计算时长
        duration = 0
        if self._stats['start_time'] > 0:
            if self._state == AutoLabelerState.PAUSED:
                # 处于暂停状态，使用暂停时间计算
                duration = self._stats['pause_time'] - self._stats['start_time'] - self._stats['paused_duration']
            else:
                # 处于活动状态，使用当前时间计算
                duration = time.time() - self._stats['start_time'] - self._stats['paused_duration']

        stats['duration'] = duration

        # 计算速率
        if duration > 0:
            stats['boxes_per_minute'] = (stats['session_boxes'] / duration) * 60
            stats['images_per_minute'] = (stats['session_images'] / duration) * 60
        else:
            stats['boxes_per_minute'] = 0
            stats['images_per_minute'] = 0

        return stats

    def start_monitoring(self):
        """开始监控鼠标操作"""
        current_time = time.time()

        if self._state == AutoLabelerState.IDLE:
            # 从空闲状态开始
            self._stats['start_time'] = current_time
            self._stats['session_boxes'] = 0
            self._stats['session_images'] = 0
            self._stats['paused_duration'] = 0
            self._stats['pause_time'] = 0
            self._state = AutoLabelerState.MONITORING
            self._stats_timer.start()

        elif self._state == AutoLabelerState.PAUSED:
            # 从暂停状态恢复
            if self._stats['pause_time'] > 0:
                # 计算暂停的时长并累加
                self._stats['paused_duration'] += (current_time - self._stats['pause_time'])
                self._stats['pause_time'] = 0
            self._state = AutoLabelerState.MONITORING
            self._stats_timer.start()

        self._draw_detected = False
        self.state_changed.emit(self._state)
        self.status_changed.emit("监控已启动", "success")
        self.statistics_updated.emit(self.statistics)

    def pause_monitoring(self):
        """暂停监控"""
        if self._state == AutoLabelerState.MONITORING or self._state == AutoLabelerState.DRAWING:
            self._state = AutoLabelerState.PAUSED
            # 记录暂停开始时间
            self._stats['pause_time'] = time.time()
            # 停止统计定时器
            self._stats_timer.stop()
            # 停止所有活动定时器
            self._auto_draw_timer.stop()
            self._auto_next_timer.stop()

            self.state_changed.emit(self._state)
            self.status_changed.emit("监控已暂停", "warning")

    def stop_monitoring(self):
        """停止监控"""
        if self._state != AutoLabelerState.IDLE:
            self._state = AutoLabelerState.IDLE
            self._auto_draw_timer.stop()
            self._auto_next_timer.stop()
            self._stats_timer.stop()

            # 重置统计相关时间
            self._stats['start_time'] = 0
            self._stats['paused_duration'] = 0
            self._stats['pause_time'] = 0

            # 最后一次更新统计
            self.statistics_updated.emit(self.statistics)

            self.state_changed.emit(self._state)
            self.status_changed.emit("监控已停止", "warning")

    def set_mode(self, mode):
        """设置标注模式"""
        if isinstance(mode, AutoLabelerMode):
            self._mode = mode

            mode_str = "仅自动绘制" if mode == AutoLabelerMode.DRAW_ONLY else "仅自动跳转下一张" if mode == AutoLabelerMode.NEXT_ONLY else "绘制并下一张"
            self.status_changed.emit(f"标注模式: {mode_str}", "info")

    def set_delay_draw(self, ms):
        """设置绘制延迟时间"""
        self._delay_draw = max(100, min(2000, ms))

    def set_delay_next(self, ms):
        """设置下一张延迟时间"""
        self._delay_next = max(100, min(2000, ms))

    def set_delay_click_detection(self, ms):
        """设置点击检测延迟时间"""
        self._delay_click_detection = max(100, min(1000, ms))  # 限制在100ms到1000ms之间

    def handle_mouse_press(self, event: QMouseEvent):
        """处理鼠标按下事件"""
        if self._state != AutoLabelerState.MONITORING:
            return

        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self._mouse_pressed = True
                self._press_time = time.time()  # 记录按下时间
                self._state = AutoLabelerState.DRAWING
                self.state_changed.emit(self._state)
        except Exception as e:
            self.logger.error(f"处理鼠标按下事件出错: {e}")

    def handle_mouse_release(self, event: QMouseEvent):
        """处理鼠标释放事件"""
        if self._state != AutoLabelerState.DRAWING:
            return

        try:
            if event.button() == Qt.MouseButton.LeftButton and self._mouse_pressed:
                self._mouse_pressed = False
                self._release_time = time.time()  # 记录释放时间
                click_duration = (self._release_time - self._press_time) * 1000  # 转换为毫秒

                # 如果点击时间超过设定的延迟时间，则视为有效绘制
                if click_duration >= self._delay_click_detection:
                    self._draw_detected = True
                    self._auto_draw_timer.start(self._delay_draw)

                    # 更新统计
                    self._stats['total_boxes'] += 1
                    self._stats['session_boxes'] += 1
                    self.statistics_updated.emit(self.statistics)

                    self.status_changed.emit("检测到框绘制完成", "info")
                else:
                    self.logger.debug(f"点击时间过短（{click_duration:.0f}ms < {self._delay_click_detection}ms），忽略")

                # 无论是否满足条件，都退出"绘制中"状态
                self._state = AutoLabelerState.MONITORING
                self.state_changed.emit(self._state)

        except Exception as e:
            self.logger.error(f"处理鼠标释放事件出错: {e}")
            # 发生异常时也确保退出"绘制中"状态
            self._state = AutoLabelerState.MONITORING
            self.state_changed.emit(self._state)

    def handle_key_press(self, event: QKeyEvent):
        """处理键盘按键事件(用于捕获和计数D键)"""
        try:
            if event.key() == Qt.Key.Key_D:
                # 更新统计
                self._stats['total_images'] += 1
                self._stats['session_images'] += 1
                self.statistics_updated.emit(self.statistics)
        except Exception as e:
            self.logger.error(f"处理键盘事件出错: {e}")

    def _send_draw_key(self):
        """发送W键以开启绘制模式"""
        if self._state == AutoLabelerState.MONITORING and self._draw_detected:
            # 如果是仅跳转下一张模式，直接发送D键
            if self._mode == AutoLabelerMode.NEXT_ONLY:
                self._auto_next_timer.start(self._delay_next)
                self._draw_detected = False
                self._reset_state_timer.start(500)
                return

            # 其他模式发送W键
            self.status_changed.emit("自动发送绘制快捷键", "info")
            self.send_key_signal.emit("W")

            # 如果是绘制并下一张模式，则启动下一张定时器
            if self._mode == AutoLabelerMode.DRAW_AND_NEXT:
                self._auto_next_timer.start(self._delay_next)

            self._draw_detected = False
            self._reset_state_timer.start(500)  # 0.5秒后切换

    def _send_next_key(self):
        """发送D键以跳转下一张"""
        if self._state == AutoLabelerState.MONITORING:
            self.status_changed.emit("自动前往下一张", "info")

            # 通知控制器发送D键
            self.send_key_signal.emit("D")

            # 缩短延迟时间并直接触发状态恢复
            self._reset_state_timer.start(500)  # 0.5秒后切换

    def _clear_status(self):
        """清除状态信息"""
        self.status_changed.emit("", "normal")

    def _update_stats(self):
        """定时更新统计信息"""
        if self._state == AutoLabelerState.MONITORING or self._state == AutoLabelerState.DRAWING:
            self.statistics_updated.emit(self.statistics)

    def _reset_to_monitoring(self):
        """延时切换回监控中状态"""
        if self._state == AutoLabelerState.MONITORING:
            # 强制更新状态为 MONITORING
            self._state = AutoLabelerState.MONITORING
            self.state_changed.emit(self._state)
            # 仅发送状态变更信号，不触发status_changed
            # 防止状态恢复时status_changed覆盖state_changed触发的动画
            # self.status_changed.emit("监控中", "success")