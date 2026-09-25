---
name: evolve-blender-assets
description: Build, admit, and evolve Blender assets through frozen contracts, versioned Python/spec workflows, fixed-camera evidence, content-bound reports, independent glTF round-trip QA, and optional Godot or Three.js validation. Use for AI-authored procedural buildings, props, or environment assets; turning one-shot Blender scripts into reusable generators; importing Meshy/Tripo or other external meshes under provenance and license custody; comparing immutable candidates; or preparing semantic GLB exports with anchors, collision, and visibility groups. Do not use for manual-only Blender tutorials, character sculpting or rigging, or unvalidated one-shot mesh generation.
---

# Evolve Blender Assets

Treat the result as an asset-producing system with evidence, not as a pleasing render. Keep the editable `.blend`, runtime `.glb`, review images, validation reports, candidate seal, and human promotion decision separate.

## Route the request

1. Inspect repository instructions, dirty files, existing asset pipelines, installed Blender/engine versions, and native validators.
2. Reuse the repository's Artifact Evolution workflow when one exists. Map this asset subgraph into it instead of creating a competing authority.
3. Otherwise use the portable scripts in this Skill.
4. Freeze two independent choices:

| Axis | Value | Meaning |
| --- | --- | --- |
| Authoring | `procedural-generator` | Reviewed Python/spec creates the geometry. |
| Authoring | `deterministic-adapter` | A pinned input mesh is transformed by a replayable adapter. |
| Authoring | `external-mesh-intake` | A Meshy, Tripo, scan, or vendor mesh is admitted, repaired, and semantically packaged. |
| Validation | `prototype` | Prove build, runtime export, round trip, and fixed-view quality. |
| Validation | `reusable` | Add same-input replay; procedural generators also need two controlled parameter families. |
| Validation | `engine-ready` | Add real target-engine import, semantics, collision, visibility, and engine-native evidence. |

Do not force procedural parameter probes onto an external mesh. For an external input, prove custody and, at `reusable` or `engine-ready`, replay of the transformation pipeline.

Require blind A/B review only for `original_control` superiority claims. A mechanism transfer or independent creation can pass an absolute frozen contract without inventing an Original Baseline.

## Read the contracts

Before building or promoting, read:

- `references/evolution-contract.md` for scope custody, candidate lineage, seals, and promotion authority.
- `references/blender-runtime-contract.md` for CLI execution, semantic accumulation, GLB export, and engine integration.
- `references/evidence-and-review.md` for fixed evidence, report bindings, controlled probes, replay, and stopping conditions.

Project-specific contracts are stronger than these portable defaults.

## Initialize and freeze the case

Resolve this Skill directory, then initialize a new portable case with every routing choice explicit:

```powershell
python scripts/init_asset_case.py `
  --root path/to/asset-case `
  --asset-id medieval-watchtower `
  --candidate-id r01 `
  --authoring-kind procedural-generator `
  --validation-level engine-ready `
  --engine godot `
  --views hero,front,gable,roof-off,game-camera
```

Complete `brief.md`, `source-manifest.json`, `quality-contract.json`, and `toolchain.json`. Pin positive budgets, quality dimensions, full camera contracts, coordinate frames, semantic groups, executables or explicit discovery rules, and exact version output. Record every included mesh/texture with a SHA-256 digest, verified license reference, allowed uses, and remaining unknowns.

Prepare all four root records before requesting the required scope approval. Reuse approval only when it covers these exact records. The actor argument records the approving authority; running the command does not create that authority. After approval, freeze the records before relying on candidate evidence:

```powershell
python scripts/anchor_asset_case.py freeze-scope `
  --root path/to/asset-case `
  --actor reviewer-id `
  --reason "Approved asset scope and quality bar"
```

The portable schemas impose mandatory reports and accept only `passed` for those gates. A case contract may add gates, but it cannot remove or weaken built-in ones.

## Build from a clean scene

Prefer a structured spec plus reusable constructors over a monolithic prompt or opaque mesh. Change the spec first; extend the construction vocabulary only when the current vocabulary cannot express the requested change.

Accumulate the model through named semantic milestones:

1. primary blockout;
2. silhouette and negative space;
3. gameplay structure and interaction clearances;
4. secondary construction forms;
5. surface and style treatment;
6. runtime materialization.

Validate cheap structural invariants after each milestone. A build-event log is recommended diagnostic evidence, but the content-bound build report is the portable authority.

Keep three layers distinct:

- **Authoring:** editable named pieces, modifiers, helpers, and source structure.
- **Runtime:** deliberately grouped meshes, semantic anchors, collision proxies, extras, and exportable materials.
- **Evidence-only:** cameras, lights, ground, labels, and debug helpers that must not enter the GLB.

Run reviewed code with a pinned Blender CLI from factory startup. Prefer checked-in Python/JSON to transient MCP code. Use Blender MCP only after the CLI path works, inside an isolated workspace without unrelated secrets.

## Produce bound evidence and reports

While the candidate is still a mutable `working_draft`:

