# 使用与验证

## 环境按任务安装

| 工作 | 需要什么 |
|---|---|
| 阅读、安装、写方案 | 支持 SKILL.md 的代理；安装脚本需要 Python 3.10+ |
| 准备油画任务 | Python 标准库，不调用图像服务 |
| 生图、编辑画芯／人物法线 | 宿主已配置的图像生成与编辑能力；系统 imagegen 技能不在本仓库中 |
| 人物图检查 | Python + Pillow |
| 通用油画表面生成 | Python + NumPy；读取高度稿或渲染预览需在 Blender 的 Python 中运行 |
| 画框与 Blender 模型 | Blender（含其 Python/NumPy），从后台新场景运行 |
| Meshy 任务 | Node.js/npm 或兼容 CLI、自己的 Meshy 账号、网络和已授权预算；见该技能 setup |
| 包内容检查 | Python + Pillow + PyYAML；requirements.txt 同时包含 NumPy |

Meshy 上游快照使用 CLI 0.4.0。端点、限额和价格按执行时的官方帮助核对，安装技能不会提供积分或登录状态。上游提到的 3D 打印技能不在本集合里。

使用独立 Python 虚拟环境可避免改动其他项目依赖：

```sh
python -m venv .venv
```

Windows：

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe tools/validate.py
```

macOS/Linux：

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/validate.py
```

## 技能协作

每个目录可以单独安装。机关技能的连续加工章节会引用 `curio-part-finishing`；需要该玩法时一起安装，普通模型制作可以跳过。油画和画框互相配合，但也能分别使用自己的画芯或框体。进阶 Blender 契约流程仅在任务确实需要时启用。

技能里出现的 ImageGen、Blender、Three.js、Godot 是工具或引擎能力，不是该目录附带的运行时。没有对应工具时先完成可做的设计／准备阶段，再明确未执行的生成或接入；不将截图当可运行交付。

## 不付费的油画任务准备

```sh
python skills/curio-oil-paintings/scripts/prepare_painting.py --recipe C01 --out work/rabbit-v1
```

输出 3 份提示词和 task.json、surface.json、frame.json；状态保持待生图／检查。自定义配方见 [示例](../skills/curio-oil-paintings/assets/painting-recipe.example.json)，图像文件按自己的项目替换。

```sh
python skills/curio-oil-paintings/scripts/paint_surface.py --spec work/rabbit-v1/surface.json --out work/rabbit-v1/surface
```

默认是通用笔触与织纹的技术材质，未自动生成画芯。它不会完成按形体法线方向场布笔的定制流程，也不会实现游戏清洁交互。

## 制作一副示例画框

从仓库根运行，`blender` 替换为本机可执行文件路径：

```sh
blender --background --factory-startup --threads 4 --python skills/curio-frame-workshop/scripts/frame_workshop.py -- --spec skills/curio-frame-workshop/assets/frame-spec.json --out work/frame-v1
```

此命令打开后台新场景，不应对正在编辑的 Blender 场景执行清空脚本。规格、批量模板与纹章导出见 [画框制作接口](../skills/curio-frame-workshop/references/production.md)。

## 检查人物法线与模型

```sh
python skills/noir-character-pipeline/scripts/check_character_maps.py --albedo path/to/color.png --mask path/to/mask.png --normal path/to/normal.png --report work/pixel-check.json
python skills/curio-mechanism-workshop/scripts/inspect_glb.py path/to/model.glb --max-triangles 35000 --require-uv
```

将示例路径替换为自己的文件。检查器分别验证图像与 GLB 元数据，不替代五官配准、实际 UV、网格拓扑或游戏画面的目视验收。

## 仓库检查

```sh
python tools/validate.py
python -m unittest discover -s skills/mesh-split-fill/tests -v
```

前者不运行付费任务；后者来自上游拆件技能。设置 `BLENDER_TEST_PATH` 时启用其可选 Blender 集成测试，否则会明确跳过。

仓库提供 [GitHub Actions 配置模板](validation-workflow.example.yml)，当前未启用 CI。需要自动验证时，由具有工作流写入权限的维护者将它放到 `.github/workflows/validate.yml`；模板会在 Linux 执行离线包验证和上游 Python 测试，不会调用付费服务。这些检查不证明所有平台、生成服务与目标引擎都已验证。

图片只是带版本记录的历史成果展示；公开集合不会为检查文档重新生成模型或修改玩家存档。
