import ast
import csv
import json
import os
import re
from collections import OrderedDict


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_ID_PATH = os.path.join(ROOT, "data_id.json")
FIGURE_ID_PATH = os.path.join(ROOT, "figure_id.json")
SCRIPT_ID_PATH = os.path.join(ROOT, "script_id.json")
REGISTRY_JSON_OUT = os.path.join(ROOT, "figure_registry.json")
REGISTRY_CSV_OUT = os.path.join(ROOT, "figure_registry.csv")

SCRIPT_ROOTS = [
    os.path.join(ROOT, "Scripts", "Python"),
    os.path.join(ROOT, "Scripts", "MATLAB"),
]
FIGURE_ROOTS = [
    os.path.join(ROOT, "Figures_Main"),
    os.path.join(ROOT, "Figures_SI"),
]


def load_json_with_preamble(path):
    """Load JSON files that may have notes before the first object."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(text[start:])


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_mapping(mapping):
    return OrderedDict(
        (key, value)
        for key, value in mapping.items()
        if not key.startswith("_comment")
    )


def figure_sort_key(figure):
    if not figure:
        return (2, 9999, "")

    match = re.match(r"Figure(S?)(\d+)(.*)", figure)
    if not match:
        return (2, 9999, figure)

    is_si, number, tail = match.groups()
    return (1 if is_si else 0, int(number), tail)


def relpath(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def build_dir_index(roots):
    index = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                index.setdefault(name, path)
                index.setdefault(name.lower(), path)
    return index


def find_script(script_id, script_dir_index, script_path_by_stable_id):
    if not script_id:
        return ""

    script_dir = script_dir_index.get(script_id) or script_dir_index.get(script_id.lower())
    if not script_dir:
        return script_path_by_stable_id.get(script_id, "")

    candidates = [
        os.path.join(script_dir, "make_plot.py"),
        os.path.join(script_dir, "make_plot.m"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return relpath(candidate)
    return relpath(script_dir)


def find_figure_path(figure_id, figure_dir_index):
    if not figure_id:
        return ""
    figure_dir = figure_dir_index.get(figure_id) or figure_dir_index.get(figure_id.lower())
    return relpath(figure_dir) if figure_dir else ""


def literal_or_marker(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        values = []
        for element in node.elts:
            if isinstance(element, ast.Constant):
                values.append(element.value)
            else:
                return "<non-literal>"
        return values
    return "<non-literal>"


def extract_python_metadata(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=path)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "FIGURE_METADATA" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            return {}

        metadata = {}
        for key_node, value_node in zip(node.value.keys, node.value.values):
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                metadata[key_node.value] = literal_or_marker(value_node)
        return metadata
    return {}


def parse_matlab_string_assignment(source, field):
    match = re.search(rf"m\.{field}\s*=\s*\"([^\"]*)\"", source)
    return match.group(1) if match else ""


def parse_matlab_vector_assignment(source, field):
    match = re.search(rf"m\.{field}\s*=\s*\[(.*?)\]", source, re.S)
    if not match:
        single = parse_matlab_string_assignment(source, field)
        return single if single else []
    values = re.findall(r"\"([^\"]*)\"", match.group(1))
    return values


def extract_matlab_metadata(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    return {
        "stable_id": parse_matlab_string_assignment(source, "stable_id"),
        "data_keys": parse_matlab_vector_assignment(source, "data_keys"),
        "figure_type": parse_matlab_string_assignment(source, "figure_type"),
    }


def extract_metadata(path):
    if path.endswith(".py"):
        return extract_python_metadata(path)
    if path.endswith(".m"):
        return extract_matlab_metadata(path)
    return {}


def build_script_metadata():
    metadata_by_script_path = {}
    script_path_by_stable_id = {}
    for root in SCRIPT_ROOTS:
        if not os.path.isdir(root):
            continue
        for folder, _, files in os.walk(root):
            if "make_plot.py" in files:
                path = os.path.join(folder, "make_plot.py")
            elif "make_plot.m" in files:
                path = os.path.join(folder, "make_plot.m")
            else:
                continue

            try:
                metadata = extract_metadata(path)
            except Exception as exc:
                print(f"[WARN] Could not read metadata from {relpath(path)}: {exc}")
                metadata = {}
            relative_path = relpath(path)
            metadata_by_script_path[relative_path] = metadata
            stable_id = metadata.get("stable_id")
            if stable_id:
                script_path_by_stable_id[stable_id] = relative_path
    return metadata_by_script_path, script_path_by_stable_id


def resolve_data_paths(data_keys, data_id):
    if data_keys in ("", None):
        return ""
    if isinstance(data_keys, str):
        return data_id.get(data_keys, data_keys)
    if isinstance(data_keys, list):
        return [data_id.get(key, key) for key in data_keys]
    return str(data_keys)


def csv_value(value):
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return value


def build_registry():
    data_id = load_json_with_preamble(DATA_ID_PATH)
    figure_id = clean_mapping(load_json_with_preamble(FIGURE_ID_PATH))
    script_id = clean_mapping(load_json_with_preamble(SCRIPT_ID_PATH))

    figure_dir_index = build_dir_index(FIGURE_ROOTS)
    script_dir_index = build_dir_index(SCRIPT_ROOTS)
    script_metadata, script_path_by_stable_id = build_script_metadata()

    rows = []
    for figure in sorted(figure_id.keys(), key=figure_sort_key):
        figure_ids = as_list(figure_id.get(figure))
        script_ids = as_list(script_id.get(figure))
        count = max(len(figure_ids), len(script_ids), 1)

        for idx in range(count):
            current_figure_id = figure_ids[idx] if idx < len(figure_ids) else figure_ids[-1]
            current_script_id = script_ids[idx] if idx < len(script_ids) else script_ids[-1]

            script_path = find_script(current_script_id, script_dir_index, script_path_by_stable_id)
            metadata = script_metadata.get(script_path, {})
            metadata_stable_id = metadata.get("stable_id", "")
            figure_path = (
                find_figure_path(current_figure_id, figure_dir_index)
                or find_figure_path(metadata_stable_id, figure_dir_index)
            )
            data_keys = metadata.get("data_keys", "")
            data_paths = resolve_data_paths(data_keys, data_id)

            rows.append(
                {
                    "Figure": figure,
                    "figure_id": current_figure_id,
                    "figure_path": figure_path,
                    "script_id": current_script_id,
                    "script_path": script_path,
                    "data_keys": data_keys,
                    "data_path": data_paths,
                    "figure_type": metadata.get("figure_type", "SI" if figure.startswith("FigureS") else "Main"),
                }
            )

    return rows


def write_registry_json(rows):
    registry = OrderedDict()
    for row in rows:
        figure = row["Figure"]
        entry = {
            "figure_id": row["figure_id"],
            "figure_path": row["figure_path"],
            "script_id": row["script_id"],
            "script_path": row["script_path"],
            "data_keys": row["data_keys"],
            "data_path": row["data_path"],
            "figure_type": row["figure_type"],
        }
        registry.setdefault(figure, []).append(entry)

    for figure, entries in list(registry.items()):
        if len(entries) == 1:
            registry[figure] = entries[0]

    with open(REGISTRY_JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def write_registry_csv(rows):
    with open(REGISTRY_CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Figure", "Figure path", "script path", "data path"])
        for row in rows:
            writer.writerow(
                [
                    row["Figure"],
                    row["figure_path"],
                    row["script_path"],
                    csv_value(row["data_path"]),
                ]
            )


def main():
    rows = build_registry()
    write_registry_json(rows)
    write_registry_csv(rows)

    print(f"[DONE] Updated {relpath(REGISTRY_JSON_OUT)}")
    print(f"[DONE] Updated {relpath(REGISTRY_CSV_OUT)}")
    print(f"[INFO] Registry rows: {len(rows)}")


if __name__ == "__main__":
    main()
