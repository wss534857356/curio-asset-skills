# Blender and Runtime Contract

## Toolchain preflight

Discover rather than assume:

- Blender executable and exact `--version` output;
- Python API compatibility and enabled extensions;
- glTF exporter version and full settings;
- render engine, samples, and color management;
- target-engine executable/version when engine-ready;
- image decoder/comparator used for replay;
- workspace isolation and network policy.

Use an existing absolute `executable_path` when available. Otherwise record a concrete `discovery_rule` that another runner can resolve; never put a prose description into an executable field. A toolchain change invalidates strict replay until re-baselined.

## Safe CLI baseline

Run reviewed repository files from an empty scene:

```powershell
& $blenderExe `
  --background `
  --factory-startup `
  --disable-autoexec `
  --python-exit-code 1 `
  --python path/to/build_asset.py `
  -- `
  --spec path/to/spec.json `
  --out path/to/working-output
```

Validate authoring and runtime artifacts in separate processes:

```powershell
& $blenderExe `
  --background `
  --disable-autoexec `
  path/to/candidate.blend `
  --python-exit-code 1 `
  --python path/to/validate_authoring.py `
  -- `
  --out path/to/authoring-observations.json

& $blenderExe `
  --background `
  --factory-startup `
  --disable-autoexec `
  --python-exit-code 1 `
  --python path/to/validate_glb.py `
  -- `
  --glb path/to/candidate.glb `
  --out path/to/roundtrip-observations.json
```

Blender processes arguments in order. Test the exact command on the pinned version. Prefer `bpy.data`, `Mesh.from_pydata`, or BMesh for deterministic construction. Use context-sensitive `bpy.ops` only with an explicitly established context.

## Choose the authoring route

### Procedural generator

Keep a small JSON spec and checked-in construction vocabulary. A useful vocabulary includes:

- primitive/profile constructors with explicit dimensions and transforms;
- named materials from a frozen palette;
- collection assignment and semantic tagging;
- stable empty/anchor creation;
- runtime grouping and merge functions;
- evidence camera/light presets;
- export and observation writers.

Category-specific constructors belong in the project, not this generic Skill. Buildings might define gables, roof slabs, window grids, snow caps, beams, stairs, and porch bays. Props might define revolved profiles, lids, sockets, fasteners, and collision hulls.

### Deterministic adapter

Use when a stable, reviewed program transforms a pinned input mesh. Preserve the original input under `inputs/`, bind its source-manifest ID and digest, and record every transformation stage. The adapter must be replayable without modifying its input.

### External mesh intake

Use for Meshy, Tripo, scans, or vendor assets. Generation success is not pipeline success. Before admission:

- preserve the exact downloaded input and SHA-256;
- record producer, locator/job reference, license evidence, and allowed modification/runtime distribution;
- inspect topology, UVs, materials, normals, scale, axes, and hidden geometry;
- repair or retopologize in a deterministic, reviewable stage where practical;
- add semantic groups, anchors, collision, and export selection;
- validate the final GLB independently and in the target engine when required.

Do not demand artificial parameter probes from a one-off external mesh. Claim only the repeatability of the intake/transformation process.

## Accumulate through semantic milestones

“The model accumulated successfully” means each named stage left inspectable structure:

1. **Primary blockout:** origin, units, footprint, largest volumes, bounds, and target-camera occupancy.
2. **Silhouette:** roof/profile/crown/handle masses and important negative spaces at game resolution.
3. **Gameplay structure:** entrances, openings, removable/movable parts, anchors, clearances, and interaction volumes.
4. **Secondary forms:** trim, supports, frames, panels, roots, fasteners, and repeated construction grammar.
5. **Surface/style:** frozen palette, snow/damage/wear layers, emissive accents, and material separation.
6. **Runtime materialization:** semantic merges, collision, extras, export selection, and engine-facing names.

Give stages stable IDs and run cheap checks after each. A `build-events.jsonl` recording stage, constructor, object names, semantic group, source spec paths, and resulting counts/bounds is recommended for diagnosis. It is optional unless the project contract declares and content-binds it. On failure, record the last completed stage and first violated invariant.

Use milestone renders for blockout, silhouette, gameplay structure, and final presentation when they aid diagnosis. Rendering every primitive usually obscures causality and wastes iteration time.

## Separate authoring, runtime, and evidence roles

An authoring scene may contain hundreds of editable objects while the GLB contains only a few runtime groups. Merge by gameplay responsibility, not merely by material.

```text
ASSET_Root
  AUTHORING_*           editable pieces; not exported directly
  RUNTIME_static_*      always-visible runtime meshes
  RUNTIME_occluder_*    camera/room visibility group
  RUNTIME_dynamic_*     interactive or separately animated meshes
  SOCKET_*              interaction, VFX, NPC, camera, or attachment anchors
  *-colonly             optional, version-tested collision convention
  EVIDENCE_*            cameras, lights, debug ground; never exported
