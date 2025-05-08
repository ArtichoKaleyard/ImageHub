"""
通知模块

使用方法:
    from utils.windows_notification import notification

    # 发送通知
    notification("标题", "内容", duration=5)
"""
from win10toast import ToastNotifier
import threading
import pythoncom

class SafeToastNotifier(ToastNotifier):
    """修复WNDPROC返回类型错误的Toast通知器"""
    def __init__(self):
        super().__init__()
        # 强制设置消息处理超时
        self._timeout = 5  # 秒
    def on_destroy(self, hwnd, msg, wparam, lparam):
        """修复返回类型必须为int的问题"""
        try:
            super().on_destroy(hwnd, msg, wparam, lparam)
        finally:
            return 0  # 必须明确返回整数
def notification(title, message, duration=5):
    """线程安全的通知显示方法"""
    def _show():
        pythoncom.CoInitialize()  # 初始化COM
        try:
            # 使用修复后的通知器
            toaster = SafeToastNotifier()
            # 使用同步显示模式避免线程冲突
            toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=False,
                icon_path='icons\\ImageHub.ico'
            )
        except Exception as e:
            print(f"[通知异常] {str(e)}")
        finally:
            pythoncom.CoUninitialize()  # 清理COM
    # 在独立线程中运行
    threading.Thread(target=_show, daemon=True).start()