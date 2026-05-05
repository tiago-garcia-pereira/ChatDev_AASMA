"""Input/output helpers shared by debugger workflow scripts."""

import json
import os
import re
from pathlib import Path
from typing import Any


def load_node_inputs() -> list[dict[str, Any]]:
    payload = os.getenv("CHATDEV_NODE_INPUTS", "[]")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def input_texts() -> list[str]:
    texts: list[str] = []
    for message in load_node_inputs():
        content = message.get("content", "")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(str(block.get("text") or block.get("data") or ""))
            texts.append("\n".join(part for part in parts if part))
    return texts


def combined_input_text() -> str:
    chunks = []
    for message in load_node_inputs():
        source = (message.get("metadata") or {}).get("source", "unknown")
        content = message.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        chunks.append(f"=== INPUT FROM {source} ===\n{content}")
    return "\n\n".join(chunks)


def attachment_refs() -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for message in load_node_inputs():
        content = message.get("content", "")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            attachment = block.get("attachment")
            if isinstance(attachment, dict):
                refs.append(attachment)
    return refs


def uploaded_python_files() -> list[Path]:
    paths: list[Path] = []
    for attachment in attachment_refs():
        name = str(attachment.get("name") or "")
        local_path = attachment.get("local_path")
        if not local_path:
            continue
        path = Path(str(local_path)).expanduser().resolve()
        if path.exists() and (path.suffix == ".py" or name.endswith(".py")):
            paths.append(path)
    return paths


def extract_json_objects(text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates.append(text.strip())
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
        elif isinstance(parsed, list):
            objects.extend(item for item in parsed if isinstance(item, dict))
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\{\[]", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            objects.append(parsed)
        elif isinstance(parsed, list):
            objects.extend(item for item in parsed if isinstance(item, dict))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for obj in objects:
        key = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append(obj)
    return unique


def find_project_path(text: str) -> Path:
    explicit = os.getenv("DEBUG_TARGET_PROJECT_PATH") or os.getenv("PROJECT_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()

    for obj in extract_json_objects(text):
        value = obj.get("project_path") or obj.get("path_project")
        if isinstance(value, str) and value.strip():
            return Path(value.strip()).expanduser().resolve()

    match = re.search(r"(?:project_path|PROJECT_PATH|path_project|PATH_PROJECT|path)\s*[:=]\s*([^\s]+)", text)
    if match:
        return Path(match.group(1)).expanduser().resolve()

    file_match = re.search(r'File "([^"]+)"', text)
    if file_match:
        path = Path(file_match.group(1)).expanduser()
        return (path if path.is_dir() else path.parent).resolve()

    uploaded = uploaded_python_files()
    if uploaded:
        return uploaded[0].resolve()

    return Path.cwd().resolve()


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))
