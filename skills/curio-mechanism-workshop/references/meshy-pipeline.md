# Meshy 立体部件、中模与 UV

仅对复杂完整器物、圆雕和需要实际体积的部件执行本页。平面猫咪浅浮雕、徽记、刻花使用 [ImageGen 材质路线](surface-relief.md)，不提交模型生成、Remesh 或 UV 任务。材质路线是完整交付路径，不是等待 Meshy 的占位方案。

本仓库收录 Meshy 官方插件 0.6.0 的 generation skill 快照，使用 CLI 0.4.0。执行时先读当前安装版本的 skill 与命令帮助；本文记录工作方式，不替代版本核验。认证、上传、任务和下载均走插件 CLI，不另写保存密钥的请求层。

## 接口边界

- [Remesh API](https://docs.meshy.ai/en/api/remesh)：`POST /openapi/v1/remesh`。选择成功的来源任务或模型输入；支持 `triangle` 与四边面为主的 `quad`。`target_polycount` 是目标值，不是输出保证；设置 `decimation_mode` 会覆盖目标面数。机关外观中模通常用三角形预算。
- [UV Unwrap API](https://docs.meshy.ai/en/api/uv-unwrap)：`POST /openapi/v1/uv-unwrap`。输入格式、面数限制和账号开放情况以当前文档为准，调用前统计实际三角形数。输出新 UV 的无纹理灰模；404 不应反复付费重试。
- [Retexture API](https://docs.meshy.ai/en/api/retexture)：为已有好 UV 保留 `enable_original_uv=true`。UV 任务 ID 不在当前 Retexture 来源任务列表中；对此使用下载的 UV GLB 经 CLI 的 `--model-url` 输入，不假定任何任务 ID 均可串接。

额度与价格执行时查看 [官方价格](https://docs.meshy.ai/en/api/pricing)，不要把本页限制或旧价格视为永久保证。创建本 skill 不需要登录或提交这些任务。

## 任务记录和费用

将计划内的高模生成、拆件生成、中模 Remesh、必要 UV 与贴图列为一张计划，核验余额并说明估算。按已经授权的范围继续；新增变体／重试不是无限免费步骤。

每个任务保存 `part_id`、来源文件、`resource`、`task_id`、父任务、阶段、输出和 `consumed_credits`。未返回实际费用则记为未知。精细生成失败先检查输入和错误，等待超时继续等待同一任务；提交结果未知先查记录，不再次 create。

## 可执行步骤模板

以下每条是独立命令模板；替换变量后逐条读取 JSON，不一次粘贴执行整条制作链。PowerShell 使用单独参数或参数数组，避免把提示词拼进可执行 shell 文本。兼容 runner 按当前 Meshy skill 选择；插件当前可使用 `npm exec --yes --package=meshy-cli@0.4.0 -- meshy`。

1. 形体生成：复用经过查看的部件参考图，`meshy image-to-3d create --help` 核对选项。只需几何时用 `--should-texture false`，之后走 UV／纹理阶段；已有合适高模时直接复用。
2. 首次 `create --async` 取得 `result.submission.task_id` 后，再用 `project init` 登记项目。项目存在后的任务传回实际 `result.project_dir`。这避免已扣费却因本地项目路径不存在丢失任务跟踪。
3. 中模用现有来源做 Remesh，例如：

```text
meshy remesh create --input-task-id SOURCE_ID --topology triangle --target-polycount 16000 --target-formats glb --async --project PROJECT_DIR --stage crow-lantern-body-mid --workspace WORKSPACE --output-schema v1 --format json --no-update-check
```

`SOURCE_ID` 必须是端点当前支持的来源类型；本地修整过的模型或不支持的任务类型改用 `--model-url` 指向实际 GLB。CLI 可处理本地文件；这不表示 HTTP API 能读取本地磁盘路径。

4. 每个新 ID 用它自己的资源等待：

```text
meshy remesh wait TASK_ID --timeout 600 --project PROJECT_DIR --stage crow-lantern-body-mid --workspace WORKSPACE --output-schema v1 --format json --no-update-check
```

使用持久工具会话承载长等待，给用户阶段进展；不把 wait 改成不断重提 create。此后的 UV、贴图等任务分别使用它们所属的资源等待。

5. 下载并计数。Meshy task snapshot 可用 `meshy inspect faces --help` 对照；外部 GLB 用本 skill 的 `inspect_glb.py` 或 Blender 统计实际网格。输出计数未知就调查，不能把目标面数当成已通过当前 API 上限。Blender 面数和导出三角形数同时记录。
6. UV 能用时：

```text
meshy uv-unwrap create --input-task-id MID_TASK_ID --async --project PROJECT_DIR --stage crow-lantern-body-uv --workspace WORKSPACE --output-schema v1 --format json --no-update-check
```

简单程序部件无需此步骤。账号无权限、UV 拉伸或关键边界不合适时，使用 Blender 标缝和展开；机械配合面保留合理纹理方向。
7. 用真实返回的 asset key 下载 UV GLB。将高模颜色／法线等烘焙到新 UV，或对该 GLB 做一次计划内 Retexture 并保留原 UV；先查看 `meshy retexture create --help`。若原材质仍要保留，不能把 UV 白模当作纹理版交付。
8. 回到 Blender 统一尺度、轴向、接缝和材质，装到本地粗模提供的枢轴。API 输出不具有游戏节点、碰撞体和精密配合的权威。

## 远观版与恢复

远观版从已选中的中模派生。可按部件在 Blender 简化；若本轮计划选 Meshy Remesh，则复用模型输入并单独登记该 LOD 任务，不能重新从文字生成一件相似物。

每个 LOD 都复核 UV 与材质。UV 改了就重烘焙；UV 保留则检查接缝和贴图引用。签名下载地址过期时根据原资源和任务 ID 重新取下载信息，不重新生成。
