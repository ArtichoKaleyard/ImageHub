"""
粘贴板图像自动缩放器 - 主程序
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from clipboard_image_scaler_gui import ClipboardImageScalerGUI

if __name__ == "__main__":
    # 创建应用程序实例
    app = QApplication(sys.argv)

    # 设置应用程序图标
    # app.setWindowIcon(QIcon('icon.png'))  # 如果有图标文件，可以取消注释

    # 创建并显示主窗口
    window = ClipboardImageScalerGUI()
    window.show()

    # 进入应用程序主循环
    sys.exit(app.exec())