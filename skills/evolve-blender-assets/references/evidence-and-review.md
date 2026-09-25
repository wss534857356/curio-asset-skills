# Evidence, Reports, Review, and Promotion

## Freeze evidence before seeing results

For every view, record:

- stable ID and review purpose;
- perspective/orthographic type, location, Euler rotation, target, and lens/ortho scale;
- exact PNG width and height;
- renderer, samples, and color-management record;
- visible and hidden semantic groups;
- scene state such as roof-on, roof-off, open, closed, or gameplay-camera;
- frame, seed, time, and deterministic mode when applicable.

Choose views that expose different risks. A building might use hero, front, gable, roof-off, interior, and game camera. A prop might use hero, silhouette, open/exploded state, socket/interaction, and game camera. Every view needs a purpose; more images are not automatically stronger evidence.

Open the actual generated images at sufficient detail. Inspect a contact sheet for composition and individual critical views for intersections, Z-fighting, material separation, openings, and interaction readability. A renderer exit code, file hash, or thumbnail is not visual review.

## Evidence custody

Each candidate evidence entry binds:

- view ID;
- stage: `authoring` or `engine`;
- `image/png` media type;
- decoded width and height;
- relative path and SHA-256.

The validator decodes the PNG header and compares dimensions with both the entry and camera contract. Engine-ready candidates need at least one engine-stage image. The visual report binds the complete evidence map; the engine report separately binds exactly the engine-stage evidence map.

## Matched evidence and claim boundaries

Comparisons are valid only when slots share:

- view IDs and camera contracts;
- dimensions and crop;
- renderer class and presentation treatment;
- visible/hidden groups and state;
- animation/simulation time;
- no identity-bearing labels in blind packets.

Return `insufficient_evidence` when a slot lacks a required view or uses materially different framing. Never infer topology, collision, anchors, or hidden geometry from matched pixels.

For `original_control`, use an independent anonymous A/B packet. Keep identity mapping separate until the reviewer records `A`, `B`, `tie`, or `insufficient_evidence`. A tie remains a tie. Mechanism transfer and independent creation use their frozen absolute quality contract instead.

## Every report is content-bound

All portable reports contain:

- the exact schema for that report;
- matching asset and candidate IDs;
- status exactly `passed` for eligibility;
- `failures: []`;
- `bindings.scope_freeze_sha256`;
- route-specific artifact hash maps;
- concrete observations rather than a bare status.

Candidate records hash the report files, and the candidate seal hashes that report inventory. This creates a chain:

```text
root records -> scope freeze
candidate artifacts -> report bindings
reports -> candidate record
candidate record + inventory -> candidate seal
candidate seal + report hashes -> promotion receipt
```

Portable files detect accidental drift. A promotion receipt may contain a Git/signature/native-workflow reference, but the validator reports `promoted` only when a trusted caller independently supplies the same value.

## Report-specific minimums

### `build_execution`

Binds exact source, input, and output maps. Records zero exit code, factory startup, background mode, and disabled auto-execution. Observations include triangles, runtime meshes, and GLB bytes for budget enforcement.

### `roundtrip`

Binds the runtime GLB and records that the exact hash was imported independently. It verifies semantic inventory, coordinate frame, numeric axis marker, zero export leaks, and zero degenerate faces.

### `visual_review`

Binds every candidate evidence PNG. It lists all required reviewed views, includes `inspection_attestation.opened_images: true` and a named reviewer, and supplies a finite 0–1 score for every frozen quality dimension. Every score must meet its predeclared minimum.

Example shape:

```json
{
  "schema": "blender_asset_visual_review/v1",
  "asset_id": "medieval-watchtower",
  "candidate_id": "r01",
  "status": "passed",
  "failures": [],
  "bindings": {
    "scope_freeze_sha256": "...",
    "evidence": {"hero": "...", "game-camera": "..."}
  },
  "independent": false,
  "reviewed_views": ["hero", "game-camera"],
  "inspection_attestation": {
    "opened_images": true,
    "reviewer": "reviewer-id"
  },
  "quality_scores": {
    "silhouette": 0.82,
    "game_camera_legibility": 0.78
  },
  "known_limits": ["Runtime materials remain first-pass art."]
}
```

