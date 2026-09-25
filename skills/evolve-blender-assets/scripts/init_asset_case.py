#!/usr/bin/env python3
"""Create a non-overwriting Blender asset case or defect-linked candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import validate_asset_case as validator


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
AUTHORING_KINDS = (
    "procedural-generator",
    "deterministic-adapter",
    "external-mesh-intake",
)
VALIDATION_LEVELS = ("prototype", "reusable", "engine-ready")
ENGINES = ("none", "godot", "threejs", "other")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a frozen-contract Blender asset case or a new candidate.",
    )
    parser.add_argument("--root", required=True, type=Path, help="Case directory")
    parser.add_argument("--asset-id", required=True, help="Stable asset identifier")
    parser.add_argument("--candidate-id", required=True, help="New candidate identifier")
    parser.add_argument(
        "--authoring-kind",
        choices=AUTHORING_KINDS,
        help="Required when creating a case; cannot change after scope freeze",
    )
    parser.add_argument(
        "--validation-level",
        choices=VALIDATION_LEVELS,
        help="Required when creating a case; cannot change after scope freeze",
    )
    parser.add_argument(
        "--engine",
        choices=ENGINES,
        help="Required when creating a case; engine-ready cannot use none",
    )
    parser.add_argument(
        "--views",
        help="Comma-separated frozen evidence view IDs; required for a new case",
    )
    parser.add_argument("--campaign-id", help="Campaign ID; inherited when omitted")
    parser.add_argument("--parent", help="Existing sealed parent candidate")
    parser.add_argument(
        "--defect-id",
        action="append",
        default=[],
        help="Parent defect addressed by this revision; repeat as needed",
    )
    parser.add_argument(
        "--new-campaign-reason",
        help="Required when changing campaign ID after a three-round lineage",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    raise ValueError(message)


def validate_id(value: str, label: str) -> None:
    if not ID_PATTERN.fullmatch(value):
        fail(f"{label} must match {ID_PATTERN.pattern}: {value!r}")


def resolve_descendant(base: Path, child: str, label: str) -> Path:
    path = (base / child).resolve()
    if path == base or base not in path.parents:
        fail(f"{label} resolves outside {base}: {path}")
    return path


def reject_json_constant(value: str) -> None:
    fail(f"Non-finite JSON number is not allowed: {value}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_json_constant,
        )
    except FileNotFoundError:
        fail(f"Missing required file: {path}")
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"Expected a JSON object in {path}")
    return value


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def write_text_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def parse_views(raw: str | None) -> list[str]:
    if raw is None:
        return []
    views: list[str] = []
    for item in raw.split(","):
        view = item.strip()
        if not view:
            continue
        validate_id(view, "view ID")
        if view not in views:
            views.append(view)
    return views


def mandatory_reports(authoring_kind: str, validation_level: str) -> list[str]:
    reports = ["build_execution", "roundtrip", "visual_review"]
    if authoring_kind == "procedural-generator":
        if validation_level in {"reusable", "engine-ready"}:
            reports.extend(["reproducibility", "controlled_changes"])
    else:
        reports.append("input_custody")
        if validation_level in {"reusable", "engine-ready"}:
            reports.append("transformation_replay")
    if validation_level == "engine-ready":
        reports.append("engine_import")
    return reports


def initialize_case(
    root: Path,
    asset_id: str,
    authoring_kind: str,
    validation_level: str,
    engine: str,
    views: list[str],
) -> None:
    if root.exists() and any(root.iterdir()):
        fail(
            "Refusing to initialize a case in a non-empty directory without "
            f"quality-contract.json: {root}"
        )
    if validation_level == "engine-ready" and engine == "none":
        fail("engine-ready validation requires a target engine")
    if not views:
        fail("At least one frozen evidence view is required")

    root.mkdir(parents=True, exist_ok=True)
    reports = mandatory_reports(authoring_kind, validation_level)

    write_text_exclusive(
        root / "brief.md",
        "# Asset Brief\n\n"
        f"Asset ID: `{asset_id}`\n\n"
        "## Player-facing purpose\n\n"
        "Describe what the asset must communicate or enable in the game.\n\n"
        "## Visual and structural intent\n\n"
        "Describe silhouette, proportions, material grammar, and important states.\n\n"
        "## Explicit exclusions\n\n"
        "List work that is outside this case.\n",
    )
    write_json_exclusive(
        root / "source-manifest.json",
        {
            "schema": "blender_asset_source_manifest/v2",
            "asset_id": asset_id,
            "authoring_kind": authoring_kind,
            "claim_mode": "independent_creation",
            "sources": [],
            "license_notes": [],
            "unknowns": [],
        },
    )
    write_json_exclusive(
        root / "quality-contract.json",
        {
            "schema": "blender_asset_quality_contract/v2",
            "asset_id": asset_id,
            "authoring_kind": authoring_kind,
            "validation_level": validation_level,
            "target_engine": engine,
            "definition_of_done": [
                "A factory-startup Blender build exits successfully.",
                "The runtime GLB passes an independent clean-process reload.",
                "Every frozen evidence view is decoded and inspected.",
            ],
            "quality_dimensions": [],
            "blocking_failures": [
                "An included source lacks verified usage authority.",
                "A render-only or authoring-only object leaks into the runtime GLB.",
                "A required runtime group, anchor, or collision semantic is missing.",
                "A required report, output, or evidence view is missing.",
            ],
            "budgets": {
                "max_triangles": None,
                "max_runtime_meshes": None,
                "max_glb_bytes": None,
            },
            "review_viewpoints": views,
            "review": {"require_independent": False},
            "required_reports": reports,
            "report_status_policy": {name: ["passed"] for name in reports},
        },
    )
    write_json_exclusive(
        root / "toolchain.json",
        {
            "schema": "blender_asset_toolchain/v2",
            "asset_id": asset_id,
            "blender": {
                "executable_path": None,
                "discovery_rule": None,
                "version_output": None,
                "binary_sha256": None,
            },
            "gltf_exporter": {"version": None, "settings": {}},
            "renderer": {
                "engine": None,
                "samples": None,
                "color_management": {},
            },
            "target_engine": {
                "name": engine,
                "executable_path": None,
                "discovery_rule": None,
                "version_output": None,
                "binary_sha256": None,
            },
            "image_comparator": {"name": None, "version_output": None},
            "isolation": {"workspace_root": None, "network_policy": None},
        },
    )
    for name in ("candidates", "seals", "promotions"):
        (root / name).mkdir(exist_ok=True)


def parent_defects(parent_dir: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    defects_dir = resolve_descendant(parent_dir, "defects", "parent defects directory")
    for discovered in sorted(defects_dir.glob("*.json")):
        path = discovered.resolve()
        if defects_dir not in path.parents:
            fail(f"Parent defect resolves outside defects directory: {path}")
        value = load_json(path)
        defect_id = value.get("id")
        if isinstance(defect_id, str) and defect_id:
            if defect_id in records:
                fail(f"Duplicate parent defect ID: {defect_id}")
            records[defect_id] = validator.sha256_file(path)
    return records


def create_candidate(
    root: Path,
    asset_id: str,
    candidate_id: str,
    campaign_id: str | None,
    parent: str | None,
    defect_ids: list[str],
    new_campaign_reason: str | None,
) -> Path:
    candidates_dir = resolve_descendant(root, "candidates", "candidates directory")
    candidate_dir = resolve_descendant(candidates_dir, candidate_id, "candidate directory")
    if candidate_dir.exists():
        fail(f"Refusing to overwrite existing candidate: {candidate_dir}")

    existing = [path for path in candidates_dir.iterdir() if path.is_dir()]
    inherited_spec: dict[str, Any] | None = None
    round_index = 1
    resolved_campaign = campaign_id or f"{asset_id}-campaign-01"
    defect_bindings: list[dict[str, str]] = []

    if parent is None:
        if existing:
            fail("A later candidate requires --parent and at least one --defect-id")
        if defect_ids:
            fail("An initial candidate cannot declare parent defects")
        if new_campaign_reason:
            fail("An initial candidate does not use --new-campaign-reason")
    else:
        validate_id(parent, "parent candidate ID")
        if not defect_ids:
            fail("A descendant candidate requires at least one --defect-id")
        parent_dir = resolve_descendant(candidates_dir, parent, "parent candidate directory")
        parent_record = load_json(
            resolve_descendant(parent_dir, "candidate.json", "parent candidate record")
        )
        if parent_record.get("asset_id") != asset_id:
            fail(f"Parent asset_id does not match {asset_id!r}")
        if parent_record.get("candidate_id") != parent:
            fail("Parent candidate_id does not match its directory")
        if parent_record.get("status") != "candidate_snapshot":
            fail(f"Parent {parent!r} is not a candidate_snapshot")
        parent_audit = validator.audit_case(root, parent, require_seal=True)
        if not parent_audit.get("sealed_candidate"):
            messages = [
                finding.get("message", finding.get("code", "unknown error"))
                for finding in parent_audit.get("findings", [])
                if finding.get("level") == "error"
            ]
            fail(
                f"Parent {parent!r} failed its complete sealed audit: "
                + "; ".join(messages[:6])
            )

        inherited_spec = load_json(
            resolve_descendant(parent_dir, "spec.json", "parent candidate spec")
        )
        known_defects = parent_defects(parent_dir)
        missing = sorted(set(defect_ids) - set(known_defects))
        if missing:
            fail(f"Parent defects do not exist: {', '.join(missing)}")
        defect_bindings = [
            {"id": defect_id, "sha256": known_defects[defect_id]}
            for defect_id in defect_ids
        ]

        parent_campaign = parent_record.get("campaign_id")
        parent_round = parent_record.get("round_index")
        if not isinstance(parent_campaign, str) or not ID_PATTERN.fullmatch(parent_campaign):
            fail("Parent has no valid campaign_id")
        if not isinstance(parent_round, int) or isinstance(parent_round, bool):
            fail("Parent has no valid round_index")

        if campaign_id is None or campaign_id == parent_campaign:
            resolved_campaign = parent_campaign
            round_index = parent_round + 1
            if round_index > 3:
                fail("A campaign is capped at three rounds; provide a new --campaign-id")
            if new_campaign_reason:
                fail("--new-campaign-reason is only for a changed campaign ID")
        else:
            if not new_campaign_reason or not new_campaign_reason.strip():
                fail("A changed --campaign-id requires --new-campaign-reason")
            resolved_campaign = campaign_id
            round_index = 1

    validate_id(resolved_campaign, "campaign ID")
    candidate_dir.mkdir(parents=True)
    for name in ("source", "inputs", "outputs", "evidence", "reports", "defects"):
        (candidate_dir / name).mkdir()

    if inherited_spec is None:
        spec = {
            "schema": "procedural_blender_asset_spec/v2",
            "asset_id": asset_id,
            "candidate_id": candidate_id,
            "campaign_id": resolved_campaign,
            "round_index": round_index,
            "units": "meters",
            "seed": 0,
            "parameters": {},
            "coordinate_frame": {
                "authoring_up": None,
                "authoring_forward": None,
                "runtime_up": None,
                "runtime_forward": None,
                "origin_policy": None,
            },
            "semantics": {"runtime_groups": [], "anchors": [], "collision": []},
            "render": {"views": {}},
        }
    else:
        spec = inherited_spec
        spec["candidate_id"] = candidate_id
        spec["campaign_id"] = resolved_campaign
        spec["round_index"] = round_index
    write_json_exclusive(candidate_dir / "spec.json", spec)

    write_json_exclusive(
        candidate_dir / "candidate.json",
        {
            "schema": "blender_asset_candidate/v2",
            "asset_id": asset_id,
            "candidate_id": candidate_id,
            "campaign_id": resolved_campaign,
            "round_index": round_index,
            "status": "working_draft",
            "parent": parent,
            "revision_rationale": {
                "defect_ids": defect_ids,
                "defect_bindings": defect_bindings,
                "summary": "",
                "new_campaign_reason": new_campaign_reason,
            },
            "frozen_case_hashes": {},
            "source_files": [],
            "input_files": [],
            "outputs": [],
            "evidence": [],
            "reports": {},
            "known_limits": [],
        },
    )
    return candidate_dir


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    validate_id(args.asset_id, "asset ID")
    validate_id(args.candidate_id, "candidate ID")
    if args.campaign_id is not None:
        validate_id(args.campaign_id, "campaign ID")
    views = parse_views(args.views)

    try:
        contract_path = resolve_descendant(root, "quality-contract.json", "quality contract")
        if not contract_path.exists():
            missing = [
                name
                for name, value in (
                    ("--authoring-kind", args.authoring_kind),
                    ("--validation-level", args.validation_level),
                    ("--engine", args.engine),
                    ("--views", args.views),
                )
                if value is None
            ]
            if missing:
                fail(f"A new case requires: {', '.join(missing)}")
            assert args.authoring_kind is not None
            assert args.validation_level is not None
            assert args.engine is not None
            initialize_case(
                root,
                args.asset_id,
                args.authoring_kind,
                args.validation_level,
                args.engine,
                views,
            )
        else:
            contract = load_json(contract_path)
            if contract.get("asset_id") != args.asset_id:
                fail(
                    f"Case asset_id {contract.get('asset_id')!r} does not match "
                    f"{args.asset_id!r}"
                )
            frozen_args = (
                ("--authoring-kind", args.authoring_kind, contract.get("authoring_kind")),
                (
                    "--validation-level",
                    args.validation_level,
                    contract.get("validation_level"),
                ),
                ("--engine", args.engine, contract.get("target_engine")),
            )
            for name, supplied, frozen in frozen_args:
                if supplied is not None and supplied != frozen:
                    fail(f"{name} cannot change an existing contract")
            if views and views != contract.get("review_viewpoints"):
                fail("--views cannot change an existing contract")

        candidate_dir = create_candidate(
            root,
            args.asset_id,
            args.candidate_id,
            args.campaign_id,
            args.parent,
            args.defect_id,
            args.new_campaign_reason,
        )
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        json.dumps(
            {
                "status": "created",
                "case_root": str(root),
                "candidate": str(candidate_dir),
                "next": (
                    "Complete the case records, freeze scope, build the working draft, "
                    "then snapshot and seal the full evidence package."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
