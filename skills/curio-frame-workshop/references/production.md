# 可运行接口

以当前环境的 Blender 可执行文件运行，不在用户正在编辑的 Blender 场景里清空对象。下面的 `blender` 可替换为实际绝对路径。

```text
blender --background --factory-startup --threads 4 --python SKILL_DIR/scripts/frame_workshop.py -- --spec JOB/frame.json --out JOB/frame-r01
blender --background --factory-startup --threads 4 --python SKILL_DIR/scripts/frame_workshop.py -- --kit --out JOB/frame-kit-r01
blender --background --factory-startup --threads 4 --python SKILL_DIR/scripts/frame_workshop.py -- --badges-only --out JOB/heraldry-r01
```

`--kit` 生成四种框型、五个装配示例（含横幅）、五家 × 三种徽章载体的 PBR 图，以及五个可编辑 SVG 符号。每个示例有 GLB、Blender 文件、正面／斜视图和 `build-report.json`；徽章仍是单独节点。

`--badges-only` 另导出 15 个独立徽章 GLB／Blender 工程，便于复用到画框、门牌或其他载体。每枚默认宽 60 mm，可整体等比缩放，不能只拉长一个轴。

## 配方

`assets/frame-spec.json` 可直接复制。`preset` 取框型表中的键。`canvas.height_m`、`canvas.width_m` 至少给一项；`image_path` 相对配方文件，或用绝对路径。实际图像像素比优先于 `aspect_ratio`。同时指定两边时保留完整图像，超出的部分是衬边，不改变人物比例。

`profile_mode=proportional` 时框边宽按短边和框型系数计算并限制在默认区间；`physical` 默认 35 mm，显式 `border_m` 优先。模板区间是美术起点，不是古董测量数据。拱冠位于矩形画芯之外，不裁画成拱形。

`badge.family` 为 `rabbit/wolf/red_deer/bear/tiger`，`placement` 为 `none/edge_centers/top_center/four_corners/canvas_center`。`size_m` 控制徽章宽度；侧边和四角自动限制尺寸以留在框条区域。动物图案不随载体长宽比拉伸。徽章大小改变时浮雕高度按同一比例理解；需要固定物理深度时重制对应尺寸材质。

## 尺度与地图

框条采用真实斜接端点，低模截面描述 `(向外偏移, 前后深度)`。Blender 为 +Z 朝上、-Y 朝前，GLB 按导出器转换。只使用 `explode_direction`，与项目现有工作台一致。

木纹 U 沿条长，V 沿截面弧长；默认一格为 0.20 × 0.045 m。重建不同画幅后这个密度不变。画芯 UV 固定为完整 `[0,1]`，不得复用画框的重复 UV。

程序资源使用 NumPy 和 Blender，自带 PNG 写出器，不需要 Pillow。`height.png` 是 16 位数据，真实最小／最大高度在同目录 `material.json`；`normal.png` 为切线 +Y，`orm.png` 为 R=1（未烘焙 AO）、G=粗糙度、B=金属度。不得把恒定 R=1 宣称为已计算遮蔽。
