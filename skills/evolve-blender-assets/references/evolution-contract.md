# Asset Evolution Contract

## Purpose

This is a portable, asset-sized adaptation of the `graph-deeplearning` Artifact Evolution Graph. It preserves frozen scope, content-addressed candidates, defect-linked lineage, bounded revision, honest comparison claims, and human promotion without requiring the full portfolio controller for every Blender spike.

The central question is not “did AI make a good image?” It is “did an approved brief and inspectable source produce a content-bound candidate that passed the required structural, visual, replay, and runtime gates?”

## Freeze three independent choices

### Claim mode

| Claim mode | Valid basis | Allowed claim |
| --- | --- | --- |
| `original_control` | Pinned, licensed, locally runnable Original Baseline | Candidate may be compared with the Original through identity-safe evidence and independent blind review. |
| `mechanism_transfer` | Video, screenshots, papers, source excerpts, or a positive exemplar without a runnable Original | Candidate implements or tests declared transferable mechanisms; no “defeated the original” claim. |
| `independent_creation` | Original brief plus absolute quality contract | Candidate meets or misses the frozen contract; no baseline superiority claim. |

Never turn a screenshot, video, concept image, or manual approximation into a fake runnable Original Baseline.

### Authoring kind

| Authoring kind | Source obligation | Reuse obligation |
| --- | --- | --- |
| `procedural-generator` | Bind spec, builders, and toolchain. | Same-input reproducibility plus two different controlled parameter families. |
| `deterministic-adapter` | Bind a licensed input mesh and replayable adapter. | Same-input transformation replay. |
| `external-mesh-intake` | Bind the exact Meshy/Tripo/scan/vendor input and its usage authority. | Same-input transformation replay when claiming reusable or engine-ready maturity. |

### Validation level

- `prototype`: clean build, `.blend`, `.glb`, independent round trip, fixed evidence, and visual review.
- `reusable`: prototype proof plus route-specific replay/control proof.
- `engine-ready`: reusable proof plus a real target-engine import and engine-native evidence.

These axes must not be collapsed into one mode. An external mesh can be engine-ready without pretending to be a reusable procedural generator.

## Core records and authority

- **Asset Brief:** player-facing purpose, visible/structural intent, and exclusions.
- **Source Manifest:** source identity, role, locator, digest, producer, license status/reference, allowed use, and unknowns.
- **Quality Contract:** definition of done, dimensions, thresholds, blocking failures, budgets, evidence views, and mandatory reports.
- **Toolchain:** executables or explicit discovery rules, exact version output, exporter/render settings, engine, comparison tool, and isolation policy.
- **Scope Freeze:** separate approval binding the hashes of all four root records.
- **Working Draft:** mutable candidate files under construction. It has no promotion standing.
- **Candidate Snapshot:** content-indexed source, input, output, evidence, and report inventory with exact frozen-root hashes.
- **Candidate Seal:** separate receipt binding the candidate record, scope freeze, and full inventory.
- **Materialized Defect:** concrete failure bound to a candidate and evidence/report observation.
- **Revision Rationale:** mechanism-level explanation plus SHA-256 bindings for the exact parent defect records a descendant addresses.
- **Promotion Receipt:** human approval binding the candidate seal and every report hash, with an external authority reference.

The portable filesystem scripts prevent accidental overwrites and detect content drift. They do not defeat an attacker who can rewrite every file. Trusted promotion therefore needs Git history, a signature, or the native append-only Artifact Evolution controller.

## Lifecycle

```text
research or original brief
  -> choose claim / authoring / validation routes
  -> complete root records
  -> approve and hash scope-freeze.json
  -> build mutable working_draft
  -> export, reload, render, inspect, and write bound reports
  -> write complete candidate_snapshot
  -> local pre-seal audit
  -> create separate candidate seal
  -> sealed + promotion_eligible (derived state)
  -> human promotion receipt OR completed_unpromoted
  -> materialize defects on the sealed parent
  -> create defect-linked descendant
```

Evidence is produced before sealing. The seal is the boundary that makes the completed package immutable-by-convention.

## Scope freeze

Freeze at least:

- asset ID, claim mode, authoring kind, validation level, use case, units, and coordinate frame;
- sources, roles, content digests, license conditions, allowed uses, and unknowns;
- visible transferable features versus inferred or unknown construction;
- geometry, runtime-mesh, and file budgets as positive finite numbers;
- evidence view IDs and complete camera, resolution, state, renderer, samples, and color contracts;
- runtime groups, anchors, collision, visibility behavior, and target engine;
- quality dimensions, blocking failures, required reports, and exact pass policy;
- executable paths or explicit discovery rules plus exact version output and settings;
- isolation root and network policy.

