"""Read-only GLB metadata audit. It does not decode or validate vertex/UV contents."""

import argparse
import json
import struct
from pathlib import Path


def read_document(path):
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError("Truncated GLB header")
        magic, version, declared = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2 or declared != size:
            raise ValueError("Expected a complete glTF 2 GLB")
        document = None
        while stream.tell() < size:
            chunk = stream.read(8)
            if len(chunk) != 8:
                raise ValueError("Truncated chunk header")
            length, kind = struct.unpack("<II", chunk)
            if length % 4 or length > size - stream.tell():
                raise ValueError("Invalid chunk extent or alignment")
            if kind == 0x4E4F534A:
                if document is not None or stream.tell() != 20:
                    raise ValueError("Expected one initial JSON chunk")
                document = json.loads(stream.read(length).decode("utf-8"))
            else:
                stream.seek(length, 1)
        if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
            raise ValueError("Missing glTF 2 document")
    return document, size


def audit(path, max_triangles=None, required_nodes=(), require_uv=False):
    doc, size = read_document(path)
    accessors, meshes, nodes = (doc.get(key, []) for key in ("accessors", "meshes", "nodes"))

    def accessor(index):
        if type(index) is not int or not 0 <= index < len(accessors):
            raise ValueError("Invalid accessor reference")
        value = accessors[index]
        if type(value.get("count")) is not int or value["count"] <= 0:
            raise ValueError("Missing or invalid accessor count")
        return value

    records, mesh_counts, failures = [], [], []
    for mesh_id, mesh in enumerate(meshes):
        total = 0
        for primitive_id, primitive in enumerate(mesh.get("primitives", [])):
            attributes = primitive.get("attributes", {})
            position = accessor(attributes.get("POSITION"))
            if position.get("type") != "VEC3":
                raise ValueError("POSITION must use VEC3")
            count = accessor(primitive["indices"])["count"] if "indices" in primitive else position["count"]
            mode = primitive.get("mode", 4)
            if mode == 4 and count % 3 == 0:
                triangles = count // 3
            elif mode in (5, 6) and count >= 3:
                triangles = count - 2
            else:
                raise ValueError(f"Unknown triangle count for primitive mode {mode}, count {count}")
            uv_index = attributes.get("TEXCOORD_0")
            uv = accessor(uv_index) if uv_index is not None else None
            uv_present = bool(uv and uv.get("type") == "VEC2" and uv["count"] == position["count"])
            if require_uv and not uv_present:
                failures.append(f"mesh {mesh_id} primitive {primitive_id}: missing/mismatched TEXCOORD_0")
            total += triangles
            records.append({"mesh": mesh_id, "primitive": primitive_id, "triangles": triangles,
                            "vertices": position["count"], "uv0_metadata_valid": uv_present})
        mesh_counts.append(total)

    instances = 0
    for node in nodes:
        if "mesh" not in node:
            continue
        mesh_id = node["mesh"]
        if type(mesh_id) is not int or not 0 <= mesh_id < len(mesh_counts):
            raise ValueError("Invalid node mesh reference")
        multiplier = 1
        gpu = node.get("extensions", {}).get("EXT_mesh_gpu_instancing")
        if gpu is not None:
            counts = {accessor(index)["count"] for index in gpu.get("attributes", {}).values()}
            if len(counts) != 1:
                raise ValueError("Unknown or inconsistent GPU instance count")
            multiplier = counts.pop()
        instances += mesh_counts[mesh_id] * multiplier
    stored = sum(mesh_counts)
    upper_bound = max(stored, instances)
    names = [node.get("name") for node in nodes if node.get("name")]
    if not stored:
        failures.append("No triangle geometry")
    for name in required_nodes:
        if names.count(name) != 1:
            failures.append(f"Expected one node named {name!r}, found {names.count(name)}")
    if max_triangles is not None and upper_bound > max_triangles:
        failures.append(f"Triangle upper bound {upper_bound} exceeds {max_triangles}")
    return {
        "path": str(path.resolve()), "bytes": size, "triangles_stored": stored,
        "triangles_all_node_instances": instances, "triangle_budget_upper_bound": upper_bound,
        "node_names": names, "mesh_count": len(meshes), "material_count": len(doc.get("materials", [])),
        "primitives": records, "failures": failures,
        "scope": "Metadata only; includes all node instances, even inactive scenes. Does not validate vertex data, UV layout, pivot correctness, or rendering."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--max-triangles", type=int)
    parser.add_argument("--require-node", action="append", default=[])
    parser.add_argument("--require-uv", action="store_true")
    args = parser.parse_args()
    if args.max_triangles is not None and args.max_triangles < 1:
        parser.error("--max-triangles must be positive")
    try:
        report = audit(args.file, args.max_triangles, args.require_node, args.require_uv)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(json.dumps({"status": "unknown", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