### `reproducibility`

For procedural reusable/engine-ready routes. Binds source and runtime output, names two distinct clean run IDs, confirms identical input hashes, passes decoded-evidence equality/tolerance, and passes normalized semantic equality.

### `controlled_changes`

For procedural reusable/engine-ready routes. Provides at least two passed variants from distinct parameter families. Each binds overrides, exact allowed and actual changed paths, unchanged builder, preserved semantic inventory, observed metric response, and passed GLB round trip.

### `input_custody`

For adapters and external intake. Binds every candidate input and confirms hashes, verified license status, and source-manifest ID matching.

### `transformation_replay`

For reusable/engine-ready adapters and external intake. Binds source, input, and runtime output, names two clean run IDs, confirms identical input hashes, and passes normalized output equality.

### `engine_import`

For engine-ready routes. Binds the exact runtime GLB and exact engine-stage evidence. Records engine/version match, GLB hash match, node inventory, metadata, anchors, collision, visibility, coordinate frame, decoded screenshots, and material status.

### `blind_review`

For `original_control`. Binds matched evidence and records independent review, identity isolation, and one of `A`, `B`, `tie`, or `insufficient_evidence`.

## Defect quality

Every materialized defect should include:

- unique ID and affected candidate;
- evidence view or report field;
- object, semantic group, material, or construction stage;
- severity and blocking classification;
- concrete problem;
- requested change constrained by frozen budgets and semantics.

Bad: “make the roof nicer.”

Good: “In `game-camera`, the snow cap hides the dark roof silhouette. Reduce eave coverage and introduce two height levels without changing footprint, runtime-group count, or palette.”

Preserve failed drafts and logs when they explain a repair, but do not present them as current passing evidence.

## Replay and control interpretation

Same-input replay compares decoded evidence and normalized scene semantics, not container bytes. Localize differences to seed, iteration order, modifier/simulation state, renderer, serializer metadata, engine importer, or toolchain drift.

Controlled probes prove that a procedural builder exposes a useful design space. Declare the variant, base source hashes, overrides, exact allow-listed paths, expected metric, and invariants before running it. Two cosmetic color tweaks do not establish structural reuse.

An external mesh route uses custody and transformation replay instead. It must not fabricate a procedural design-space claim.

## Stop conditions

Stop adding detail and repair or re-scope when:

- two clean runs differ in normalized runtime structure;
- an intended spec-only change requires broad builder surgery;
- GLB reload loses axes, groups, anchors, collision, or required metadata;
- a Blender-only visual improvement regresses in the target engine;
- the same blocking topology/overlap defect returns in two descendants;
- evidence views or thresholds keep changing after results are seen;
- source or license authority is unresolved;
- tool/MCP failure and modeling failure cannot be distinguished;
- three campaign rounds finish without meaningful loss reduction.

Stopping is not failure. Preserve the best evidence and counterexample, then decide whether the next campaign needs a new representation, constructor vocabulary, toolchain, or source route.

## Eligibility checklist

All candidates:

- completed root records and valid scope freeze;
- clean bound build report;
- bound `.blend` and `.glb`;
- independent GLB round trip;
- every frozen PNG decoded and actually reviewed;
- budgets, provenance, and known limits explicit;
- candidate snapshot plus separate valid seal.

Procedural reusable/engine-ready adds reproducibility and two controlled parameter families. Adapter/external reusable/engine-ready adds input custody and transformation replay. Engine-ready adds a real engine report and engine PNGs. Original-control adds independent blind review.

Eligibility is not promotion. A bound human receipt plus a matching authority reference supplied from outside the case is required for `promoted`.
