# 画框材质与纹章

配套 `ornaments.py` 同时定义矢量图形和高度场：动物轮廓、眼鼻刻线及载体边线共用坐标，因此颜色、浅刻和法线配准。五家分别有长耳、尖耳长吻、分叉鹿角、圆耳宽吻、额纹侧斜纹，不能仅用不同颜色或文字区分。

三种载体单独设计：边沿为窄菱牌，中央为带尖底的盾章，四角为削角扣牌与折角刻纹。四角可复用家族核心符号，但不是把盾章随意压扁成角件。当前起始 SVG 的背景色仅用于阅读；实际牌面由独立低模载体决定。

程序起始材质让木纹／金箔形状在底色和高度中一致。制作更精细的 ImageGen 材质时，先出无固定阴影的平铺底色，再取得对应的浅雕高度稿或在矢量／雕刻中明确高度。不要把金属高光或黑木底色直接当高度。

推荐提示词骨架：`Orthographic shallow heraldic plaque, [animal motif], [carrier outline], isolated frontal design, coherent old brass and engraved recesses, restrained relief, no letters, no surrounding picture or painting; provide a separate neutral clay relief reference.` 高度稿另请求 `registered grayscale relief height guide, white raised, black recessed, no lighting, no perspective`；它仍需检查配准，不能当成模型已完成。

正常表面细节走法线；载体厚度、尖角轮廓、真实镂空与会投下重要阴影的凸饰保留几何。金属层用金属度，木底与釉层用非金属；不同层不能只靠一张金色底图区分。

验收时让侧光从左右移动：木纹不应像印上去的阴影，凸起与凹槽方向正确，载体边缘有厚度，徽章在目标检视尺寸仍可分辨。程序起始符号可作为正式设计的底稿，进一步艺术修订另存版本。
