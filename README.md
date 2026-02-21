# Python 源文件转 EXE（Windows）

一个基于 **PyQt5** 的桌面工具，通过 **PyInstaller** 将 Python 源代码（`.py`）一键打包为 Windows 可执行文件（`.exe`）。

- GUI：PyQt5
- 构建：PyInstaller
- 实时日志输出 + 常见错误提示
- 语言：简体中文 / English
- 主题：浅色 / 深色

English README: `README_EN.md`

## 环境要求

- Windows 10 / 11
- Python 3.8–3.12

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动

```bash
python main.py
```

## 使用说明

1. 选择 Python 源文件（`.py`）。
2. 选择输出目录。
3. 选择打包模式：
   - `--onefile`（生成单个 exe）
   - `--onedir`（生成目录结构）
4. 选择运行模式：
   - `--windowed`（无控制台窗口）
   - `--console`（显示控制台窗口）
5. 可选设置：
   - 程序名称：`--name`
   - 程序图标：`--icon`（`.ico`）
   - 管理员权限：`--uac-admin`
   - 清理缓存：`--clean`
   - 自动覆盖：`-y`

## UPX 压缩

现在 UPX 只有一个开关：**使用 UPX 压缩**。

- 勾选后：
  - 你可以手动选择 UPX 目录（包含 `upx.exe` 的文件夹）。
  - 如果不填写路径，程序会默认使用工作区自带的 `UPX.EXE`（当前目录下）。
- 不勾选：
  - 程序会自动传入 `--noupx` 禁用压缩。

## 输出位置

构建产物会输出到你选择的 `--distpath` 目录。

## 常见问题

- PyInstaller 未安装
  - 执行：`pip install pyinstaller`
- 模块缺失（`ModuleNotFoundError`）
  - 安装缺失依赖：`pip install <module>`
- 权限不足（`PermissionError` / Access is denied）
  - 尝试勾选管理员权限，或以管理员方式运行本工具

## 说明

- 本工具通过 `python -m PyInstaller ...` 调用 PyInstaller，并将输出实时显示在日志窗口。
