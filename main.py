# main.py

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用程序图标
    # app.setWindowIcon(QIcon('icon.png'))  # 如果有图标文件，可以取消注释

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
