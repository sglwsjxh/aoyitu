<h1 align="center">Aoyitu · 奥义图动画生成器</h1>

<p align="center">86 帧火影式奥义图动画生成工具 · Tkinter 实时调参 · GIF/MP4 一键导出</p>

## 功能

- **86 帧动画**：闪光揭示、动感模糊、角色振动、渐变收尾，一套完整的奥义图节奏
- **仙线特效**：7 种仙线精灵（`xian.png` / `xian2~4` 及横向变体）按帧摆放，可调透明度
- **实时调参**：GUI 提供 26 个参数滑杆（缩放/振动/模糊/噪点/闪光/仙线透明度…），改完立刻生效
- **中文字幕**：输入中文（+其他语言）自动用 `方正艺黑` 渲染字幕，可调位置/字号/平滑度
- **双格式导出**：GIF（256 色抖动优化）和 MP4（H.264，可混入多段音频）
- **CLI 批量生成**：一条命令从图片生成动画，适合脚本化调用

## 系统要求

- Windows 10/11（GUI 基于 Tkinter）
- Python 3.13+
- ffmpeg（可选）：加入系统 PATH 后 MP4 用 H.264 编码；未安装时自动回退 mp4v

## 快速开始

```bash
# 安装依赖（uv）
uv sync

# 启动 GUI
.\.venv\Scripts\python.exe aoyitu_gui.py
```

GUI 里：选择清晰角色图 → 勾选"字幕图"或输入中文字幕 → 点「加载素材」→ 调整右侧参数 → 「生成GIF / 生成MP4」。勾选「导入音频」可混入 MP3/WAV（支持多段），生成 MP4 时自动合成。

> 角色图和字幕图由你自己提供（建议透明 PNG、横版，画布按角色图尺寸自适应，默认 568×320），`public/Sprite/` 里是渐变、噪点、仙线、字幕背景条等内部素材。

## CLI 使用

```bash
# 基础用法：角色图 + 中文字幕
.\.venv\Scripts\python.exe aoyitu.py -c 角色.png --chinese-text "忍法·千鸟" --sub-bg public\Sprite\zuozhu_000_bg.png -o out.gif

# 带模糊图 + 字幕图 + 自定义参数
.\.venv\Scripts\python.exe aoyitu.py -c 角色.png -b 模糊.png -s 字幕.png --sub-bg public\Sprite\zuozhu_000_bg.png --fps 30 --format video -o out.mp4
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `-c, --clear` | 清晰角色图（必填） | - |
| `-b, --blur` | 模糊角色图（省略则自动生成动感模糊） | - |
| `-s, --subtitle` | 字幕图（与 `--chinese-text` 二选一） | - |
| `--chinese-text` | 中文字幕（启用文字模式，需字体） | - |
| `--other-text` | 第二行其他语言字幕 | - |
| `--sub-bg` | 字幕背景条 PNG（必填） | - |
| `-o, --output` | 输出文件（`.gif` / `.mp4`） | `aoyitu_output.gif` |
| `--fps` | 帧率 | 30 |
| `--format` | `auto` / `video` / `gif` | `auto` |
| `--loops` | 86 帧循环次数 | 1 |
| `--vib-x` / `--vib-y` | 角色振动幅度倍率（0=关闭） | 1.0 |
| `--blur-start1` / `--blur-start2` | 两段模糊渐入的起始帧 | 22 / 60 |
| `--scale-min` | 模糊时角色缩放下限 | 0.95 |
| `--sub-y` / `--sub-h` | 字幕 Y 位置 / 高度 | 245 / 32 |
| `--bg-y` / `--bg-h` | 字幕背景条 Y 位置 / 高度 | 239 / 44 |
| `--char-scale` | 角色缩放 | 1.2 |
| `--noise-str` / `--noise-scale` | 噪点强度 / 颗粒大小 | 0.7 / 3.5 |
| `--flash-f1..f3` | 三段闪光亮度 | 0.42/0.48/0.62 |
| `--xian-op-1..7` | 7 种仙线透明度 | 见 GUI |

## 项目结构

```
aoyitu/
├── aoyitu.py            # 核心渲染器 + CLI 入口
├── aoyitu_gui.py        # Tkinter 图形界面
├── public/              # 静态资源（随项目分发）
│   ├── 方正艺黑_GBK.ttf # 中文字幕字体
│   └── Sprite/          # 渐变 / 噪点 / 仙线 / 字幕背景条
├── xian_positions.json  # 仙线逐帧摆放数据
├── pyproject.toml       # uv 项目定义
└── output/              # GUI 导出目录（自动创建）
```

## 素材说明

### `public/Sprite/`

| 文件 | 用途 |
|------|------|
| `heisejianbian.png` | 左右黑色渐变（收尾压暗） |
| `noise-OldMovie.png` | 胶片噪点颗粒 |
| `xian*.png`（7 张） | 仙线特效精灵（`_h` 为横向变体） |
| `zuozhu_000_bg.png` | 字幕背景条 |

### `xian_positions.json`

仙线特效的**逐帧摆放表**：顶层键是帧号（`"0"`~`"85"`），每帧下列出要渲染的仙线精灵及实例列表。每个实例是最少 2 个元素的数组：

```
"10": { "xian3.png": [[275, 0]] }   # 第 10 帧，xian3 精灵放在 (275, 0)
```

可选第 3、4 个元素为旋转角度（单位：度）和缩放。**渲染器运行时读取**（`AoyituRenderer._load_xian`），缺失时仙线不显示、程序不崩。

## 注意事项

- **ffmpeg**：MP4 的 H.264 编码依赖系统 PATH 里的 ffmpeg，找不到会自动降级为 mp4v 编码（部分播放器不兼容）
- **字体**：中文字幕模式需要 `public/方正艺黑_GBK.ttf` 存在，否则 CLI 会直接报错
- **输出目录**：GUI 导出固定写入项目内 `output/`，不会往系统目录写文件

## 许可证

[AGPL License](LICENSE)