```

Useful extras include `semantic_group`, `visibility_group`, `semantic_type`, `runtime_merged`, `source_object_count`, and asset schema/version. Export custom properties as glTF extras and verify where the installed target engine exposes them.

## Required artifacts and build report

Every candidate snapshot binds at least:

- `spec.json` and one builder/adapter under `source/`;
- every external input used, with a source-manifest ID;
- output role `authoring_blend` ending in `.blend`;
- output role `runtime_glb` ending in `.glb`;
- every frozen evidence PNG and its decoded dimensions;
- every mandatory report.

The `build_execution` report must bind exact source, input, and output hashes. It records a zero exit code and attests factory startup, background mode, and disabled auto-execution. Its observations include at least triangles, runtime mesh count, and GLB bytes so the validator can enforce positive frozen budgets.

Additional useful observations include authoring object count/bounds, merge sources per group, anchor transforms, emitted file sizes, last completed milestone, and deferred art limitations.

## Independent GLB round trip

Import the exact output GLB hash in a clean process and verify:

- loader success and independent process identity;
- root, runtime groups, anchors, and collision;
- no camera, light, render ground, authoring helper, or debug export leaks;
- finite transforms, positive scales, plausible bounds, and numeric axis markers;
- exporter-triangulated triangle/material/mesh/file budgets;
- required extras and anchor transforms within tolerance;
- zero degenerate faces;
- explicit authoring/runtime coordinate-frame conversion.

Open boundaries or non-manifold edges may be legitimate for shells, foliage cards, or modular pieces. Record per-mesh diagnostics and contract-specific failures; never weld unrelated pieces merely to make a global counter zero.

## Reproducibility and controlled changes

For a reusable procedural generator, rebuild the same source/spec in two clean runs. Bind identical input hashes and compare:

- decoded evidence pixels or declared perceptual tolerance;
- normalized object/mesh/material/anchor inventory;
- normalized bounds, topology metrics, extras, and group membership.

Do not require byte-identical PNG, GLB, or `.blend` containers.

Run two controlled variants from different parameter families, for example roof pitch and porch width. Each declares overrides, exact allowed JSON paths, expected metric response, and invariants. Prove actual paths equal the allow-list, builders remain unchanged, semantics survive, the requested metric responds, budgets hold, and each GLB round trip passes.

For an adapter or external intake, replay the exact input and source pipeline twice. Bind input and source hashes and compare normalized outputs. This proves deterministic transformation, not that the third-party generator itself is deterministic.

## Target-engine bridge

Engine-ready validation imports the exact runtime GLB and records:

- engine name and exact version output;
- node inventory, scale, axes, bounds, and origin;
- extras/metadata and semantic groups;
- anchors and collision behavior;
- visibility hide/fade or open/closed behavior;
- decoded engine screenshots at frozen cameras;
- explicit material status and known drift.

For Godot, verify the installed version. glTF extras may appear under `metadata.extras`, and collision suffix conventions may create `StaticBody3D`/`CollisionShape3D`; neither should be assumed across versions. Prefer `EditorScenePostImport` to translate explicit metadata into groups, scripts, collisions, and interaction components.

Three.js can provide a fast loader and evidence host. Verify scene traversal, extras in `userData`, axes, bounds, mesh count, and target camera. It does not replace Godot validation when Godot is the shipping engine.

## MCP security boundary

MCP improves observation and invocation latency; it does not make generated code safe or deterministic. Use this order:

1. make the checked-in CLI build pass;
2. review generated Python and dependency changes;
3. isolate Blender from secrets and unrelated files;
4. disable network unless the frozen source manifest requires it;
5. enable MCP only as a replaceable connector;
6. retain final source/spec on disk so the result replays without MCP.
