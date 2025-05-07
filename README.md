# ImageHub - 图像处理工具集

ImageHub是一个基于PyQt6开发的图像处理工具集合，提供了多个实用的图像处理功能模块。目前包含图像缩放器、自动重命名和自动标注辅助工具三个主要功能。

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

### 3. 图像处理验证器
- 批量验证图像处理结果
- 支持多种命名规则验证
- 自动检测处理完整性
- 多线程并行处理
- 详细的验证报告
- JSON配置支持

### 4. 自动标注辅助工具（新增）
- 支持两种标注模式：仅自动绘制、绘制并下一张
- 可自定义绘制延迟和下一张延迟时间
- 实时统计绘制框数和处理图片数
- 支持快捷键自定义
- 状态动画和颜色标记
- 详细的日志记录功能

## 技术特性

- 现代化UI设计
- 深色/浅色主题自适应
- 流畅的动画效果
- 多线程处理
- 实时状态反馈
- 自定义字体支持
- 错误处理与提示
- JSON配置管理

### 主要组件说明：

1. **主程序文件**
   - main.py: 应用程序入口点
   - main_window.py: 主窗口框架实现

2. **图像缩放器模块**
   - clipboard_image_scaler_core.py: 核心功能实现，包含图像处理逻辑
   - clipboard_image_scaler_gui.py: 图形界面实现，处理用户交互

3. **自动标注辅助工具模块（新增）**
   - auto_labeler_model.py: 核心逻辑和状态管理
   - auto_labeler_view.py: 图形用户界面
   - auto_labeler_controller.py: 控制器层，处理用户交互

4. **配置模块**
   - config.py: 包含主题设置、样式定义和动画配置

5. **图像处理验证器模块**
   - image_verifier_gui.py: 验证器GUI实现
   - image_verifier_adapter.py: 验证器中间层实现
   - image_verifier_core.py: 验证器核心实现
   - help.html: 配置说明文档

6. **资源目录**
   - icons: 存放UI所需的图标资源

### 功能模块划分：

1. **核心功能层**
   - 图像处理和缩放
   - 剪贴板操作
   - 配置管理
   - 图像验证

2. **界面层**
   - 主窗口框架
   - 图像缩放器界面
   - 状态动画效果
   - 验证器界面

3. **配置层**
   - 主题配置
   - 样式定义
   - 动画参数
   - JSON配置

## 环境要求

- Python 3.12+
- PyQt6 6.9.0+
- OpenCV (cv2)
- Numpy 2.2+
- Win32clipboard (Windows平台)
- Watchdog 6.0+
- Pillow (PIL)
- pynput (可选，用于全局快捷键支持)

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

### 图像处理验证器使用

1. 配置 config/IPV_config.json
2. 选择验证模式：
   - range: 固定范围序号
   - numeric: 任意数字序号
   - custom: 自定义正则匹配
3. 点击"开始验证"
4. 查看验证报告和日志

![image](https://github.com/user-attachments/assets/923b70dc-1d09-432a-88e8-127f286ada65)

### 标注加速器使用

1. 设置操作模式（默认仅自动绘制）
   - 仅自动绘制
   - 绘制并下一张
3. 调整绘制参数（可选）：
   - 绘制延迟
   - 下一张延迟
   - 点击检测延迟
   - 绘制快捷键
   - 下一张快捷键
4. 点击"开始监控"
5. 开始在标注工具绘制锚框
6. 程序会自动处理并显示结果

![image](https://github.com/user-attachments/assets/f7c5a173-b97c-4712-a294-485c520eef30)

## 项目结构

```
ImageHub/
├── main.py                 # 主程序入口
├── main_window.py          # 主窗口实现
├── config/
│   ├── style_config.py    # 样式配置
│   ├── style_interface.py # 样式接口
│   └── IPV_config.json    # 验证器配置
│
├── AutoLabeler/            # 自动标注辅助工具模块
│   ├── auto_labeler_model.py  # 模型层(状态管理/核心逻辑)
│   ├── auto_labeler_view.py   # 视图层(图形界面)
│   └── auto_labeler_controller.py # 控制器层(事件处理)
│
├── ClipboardImageScaler/   # 剪贴板图片缩放模块
│   ├── clipboard_image_scaler_gui.py # 图形界面
│   └── clipboard_image_scaler_core.py # 核心功能
│
├── AutoRename/            # 图片自动重命名模块
│   └── auto_rename_gui.py # 图形界面
│
├── ImageProcessingValidator/ # 图像处理验证器
│   ├── image_verifier_gui.py # 图形界面层
│   ├── image_verifier_adapter.py # 适配器层(GUI/CLI双模式)
│   ├── image_verifier_core.py # 核心验证逻辑
│   └── help.html          # 可交互式帮助文档
│
├── Logger/                # 日志系统
│   └── logger.py          # 日志记录器实现
│
├── style/                 # 样式资源
│   ├── style_config.py    # 样式配置
│   ├── log_style.py       # 日志样式定义
│   └── style_usage_example.py # 样式使用示例
│
├── icons/                 # 图标资源目录
│   ├── app_icon.png       # 应用图标
│   ├── dark/              # 深色主题图标
│   └── light/             # 浅色主题图标
│
├── requirements.txt       # Python依赖
└── environment.yml        # Conda环境配置
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
- [ ] 自动标注工具的更多模式支持

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
