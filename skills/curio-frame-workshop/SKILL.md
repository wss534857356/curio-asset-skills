---
name: curio-frame-workshop
description: Build reusable low-poly painting frames with automatic canvas sizing, stable texture scale, PBR moulding detail and animal family badges. Use for frame kits, resizing and heraldic attachments; painted scenes and authenticity edits belong to curio-oil-paintings.
---

# 油画框与家族徽章工坊

交付可重复运行的尺寸配方、独立画框和徽章节点、GLB、Blender 工程及实际预览。只处理请求的框或模板，不因调用技能自动重制整套画作。

## 选型与制作

四套截面在 [frame-presets.json](assets/frame-presets.json)：胡桃木窄框、凹线暗金框、红木拱冠框、乌木银线框。五家符号在 [heraldry.json](assets/heraldry.json)：兔、狼、赤鹿、熊、虎。纹章不预设剧情家族姓名或血缘。

使用 [frame-spec.json](assets/frame-spec.json) 和 `scripts/frame_workshop.py`。命令、尺寸和 UV 约定见 [制作接口](references/production.md)。只给一边时按实际画芯比例求另一边；两边都给且比例不同时默认完整容纳并留衬边。框条随长度重建，UV 按物理长度重复，徽章保持比例，不能靠横向拉伸成品凑尺寸。

布局支持侧边中点 `edge_centers`、上沿正中 `top_center`、四角 `four_corners`、画面正中 `canvas_center` 及无徽章。画面正中会覆盖画作，只在请求选用该布局时使用。四角载体可镜像，动物符号保持正立。每枚徽章独立命名，可换家族、移动或隐藏。

低模承担厚度、截面、拱冠和载体轮廓；木纹、金箔接缝、浅刻和动物图案用配准的底色、法线、粗糙度表现。法线不承担镂空、明显剪影或活动结构。详见 [材质和纹章](references/materials-and-heraldry.md)。程序材质和矢量纹章是可用起始资源，不冒充 ImageGen 艺术稿；制作新艺术参考或纹理时读取可用的 `imagegen` skill，使用内置工具并把输出保存进项目。

画芯、背板与框体分开，画框不烘进画作底色。真伪画作共用框型、比例和摄像机，除非框或徽章本身就是指定线索。画芯可由 `curio-oil-paintings` 生成，也可直接使用现有文件；本技能可独立运行。

检查至少两个不同长宽比：画芯完整、木纹密度稳定、徽章不变形、挂点随尺寸变化。检查实际导出节点、法线引用及正面／斜视材质响应。目标项目的接入约定见 [项目接入](references/project-integration.md)。
