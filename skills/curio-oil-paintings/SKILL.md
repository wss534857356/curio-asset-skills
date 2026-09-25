---
name: curio-oil-paintings
description: Create animal-world oil paintings as registered genuine and forged pairs, with paint-relief normals, linen texture and separate oil-stain or raised-repair layers. Use for painting authenticity clues and surface materials; frame geometry and badges belong to curio-frame-workshop.
---

# 油画画芯、真伪与表面痕迹

画作身份、描绘内容和保存状况分开记录。按请求制作真伪配对、颜料材质或污渍／补缀层，不自动重绘项目所有画作。

## 制作节点

- 真伪配对：读取 [鉴定规则](references/authenticity.md) 和 [画作配方](assets/painting-recipes.json)，运行 `scripts/prepare_painting.py` 输出任务包与 ImageGen 提示词。这个脚本不调用生图服务，不把计划标为完成。
- 微雕与笔触：当用户要求先有画中形体、再让笔刷顺着形体走时，读取 [法线先行流程](references/normal-first.md)。先用 ImageGen 生成同构图微雕法线，再提取方向场和局部特征驱动笔刷，最后组合渲染法线。
- 颜料与画布：读取 [材质约定](references/surface-materials.md)。只需要通用颜料表面时，用 `scripts/paint_surface.py` 生成起始笔触、织纹、法线和粗糙度，或传入同构图的高度稿；不能把通用笔触预览当成已完成微雕法线先行流程。
- 油污与补缀：输出独立遮罩、颜色／粗糙度与高度层。清洁只移除指定污渍，不把赝品画面变回真品；补缀保持独立。

## 必守的配对关系

先复用或生成真品画芯，再以它作为编辑参考制作赝品；艺术画芯生成和语义修改使用宿主已配置的图像生成／编辑工具（如可用的 `imagegen`），不能独立抽两张不配准的图。除指定差异外保持动物、姿势、构图、光线与笔触风格。原画芯和概念图不覆盖，新稿另存版本。

|画作|真品|赝品|
|---|---|---|
|戴珍珠的灰兔|珍珠耳环|同位置的钻石耳坠|
|倒奶的獾|不透明牛奶|透明清水，保留水流与接收容器|
|抱空匣的雪豹|匣内只有衬布|匣内多一枚画出来的戒指或指定小首饰|
|多人画|固定名单与人数|增加一名或删除一名，其他主要人物不变|

钻石、戒指默认是画内物体，不是真首饰贴到画布上。多人画登记物种、位置及计数规则，阴影、画中画和同一人的倒影不另计。示例 C04 将牛奶定义为真品、清水定义为赝品。内置配方 C01～C10 仅用于演示，其他项目以其设定为准；可用 `--recipe-file` 读取 [自定义配方](assets/painting-recipe.example.json)。原项目图像不随技能分发。

## 材质与验证

颜料厚度不由画面明暗推断。高度稿与画芯同画幅同 UV；按物理尺寸从高度求切线法线，默认 +Y，颜色和数据图使用各自色彩空间。分层高度合成后重新求法线；微雕形体与笔触法线按局部方向旋转组合并归一化，不直接平均法线 RGB。

真伪与干净／脏污是独立轴。油膜可压暗局部并降低粗糙度，补缀用短段连续凸起来表现。影响剪影的缝线另建几何；没有动态清洁实现时，不把静态材质图称为物理模拟。

逐对目视核对指定差异、未编辑人物和比例；用正面与移动的掠射光检查凸起方向、油膜和补痕。脚本通过只代表文件和数值正确，不代替画作语义验收。可用 `curio-frame-workshop` 组框，或沿用现有框体；[项目接入](references/project-integration.md) 说明状态映射和运行时边界。
