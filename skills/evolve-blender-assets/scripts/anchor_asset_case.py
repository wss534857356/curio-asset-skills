#!/usr/bin/env python3
"""Create immutable-by-convention scope, seal, and promotion receipts.

These receipts are deliberately stored outside candidate directories and are
created with exclusive writes.  A portable filesystem cannot provide a trust
root by itself, so promotion also requires an authority reference that resolves
to Git, a signature, or the native append-only Artifact Evolution workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validate_asset_case as validator


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
CORE_FILES = {
    "brief": "brief.md",
    "source_manifest": "source-manifest.json",
    "quality_contract": "quality-contract.json",
    "toolchain": "toolchain.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze asset scope, seal a validated candidate, or record human promotion.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze = subparsers.add_parser(
        "freeze-scope",
        help="Hash and approve the completed case contract before building candidates",
    )
    add_common_case_args(freeze, candidate=False)
    freeze.add_argument("--authority-ref", help="Optional external approval reference")

    seal = subparsers.add_parser(
        "seal",
        help="Preflight a candidate and create a separate content-bound seal",
    )
    add_common_case_args(seal, candidate=True)
    seal.add_argument("--authority-ref", help="Optional external sealing reference")

    promote = subparsers.add_parser(
        "promote",
        help="Record an externally anchored human promotion decision",
    )
    add_common_case_args(promote, candidate=True)
    promote.add_argument(
        "--authority-ref",
        required=True,
        help="Git commit/tag, signature, or native append-only workflow receipt",
    )
    return parser.parse_args()


def add_common_case_args(parser: argparse.ArgumentParser, *, candidate: bool) -> None:
    parser.add_argument("--root", required=True, type=Path, help="Case directory")
    if candidate:
        parser.add_argument("--candidate-id", required=True, help="Candidate identifier")
    parser.add_argument("--actor", required=True, help="Person or service creating the receipt")
    parser.add_argument("--reason", required=True, help="Non-empty decision rationale")


def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(2)


def strict_load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=validator.reject_json_constant,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        fail(f"Cannot read {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"Expected a JSON object: {path}")
    return value


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def safe_descendant(base: Path, *parts: str) -> Path:
    path = base.joinpath(*parts).resolve()
    if path == base or base not in path.parents:
        fail(f"Path resolves outside case root: {path}")
    return path


def validate_id(value: str, label: str) -> None:
    if not ID_PATTERN.fullmatch(value):
        fail(f"{label} must match {ID_PATTERN.pattern}: {value!r}")


def validate_text(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        fail(f"{label} cannot be empty")
    return cleaned


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        fail(f"Refusing to overwrite existing receipt: {path}")
    print(path)


def resolve_root(raw: Path) -> Path:
    root = raw.resolve()
    if not root.is_dir():
        fail(f"Case root does not exist: {root}")
    return root


def freeze_scope(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    scope_report = validator.audit_scope(root)
    if not scope_report.get("local_preflight_passed"):
        errors = [
            item.get("message", item.get("code", "unknown error"))
            for item in scope_report.get("findings", [])
            if item.get("level") == "error"
        ]
        fail("Scope preflight failed: " + "; ".join(errors[:8]))
    asset_id = scope_report.get("asset_id")
    if not isinstance(asset_id, str):
        fail("Scope preflight returned no asset_id")
    validate_id(asset_id, "asset ID")
    hashes = scope_report.get("case_hashes")
    if not isinstance(hashes, dict) or set(hashes) != set(CORE_FILES):
        fail("Scope preflight did not hash every core record")
    receipt: dict[str, Any] = {
        "schema": validator.CORE_SCHEMAS["scope_freeze"],
        "asset_id": asset_id,
        "status": "approved",
        "actor": validate_text(args.actor, "actor"),
        "reason": validate_text(args.reason, "reason"),
        "decided_at": timestamp(),
        "frozen_case_hashes": hashes,
    }
    if args.authority_ref:
        receipt["authority_ref"] = validate_text(args.authority_ref, "authority_ref")
    write_exclusive(safe_descendant(root, "scope-freeze.json"), receipt)


def load_candidate(root: Path, candidate_id: str) -> tuple[dict[str, Any], Path]:
    validate_id(candidate_id, "candidate ID")
    path = safe_descendant(root, "candidates", candidate_id, "candidate.json")
    candidate = strict_load(path)
    if candidate.get("schema") != validator.CORE_SCHEMAS["candidate"]:
        fail(f"Unsupported candidate schema: {candidate.get('schema')!r}")
    if candidate.get("candidate_id") != candidate_id:
        fail("Candidate record ID does not match the requested candidate")
    return candidate, path


def seal_candidate(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    candidate_id = args.candidate_id
    candidate, candidate_path = load_candidate(root, candidate_id)
    report = validator.audit_case(root, candidate_id, require_seal=False)
    if not report.get("local_preflight_passed"):
        errors = [
            item.get("message", item.get("code", "unknown error"))
            for item in report.get("findings", [])
            if item.get("level") == "error"
        ]
        fail("Candidate preflight failed: " + "; ".join(errors[:8]))
    freeze_path = safe_descendant(root, "scope-freeze.json")
    freeze = strict_load(freeze_path)
    receipt: dict[str, Any] = {
        "schema": validator.CORE_SCHEMAS["candidate_seal"],
        "asset_id": report["asset_id"],
        "candidate_id": candidate_id,
        "candidate_record_sha256": digest(candidate_path),
        "scope_freeze_sha256": digest(freeze_path),
        "frozen_case_hashes": freeze["frozen_case_hashes"],
        "inventory": validator.expected_seal_inventory(candidate),
        "actor": validate_text(args.actor, "actor"),
        "reason": validate_text(args.reason, "reason"),
        "sealed_at": timestamp(),
    }
    if args.authority_ref:
        receipt["authority_ref"] = validate_text(args.authority_ref, "authority_ref")
    write_exclusive(safe_descendant(root, "seals", f"{candidate_id}.json"), receipt)


def promote_candidate(args: argparse.Namespace) -> None:
    root = resolve_root(args.root)
    candidate_id = args.candidate_id
    candidate, _ = load_candidate(root, candidate_id)
    report = validator.audit_case(root, candidate_id, require_seal=True)
    if not report.get("promotion_eligible"):
        errors = [
            item.get("message", item.get("code", "unknown error"))
            for item in report.get("findings", [])
            if item.get("level") == "error"
        ]
        fail("Candidate is not promotion-eligible: " + "; ".join(errors[:8]))
    seal_path = safe_descendant(root, "seals", f"{candidate_id}.json")
    reports = candidate.get("reports")
    if not isinstance(reports, dict):
        fail("Candidate reports must be an object")
    report_hashes = {
        name: entry["sha256"]
        for name, entry in reports.items()
        if isinstance(entry, dict) and isinstance(entry.get("sha256"), str)
    }
    if len(report_hashes) != len(reports):
        fail("Every candidate report needs a SHA-256 digest")
    authority_ref = validate_text(args.authority_ref, "authority_ref")
    if not validator.valid_authority_ref(authority_ref):
        fail(
            "authority_ref must use git:commit:, git:tag:, signature:, "
            "or artifact-evolution:"
        )
    receipt = {
        "schema": validator.CORE_SCHEMAS["promotion"],
        "asset_id": report["asset_id"],
        "candidate_id": candidate_id,
        "decision": "approve",
        "human_author": validate_text(args.actor, "human author"),
        "reason": validate_text(args.reason, "reason"),
        "authority_ref": authority_ref,
        "candidate_seal_sha256": digest(seal_path),
        "report_hashes": report_hashes,
        "decided_at": timestamp(),
    }
    write_exclusive(safe_descendant(root, "promotions", f"{candidate_id}.json"), receipt)


def main() -> None:
    args = parse_args()
    try:
        if args.command == "freeze-scope":
            freeze_scope(args)
        elif args.command == "seal":
            seal_candidate(args)
        elif args.command == "promote":
            promote_candidate(args)
        else:
            fail(f"Unsupported command: {args.command}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