1. save the authoring `.blend` and export the runtime `.glb`;
2. import the GLB in an independent clean Blender process;
3. verify budgets, finite transforms, coordinate markers, semantics, anchors, collision, degenerates, and export leaks;
4. render every frozen authoring and engine view at its exact camera and resolution;
5. actually open and inspect every PNG;
6. write the required JSON reports with empty `failures`, concrete observations, the scope-freeze hash, and exact hashes of their source/input/output/evidence dependencies.

A successful Blender command or attractive screenshot does not prove runtime structure. The report status alone is never enough; the validator checks its content bindings.

## Snapshot, seal, and revise

After all files and hashes are final, change the candidate record from `working_draft` to `candidate_snapshot`, bind the frozen root hashes, source/input/output/evidence/report inventory, then run:

```powershell
python scripts/validate_asset_case.py `
  --root path/to/asset-case `
  --candidate-id r01 `
  --pre-seal

python scripts/anchor_asset_case.py seal `
  --root path/to/asset-case `
  --candidate-id r01 `
  --actor reviewer-id `
  --reason "Preflight and evidence package passed"

python scripts/validate_asset_case.py `
  --root path/to/asset-case `
  --candidate-id r01
```

The separate seal binds the candidate record, frozen scope, and complete inventory. The scripts create records exclusively and refuse overwrites, but a local filesystem is not an adversarial trust root. Use Git, signatures, or the native append-only Artifact Evolution workflow for authoritative custody.

Never edit a sealed candidate in place. Materialize a defect on the parent, then initialize a descendant with `--parent` and one or more `--defect-id` arguments. The initializer content-binds those defect records into the descendant rationale. A descendant must explain the mechanism change and provide fresh outputs, evidence, and reports. Use at most three rounds per campaign; start a new named campaign with an explicit reason if more work remains.

## Prove the selected authoring route

For a `procedural-generator` at `reusable` or `engine-ready`:

- rebuild the same source/spec twice in clean processes;
- compare decoded pixels or declared tolerances and normalized imported semantics, not container bytes;
- run at least two spec-only probes from different parameter families;
- prove exact changed paths, fixed builder hashes, expected metric response, preserved semantics, budgets, and GLB round trips.

For `deterministic-adapter` or `external-mesh-intake`:

- bind every local input to a declared source-manifest entry and matching SHA-256;
- verify license authority for modification and runtime distribution;
- record repair, retopology, material, merge, semantic, and export steps;
- at `reusable` or `engine-ready`, replay the same transformation twice and compare normalized outputs.

Do not claim binary determinism for PNG, GLB, or `.blend` when only decoded pixels and normalized semantics match.

## Validate the target engine

For `engine-ready`, import the exact candidate GLB into the named engine and bind that GLB hash in the engine report. Verify nodes, coordinate frame, scale, materials, extras/metadata, anchors, collision, visibility behavior, and representative gameplay-camera screenshots.

For Godot, check the installed version's actual glTF metadata and collision-import behavior. Prefer an explicit `EditorScenePostImport` bridge for production semantics. Blender lighting is not runtime material authority.

## Decide promotion honestly

Portable preflight can establish a sealed, promotion-eligible candidate; it cannot establish trusted human approval by itself. Record promotion only with an authority reference:

```powershell
python scripts/anchor_asset_case.py promote `
  --root path/to/asset-case `
  --candidate-id r01 `
  --actor human-reviewer `
  --reason "Approved for the shared environment baseline" `
  --authority-ref "git:commit:<commit-sha>"

python scripts/validate_asset_case.py `
  --root path/to/asset-case `
  --candidate-id r01 `
  --require-promotion `
  --trusted-authority-ref "git:commit:<commit-sha>"
```

Use state labels precisely:

- `working_draft`: mutable construction state;
- `candidate_snapshot`: complete local record awaiting or carrying a separate seal;
- sealed candidate: derived from a valid external seal plus a passing audit;
- `promotion_eligible`: sealed and all local gates pass;
- valid promotion receipt: the human decision binds the seal and all reports, but its external authority is not yet trusted by portable file inspection alone;
- `promoted`: the receipt is valid and a trusted caller supplies the same Git, signature, or native-workflow authority reference;
- `completed_unpromoted`: evidence retained without human promotion;
- `quarantined`: provenance or integrity failure invalidates the package.

Report pipeline maturity and art maturity separately.

## Hard rules

- Never execute unreviewed model-generated Blender code against a broad or sensitive filesystem.
- Never overwrite a scope freeze, candidate, seal, or promotion receipt.
- Never claim exact reconstruction without source and license authority.
- Never use image similarity as proof of hidden topology, anchors, collision, or runtime behavior.
- Never hide `tie`, `insufficient_evidence`, known defects, or engine material drift inside a pass.
- Never admit third-party meshes, textures, or frames without digest-bound provenance and verified allowed use.

## Handoff

Lead with the authoring kind, validation level, strongest verified gate, and whether the result is only locally eligible or externally promoted. Link the frozen contract, candidate record, `.blend`, `.glb`, round-trip report, visual evidence, route-specific replay/control reports, engine report when required, seal, and promotion receipt when one exists. State known defects and remaining art work.