Changing any root record after approval invalidates the scope freeze and every candidate binding it. Start a new freeze; never rewrite thresholds to make observed evidence pass.

## Mandatory reports

Every route requires:

- `build_execution`;
- `roundtrip`;
- `visual_review`.

Additional built-in gates:

| Condition | Required report |
| --- | --- |
| Procedural + reusable/engine-ready | `reproducibility`, `controlled_changes` |
| Adapter or external intake at any level | `input_custody` |
| Adapter or external intake + reusable/engine-ready | `transformation_replay` |
| Engine-ready | `engine_import` |
| Original-control claim | `blind_review` |

A portable contract may add reports. It may not omit a built-in report or allow a built-in status other than exactly `passed`.

## Candidate snapshot and seal

Portable layout:

```text
asset-case/
  brief.md
  source-manifest.json
  quality-contract.json
  toolchain.json
  scope-freeze.json
  candidates/
    r01/
      candidate.json
      spec.json
      source/
      inputs/
      outputs/
      evidence/
      reports/
      defects/
  seals/r01.json
  promotions/r01.json        # only after human approval
```

A candidate record uses schema `blender_asset_candidate/v2`, status `candidate_snapshot`, a campaign ID and round index, frozen root hashes, and arrays/maps binding every artifact by relative path and SHA-256. Required output roles are `authoring_blend` and `runtime_glb`. Every evidence entry binds its view, stage (`authoring` or `engine`), PNG dimensions, media type, path, and hash.

Reports are part of the candidate inventory. Each report must also bind the exact scope freeze and the artifacts it actually consumed. This prevents a passing report for one GLB or screenshot set from being attached to another candidate.

The separate seal uses `blender_asset_candidate_seal/v1` and binds:

- asset and candidate IDs;
- candidate-record hash;
- scope-freeze hash and frozen root hashes;
- sorted source/input/output/evidence/report inventory;
- actor, reason, and timezone-aware timestamp.

Do not edit any sealed file. Produce `r02`, not “fixed r01.”

## Lineage, defects, and campaigns

An initial candidate has no parent and is round 1. A descendant must point to a valid sealed parent and list one or more defects that exist under that parent. The descendant record binds each referenced defect's SHA-256 so later edits cannot rewrite the reason for the revision. Its rationale must describe the intended mechanism change; “make it better” is insufficient.

A defect should contain:

```json
{
  "id": "roof-silhouette-r01",
  "affected_candidate": "r01",
  "view": "game-camera",
  "object_or_group": "RUNTIME_occluder_roof",
  "severity": "high",
  "problem": "The roof reads as a flat slab at target resolution.",
  "requested_change": "Expose the pitch without changing footprint or runtime mesh budget."
}
```

Use one coherent defect cluster per revision. Campaign rounds must progress 1, 2, 3. After round 3, start a new campaign at round 1 with an explicit reason while retaining the sealed parent link. Preserve cycles, missing parents, or campaign drift as hard failures.

## Promotion

Machine gates produce only promotion eligibility. Promotion requires a human-authored `blender_asset_promotion/v1` receipt binding:

- decision `approve`;
- the candidate seal hash;
- exact report hashes;
- human author and reason;
- timezone-aware timestamp;
- a syntactically explicit `authority_ref`: `git:commit:...`, `git:tag:...`, `signature:...`, or `artifact-evolution:...`.

The portable validator can prove that the receipt is internally bound, but it cannot trust a reference merely because the case contains it. It reports `promoted` only when a trusted caller supplies the same reference through `--trusted-authority-ref`. If approval or trusted authority is absent, preserve the result as `completed_unpromoted`. If integrity or provenance fails, quarantine it. Never coerce `tie` or `insufficient_evidence` into approval.

## Mapping to native Artifact Evolution

| Portable asset record | Artifact Evolution record |
| --- | --- |
| Source manifest and research notes | Deep Research Package |
| Quality contract, toolchain, and scope freeze | Artifact Contract plus scope freeze |
| Runnable comparison control | Original Baseline |
| Construction vocabulary/stages | Baseline Mechanism Model |
| Candidate snapshot plus seal | Candidate Version plus Candidate Evidence |
| Fixed matched evidence | Blind Evidence Packet |
| Structured failure | Materialized Defect |
| Descendant explanation | Revision Rationale |
| Passing local audit | Evolution Preflight |
| Human receipt | Promotion Approval |

Let the native controller own locks, append-only custody, privacy projection, campaign state, and promotion authority. The Blender subgraph contributes asset-specific sources, artifacts, evidence, and validators.
