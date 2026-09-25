#!/usr/bin/env python3
"""Audit a portable Blender asset case without trusting editable status claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
AUTHORITY_REF_PATTERN = re.compile(
    r"^(?:git:(?:commit|tag):[A-Za-z0-9._/@+-]+|"
    r"signature:[A-Za-z0-9._/@:+-]+|"
    r"artifact-evolution:[A-Za-z0-9._/@:+-]+)$"
)
AUTHORING_KINDS = {
    "procedural-generator",
    "deterministic-adapter",
    "external-mesh-intake",
}
VALIDATION_LEVELS = {"prototype", "reusable", "engine-ready"}
TARGET_ENGINES = {"none", "godot", "threejs", "other"}
CLAIM_MODES = {"original_control", "mechanism_transfer", "independent_creation"}
INCLUDED_SOURCE_ROLES = {
    "included_source_mesh",
    "included_texture",
    "original_baseline",
}
REPORT_SCHEMAS = {
    "build_execution": "blender_asset_build_execution/v1",
    "roundtrip": "blender_asset_roundtrip_report/v1",
    "visual_review": "blender_asset_visual_review/v1",
    "reproducibility": "blender_asset_reproducibility_report/v1",
    "controlled_changes": "blender_asset_controlled_changes_report/v1",
    "input_custody": "blender_asset_input_custody_report/v1",
    "transformation_replay": "blender_asset_transformation_replay_report/v1",
    "engine_import": "blender_asset_engine_import_report/v1",
    "blind_review": "blender_asset_blind_review_report/v1",
}
CORE_SCHEMAS = {
    "quality_contract": "blender_asset_quality_contract/v2",
    "source_manifest": "blender_asset_source_manifest/v2",
    "toolchain": "blender_asset_toolchain/v2",
    "candidate": "blender_asset_candidate/v2",
    "spec": "procedural_blender_asset_spec/v2",
    "scope_freeze": "blender_asset_scope_freeze/v1",
    "candidate_seal": "blender_asset_candidate_seal/v1",
    "promotion": "blender_asset_promotion/v1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate frozen scope, lineage, artifacts, evidence, report bindings, "
            "candidate seal, and optional promotion receipt."
        ),
    )
    parser.add_argument("--root", required=True, type=Path, help="Case directory")
    parser.add_argument("--candidate-id", required=True, help="Candidate to audit")
    parser.add_argument(
        "--pre-seal",
        action="store_true",
        help="Run all local gates without requiring an external candidate seal",
    )
    parser.add_argument(
        "--require-promotion",
        action="store_true",
        help="Fail unless a valid human receipt matches --trusted-authority-ref",
    )
    parser.add_argument(
        "--trusted-authority-ref",
        help=(
            "Authority reference supplied by a trusted caller, not read from the case; "
            "must match the promotion receipt"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional new JSON report path; existing files are never overwritten",
    )
    return parser.parse_args()


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number is not allowed: {value}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_json_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def valid_authority_ref(value: Any) -> bool:
    return isinstance(value, str) and AUTHORITY_REF_PATTERN.fullmatch(value) is not None


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def number_vector(value: Any, length: int) -> bool:
    return isinstance(value, list) and len(value) == length and all(
        finite_number(item) for item in value
    )


def mandatory_reports(
    authoring_kind: str,
    validation_level: str,
    claim_mode: str,
) -> list[str]:
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
    if claim_mode == "original_control":
        reports.append("blind_review")
    return reports


class Audit:
    def __init__(self, root: Path, candidate_id: str) -> None:
        self.root = root.resolve()
        self.candidate_id = candidate_id
        self.candidates_dir = self.case_path("candidates", "candidates directory")
        self.candidate_dir = self.descendant(
            self.candidates_dir,
            candidate_id,
            "candidate directory",
        )
        self.findings: list[dict[str, str]] = []
        self.checked_files: list[dict[str, Any]] = []

    @staticmethod
    def descendant(base: Path, child: str, label: str) -> Path:
        path = (base / child).resolve()
        if path == base or base not in path.parents:
            raise ValueError(f"{label} resolves outside {base}: {path}")
        return path

    def case_path(self, relative: str, label: str) -> Path:
        return self.descendant(self.root, relative, label)

    def candidate_path(self, relative: Any, label: str) -> Path | None:
        if not isinstance(relative, str) or not relative:
            self.error("invalid_path", f"{label} path must be a non-empty string")
            return None
        try:
            return self.descendant(self.candidate_dir, relative, label)
        except ValueError as exc:
            self.error("path_escape", str(exc))
            return None

    def finding(self, level: str, code: str, message: str, path: Path | None = None) -> None:
        item = {"level": level, "code": code, "message": message}
        if path is not None:
            item["path"] = str(path)
        self.findings.append(item)

    def error(self, code: str, message: str, path: Path | None = None) -> None:
        self.finding("error", code, message, path)

    def warning(self, code: str, message: str, path: Path | None = None) -> None:
        self.finding("warning", code, message, path)

    def json_file(self, path: Path, label: str) -> dict[str, Any] | None:
        try:
            value = load_json(path)
        except FileNotFoundError:
            self.error("missing_file", f"Missing {label}", path)
            return None
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.error("invalid_json", f"Invalid {label}: {exc}", path)
            return None
        self.checked_files.append(
            {"kind": label, "path": str(path), "bytes": path.stat().st_size}
        )
        return value

    def verify_artifact(self, entry: Any, label: str) -> tuple[Path, str] | None:
        if not isinstance(entry, dict):
            self.error("invalid_artifact", f"{label} must contain path and sha256")
            return None
        path = self.candidate_path(entry.get("path"), label)
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not SHA256_PATTERN.fullmatch(expected):
            self.error("missing_digest", f"{label} requires a lowercase SHA-256 digest")
        if path is None:
            return None
        if not path.is_file():
            self.error("missing_artifact", f"Missing {label}", path)
            return None
        actual = sha256_file(path)
        self.checked_files.append(
            {
                "kind": label,
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": actual,
            }
        )
        if isinstance(expected, str) and actual != expected:
            self.error(
                "digest_mismatch",
                f"{label} SHA-256 mismatch: expected {expected}, observed {actual}",
                path,
            )
        return path, actual


def core_case_paths(audit: Audit) -> dict[str, Path]:
    return {
        "brief": audit.case_path("brief.md", "asset brief"),
        "source_manifest": audit.case_path("source-manifest.json", "source manifest"),
        "quality_contract": audit.case_path("quality-contract.json", "quality contract"),
        "toolchain": audit.case_path("toolchain.json", "toolchain"),
    }


def validate_brief(audit: Audit, path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        audit.error("missing_file", "Missing asset brief", path)
        return
    except OSError as exc:
        audit.error("invalid_brief", f"Cannot read asset brief: {exc}", path)
        return
    audit.checked_files.append(
        {"kind": "asset brief", "path": str(path), "bytes": path.stat().st_size}
    )
    placeholders = (
        "Describe what the asset must communicate",
        "Describe silhouette, proportions",
        "List work that is outside this case",
    )
    if any(marker in text for marker in placeholders):
        audit.error("brief_not_frozen", "Asset brief still contains scaffold placeholders", path)
    if len(text.strip()) < 80:
        audit.error("brief_too_short", "Asset brief is too short to freeze scope", path)


def validate_scope_freeze(
    audit: Audit,
    asset_id: str,
    hashes: dict[str, str],
) -> tuple[dict[str, Any] | None, str | None]:
    path = audit.case_path("scope-freeze.json", "scope freeze")
    freeze = audit.json_file(path, "scope freeze")
    if freeze is None:
        return None, None
    if freeze.get("schema") != CORE_SCHEMAS["scope_freeze"]:
        audit.error("invalid_schema", "Unsupported scope freeze schema", path)
    if freeze.get("asset_id") != asset_id:
        audit.error("asset_id_mismatch", "Scope freeze asset_id mismatch", path)
    if freeze.get("status") != "approved":
        audit.error("scope_not_approved", "Scope freeze must have status approved", path)
    for field in ("actor", "reason"):
        if not isinstance(freeze.get(field), str) or not freeze[field].strip():
            audit.error("invalid_scope_authority", f"Scope freeze {field} is empty", path)
    if not valid_timestamp(freeze.get("decided_at")):
        audit.error("invalid_scope_timestamp", "Scope freeze needs a timezone-aware decided_at", path)
    if freeze.get("frozen_case_hashes") != hashes:
        audit.error("scope_hash_mismatch", "Frozen case files changed after scope approval", path)
    return freeze, sha256_file(path)


def validate_source_manifest(
    audit: Audit,
    manifest: dict[str, Any],
    asset_id: str,
    authoring_kind: str,
) -> tuple[str, dict[str, dict[str, Any]]]:
    if manifest.get("schema") != CORE_SCHEMAS["source_manifest"]:
        audit.error("invalid_schema", "Unsupported source manifest schema")
    if manifest.get("asset_id") != asset_id:
        audit.error("asset_id_mismatch", "Source manifest asset_id mismatch")
    if manifest.get("authoring_kind") != authoring_kind:
        audit.error("authoring_kind_mismatch", "Source manifest authoring_kind mismatch")
    claim_mode = manifest.get("claim_mode")
    if claim_mode not in CLAIM_MODES:
        audit.error("invalid_claim_mode", f"Unsupported claim_mode: {claim_mode!r}")
        claim_mode = "independent_creation"

    sources = manifest.get("sources")
    source_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(sources, list):
        audit.error("invalid_sources", "Source manifest sources must be a list")
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            audit.error("invalid_source_entry", f"sources[{index}] must be an object")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            audit.error("invalid_source_id", f"Invalid sources[{index}].id")
            continue
        if source_id in source_by_id:
            audit.error("duplicate_source_id", f"Duplicate source ID: {source_id}")
        source_by_id[source_id] = source
        for key in ("origin", "role", "producer", "locator"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                audit.error("incomplete_source", f"Source {source_id!r} has no {key}")
        role = source.get("role")
        if role in INCLUDED_SOURCE_ROLES:
            digest = source.get("content_sha256")
            if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                audit.error("missing_source_digest", f"Included source {source_id!r} lacks SHA-256")
            if source.get("license_status") != "verified":
                audit.error("unverified_source_license", f"Included source {source_id!r} is not verified")
            if not isinstance(source.get("license_reference"), str) or not source[
                "license_reference"
            ].strip():
                audit.error("missing_license_reference", f"Included source {source_id!r} has no license reference")
            allowed = source.get("allowed_use")
            if not isinstance(allowed, list) or not allowed or not all(
                isinstance(item, str) and item.strip() for item in allowed
            ):
                audit.error("missing_allowed_use", f"Included source {source_id!r} has no allowed_use list")
            unknowns = source.get("unknowns")
            if not isinstance(unknowns, list):
                audit.error("invalid_source_unknowns", f"Source {source_id!r} unknowns must be a list")

    if authoring_kind in {"deterministic-adapter", "external-mesh-intake"}:
        included_meshes = [
            source
            for source in source_by_id.values()
            if source.get("role") == "included_source_mesh"
        ]
        if not included_meshes:
            audit.error("missing_external_mesh_source", f"{authoring_kind} requires an included_source_mesh")
        for source in included_meshes:
            allowed = source.get("allowed_use")
            if isinstance(allowed, list):
                for required in ("modify", "runtime_distribution"):
                    if required not in allowed:
                        audit.error(
                            "insufficient_source_rights",
                            f"Source {source.get('id')!r} does not allow {required}",
                        )

    if claim_mode == "mechanism_transfer" and not source_by_id:
        audit.error("missing_declared_source", "mechanism_transfer requires a source")
    if claim_mode == "original_control":
        originals = [
            source
            for source in source_by_id.values()
            if source.get("role") == "original_baseline"
            and source.get("runnable") is True
            and isinstance(source.get("content_sha256"), str)
            and SHA256_PATTERN.fullmatch(source["content_sha256"])
        ]
        if not originals:
            audit.error("missing_runnable_original", "original_control requires a runnable original_baseline")
    return claim_mode, source_by_id


def validate_toolchain(
    audit: Audit,
    toolchain: dict[str, Any],
    asset_id: str,
    validation_level: str,
    target_engine: str,
) -> None:
    if toolchain.get("schema") != CORE_SCHEMAS["toolchain"]:
        audit.error("invalid_schema", "Unsupported toolchain schema")
    if toolchain.get("asset_id") != asset_id:
        audit.error("asset_id_mismatch", "Toolchain asset_id mismatch")

    def executable_record(record: Any, label: str, required: bool) -> None:
        if not isinstance(record, dict):
            audit.error("invalid_toolchain", f"{label} must be an object")
            return
        path_value = record.get("executable_path")
        discovery = record.get("discovery_rule")
        has_path = isinstance(path_value, str) and bool(path_value.strip())
        has_discovery = isinstance(discovery, str) and bool(discovery.strip())
        if required and not (has_path or has_discovery):
            audit.error("unresolved_executable", f"{label} needs executable_path or discovery_rule")
        if has_path:
            executable = Path(path_value).expanduser()
            if not executable.is_absolute() or not executable.is_file():
                audit.error("invalid_executable", f"{label} executable_path is not an existing absolute file")
            digest = record.get("binary_sha256")
            if digest is not None:
                if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
                    audit.error("invalid_binary_digest", f"{label} binary_sha256 is invalid")
                elif executable.is_file() and sha256_file(executable) != digest:
                    audit.error("binary_digest_mismatch", f"{label} executable hash changed")
        version = record.get("version_output")
        if required and (not isinstance(version, str) or not version.strip()):
            audit.error("unpinned_version", f"{label} version_output is empty")

    executable_record(toolchain.get("blender"), "Blender", True)
    exporter = toolchain.get("gltf_exporter")
    if not isinstance(exporter, dict):
        audit.error("invalid_toolchain", "gltf_exporter must be an object")
    else:
        if not isinstance(exporter.get("version"), str) or not exporter["version"].strip():
            audit.error("unpinned_exporter", "gltf_exporter.version is empty")
        if not isinstance(exporter.get("settings"), dict) or not exporter["settings"]:
            audit.error("unfrozen_exporter", "gltf_exporter.settings is empty")
    renderer = toolchain.get("renderer")
    if not isinstance(renderer, dict):
        audit.error("invalid_toolchain", "renderer must be an object")
    else:
        if not isinstance(renderer.get("engine"), str) or not renderer["engine"].strip():
            audit.error("unpinned_renderer", "renderer.engine is empty")
        if not isinstance(renderer.get("samples"), int) or isinstance(renderer.get("samples"), bool) or renderer[
            "samples"
        ] <= 0:
            audit.error("unfrozen_renderer_samples", "renderer.samples must be positive")
        if not isinstance(renderer.get("color_management"), dict) or not renderer[
            "color_management"
        ]:
            audit.error("unfrozen_color_management", "renderer.color_management is empty")

    comparator = toolchain.get("image_comparator")
    if validation_level in {"reusable", "engine-ready"}:
        if not isinstance(comparator, dict):
            audit.error("missing_image_comparator", "Reusable validation needs image_comparator")
        else:
            for key in ("name", "version_output"):
                if not isinstance(comparator.get(key), str) or not comparator[key].strip():
                    audit.error("missing_image_comparator", f"image_comparator.{key} is empty")

    target = toolchain.get("target_engine")
    if not isinstance(target, dict) or target.get("name") != target_engine:
        audit.error("target_engine_mismatch", "Toolchain target engine does not match contract")
    executable_record(target, "Target engine", validation_level == "engine-ready")

    isolation = toolchain.get("isolation")
    if not isinstance(isolation, dict):
        audit.error("missing_isolation_record", "toolchain.isolation must be an object")
    else:
        if not isinstance(isolation.get("workspace_root"), str) or not isolation[
            "workspace_root"
        ].strip():
            audit.error("missing_isolation_root", "isolation.workspace_root is empty")
        policy = isolation.get("network_policy")
        if policy not in {"disabled", "allowlisted", "unrestricted"}:
            audit.error("invalid_network_policy", "isolation.network_policy is invalid")
        elif policy == "unrestricted":
            audit.warning("unrestricted_network", "Asset build ran with unrestricted network access")


def validate_quality_contract(
    audit: Audit,
    contract: dict[str, Any],
    asset_id: str,
    claim_mode: str,
) -> tuple[str, str, str, list[str], list[dict[str, Any]]]:
    if contract.get("schema") != CORE_SCHEMAS["quality_contract"]:
        audit.error("invalid_schema", "Unsupported quality contract schema")
    if contract.get("asset_id") != asset_id:
        audit.error("asset_id_mismatch", "Quality contract asset_id mismatch")
    authoring_kind = contract.get("authoring_kind")
    validation_level = contract.get("validation_level")
    target_engine = contract.get("target_engine")
    if authoring_kind not in AUTHORING_KINDS:
        audit.error("invalid_authoring_kind", f"Invalid authoring_kind: {authoring_kind!r}")
        authoring_kind = "procedural-generator"
    if validation_level not in VALIDATION_LEVELS:
        audit.error("invalid_validation_level", f"Invalid validation_level: {validation_level!r}")
        validation_level = "prototype"
    if target_engine not in TARGET_ENGINES:
        audit.error("invalid_target_engine", f"Invalid target_engine: {target_engine!r}")
        target_engine = "none"
    if validation_level == "engine-ready" and target_engine == "none":
        audit.error("missing_target_engine", "engine-ready validation cannot target none")

    dimensions = contract.get("quality_dimensions")
    valid_dimensions: list[dict[str, Any]] = []
    if not isinstance(dimensions, list) or not dimensions:
        audit.error("missing_quality_dimensions", "At least one quality dimension is required")
    else:
        keys: set[str] = set()
        for index, dimension in enumerate(dimensions):
            if not isinstance(dimension, dict):
                audit.error("invalid_quality_dimension", f"quality_dimensions[{index}] is not an object")
                continue
            key = dimension.get("key")
            minimum = dimension.get("minimum_score")
            description = dimension.get("description")
            if not isinstance(key, str) or not ID_PATTERN.fullmatch(key):
                audit.error("invalid_quality_dimension", f"quality_dimensions[{index}] has invalid key")
                continue
            if key in keys:
                audit.error("duplicate_quality_dimension", f"Duplicate quality dimension {key!r}")
            keys.add(key)
            if not finite_number(minimum) or not 0 <= float(minimum) <= 1:
                audit.error("invalid_quality_minimum", f"Quality dimension {key!r} minimum is invalid")
            if not isinstance(description, str) or not description.strip():
                audit.error("invalid_quality_dimension", f"Quality dimension {key!r} has no description")
            valid_dimensions.append(dimension)

    budgets = contract.get("budgets")
    for key in ("max_triangles", "max_runtime_meshes", "max_glb_bytes"):
        value = budgets.get(key) if isinstance(budgets, dict) else None
        if not finite_number(value) or float(value) <= 0:
            audit.error("invalid_budget", f"Budget {key!r} must be a positive finite number")

    views = contract.get("review_viewpoints")
    if not isinstance(views, list) or not views:
        audit.error("missing_review_views", "At least one review viewpoint is required")
        views = []
    elif any(not isinstance(view, str) or not ID_PATTERN.fullmatch(view) for view in views):
        audit.error("invalid_review_view", "Every review viewpoint must be a safe ID")
    elif len(set(views)) != len(views):
        audit.error("duplicate_review_view", "Review viewpoints contain duplicates")

    builtins = mandatory_reports(authoring_kind, validation_level, claim_mode)
    declared = contract.get("required_reports")
    if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared):
        audit.error("invalid_required_reports", "required_reports must be a list of strings")
        declared = []
    missing_builtins = [name for name in builtins if name not in declared]
    if missing_builtins:
        audit.error(
            "contract_weakens_builtin_gates",
            f"Contract omits mandatory reports: {missing_builtins}",
        )
    reports = list(dict.fromkeys(builtins + declared))
    policies = contract.get("report_status_policy")
    if not isinstance(policies, dict):
        audit.error("invalid_report_policy", "report_status_policy must be an object")
        policies = {}
    for name in reports:
        if policies.get(name) != ["passed"]:
            audit.error(
                "contract_weakens_status_gate",
                f"Report {name!r} must require exactly ['passed']",
            )
    return authoring_kind, validation_level, target_engine, views, valid_dimensions


def validate_camera_contract(audit: Audit, view: str, value: Any) -> tuple[int, int] | None:
    if not isinstance(value, dict):
        audit.error("unfrozen_camera_view", f"render.views.{view} must be an object")
        return None
    camera_type = value.get("camera_type")
    if camera_type not in {"perspective", "orthographic"}:
        audit.error("invalid_camera_type", f"render.views.{view}.camera_type is invalid")
    if not number_vector(value.get("location_m"), 3):
        audit.error("invalid_camera_transform", f"render.views.{view}.location_m is invalid")
    if not number_vector(value.get("rotation_euler_deg"), 3):
        audit.error("invalid_camera_transform", f"render.views.{view}.rotation_euler_deg is invalid")
    if not number_vector(value.get("target_m"), 3):
        audit.error("invalid_camera_target", f"render.views.{view}.target_m is invalid")
    resolution = value.get("resolution_px")
    if not (
        isinstance(resolution, list)
        and len(resolution) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in resolution)
    ):
        audit.error("invalid_view_resolution", f"render.views.{view}.resolution_px is invalid")
        result = None
    else:
        result = (resolution[0], resolution[1])
    if camera_type == "perspective" and (not finite_number(value.get("lens_mm")) or value["lens_mm"] <= 0):
        audit.error("invalid_camera_lens", f"render.views.{view}.lens_mm is invalid")
    if camera_type == "orthographic" and (
        not finite_number(value.get("ortho_scale")) or value["ortho_scale"] <= 0
    ):
        audit.error("invalid_camera_scale", f"render.views.{view}.ortho_scale is invalid")
    if not isinstance(value.get("renderer"), str) or not value["renderer"].strip():
        audit.error("unfrozen_view_renderer", f"render.views.{view}.renderer is empty")
    if not isinstance(value.get("samples"), int) or isinstance(value.get("samples"), bool) or value[
        "samples"
    ] <= 0:
        audit.error("unfrozen_view_samples", f"render.views.{view}.samples is invalid")
    if not isinstance(value.get("color_management"), dict) or not value["color_management"]:
        audit.error("unfrozen_view_color", f"render.views.{view}.color_management is empty")
    for key in ("visible_groups", "hidden_groups"):
        if not isinstance(value.get(key), list) or not all(
            isinstance(item, str) for item in value[key]
        ):
            audit.error("invalid_view_groups", f"render.views.{view}.{key} is invalid")
    if not isinstance(value.get("state"), str) or not value["state"].strip():
        audit.error("unfrozen_view_state", f"render.views.{view}.state is empty")
    return result


def png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def artifact_map(entries: list[dict[str, Any]], key: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        name = entry.get(key)
        digest = entry.get("sha256")
        if isinstance(name, str) and isinstance(digest, str):
            result[name] = digest
    return result


def validate_bindings_map(
    audit: Audit,
    report_name: str,
    bindings: dict[str, Any],
    field: str,
    expected: dict[str, str],
    exact: bool = True,
) -> None:
    actual = bindings.get(field)
    if not isinstance(actual, dict):
        audit.error("missing_report_binding", f"Report {report_name!r} lacks bindings.{field}")
        return
    if exact and actual != expected:
        audit.error("report_binding_mismatch", f"Report {report_name!r} bindings.{field} mismatch")
        return
    if not exact:
        for key, digest in expected.items():
            if actual.get(key) != digest:
                audit.error(
                    "report_binding_mismatch",
                    f"Report {report_name!r} does not bind {field}.{key}",
                )


def validate_report(
    audit: Audit,
    name: str,
    report: dict[str, Any],
    asset_id: str,
    candidate_id: str,
    scope_freeze_sha: str,
    source_map: dict[str, str],
    input_map: dict[str, str],
    output_map: dict[str, str],
    evidence_map: dict[str, str],
    engine_evidence_map: dict[str, str],
    required_views: list[str],
    dimensions: list[dict[str, Any]],
    target_engine: str,
    toolchain: dict[str, Any],
) -> None:
    expected_schema = REPORT_SCHEMAS.get(name)
    if expected_schema is not None and report.get("schema") != expected_schema:
        audit.error("invalid_report_schema", f"Report {name!r} has unsupported schema")
    if report.get("asset_id") != asset_id:
        audit.error("report_asset_mismatch", f"Report {name!r} asset_id mismatch")
    if report.get("candidate_id") != candidate_id:
        audit.error("report_candidate_mismatch", f"Report {name!r} candidate_id mismatch")
    if report.get("status") != "passed":
        audit.error("report_not_passed", f"Report {name!r} status is not passed")
    failures = report.get("failures")
    if not isinstance(failures, list) or failures:
        audit.error("report_has_failures", f"Report {name!r} failures must be an empty list")
    bindings = report.get("bindings")
    if not isinstance(bindings, dict):
        audit.error("missing_report_bindings", f"Report {name!r} has no bindings object")
        return
    if bindings.get("scope_freeze_sha256") != scope_freeze_sha:
        audit.error("report_scope_mismatch", f"Report {name!r} does not bind the scope freeze")

    runtime = {"runtime_glb": output_map.get("runtime_glb", "")}
    runtime = {key: value for key, value in runtime.items() if value}
    if name == "build_execution":
        validate_bindings_map(audit, name, bindings, "source_files", source_map)
        validate_bindings_map(audit, name, bindings, "input_files", input_map)
        validate_bindings_map(audit, name, bindings, "outputs", output_map)
        execution = report.get("execution")
        if not isinstance(execution, dict):
            audit.error("missing_build_execution", "build_execution.execution is missing")
        else:
            expected = {
                "exit_code": 0,
                "factory_startup": True,
                "background": True,
                "disable_autoexec": True,
            }
            for key, value in expected.items():
                if execution.get(key) != value:
                    audit.error("unsafe_build_execution", f"build_execution.execution.{key} must be {value!r}")
    elif name == "roundtrip":
        validate_bindings_map(audit, name, bindings, "outputs", runtime, exact=False)
        observations = report.get("observations")
        required_true = (
            "independent_process",
            "semantic_inventory_verified",
            "coordinate_frame_verified",
            "axis_marker_verified",
        )
        if not isinstance(observations, dict):
            audit.error("missing_roundtrip_observations", "roundtrip.observations is missing")
        else:
            if observations.get("imported_glb_sha256") != output_map.get("runtime_glb"):
                audit.error("roundtrip_input_mismatch", "Round-trip imported a different GLB")
            for key in required_true:
                if observations.get(key) is not True:
                    audit.error("incomplete_roundtrip", f"roundtrip.observations.{key} must be true")
            if observations.get("export_leaks") != []:
                audit.error("roundtrip_export_leaks", "Round-trip export_leaks must be empty")
            if observations.get("degenerate_faces") != 0:
                audit.error("roundtrip_degenerate_faces", "Round-trip degenerate_faces must be zero")
    elif name == "visual_review":
        validate_bindings_map(audit, name, bindings, "evidence", evidence_map)
        reviewed = report.get("reviewed_views")
        if not isinstance(reviewed, list) or any(view not in reviewed for view in required_views):
            audit.error("views_not_reviewed", "Visual review did not inspect every required view")
        attestation = report.get("inspection_attestation")
        if not isinstance(attestation, dict) or attestation.get("opened_images") is not True:
            audit.error("images_not_inspected", "Visual review lacks opened-images attestation")
        elif not isinstance(attestation.get("reviewer"), str) or not attestation["reviewer"].strip():
            audit.error("missing_reviewer", "Visual review reviewer is empty")
        scores = report.get("quality_scores")
        for dimension in dimensions:
            key = dimension.get("key")
            minimum = dimension.get("minimum_score")
            score = scores.get(key) if isinstance(scores, dict) else None
            if not finite_number(score) or not 0 <= float(score) <= 1:
                audit.error("invalid_quality_score", f"Visual score {key!r} is invalid")
            elif finite_number(minimum) and float(score) < float(minimum):
                audit.error("quality_score_below_minimum", f"Visual score {key!r} is below minimum")
    elif name == "reproducibility":
        validate_bindings_map(audit, name, bindings, "source_files", source_map)
        validate_bindings_map(audit, name, bindings, "outputs", runtime, exact=False)
        observations = report.get("observations")
        if not isinstance(observations, dict):
            audit.error("missing_replay_observations", "reproducibility.observations is missing")
        else:
            run_ids = observations.get("run_ids")
            if not isinstance(run_ids, list) or len(run_ids) != 2 or len(set(run_ids)) != 2:
                audit.error("invalid_replay_runs", "Reproducibility needs two distinct run IDs")
            if observations.get("identical_input_hashes") is not True:
                audit.error("replay_input_drift", "Reproducibility inputs are not identical")
            pixel_pass = observations.get("decoded_evidence_equal") is True or observations.get(
                "decoded_evidence_within_tolerance"
            ) is True
            if not pixel_pass:
                audit.error("replay_pixels_differ", "Decoded evidence comparison did not pass")
            if observations.get("normalized_semantics_equal") is not True:
                audit.error("replay_semantics_differ", "Normalized runtime semantics differ")
    elif name == "controlled_changes":
        validate_bindings_map(audit, name, bindings, "source_files", source_map)
        variants = report.get("variants")
        if not isinstance(variants, list) or len(variants) < 2:
            audit.error("insufficient_controlled_changes", "At least two controlled variants are required")
        else:
            families: set[str] = set()
            for index, variant in enumerate(variants):
                if not isinstance(variant, dict) or variant.get("status") != "passed":
                    audit.error("controlled_change_not_passed", f"Controlled variant {index} did not pass")
                    continue
                family = variant.get("parameter_family")
                if not isinstance(family, str) or not family.strip():
                    audit.error("missing_parameter_family", f"Controlled variant {index} lacks parameter_family")
                elif family in families:
                    audit.error("duplicate_parameter_family", "Controlled probes must use distinct parameter families")
                else:
                    families.add(family)
                allowed = variant.get("allowed_changed_paths")
                actual = variant.get("actual_changed_paths")
                if not isinstance(allowed, list) or not allowed or sorted(allowed) != sorted(actual or []):
                    audit.error("controlled_change_scope_drift", f"Controlled variant {index} changed undeclared paths")
                if not isinstance(variant.get("overrides"), dict) or not variant["overrides"]:
                    audit.error("missing_controlled_override", f"Controlled variant {index} has no overrides")
                for key in (
                    "builder_unchanged",
                    "semantic_inventory_unchanged",
                    "metric_response_observed",
                ):
                    if variant.get(key) is not True:
                        audit.error("controlled_change_failed", f"Controlled variant {index} {key} is not true")
                if variant.get("roundtrip_status") != "passed":
                    audit.error("controlled_change_roundtrip_failed", f"Controlled variant {index} round-trip failed")
    elif name == "input_custody":
        validate_bindings_map(audit, name, bindings, "input_files", input_map)
        observations = report.get("observations")
        if not isinstance(observations, dict):
            audit.error("missing_custody_observations", "input_custody.observations is missing")
        else:
            for key in ("all_hashes_verified", "license_status_verified", "source_ids_matched"):
                if observations.get(key) is not True:
                    audit.error("input_custody_failed", f"input_custody.observations.{key} must be true")
    elif name == "transformation_replay":
        validate_bindings_map(audit, name, bindings, "source_files", source_map)
        validate_bindings_map(audit, name, bindings, "input_files", input_map)
        validate_bindings_map(audit, name, bindings, "outputs", runtime, exact=False)
        observations = report.get("observations")
        if not isinstance(observations, dict):
            audit.error("missing_transform_replay", "transformation_replay.observations is missing")
        else:
            run_ids = observations.get("run_ids")
            if not isinstance(run_ids, list) or len(run_ids) != 2 or len(set(run_ids)) != 2:
                audit.error("invalid_transform_runs", "Transformation replay needs two distinct run IDs")
            for key in ("identical_input_hashes", "normalized_output_equal"):
                if observations.get(key) is not True:
                    audit.error("transformation_replay_failed", f"transformation_replay.{key} must be true")
    elif name == "engine_import":
        validate_bindings_map(audit, name, bindings, "outputs", runtime, exact=False)
        validate_bindings_map(audit, name, bindings, "evidence", engine_evidence_map)
        observations = report.get("observations")
        target = toolchain.get("target_engine")
        if not isinstance(observations, dict):
            audit.error("missing_engine_observations", "engine_import.observations is missing")
        else:
            if observations.get("engine_name") != target_engine:
                audit.error("engine_name_mismatch", "Engine report name does not match contract")
            expected_version = target.get("version_output") if isinstance(target, dict) else None
            if observations.get("engine_version") != expected_version:
                audit.error("engine_version_mismatch", "Engine report version does not match toolchain")
            if observations.get("imported_glb_sha256") != output_map.get("runtime_glb"):
                audit.error("engine_input_mismatch", "Engine imported a different GLB")
            for key in (
                "node_inventory_verified",
                "metadata_verified",
                "anchors_verified",
                "collision_verified",
                "visibility_exercised",
                "coordinate_frame_verified",
                "screenshots_decoded",
            ):
                if observations.get(key) is not True:
                    audit.error("engine_gate_failed", f"engine_import.observations.{key} must be true")
            if not isinstance(observations.get("material_status"), str) or not observations[
                "material_status"
            ].strip():
                audit.error("missing_material_status", "Engine report must state material_status")
    elif name == "blind_review":
        validate_bindings_map(audit, name, bindings, "evidence", evidence_map)
        observations = report.get("observations")
        if not isinstance(observations, dict):
            audit.error("missing_blind_review", "blind_review.observations is missing")
        else:
            if observations.get("independent") is not True or observations.get("identity_isolated") is not True:
                audit.error("blind_review_not_independent", "Blind review independence/isolation failed")
            if observations.get("outcome") not in {"A", "B", "tie", "insufficient_evidence"}:
                audit.error("invalid_blind_outcome", "Blind review outcome is invalid")


def validate_lineage(
    audit: Audit,
    candidate: dict[str, Any],
    asset_id: str,
    scope_freeze_sha: str,
    case_hashes: dict[str, str],
) -> None:
    current = candidate
    current_id = audit.candidate_id
    seen = {current_id}
    while True:
        campaign = current.get("campaign_id")
        round_index = current.get("round_index")
        if not isinstance(campaign, str) or not ID_PATTERN.fullmatch(campaign):
            audit.error("invalid_campaign_id", f"Candidate {current_id!r} has invalid campaign_id")
        if not isinstance(round_index, int) or isinstance(round_index, bool) or not 1 <= round_index <= 3:
            audit.error("invalid_round_index", f"Candidate {current_id!r} round_index must be 1..3")
        parent = current.get("parent")
        if parent is None:
            if round_index != 1:
                audit.error("invalid_root_round", f"Root candidate {current_id!r} must be round 1")
            return
        if not isinstance(parent, str) or not ID_PATTERN.fullmatch(parent):
            audit.error("invalid_parent", f"Candidate {current_id!r} has invalid parent")
            return
        if parent in seen:
            audit.error("lineage_cycle", f"Candidate lineage cycles at {parent!r}")
            return
        seen.add(parent)
        try:
            parent_dir = audit.descendant(audit.candidates_dir, parent, "parent candidate directory")
            record_path = audit.descendant(parent_dir, "candidate.json", "parent candidate record")
        except ValueError as exc:
            audit.error("parent_path_escape", str(exc))
            return
        parent_record = audit.json_file(record_path, "parent candidate")
        if parent_record is None:
            return
        if parent_record.get("schema") != CORE_SCHEMAS["candidate"]:
            audit.error("invalid_parent_schema", f"Parent {parent!r} schema is invalid")
        if parent_record.get("asset_id") != asset_id or parent_record.get("candidate_id") != parent:
            audit.error("parent_identity_mismatch", f"Parent {parent!r} identity mismatch")
        if parent_record.get("status") != "candidate_snapshot":
            audit.error("parent_not_snapshot", f"Parent {parent!r} is not a candidate_snapshot")
        if parent_record.get("frozen_case_hashes") != case_hashes:
            audit.error(
                "parent_scope_mismatch",
                f"Parent {parent!r} does not bind the current frozen case files",
            )
        try:
            seal_path = audit.descendant(
                audit.case_path("seals", "seals directory"),
                f"{parent}.json",
                "parent seal",
            )
        except ValueError as exc:
            audit.error("parent_seal_escape", str(exc))
            return
        seal = audit.json_file(seal_path, "parent seal")
        expected_inventory = expected_seal_inventory(parent_record)
        if seal is None:
            audit.error("invalid_parent_seal", f"Parent {parent!r} has no readable seal")
        else:
            seal_checks = {
                "schema": CORE_SCHEMAS["candidate_seal"],
                "asset_id": asset_id,
                "candidate_id": parent,
                "candidate_record_sha256": sha256_file(record_path),
                "scope_freeze_sha256": scope_freeze_sha,
                "frozen_case_hashes": case_hashes,
                "inventory": expected_inventory,
            }
            for key, expected in seal_checks.items():
                if seal.get(key) != expected:
                    audit.error(
                        "invalid_parent_seal",
                        f"Parent {parent!r} seal {key} mismatch",
                        seal_path,
                    )
            for field in ("actor", "reason"):
                if not isinstance(seal.get(field), str) or not seal[field].strip():
                    audit.error(
                        "invalid_parent_seal",
                        f"Parent {parent!r} seal {field} is empty",
                        seal_path,
                    )
            if not valid_timestamp(seal.get("sealed_at")):
                audit.error(
                    "invalid_parent_seal",
                    f"Parent {parent!r} seal timestamp is invalid",
                    seal_path,
                )

        for index, entry in enumerate(expected_inventory):
            relative = entry.get("path")
            expected_digest = entry.get("sha256")
            if not isinstance(relative, str) or not isinstance(expected_digest, str):
                audit.error(
                    "invalid_parent_inventory",
                    f"Parent {parent!r} inventory item {index} is invalid",
                )
                continue
            try:
                artifact_path = audit.descendant(
                    parent_dir,
                    relative,
                    f"parent {parent} inventory item",
                )
            except ValueError as exc:
                audit.error("parent_inventory_escape", str(exc))
                continue
            if not artifact_path.is_file():
                audit.error(
                    "missing_parent_artifact",
                    f"Parent {parent!r} sealed artifact is missing",
                    artifact_path,
                )
                continue
            observed_digest = sha256_file(artifact_path)
            audit.checked_files.append(
                {
                    "kind": f"parent {parent} sealed inventory",
                    "path": str(artifact_path),
                    "bytes": artifact_path.stat().st_size,
                    "sha256": observed_digest,
                }
            )
            if observed_digest != expected_digest:
                audit.error(
                    "parent_artifact_digest_mismatch",
                    f"Parent {parent!r} sealed artifact changed: {relative}",
                    artifact_path,
                )

        child_campaign = current.get("campaign_id")
        child_round = current.get("round_index")
        parent_campaign = parent_record.get("campaign_id")
        parent_round = parent_record.get("round_index")
        if child_campaign == parent_campaign:
            if not isinstance(child_round, int) or not isinstance(parent_round, int) or child_round != parent_round + 1:
                audit.error("lineage_round_mismatch", f"Candidate {current_id!r} round does not follow parent")
        elif child_round != 1:
            audit.error("campaign_restart_round", f"New campaign candidate {current_id!r} must be round 1")

        rationale = current.get("revision_rationale")
        defect_ids = rationale.get("defect_ids") if isinstance(rationale, dict) else None
        summary = rationale.get("summary") if isinstance(rationale, dict) else None
        if (
            not isinstance(defect_ids, list)
            or not defect_ids
            or any(not isinstance(item, str) or not ID_PATTERN.fullmatch(item) for item in defect_ids)
            or len(set(defect_ids)) != len(defect_ids)
        ):
            audit.error(
                "missing_parent_defects",
                f"Descendant {current_id!r} needs unique, valid parent defect IDs",
            )
        if not isinstance(summary, str) or not summary.strip():
            audit.error(
                "missing_revision_summary",
                f"Descendant {current_id!r} revision rationale is empty",
            )
        known: dict[str, str] = {}
        try:
            defects_dir = audit.descendant(parent_dir, "defects", "parent defects directory")
        except ValueError as exc:
            audit.error("parent_defects_escape", str(exc))
            return
        if defects_dir.is_dir():
            for discovered in sorted(defects_dir.glob("*.json")):
                resolved = discovered.resolve()
                if defects_dir not in resolved.parents:
                    audit.error("parent_defect_escape", f"Parent defect escapes directory: {resolved}")
                    continue
                defect = audit.json_file(resolved, "parent defect")
                if defect is not None:
                    defect_id = defect.get("id")
                    if isinstance(defect_id, str):
                        if defect_id in known:
                            audit.error(
                                "duplicate_parent_defect",
                                f"Parent {parent!r} has duplicate defect ID {defect_id!r}",
                            )
                        else:
                            known[defect_id] = sha256_file(resolved)
                    if defect.get("affected_candidate") != parent:
                        audit.error(
                            "defect_parent_mismatch",
                            f"Defect for parent {parent!r} affects another candidate",
                        )
        safe_defect_ids = [item for item in defect_ids or [] if isinstance(item, str)]
        missing = [item for item in safe_defect_ids if item not in known]
        if missing:
            audit.error(
                "unknown_parent_defects",
                f"Descendant {current_id!r} references unknown parent defects: {missing}",
            )
        bindings = rationale.get("defect_bindings") if isinstance(rationale, dict) else None
        binding_map: dict[str, str] = {}
        if not isinstance(bindings, list):
            audit.error(
                "missing_defect_bindings",
                f"Descendant {current_id!r} does not bind parent defect content",
            )
        else:
            for index, binding in enumerate(bindings):
                if not isinstance(binding, dict):
                    audit.error(
                        "invalid_defect_binding",
                        f"Descendant {current_id!r} defect binding {index} is invalid",
                    )
                    continue
                defect_id = binding.get("id")
                defect_sha = binding.get("sha256")
                if (
                    not isinstance(defect_id, str)
                    or not ID_PATTERN.fullmatch(defect_id)
                    or not isinstance(defect_sha, str)
                    or not SHA256_PATTERN.fullmatch(defect_sha)
                ):
                    audit.error(
                        "invalid_defect_binding",
                        f"Descendant {current_id!r} defect binding {index} is incomplete",
                    )
                    continue
                if defect_id in binding_map:
                    audit.error(
                        "duplicate_defect_binding",
                        f"Descendant {current_id!r} repeats defect binding {defect_id!r}",
                    )
                binding_map[defect_id] = defect_sha
        expected_bindings = {
            defect_id: known[defect_id]
            for defect_id in safe_defect_ids
            if defect_id in known
        }
        if binding_map != expected_bindings:
            audit.error(
                "defect_binding_mismatch",
                f"Descendant {current_id!r} defect bindings do not match parent records",
            )
        if child_campaign != parent_campaign:
            reason = rationale.get("new_campaign_reason") if isinstance(rationale, dict) else None
            if not isinstance(reason, str) or not reason.strip():
                audit.error(
                    "missing_campaign_reason",
                    f"Descendant {current_id!r} starts a new campaign without a reason",
                )

        current = parent_record
        current_id = parent


def expected_seal_inventory(candidate: dict[str, Any]) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    groups = (
        ("source", candidate.get("source_files"), None),
        ("input", candidate.get("input_files"), None),
        ("output", candidate.get("outputs"), "role"),
        ("evidence", candidate.get("evidence"), "view"),
    )
    for base_role, entries, suffix_key in groups:
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            role = base_role
            if suffix_key and isinstance(entry.get(suffix_key), str):
                role = f"{base_role}:{entry[suffix_key]}"
            if isinstance(entry.get("path"), str) and isinstance(entry.get("sha256"), str):
                inventory.append({"role": role, "path": entry["path"], "sha256": entry["sha256"]})
    reports = candidate.get("reports")
    if isinstance(reports, dict):
        for name, entry in reports.items():
            if isinstance(entry, dict) and isinstance(entry.get("path"), str) and isinstance(
                entry.get("sha256"), str
            ):
                inventory.append(
                    {"role": f"report:{name}", "path": entry["path"], "sha256": entry["sha256"]}
                )
    return sorted(inventory, key=lambda item: (item["role"], item["path"], item["sha256"]))


def validate_candidate_seal(
    audit: Audit,
    candidate: dict[str, Any],
    candidate_record_path: Path,
    asset_id: str,
    scope_freeze_sha: str,
    case_hashes: dict[str, str],
    require_seal: bool,
) -> tuple[bool, str | None]:
    seals_dir = audit.case_path("seals", "seals directory")
    seal_path = audit.descendant(seals_dir, f"{audit.candidate_id}.json", "candidate seal")
    if not seal_path.is_file():
        if require_seal:
            audit.error("missing_candidate_seal", "Candidate has no external seal", seal_path)
        return False, None
    seal = audit.json_file(seal_path, "candidate seal")
    if seal is None:
        return False, None
    valid = True
    checks = {
        "schema": CORE_SCHEMAS["candidate_seal"],
        "asset_id": asset_id,
        "candidate_id": audit.candidate_id,
        "candidate_record_sha256": sha256_file(candidate_record_path),
        "scope_freeze_sha256": scope_freeze_sha,
        "frozen_case_hashes": case_hashes,
        "inventory": expected_seal_inventory(candidate),
    }
    for key, expected in checks.items():
        if seal.get(key) != expected:
            audit.error("candidate_seal_mismatch", f"Candidate seal {key} mismatch", seal_path)
            valid = False
    for field in ("actor", "reason"):
        if not isinstance(seal.get(field), str) or not seal[field].strip():
            audit.error("invalid_seal_authority", f"Candidate seal {field} is empty", seal_path)
            valid = False
    if not valid_timestamp(seal.get("sealed_at")):
        audit.error("invalid_seal_timestamp", "Candidate seal needs timezone-aware sealed_at", seal_path)
        valid = False
    return valid, sha256_file(seal_path)


def validate_promotion(
    audit: Audit,
    candidate: dict[str, Any],
    asset_id: str,
    seal_sha: str | None,
) -> tuple[bool, str | None]:
    promotions_dir = audit.case_path("promotions", "promotions directory")
    path = audit.descendant(promotions_dir, f"{audit.candidate_id}.json", "promotion receipt")
    if not path.is_file():
        return False, None
    promotion = audit.json_file(path, "promotion receipt")
    if promotion is None:
        return False, None
    reports = candidate.get("reports")
    report_hashes = {
        name: entry.get("sha256")
        for name, entry in reports.items()
        if isinstance(reports, dict) and isinstance(entry, dict)
    } if isinstance(reports, dict) else {}
    checks = {
        "schema": CORE_SCHEMAS["promotion"],
        "asset_id": asset_id,
        "candidate_id": audit.candidate_id,
        "decision": "approve",
        "candidate_seal_sha256": seal_sha,
        "report_hashes": report_hashes,
    }
    valid = True
    for key, expected in checks.items():
        if promotion.get(key) != expected:
            audit.error("promotion_mismatch", f"Promotion receipt {key} mismatch", path)
            valid = False
    for field in ("human_author", "reason"):
        if not isinstance(promotion.get(field), str) or not promotion[field].strip():
            audit.error("invalid_promotion_authority", f"Promotion {field} is empty", path)
            valid = False
    authority_ref = promotion.get("authority_ref")
    if not valid_authority_ref(authority_ref):
        audit.error(
            "invalid_promotion_authority",
            "Promotion authority_ref must use git:commit:, git:tag:, signature:, or artifact-evolution:",
            path,
        )
        valid = False
    if not valid_timestamp(promotion.get("decided_at")):
        audit.error("invalid_promotion_timestamp", "Promotion needs timezone-aware decided_at", path)
        valid = False
    return valid, authority_ref if isinstance(authority_ref, str) else None


def audit_scope(root: Path) -> dict[str, Any]:
    """Validate root records before an irreversible scope-freeze receipt is created."""
    audit = Audit(root, "scope_preflight")
    paths = core_case_paths(audit)
    validate_brief(audit, paths["brief"])
    contract = audit.json_file(paths["quality_contract"], "quality contract")
    manifest = audit.json_file(paths["source_manifest"], "source manifest")
    toolchain = audit.json_file(paths["toolchain"], "toolchain")
    asset_id: Any = None
    case_hashes = {
        name: sha256_file(path)
        for name, path in paths.items()
        if path.is_file()
    }
    if contract is not None and manifest is not None and toolchain is not None:
        asset_id = contract.get("asset_id")
        if not isinstance(asset_id, str) or not ID_PATTERN.fullmatch(asset_id):
            audit.error("invalid_asset_id", f"Invalid contract asset_id: {asset_id!r}")
            asset_id = "invalid"
        authoring_hint = contract.get("authoring_kind")
        claim_mode, _ = validate_source_manifest(
            audit,
            manifest,
            asset_id,
            authoring_hint if isinstance(authoring_hint, str) else "",
        )
        authoring_kind, validation_level, target_engine, _, _ = validate_quality_contract(
            audit,
            contract,
            asset_id,
            claim_mode,
        )
        if manifest.get("authoring_kind") != authoring_kind:
            audit.error(
                "authoring_kind_mismatch",
                "Source manifest and contract authoring_kind differ",
            )
        validate_toolchain(
            audit,
            toolchain,
            asset_id,
            validation_level,
            target_engine,
        )
    errors = sum(item["level"] == "error" for item in audit.findings)
    warnings = sum(item["level"] == "warning" for item in audit.findings)
    return {
        "schema": "blender_asset_scope_audit/v1",
        "asset_id": asset_id,
        "status": "passed" if errors == 0 else "failed",
        "local_preflight_passed": errors == 0,
        "case_hashes": case_hashes,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "checked_files": len(audit.checked_files),
        },
        "findings": audit.findings,
        "checked_files": audit.checked_files,
    }


def audit_case(
    root: Path,
    candidate_id: str,
    *,
    require_seal: bool = True,
    require_promotion: bool = False,
    trusted_authority_ref: str | None = None,
) -> dict[str, Any]:
    if not ID_PATTERN.fullmatch(candidate_id):
        raise ValueError(f"candidate ID must match {ID_PATTERN.pattern}: {candidate_id!r}")
    audit = Audit(root, candidate_id)
    paths = core_case_paths(audit)
    validate_brief(audit, paths["brief"])
    contract = audit.json_file(paths["quality_contract"], "quality contract")
    manifest = audit.json_file(paths["source_manifest"], "source manifest")
    toolchain = audit.json_file(paths["toolchain"], "toolchain")
    candidate_record_path = audit.candidate_path("candidate.json", "candidate record")
    spec_path = audit.candidate_path("spec.json", "candidate spec")
    if candidate_record_path is None or spec_path is None:
        return finalize(audit, None, None, False, False, False, False)
    candidate = audit.json_file(candidate_record_path, "candidate record")
    spec = audit.json_file(spec_path, "candidate spec")
    if any(item is None for item in (contract, manifest, toolchain, candidate, spec)):
        return finalize(audit, None, None, False, False, False, False)
    assert contract is not None and manifest is not None and toolchain is not None
    assert candidate is not None and spec is not None

    asset_id = contract.get("asset_id")
    if not isinstance(asset_id, str) or not ID_PATTERN.fullmatch(asset_id):
        audit.error("invalid_asset_id", f"Invalid contract asset_id: {asset_id!r}")
        asset_id = "invalid"
    authoring_hint = contract.get("authoring_kind")
    claim_mode, source_by_id = validate_source_manifest(
        audit,
        manifest,
        asset_id,
        authoring_hint if isinstance(authoring_hint, str) else "",
    )
    authoring_kind, validation_level, target_engine, required_views, dimensions = (
        validate_quality_contract(audit, contract, asset_id, claim_mode)
    )
    if manifest.get("authoring_kind") != authoring_kind:
        audit.error("authoring_kind_mismatch", "Source manifest and contract authoring_kind differ")
    validate_toolchain(audit, toolchain, asset_id, validation_level, target_engine)

    case_hashes: dict[str, str] = {}
    for name, path in paths.items():
        if path.is_file():
            case_hashes[name] = sha256_file(path)
    _, scope_freeze_sha = validate_scope_freeze(audit, asset_id, case_hashes)
    if scope_freeze_sha is None:
        scope_freeze_sha = ""

    if candidate.get("schema") != CORE_SCHEMAS["candidate"]:
        audit.error("invalid_schema", "Unsupported candidate schema")
    if spec.get("schema") != CORE_SCHEMAS["spec"]:
        audit.error("invalid_schema", "Unsupported candidate spec schema")
    for label, value in (("candidate", candidate), ("spec", spec)):
        if value.get("asset_id") != asset_id:
            audit.error("asset_id_mismatch", f"{label} asset_id mismatch")
        if value.get("candidate_id") != candidate_id:
            audit.error("candidate_id_mismatch", f"{label} candidate_id mismatch")
    if candidate.get("status") != "candidate_snapshot":
        audit.error("candidate_not_snapshot", "Candidate status must be candidate_snapshot before sealing")
    if candidate.get("frozen_case_hashes") != case_hashes:
        audit.error("candidate_scope_mismatch", "Candidate does not bind the current frozen case files")
    if spec.get("campaign_id") != candidate.get("campaign_id") or spec.get("round_index") != candidate.get(
        "round_index"
    ):
        audit.error("spec_lineage_mismatch", "Spec campaign/round does not match candidate")
    if not isinstance(spec.get("units"), str) or not spec["units"].strip():
        audit.error("missing_units", "Candidate spec must freeze units")
    if not isinstance(spec.get("seed"), int) or isinstance(spec.get("seed"), bool):
        audit.error("missing_seed", "Candidate spec must freeze an integer seed")

    frame = spec.get("coordinate_frame")
    if not isinstance(frame, dict):
        audit.error("missing_coordinate_frame", "Spec coordinate_frame must be an object")
    else:
        for key in (
            "authoring_up",
            "authoring_forward",
            "runtime_up",
            "runtime_forward",
            "origin_policy",
        ):
            if not isinstance(frame.get(key), str) or not frame[key].strip():
                audit.error("unfrozen_coordinate_frame", f"coordinate_frame.{key} is empty")

    semantics = spec.get("semantics")
    if validation_level == "engine-ready":
        if not isinstance(semantics, dict):
            audit.error("missing_runtime_semantics", "Engine-ready spec needs semantics")
        else:
            required_fields = {
                "runtime_groups": ("name", "visibility_group"),
                "anchors": ("name", "semantic_type"),
                "collision": ("name", "semantic_type"),
            }
            for key, fields in required_fields.items():
                values = semantics.get(key)
                if not isinstance(values, list) or not values:
                    audit.error("missing_runtime_semantics", f"semantics.{key} must be non-empty")
                    continue
                names: set[str] = set()
                for index, value in enumerate(values):
                    if not isinstance(value, dict):
                        audit.error("invalid_runtime_semantic", f"semantics.{key}[{index}] is invalid")
                        continue
                    for field in fields:
                        if not isinstance(value.get(field), str) or not value[field].strip():
                            audit.error(
                                "invalid_runtime_semantic",
                                f"semantics.{key}[{index}].{field} is empty",
                            )
                    name = value.get("name")
                    if isinstance(name, str):
                        if name in names:
                            audit.error("duplicate_runtime_semantic", f"Duplicate semantics.{key} name {name!r}")
                        names.add(name)

    render = spec.get("render")
    render_views = render.get("views") if isinstance(render, dict) else None
    camera_resolutions: dict[str, tuple[int, int]] = {}
    if not isinstance(render_views, dict):
        audit.error("missing_camera_contract", "spec.render.views must be an object")
    else:
        for view in required_views:
            resolution = validate_camera_contract(audit, view, render_views.get(view))
            if resolution is not None:
                camera_resolutions[view] = resolution

    validate_lineage(audit, candidate, asset_id, scope_freeze_sha, case_hashes)

    source_entries = candidate.get("source_files")
    verified_sources: list[dict[str, Any]] = []
    source_paths: set[str] = set()
    if not isinstance(source_entries, list) or len(source_entries) < 2:
        audit.error("missing_source_files", "Candidate must bind spec and at least one builder")
        source_entries = []
    for index, entry in enumerate(source_entries):
        if not isinstance(entry, dict):
            audit.error("invalid_source_file", f"source_files[{index}] is invalid")
            continue
        relative = entry.get("path")
        if isinstance(relative, str):
            if relative in source_paths:
                audit.error("duplicate_source_file", f"Duplicate source path {relative!r}")
            source_paths.add(relative)
        if audit.verify_artifact(entry, f"source_files[{index}]") is not None:
            verified_sources.append(entry)
    source_map = artifact_map(verified_sources, "path")
    if "spec.json" not in source_map:
        audit.error("spec_not_bound", "source_files must include spec.json")
    if not any(path.startswith("source/") for path in source_map):
        audit.error("builder_not_bound", "source_files must include a builder under source/")

    input_entries = candidate.get("input_files")
    verified_inputs: list[dict[str, Any]] = []
    input_paths: set[str] = set()
    input_source_ids: set[str] = set()
    if not isinstance(input_entries, list):
        audit.error("invalid_input_files", "candidate.input_files must be a list")
        input_entries = []
    for index, entry in enumerate(input_entries):
        if not isinstance(entry, dict):
            audit.error("invalid_input_file", f"input_files[{index}] is invalid")
            continue
        relative = entry.get("path")
        if isinstance(relative, str):
            if relative in input_paths:
                audit.error("duplicate_input_file", f"Duplicate input path {relative!r}")
            input_paths.add(relative)
        source_id = entry.get("source_id")
        if isinstance(source_id, str):
            if source_id in input_source_ids:
                audit.error("duplicate_input_source", f"Duplicate input source ID {source_id!r}")
            input_source_ids.add(source_id)
        source = source_by_id.get(source_id) if isinstance(source_id, str) else None
        if source is None:
            audit.error("unknown_input_source", f"input_files[{index}] references unknown source")
        elif source.get("content_sha256") != entry.get("sha256"):
            audit.error("input_source_digest_mismatch", f"input_files[{index}] does not match source digest")
        if audit.verify_artifact(entry, f"input_files[{index}]") is not None:
            verified_inputs.append(entry)
    input_map = artifact_map(verified_inputs, "path")
    if authoring_kind in {"deterministic-adapter", "external-mesh-intake"} and not verified_inputs:
        audit.error("missing_external_input", f"{authoring_kind} requires a candidate input file")

    output_entries = candidate.get("outputs")
    verified_outputs: list[dict[str, Any]] = []
    roles: set[str] = set()
    if not isinstance(output_entries, list):
        audit.error("invalid_outputs", "candidate.outputs must be a list")
        output_entries = []
    for index, entry in enumerate(output_entries):
        if not isinstance(entry, dict):
            audit.error("invalid_output", f"outputs[{index}] is invalid")
            continue
        role = entry.get("role")
        if not isinstance(role, str) or not ID_PATTERN.fullmatch(role):
            audit.error("invalid_output_role", f"outputs[{index}] has invalid role")
        elif role in roles:
            audit.error("duplicate_output_role", f"Duplicate output role {role!r}")
        else:
            roles.add(role)
        result = audit.verify_artifact(entry, f"outputs[{index}]")
        if result is not None:
            verified_outputs.append(entry)
    output_map = artifact_map(verified_outputs, "role")
    for required_role, suffix in (("authoring_blend", ".blend"), ("runtime_glb", ".glb")):
        if required_role not in output_map:
            audit.error("missing_output", f"Candidate lacks output role {required_role!r}")
        else:
            matching = [entry for entry in verified_outputs if entry.get("role") == required_role]
            if matching and not str(matching[0].get("path", "")).lower().endswith(suffix):
                audit.error("wrong_output_type", f"Output {required_role!r} must use {suffix}")

    evidence_entries = candidate.get("evidence")
    verified_evidence: list[dict[str, Any]] = []
    evidence_by_view: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence_entries, list):
        audit.error("invalid_evidence", "candidate.evidence must be a list")
        evidence_entries = []
    for index, entry in enumerate(evidence_entries):
        if not isinstance(entry, dict):
            audit.error("invalid_evidence", f"evidence[{index}] is invalid")
            continue
        view = entry.get("view")
        stage = entry.get("stage")
        if not isinstance(view, str) or not ID_PATTERN.fullmatch(view):
            audit.error("invalid_evidence_view", f"evidence[{index}] has invalid view")
        elif view in evidence_by_view:
            audit.error("duplicate_evidence_view", f"Duplicate evidence view {view!r}")
        else:
            evidence_by_view[view] = entry
        if stage not in {"authoring", "engine"}:
            audit.error("invalid_evidence_stage", f"evidence[{index}] stage must be authoring or engine")
        result = audit.verify_artifact(entry, f"evidence[{index}]")
        if result is None:
            continue
        path, _ = result
        if entry.get("media_type") != "image/png":
            audit.error("unsupported_evidence_media", "Portable evidence must be image/png", path)
        observed_size = png_dimensions(path)
        if observed_size is None:
            audit.error("undecodable_evidence", "Evidence is not a decodable PNG", path)
        else:
            if entry.get("width") != observed_size[0] or entry.get("height") != observed_size[1]:
                audit.error("evidence_size_mismatch", "Evidence dimensions do not match file", path)
            if isinstance(view, str) and view in camera_resolutions and camera_resolutions[view] != observed_size:
                audit.error("camera_evidence_size_mismatch", f"Evidence {view!r} does not match camera contract", path)
        verified_evidence.append(entry)
    for view in required_views:
        if view not in evidence_by_view:
            audit.error("missing_view", f"Missing required evidence view {view!r}")
    engine_evidence = [entry for entry in verified_evidence if entry.get("stage") == "engine"]
    if validation_level == "engine-ready" and not engine_evidence:
        audit.error("missing_engine_evidence", "Engine-ready candidate needs engine-native screenshots")
    evidence_map = artifact_map(verified_evidence, "view")
    engine_evidence_map = artifact_map(engine_evidence, "view")

    report_entries = candidate.get("reports")
    if not isinstance(report_entries, dict):
        audit.error("invalid_reports", "candidate.reports must be an object")
        report_entries = {}
    builtins = mandatory_reports(authoring_kind, validation_level, claim_mode)
    declared = contract.get("required_reports")
    report_names = list(dict.fromkeys(builtins + (declared if isinstance(declared, list) else [])))
    loaded_reports: dict[str, dict[str, Any]] = {}
    verified_report_entries: dict[str, dict[str, Any]] = {}
    for name in report_names:
        entry = report_entries.get(name)
        if entry is None:
            audit.error("missing_report", f"Missing required report {name!r}")
            continue
        result = audit.verify_artifact(entry, f"report[{name}]")
        if result is None:
            continue
        path, _ = result
        report = audit.json_file(path, f"{name} report")
        if report is None:
            continue
        verified_report_entries[name] = entry
        loaded_reports[name] = report
        validate_report(
            audit,
            name,
            report,
            asset_id,
            candidate_id,
            scope_freeze_sha,
            source_map,
            input_map,
            output_map,
            evidence_map,
            engine_evidence_map,
            required_views,
            dimensions,
            target_engine,
            toolchain,
        )

    build = loaded_reports.get("build_execution")
    budgets = contract.get("budgets")
    observations = build.get("observations") if isinstance(build, dict) else None
    if isinstance(observations, dict) and isinstance(budgets, dict):
        metric_keys = {
            "max_triangles": "triangles",
            "max_runtime_meshes": "runtime_meshes",
            "max_glb_bytes": "glb_bytes",
        }
        for budget_key, metric_key in metric_keys.items():
            observed = observations.get(metric_key)
            limit = budgets.get(budget_key)
            if not finite_number(observed):
                audit.error("missing_budget_metric", f"build_execution lacks {metric_key}")
            elif finite_number(limit) and float(observed) > float(limit):
                audit.error("budget_exceeded", f"{metric_key}={observed} exceeds {limit}")

    review_contract = contract.get("review")
    visual = loaded_reports.get("visual_review")
    if isinstance(review_contract, dict) and review_contract.get("require_independent") is True:
        if not isinstance(visual, dict) or visual.get("independent") is not True:
            audit.error("review_not_independent", "Quality contract requires independent visual review")

    sealed, seal_sha = validate_candidate_seal(
        audit,
        candidate,
        candidate_record_path,
        asset_id,
        scope_freeze_sha,
        case_hashes,
        require_seal,
    )
    if sealed:
        promotion_receipt_valid, receipt_authority_ref = validate_promotion(
            audit,
            candidate,
            asset_id,
            seal_sha,
        )
    else:
        promotion_receipt_valid, receipt_authority_ref = False, None
    if trusted_authority_ref is not None and not valid_authority_ref(trusted_authority_ref):
        audit.error(
            "invalid_trusted_authority_ref",
            "Trusted authority must use git:commit:, git:tag:, signature:, or artifact-evolution:",
        )
    authority_verified = (
        promotion_receipt_valid
        and valid_authority_ref(trusted_authority_ref)
        and trusted_authority_ref == receipt_authority_ref
    )
    if trusted_authority_ref is not None and trusted_authority_ref != receipt_authority_ref:
        audit.error(
            "promotion_authority_mismatch",
            "Trusted caller authority does not match the promotion receipt",
        )
    if require_promotion:
        if not promotion_receipt_valid:
            audit.error("promotion_required", "No valid human promotion receipt exists")
        elif trusted_authority_ref is None:
            audit.error(
                "trusted_authority_required",
                "Promotion requires --trusted-authority-ref from an external trust boundary",
            )

    return finalize(
        audit,
        asset_id,
        candidate.get("status"),
        sealed,
        promotion_receipt_valid,
        authority_verified,
        require_seal,
    )


def finalize(
    audit: Audit,
    asset_id: Any,
    candidate_status: Any,
    sealed: bool,
    promotion_receipt_valid: bool,
    authority_verified: bool,
    seal_required: bool,
) -> dict[str, Any]:
    errors = sum(item["level"] == "error" for item in audit.findings)
    warnings = sum(item["level"] == "warning" for item in audit.findings)
    local_pass = errors == 0
    return {
        "schema": "blender_asset_case_audit/v2",
        "asset_id": asset_id,
        "candidate_id": audit.candidate_id,
        "candidate_status": candidate_status,
        "status": "passed" if local_pass else "failed",
        "local_preflight_passed": local_pass,
        "sealed_candidate": sealed and local_pass,
        "promotion_eligible": sealed and local_pass,
        "promotion_receipt_valid": promotion_receipt_valid,
        "authority_verified": authority_verified,
        "promoted": authority_verified and local_pass,
        "authority_boundary": (
            "Promotion is trusted only when its authority_ref resolves to Git, a signature, "
            "or the native append-only Artifact Evolution workflow."
        ),
        "mode": "sealed" if seal_required else "pre-seal",
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "checked_files": len(audit.checked_files),
        },
        "findings": audit.findings,
        "checked_files": audit.checked_files,
    }


def main() -> None:
    args = parse_args()
    try:
        report = audit_case(
            args.root,
            args.candidate_id,
            require_seal=not args.pre_seal,
            require_promotion=args.require_promotion,
            trusted_authority_ref=args.trusted_authority_ref,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "schema": "blender_asset_case_audit/v2",
            "candidate_id": args.candidate_id,
            "status": "failed",
            "local_preflight_passed": False,
            "sealed_candidate": False,
            "promotion_eligible": False,
            "promotion_receipt_valid": False,
            "authority_verified": False,
            "promoted": False,
            "summary": {"errors": 1, "warnings": 0, "checked_files": 0},
            "findings": [
                {"level": "error", "code": "audit_exception", "message": str(exc)}
            ],
            "checked_files": [],
        }

    output = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.out is not None:
        out = args.out.resolve()
        try:
            with out.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(output)
        except FileExistsError as exc:
            print(f"[ERROR] Refusing to overwrite report: {out}", file=sys.stderr)
            raise SystemExit(2) from exc
    print(output, end="")
    raise SystemExit(0 if report["local_preflight_passed"] else 1)


if __name__ == "__main__":
    main()
