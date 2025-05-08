# main.py

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        import pyi_splash
        pyi_splash.close()        # 关闭闪屏
    except ImportError:
        pass

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
