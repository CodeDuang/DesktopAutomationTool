# 桌面自动化工具 - 开发者文档

> **版本**: 1.2.0  
> **更新日期**: 2026-07-23  
> **适用平台**: Windows 10/11

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [环境配置](#3-环境配置)
4. [目录结构与模块职责](#4-目录结构与模块职责)
5. [运行与调试](#5-运行与调试)
6. [打包发布](#6-打包发布)
7. [代码模块详解](#7-代码模块详解)
8. [扩展指南](#8-扩展指南)

---

## 1. 项目概述

**桌面自动化工具** 是一款基于 Python + PySide6 开发的桌面 GUI 自动化软件，采用"模型-视图-引擎"三层架构设计。用户通过可视化界面配置自动化步骤序列，程序在后台线程中执行屏幕图像匹配、键盘模拟、鼠标点击等操作。

### 设计原则

- **低代码/零代码**: 用户无需编写代码，通过配置即可完成自动化流程
- **可扩展**: 新增步骤类型只需修改 4 个文件，遵循模板模式
- **可观察**: 执行过程中实时日志、进度条、循环计数全部可视化
- **健壮性**: 支持步骤级重试、失败截图、紧急停止等容错机制

---

## 2. 技术栈

| 技术  | 用途  | 版本要求 |
| --- | --- | --- |
| Python | 开发语言 | ≥3.10 |
| PySide6 | GUI 界面框架 | ≥6.5.0 |
| PyAutoGUI | 屏幕截图、图像匹配、键盘鼠标模拟 | ≥0.9.54 |
| OpenCV | 增强图像匹配（confidence 参数） | ≥4.8.0 |
| Pillow | 图像处理 | ≥10.0.0 |
| PyInstaller | 打包为 exe | ≥5.13.2 |
| pytesseract | OCR 文字识别（可选） | ≥0.3.10 |
| pyperclip | 剪贴板读写 | ≥1.8.2 |
| keyboard | 全局热键监听 | ≥0.13.5 |

---

## 3. 环境配置

### 3.1 Python 环境

```bash
# 推荐使用虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
cd automation
pip install -r requirements.txt
```

### 3.2 可选依赖 - OCR(该功能暂未验证)

如需使用 OCR 文字识别功能，还需安装 Tesseract-OCR 引擎：

1. 下载：https://github.com/UB-Mannheim/tesseract/wiki
2. 安装时勾选 Chinese Simplified 语言包
3. 将安装目录添加到系统 PATH 环境变量

### 3.3 项目初始化

```bash
python main.py
# 首次启动会自动创建 data/ 目录
```

---

## 4. 目录结构与模块职责

```
automation/
├── build.spec              # PyInstaller 打包配置
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖列表
├── version_info.txt        # exe 版本信息文件
│
├── models/                 # 数据模型层
│   ├── __init__.py
│   ├── project.py          # Project / ProjectSettings 数据类
│   └── step.py             # Step / StepType / VerifyConfig / FailureConfig
│
├── views/                  # 视图层 (UI)
│   ├── __init__.py
│   ├── main_window.py      # 主窗口：项目列表管理 + SettingsDialog
│   ├── project_editor.py   # 项目编辑器对话框
│   ├── step_dialog.py      # 步骤编辑对话框（含验证配置）
│   ├── execution_monitor.py # 执行监控窗口（日志+进度+确认按钮）
│   └── widgets/            # 可复用控件
│       ├── __init__.py
│       ├── coordinate_picker.py  # 坐标拾取器
│       ├── screenshot_tool.py    # 截图工具
│       └── hotkey_recorder.py    # 快捷键录制器
│
├── engine/                 # 执行引擎层
│   ├── __init__.py
│   ├── executor.py         # 执行主循环（QThread）
│   ├── actions.py          # 各步骤类型的执行函数
│   ├── image_finder.py     # 图像匹配 + OCR 查找
│   └── logger.py           # 执行日志记录器
│
├── utils/                  # 基础设施层
│   ├── __init__.py
│   ├── config.py           # 全局配置（AppConfig）
│   ├── storage.py          # 项目 JSON 持久化
│   └── hotkey.py           # 全局热键监听
│
├── resources/              # 静态资源
│   ├── icons/              # 图标文件
│   └── styles/             # QSS 样式文件
│
└── docs/                   # 文档
    ├── USER_GUIDE.md       # 用户使用手册
    └── DEVELOPER_GUIDE.md  # 开发者文档（本文档）
```

### 架构分层

```
┌─────────────────────────────────────┐
│             视图层 (views/)          │  ← PySide6 窗口/对话框
├─────────────────────────────────────┤
│             引擎层 (engine/)         │  ← 后台执行逻辑 (QThread)
├─────────────────────────────────────┤
│             数据模型层 (models/)     │  ← 纯数据结构 (dataclass)
├─────────────────────────────────────┤
│             基础工具层 (utils/)      │  ← 跨层共享
└─────────────────────────────────────┘
```

### 数据流

```
用户操作 → View → Model → storage.save(持久化)
                    ↓
           用户点击"运行"
                    ↓
           ExecutorThread.run()
                    ↓
           遍历步骤 → actions.execute()
                    ↓
           logger/log_signal → UI 实时更新
```

---

## 5. 运行与调试

### 5.1 开发模式运行

```bash
cd automation
python main.py
```

### 5.2 Python 3.10.0 兼容性

Python 3.10.0 的 `dis.py` 存在已知 bug（`IndexError: tuple index out of range`），会导致 PyInstaller 打包失败。

- 修复方法：修改 `{Python目录}/lib/dis.py` 第 292 行，给 `const_list[const_index]` 加 `try/except IndexError`
- 或升级 Python 到 3.10.11+

### 5.3 调试技巧

- 执行日志输出到 `data/logs/{项目名}_{时间戳}.log`
- 失败截图保存在 `data/screenshots/{项目名}_{时间戳}/`
- 可在 `executor.py` 的 `_execute_step()` 或 `actions.py` 各函数中设置断点
- 模块测试：
  
  ```python
  cd automation
  python -c "from models.step import Step; print('model OK')"
  python -c "from engine import actions; print('engine OK')"
  ```
  

### 5.4 常见开发问题

| 问题  | 原因  | 解决  |
| --- | --- | --- |
| QDialog.exec() 阻塞其他窗口 | 模态对话框启动子事件循环 | 用 `setModal(False); show()` + 信号连接 |
| 截图全黑 | Qt 遮罩覆盖了桌面 | 用 `pyautogui.screenshot()` 而非 Qt 截图 |
| 控件被压缩 | 未设置最小高度 | 对 QLineEdit/QComboBox/QSpinBox 设置 setMinimumHeight |

---

## 6. 打包发布

### 6.1 打包命令 (PowerShell)

```powershell
cd automation
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
pyinstaller build.spec --clean --log-level=WARN cmd
```

### 打包命令 (cmd)

```cmd
cd automation
rd /s /q build dist 2>nul
pyinstaller build.spec --clean --log-level=WARN
```

输出在 `dist/桌面自动化工具.exe`。

### 6.2 前置条件

```bash
pip install pyinstaller
# Python 3.10.0 用户需要降级
pip install "pyinstaller<6"
```

### 6.3 build.spec 配置说明

| 配置项 | 说明  |
| --- | --- |
| hiddenimports | C 扩展依赖（pyautogui, cv2, PIL, win32gui 等）和新增模块 |
| datas | 包含 resources 和 docs 目录 |
| excludes | 排除 numpy 测试、pandas、tkinter 等 |
| console=False | 不显示控制台窗口 |
| version | exe 版本信息文件 |

---

## 7. 代码模块详解

### 7.1 models/step.py — 步骤数据模型

```
StepType(Enum)     — 步骤类型枚举（KEYBOARD_SHORTCUT/IMAGE_CLICK/...）
VerifyType(Enum)   — 验证方法枚举（当前仅 IMAGE_MATCH）
VerifyMode(Enum)   — 验证模式枚举（CONTINUOUS/TIMED）
FailureConfig      — 失败处理配置（截图/日志/重试）
VerifyConfig       — 验证配置（启用/类型/模式/参数/超时）
Step               — 步骤（id/type/params/verify_config/...）
```

扩展新步骤类型：在 `StepType` 添加枚举值 + `get_default_params()` 添加默认参数。

### 7.2 models/project.py — 项目数据模型

```
ProjectSettings — 项目设置（速度倍率/循环次数/手动确认/紧急停止键）
Project         — 项目（id/name/steps/settings）
```

扩展新设置：在 `ProjectSettings` 加字段 → 更新 `to_dict()`/`from_dict()`。

### 7.3 views/main_window.py — 主窗口

| 组件  | 说明  |
| --- | --- |
| ProjectNameDialog | 新建/重命名项目对话框 |
| SettingsDialog | 应用设置（日志/截图目录） |
| MainWindow | 主窗口（项目列表表格 + 工具栏 + 菜单） |

- `_refresh_table()`: 从 storage 加载项目列表
- `_open_editor(project_id)`: 非模态打开编辑器
- `_duplicate_project()`: 复制并生成新 UUID

### 7.4 views/project_editor.py — 项目编辑器

| 方法  | 说明  |
| --- | --- |
| `_add_step()` | 非模态打开 StepDialog |
| `_edit_selected_step()` | 编辑选中步骤 |
| `_set_all_enabled()` | 批量启用/禁用 |
| `_toggle_selected_step()` | 切换当前步骤启用状态 |
| `_run_project()` | 启动执行 |

### 7.5 views/step_dialog.py — 步骤编辑对话框

配置区域：基本信息 → 步骤参数(动态) → 高级设置 → 失败处理 → 验证设置(可选)

动态表单构建：

```
_on_type_changed()
  ├─ _build_keyboard_params()        # ⌨ 键盘快捷键
  ├─ _build_image_click_params()     # 🖼 图像匹配点击
  ├─ _build_image_keyboard_params()  # 🖼⌨ 图像匹配→快捷键
  ├─ _build_input_text_params()      # 📝 输入文本
  ├─ _build_wait_image_params()      # ⏳ 等待图像出现
  ├─ _build_ocr_params()             # 🔤 OCR识别点击
  ├─ _build_wait_params()            # ⏱ 等待
  └─ _build_condition_params()       # 🔀 条件判断
```

### 7.6 views/execution_monitor.py — 执行监控

通过 Qt Signal 与 `ExecutorThread` 通信：

- `log_signal` / `progress_signal` / `loop_count_signal`
- `finished_signal` / `stopped_signal` / `step_result_signal`
- `loop_confirm_signal`（手动确认循环）

### 7.7 views/widgets/ — 可复用控件

| 控件  | 说明  |
| --- | --- |
| coordinate_picker.py | 坐标拾取器（实时坐标/RGB/快捷键 Ctrl+C+Esc） |
| screenshot_tool.py | 截图工具（冻结桌面背景 + 拖拽选框） |
| hotkey_recorder.py | 快捷键录制器（手动输入/录制模式） |

### 7.8 engine/executor.py — 执行主循环

执行流程：

```
ExecutorThread.run()
  ├─ 项目级循环 (for loop_iteration)
  │   ├─ 步骤序列循环 (for step)
  │   │   └─ 步骤级循环 (for step_repeat)
  │   │       ├─ 执行前等待 → _execute_step() → 执行后等待
  │   │       ├─ 失败处理（重试/截图/停止）
  │   │       └─ 验证阶段（verify_config.enabled）
  │   └─ 手动确认循环（manual_loop_confirm）
```

### 7.9 engine/actions.py — 步骤执行函数

```python
ActionResult = (success: bool, message: str, screenshot_path: str)

execute_keyboard_shortcut(params, logger, step_name)
execute_image_click(params, logger, step_name)
execute_image_keyboard(params, logger, step_name)
execute_image_relative_click(params, logger, step_name)
execute_input_text(params, logger, step_name, loop_index)
execute_wait_for_image(params, logger, step_name)
execute_ocr_click(params, logger, step_name)
execute_wait(params, logger, step_name)
execute_condition(params, logger, step_name)
execute_verify_image_match(vconfig, logger, step_name)
```

### 7.10 engine/image_finder.py — 图像匹配 + OCR

```python
find_image_on_screen(path, confidence, grayscale) -> (left, top, w, h) | None
wait_for_image(path, confidence, timeout, interval) -> location | None
find_text_on_screen(text, lang, confidence) -> [匹配结果列表]
click_location(left, top, w, h, offset_x, offset_y, click_type) -> bool
take_screenshot(filepath) -> bool
```

### 7.11 utils/ 模块

| 模块  | 职责  |
| --- | --- |
| config.py | AppConfig 全局配置（目录管理/设置缓存） |
| storage.py | 项目 JSON 持久化（CRUD + 导入/导出） |
| hotkey.py | 全局热键监听（预留） |

### 7.12 main.py — 入口

```python
main()
  ├─ check_dependencies()    # 检查缺失依赖
  ├─ QApplication            # 创建 Qt 应用
  ├─ 创建 MainWindow         # 主窗口
  ├─ 创建 CoordinatePicker   # 坐标拾取器（隐藏）
  ├─ 创建 ScreenshotTool     # 截图工具（隐藏）
  ├─ 菜单栏                  # 工具 + 帮助
  └─ app.exec()              # 事件循环
```

---

## 8. 扩展指南

### 8.1 新增步骤类型（4 个文件）

1. `models/step.py` — `StepType` 枚举加新值 + `display_name()`/`description()` + `get_default_params()`
2. `engine/actions.py` — 加 `execute_xxx()` 函数
3. `engine/executor.py` — `_execute_step()` 加 `elif` 分支
4. `views/step_dialog.py` — `_on_type_changed()` 加分支 + `_build_xxx_params()`

### 8.2 新增验证方法（5 个文件）

1. `models/step.py` — `VerifyType` 枚举加新值
2. `models/step.py` — `VerifyConfig.get_default_params()` 加默认参数
3. `engine/actions.py` — 加 `execute_xxx_verify()`
4. `engine/executor.py` — `_run_verify_check()` 加分支
5. `views/step_dialog.py` — `_on_verify_type_changed()` 加 `_build_xxx_params()`

### 8.3 新增项目设置

`ProjectSettings` 加字段 → `to_dict()`/`from_dict()` → `project_editor.py` 加 UI 控件 → `_collect_settings()`

### 8.4 新增工具窗口

`views/widgets/` 下创建控件 → `main.py` 创建实例 → 菜单栏加菜单项

---

> **文档维护**：添加新功能时同步更新本文档。文档位置：`docs/DEVELOPER_GUIDE.md`
