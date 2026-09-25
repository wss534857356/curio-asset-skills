# 人物贴图提示词

每个代码块对应一种输出，不要求在同一张图拼成四宫格。替换花括号中的信息；不要直接照搬历史人物的身份。先确定彩图，再制作与它配准的数据图。

## 新角色的平光底色

输入风格参考时明确它只定义画风，新角色身份来自当前设定。

```text
Create one production 2D character sprite for a medieval animal noir game.
Character: {species, age, gender, identity, costume, accessories, expression}.
Pose and framing: {approved pose or relaxed three-quarter front conversational pose}, full body including ears, feet, tail and carried objects, centered with modest safe margins, portrait {actual canvas/aspect}.
Style: rough confident black American-comic outlines, large scarlet, cobalt, ochre, warm ivory and brown pigment blocks, readable eyes and face. Match the supplied style reference's line density and proportions without copying its character.
LIGHTING-NEUTRAL ALBEDO: even local material colors. No directional highlights, painted cast shadows, orange rim lighting, bloom, AO shadow wedges, or shaded beauty-render lighting. Keep genuine fur markings and necessary contour/seam lines; metal is its flat local base color.
One isolated character, actual transparent alpha, no painted checkerboard, ground shadow, scenery, UI, text, border, or extra figures. Do not reduce this HD illustration to a pixel grid.
```

## 现有彩图去光照

输入原彩图；有既定遮罩时作为不能改动轮廓的辅助约束。

```text
Edit the supplied character into a LIGHTING-NEUTRAL BASE COLOR texture.
Preserve the exact canvas, pose, silhouette, proportions, eye/muzzle positions, ears, tail, clothing boundaries, fingers, feet and carried objects. Keep it registered to the supplied silhouette guide.
Remove directional highlights, colored rim lights, painted cast shadows, dense hatch shading and ambient-occlusion fills. Replace them with ordinary local material colors, not softened versions of the previous light and dark wedges.
Keep genuine pigmentation, spots/feather markings, black pupils/nose, the outer contour and necessary structural seams. Do not mistake dark fur or black fabric for shadows.
Same identity and costume. No crop, zoom, recentering, new props, labels or ground shadow. {Preserve the genuine alpha, or preserve the layout handled by the existing independent mask.}
```

## 精确轮廓遮罩

原图必须是已经选定的构图；遮罩错位会导致耳朵、手指或尾部发光/缺失。

```text
Produce an EXACT SILHOUETTE MATTE for the supplied character.
Identical full canvas, framing, pose, proportions and pixel positions. Do not crop, zoom, recenter or redesign.
Entire character and every carried object solid pure white. Entire background and actual empty gaps between limbs solid pure black. No internal face, fur, clothing, feather or tool outlines. Keep only a narrow antialias at the outer silhouette.
Output one opaque RGB black-and-white segmentation texture. No shading, grey checkerboard, legend, labels or panels.
```

## 平滑形体法线

输入 1 是当前人物彩图；输入 2 是其遮罩（若有）；输入 3 仅为已验证法线的编码/形体频率参考（若有）。未实际提供的输入不要出现在提示词里。

```text
Use case: precise-object-edit / texture derivation.
Output ONE production OpenGL +Y tangent-space RGB NORMAL MAP for the exact character in input 1, on its unchanged {width}x{height} full canvas.
Input 2 is its silhouette registration guide. Input 3 is ONLY a reference for broad-form normal encoding and smoothness, not a pose or character to copy.
Keep the character silhouette, face, eyes, ears, hands, clothing, accessories, feet and tail aligned with input 1. Same framing, scale and anatomy; no crop, zoom or new figure.
RGB encodes geometric surface direction, not lighting or pigment. Encode normalized directions as (N * 0.5 + 0.5) * 255: red is right-positive X, green is up-positive Y, blue is viewer-facing Z. Flat front-facing areas and the background are neutral (128,128,255).
Use the forward hemisphere and coherent broad forms: rounded skull and cheeks, projecting muzzle or beak, ear planes, shoulder/chest masses, arms and hands, legs/boots, tail and two or three main long garment folds. Make direction changes across substantial regions, not only a thin embossed silhouette. Small buckles and actual seams may have restrained bevels.
{Character-specific form anchors: muzzle, cheek, ear, tail, garment overlap and accessory positions.}
Ignore pigment boundaries, animal spots, feather colors, printed embroidery, black comic outlines and painted shadows. They are NOT holes, bumps or separate geometric layers. Do not derive relief from image brightness.
No grayscale height map, beauty illustration, source garment colors, AO, cast shadows, specular highlights, grain, fur noise, legends, text or borders. Outside the character and in true empty gaps: uniform opaque neutral normal (128,128,255).
```

不要把“以蓝紫为主”当作通过标准。耳尖和侧面允许比躯干更倾斜的法线；原始边缘编码少量异常先量化，再看运行时 mip 采样结果。整体偏黄/棕、全图平蓝、五官漂移或复制豹纹都是需要检查的信号。

## RGB 材质图示例（按目标 shader 适配）

仅在当前 shader 仍读取 R/G/B 为下列含义时使用。换引擎或材质应重写通道定义。

```text
Produce one precisely registered RGB MATERIAL PARAMETER texture for the supplied character. Identical full canvas, silhouette, anatomy, clothing and accessory positions.
R = rim-response weight; G = specular-response weight; B = roughness. These are linear data channels, not visual colors or an ORM texture.
Use uniform semantic material regions. Suggested art targets:
Fur / feathers: (90,35,225).
Fabric / cloak / trousers: (40,12,240).
Leather belts, pouches and boots: (40,95,170).
Actual metallic clasps, buckle frames and rings: (40,220,65).
Nose / eyes / beak: (20,110,135).
Outside character and true gaps: (0,0,0).
Ignore illumination, ink lines and fur pigmentation. No shaded gradients, grain, highlights, legend or text. Keep clean boundaries between actual materials.
```

这些 RGB 是生成目标而非实测承诺。布料塑料感优先检查粗糙度、高光权重和连续高光分支；赛璐璐分支可能有意抑制连续高光，不能据此判定材质图没有加载。
