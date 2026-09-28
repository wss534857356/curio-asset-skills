# 图片来源与版本

以下 10 张 PNG 来自原项目已保存的渲染／工作台截图，未重画、拼接、裁切或补出不存在的效果。公开文件移除了 PNG 中的作者文件路径、渲染时刻等非显示元数据，像素和色彩管理信息保持不变。另有 1 张 SVG 从模型实际 UV 数据生成。整理日期为 2026-09-26，历史截图不代表本次重新运行了原游戏。

2026-09-28 另补充 2 张宝石透射控制图，合计 12 张 PNG。新增图片来自已保存的项目检查记录，原文件不含额外 PNG 元数据，按原字节复制；本次没有重新生成对应光学实验。

| 文件 | 来源版本 | 展示内容与边界 |
|---|---|---|
| [deer-vessel-assembled.png](deer-vessel-assembled.png) | D02 mesh-split-r01 / candidate-r09 / hero | 眠鹿圣油壶六足版本；Meshy 来源模型、本地拆件后的整体渲染 |
| [deer-vessel-exploded.png](deer-vessel-exploded.png) | 同上 / exploded | 壶身、盖、柄、两半颈圈，共 5 件；分件检查不代表动画／紧固已实现 |
| [gem-comparison.png](gem-comparison.png) | C12 lynx-eye-stone-v1 / comparison-final | 左旧粗模，右程序蛋面与银座；亮带为游戏效果近似 |
| [gem-disassembled.png](gem-disassembled.png) | 同上 / assembly-open-final | 同一工作台拆座状态；截图版为前拱平底，双曲面背部是后续设计规则 |
| [oil-painting-layers.png](oil-painting-layers.png) | oil-skill-stack | 画芯与颜料／表面层工作台；不证明动态清洁或全部法线先行流程完成 |
| [character-cel-lighting.png](character-cel-lighting.png) | npc-scene-normals-20260925-v1 / stepmother-night-cel | 同一法线下连续／赛璐璐受光对照 |
| [character-form-normals.png](character-form-normals.png) | 同上 / rebel-cat-key-left | 形体法线 OFF/ON 的灰模诊断；法线是插画估计，不是三维烘焙 |
| [badger-balance-assembled.png](badger-balance-assembled.png) | A02 badger-balance-v1 / assembled-r02 / preview | R02 完整药秤渲染，獾圆雕来源工具为 Meshy，机构为代码几何 |
| [badger-sculpt-high.png](badger-sculpt-high.png) | 同上 / badger-preview | 单獾形体生成阶段保存的灰模预览，不是低模线框 |
| [badger-balance-game.png](badger-balance-game.png) | 原项目 heron-live / shop-badger-retexture | R02 游戏称量界面历史截图 |
| [badger-uv-layout.svg](badger-uv-layout.svg) | 本次读取 badger-mid 与 badger-uv 的 TEXCOORD_0 和索引 | 真实 UV 三角边布局对照；不代表已检验零重叠或零拉伸 |
| [gem-transmission-red.png](gem-transmission-red.png) | gem-transmission / after-production-front-red | 长阶切型、红色后景与白条的固定相机透射检查；非完整光线追踪 |
| [gem-transmission-blue.png](gem-transmission-blue.png) | gem-transmission / after-production-front-blue | 同一模型与反射设置，仅改变后景颜色；不代表珠宝真实性鉴定 |

D02 源文件名为 `Meshy_AI_Ceramic_Stag_Vessel_0914083449_texture.glb`。分件版本整件 87,293 个三角形，无动画；继承源模型部分开口与相交，不能据渲染推断水密、无缺陷或适合制造。该模型文件不随集合分发。来源工具署名：**Meshy**。

本集合仅发布工作流、工具与展示图；源码中的游戏身份用于说明案例，不要求使用者采用同一剧情或资产登记。图片适用 [展示说明](../../ASSET_NOTICE.md)，不适用 MIT 素材授权。

双獾药秤的几何统计、UV 数据、R01／R02 材质区别、资源大小和历史任务消耗见 [完整案例](../../examples/badger-balance/README.md)。相关原始模型与纹理没有上传。
