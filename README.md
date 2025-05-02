# ImageHub - 图像处理工具集

ImageHub是一个基于PyQt6开发的图像处理工具集合，提供了多个实用的图像处理功能模块。目前包含图像缩放器和自动重命名两个主要功能。

## 功能特点

### 1. 图像缩放器
- 自动监控系统剪贴板
- 智能调整图像尺寸
- 支持多种缩放算法
- 实时预览原图和处理结果
- 自定义目标尺寸和容差值
- 自动复制回剪贴板功能

### 2. 图片自动重命名
- 文件夹监控功能
- 自动序号重命名
- 自定义最大文件数限制
- 实时日志显示
- Windows 系统通知集成
- 防重复处理机制

## 技术特性

- 现代化UI设计
- 深色/浅色主题自适应
- 流畅的动画效果
- 多线程处理
- 实时状态反馈
- 自定义字体支持
- 错误处理与提示

### 主要组件说明：

1. **主程序文件**
   - main.py: 应用程序入口点
   - main_window.py: 主窗口框架实现

2. **图像缩放器模块**
   - clipboard_image_scaler_core.py: 核心功能实现，包含图像处理逻辑
   - clipboard_image_scaler_gui.py: 图形界面实现，处理用户交互

3. **配置模块**
   - config.py: 包含主题设置、样式定义和动画配置

4. **资源目录**
   - icons: 存放UI所需的图标资源

5. **IDE配置**
   - .idea: PyCharm IDE的项目配置文件

### 功能模块划分：

1. **核心功能层**
   - 图像处理和缩放
   - 剪贴板操作
   - 配置管理

2. **界面层**
   - 主窗口框架
   - 图像缩放器界面
   - 状态动画效果

3. **配置层**
   - 主题配置
   - 样式定义
   - 动画参数

## 环境要求

- Python 3.8+
- PyQt6
- OpenCV (cv2)
- Numpy
- Win32clipboard (Windows平台)
- Watchdog (文件监控)
- Pillow (PIL)

## 安装说明

1. 克隆项目到本地：
```bash
git clone https://github.com/yourusername/ImageHub.git
cd ImageHub
```

2. 创建并激活虚拟环境（推荐）：
```bash
conda env create -f environment.yml
conda activate your_env_name
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用说明

### 启动应用

```bash
python main.py
```

### 图像缩放器使用

1. 设置目标尺寸（默认1920x1080）
2. 调整缩放参数（可选）：
   - 纵横比容差
   - 缩放算法
   - 自动复制选项
3. 点击"开始监控"
4. 复制任意图像到剪贴板
5. 程序会自动处理并显示结果

![image](https://github.com/user-attachments/assets/dda905c9-ae15-479a-b6d6-170436fb5c65)

### 图片重命名器使用

1. 选择要监控的文件夹
2. 设置最大文件数限制
3. 点击"开始监控"
4. 将图片保存到监控文件夹
5. 程序会自动重命名并记录日志

![image](https://github.com/user-attachments/assets/f65b0e21-6d0e-458b-9aa4-6c3ed47d3dc8)


## 项目结构

```
ImageHub/
├── main.py                 # 主程序入口
├── main_window.py          # 主窗口实现
├── config/
│   └── config.py          # 配置和样式定义
│
├── ClipboardImageScaler/   # 图像缩放器模块
│   ├── clipboard_image_scaler_core.py
│   └── clipboard_image_scaler_gui.py
│
├── AutoRename/            # 图片重命名模块
│   └── auto_rename_gui.py
│
└── icons/                 # 图标资源目录
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 待实现功能

- [ ] 批量处理功能
- [ ] 更多图像处理算法
- [ ] 自定义预设配置
- [ ] 处理历史记录

## 版权和许可

该项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情

## 联系方式

- 项目地址：[https://github.com/ArtichoKaleyard/ImageHub](https://github.com/ArtichoKaleyard/ImageHub)
- 作者邮箱：[follower193949@outlook.com](follower193949@outlook.com)

## 致谢

- PyQt6 团队
- OpenCV 社区
- 完成本项目所使用的AI工具

---

如果这个项目对你有帮助，请给个 star ⭐️
