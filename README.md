# WeeklyRunner - Python 版每周定时运行工具

## 功能
- 可视化 GUI 界面
- 选择 AHK 脚本路径（浏览按钮）
- 设置执行的星期几和时间
- 一键立即测试
- 后台定时运行
- 配置自动保存到 config.json
- 执行日志记录到 log.txt

## 一键编译

双击 `OneClickBuild.bat`，自动完成：
1. 检测 / 安装 Python
2. 安装 PyInstaller
3. 编译生成 `dist/WeeklyRunner.exe`

## 手动编译

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name WeeklyRunner main.py
```

输出文件: `dist/WeeklyRunner.exe`
