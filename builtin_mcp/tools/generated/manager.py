from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from config import McpServiceSettings


TOOL_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){1,2}(?:[-+][A-Za-z0-9.-]+)?$")
SECRET_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
CAPABILITIES = {"network", "filesystem_read", "filesystem_write", "process", "secrets"}
GENERATED_ROOT_ENV = "COPY_MYSELF_GENERATED_TOOLS_ROOT"
SENSITIVE_PARTS = {".git", ".codex", ".env", "keys"}


class GeneratedToolManager:
    """Creates project-local generated MCP services without editing MCP config."""

    def __init__(self, root: Path | None = None) -> None:
        configured = os.getenv(GENERATED_ROOT_ENV)
        self.root = (Path(configured).expanduser() if configured else root) or Path(__file__).resolve().parent
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, spec: Mapping[str, Any], *, install: bool = False) -> dict[str, Any]:
        manifest = self.validate_manifest(spec)
        tool_root = self.root / manifest["tool_id"] / manifest["version"]
        if tool_root.exists():
            raise ValueError("generated_tool_version_exists")
        tool_root.mkdir(parents=True)
        try:
            entrypoint = tool_root / manifest["entrypoint"]
            entrypoint.parent.mkdir(parents=True, exist_ok=True)
            entrypoint.write_text(manifest.pop("source"), encoding="utf-8")
            if manifest["runtime"] == "node":
                package = {"private": True, "type": "module", "dependencies": self._npm_dependencies(manifest["dependencies"])}
                (tool_root / "package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
            elif manifest["dependencies"]:
                (tool_root / "requirements.txt").write_text("\n".join(manifest["dependencies"]) + "\n", encoding="utf-8")

            runtime_command = self._prepare_runtime(tool_root, manifest) if install else self._sandbox_command(manifest)
            manifest["status"] = "enabled" if install else "draft"
            manifest["command"] = runtime_command[0]
            manifest["args"] = runtime_command[1]
            manifest_path = tool_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            if install:
                (self.root / manifest["tool_id"] / "active.json").write_text(json.dumps({"version": manifest["version"]}), encoding="utf-8")
            return {"status": manifest["status"], "tool_id": manifest["tool_id"], "version": manifest["version"], "manifest": str(manifest_path), "service_id": self.service_id(manifest["tool_id"]), "next_call": manifest.get("next_call")}
        except Exception:
            failed = {**manifest, "status": "failed"}
            (tool_root / "manifest.json").write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
            raise

    def list_services(self) -> tuple[McpServiceSettings, ...]:
        services: list[McpServiceSettings] = []
        if not self.root.exists():
            return ()
        for tool_dir in sorted(item for item in self.root.iterdir() if item.is_dir() and TOOL_ID_RE.fullmatch(item.name)):
            active_path = tool_dir / "active.json"
            if not active_path.exists():
                continue
            try:
                version = json.loads(active_path.read_text(encoding="utf-8"))["version"]
                manifest = json.loads((tool_dir / version / "manifest.json").read_text(encoding="utf-8"))
                if manifest.get("status") != "enabled":
                    continue
                services.append(self._service_from_manifest(manifest, tool_dir / version))
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
        return tuple(services)

    @staticmethod
    def service_id(tool_id: str) -> str:
        return f"generated-{tool_id}"

    def validate_manifest(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(spec, Mapping):
            raise ValueError("generated_tool_spec_invalid")
        tool_id = str(spec.get("tool_id", "")).strip()
        version = str(spec.get("version", "1.0.0")).strip()
        name = str(spec.get("name", tool_id)).strip()
        description = str(spec.get("description", "")).strip()
        runtime = str(spec.get("runtime", "python")).strip().lower()
        entrypoint = str(spec.get("entrypoint", "server.py")).strip()
        source = spec.get("source", "")
        if not TOOL_ID_RE.fullmatch(tool_id):
            raise ValueError("generated_tool_id_invalid")
        if not VERSION_RE.fullmatch(version):
            raise ValueError("generated_tool_version_invalid")
        if not name or not description or runtime not in {"python", "node"} or not entrypoint or Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts:
            raise ValueError("generated_tool_manifest_invalid")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("generated_tool_source_missing")
        dependencies = self._string_list(spec.get("dependencies", []), "generated_tool_dependencies_invalid")
        capabilities = self._string_list(spec.get("capabilities", []), "generated_tool_capabilities_invalid")
        if not set(capabilities) <= CAPABILITIES:
            raise ValueError("generated_tool_capability_invalid")
        secrets = self._string_list(spec.get("secrets", []), "generated_tool_secrets_invalid")
        if not all(SECRET_RE.fullmatch(item) for item in secrets):
            raise ValueError("generated_tool_secret_invalid")
        filesystem_roots = self._filesystem_roots(spec.get("filesystem_roots", []))
        if runtime == "python":
            self._validate_python_source(source, set(capabilities))
        else:
            if "npm" in source.lower() and "package.json" not in source.lower():
                raise ValueError("generated_tool_node_source_invalid")
        return {
            "tool_id": tool_id,
            "version": version,
            "name": name,
            "description": description,
            "runtime": runtime,
            "entrypoint": entrypoint,
            "source": source,
            "dependencies": dependencies,
            "capabilities": capabilities,
            "secrets": secrets,
            "filesystem_roots": filesystem_roots,
            "next_call": spec.get("next_call"),
            "allow_install_scripts": bool(spec.get("allow_install_scripts", False)),
            "timeout_seconds": float(spec.get("timeout_seconds", 30.0)),
        }

    @staticmethod
    def _string_list(value: Any, error: str) -> list[str]:
        if isinstance(value, str) or not isinstance(value, (list, tuple)):
            raise ValueError(error)
        result = [str(item).strip() for item in value if str(item).strip()]
        if any("\n" in item or "\r" in item or ";" in item or "|" in item for item in result):
            raise ValueError(error)
        return result

    @staticmethod
    def _filesystem_roots(value: Any) -> list[str]:
        if isinstance(value, str) or not isinstance(value, (list, tuple)):
            raise ValueError("generated_tool_filesystem_roots_invalid")
        roots: list[str] = []
        project_root = Path.cwd().resolve()
        for item in value:
            candidate = str(item).strip()
            path = Path(candidate)
            if not candidate or path.is_absolute() or ".." in path.parts or any(part.casefold() in SENSITIVE_PARTS for part in path.parts):
                raise ValueError("generated_tool_filesystem_root_invalid")
            resolved = (project_root / path).resolve()
            if project_root not in resolved.parents and resolved != project_root:
                raise ValueError("generated_tool_filesystem_root_invalid")
            roots.append(candidate)
        return roots

    @staticmethod
    def _validate_python_source(source: str, capabilities: set[str]) -> None:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise ValueError("generated_tool_python_syntax_error") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile"}:
                raise ValueError("unsafe_python_source")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen"}:
                if "process" not in capabilities:
                    raise ValueError("unsafe_python_source")
            if isinstance(node, ast.Import | ast.ImportFrom):
                names = {alias.name.split(".")[0] for alias in node.names}
                if names & {"socket", "urllib", "requests", "httpx"} and "network" not in capabilities:
                    raise ValueError("network_capability_required")
                if names & {"subprocess", "ctypes", "multiprocessing"} and "process" not in capabilities:
                    raise ValueError("process_capability_required")

    @staticmethod
    def _prepare_runtime(self, tool_root: Path, manifest: dict[str, Any]) -> tuple[str, list[str]]:
        docker = shutil.which("docker")
        if not docker:
            raise ValueError("docker_runtime_unavailable")
        image = self._image_name(manifest)
        if manifest["runtime"] == "python":
            requirements = ["mcp>=1.29.0,<2.0", *manifest["dependencies"]]
            (tool_root / "requirements.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")
            dockerfile = "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . /app\nUSER 65532:65532\nCMD [\"python\", \"%s\"]\n" % manifest["entrypoint"].replace("\\", "/")
        else:
            install_flag = "" if manifest["allow_install_scripts"] else " --ignore-scripts"
            dockerfile = "FROM node:22-slim\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install --no-audit --no-fund%s\nCOPY . /app\nUSER 65532:65532\nCMD [\"node\", \"%s\"]\n" % (install_flag, manifest["entrypoint"].replace("\\", "/"))
        (tool_root / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        subprocess.run([docker, "build", "--tag", image, "."], cwd=tool_root, check=True, timeout=1800)
        manifest["image"] = image
        return self._sandbox_command(manifest)

    @staticmethod
    def _image_name(manifest: Mapping[str, Any]) -> str:
        return f"copy-myself-generated-{manifest['tool_id']}:{manifest['version']}".replace("+", "-")

    def _sandbox_command(self, manifest: Mapping[str, Any]) -> tuple[str, list[str]]:
        image = str(manifest.get("image") or self._image_name(manifest))
        network = "bridge" if "network" in set(manifest.get("capabilities", ())) else "none"
        args = [
            "run", "--rm", "-i", "--network", network, "--read-only", "--pids-limit", "32",
            "--memory", "256m", "--cpus", "1", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        ]
        for secret in manifest.get("secrets", ()):
            args.extend(["--env", str(secret)])
        roots = list(manifest.get("filesystem_roots", ()))
        if roots and set(manifest.get("capabilities", ())) & {"filesystem_read", "filesystem_write"}:
            container_roots: list[str] = []
            writable = "filesystem_write" in set(manifest.get("capabilities", ()))
            for index, root in enumerate(roots):
                source = str((Path.cwd() / root).resolve())
                target = f"/workspace/{index}"
                mount = f"type=bind,src={source},dst={target}"
                if not writable:
                    mount += ",readonly"
                args.extend(["--mount", mount])
                container_roots.append(target)
            args.extend(["--env", f"COPY_MYSELF_FILESYSTEM_ROOTS={':'.join(container_roots)}"])
        args.append(image)
        return "docker", args

    def _service_from_manifest(self, manifest: Mapping[str, Any], tool_root: Path) -> McpServiceSettings:
        risk = "side_effect" if set(manifest.get("capabilities", ())) & {"network", "filesystem_write", "process", "secrets"} else "read_only"
        metadata = {"_meta": {"copy_myself": {"risk": risk, "capabilities": list(manifest.get("capabilities", ())), "secrets": list(manifest.get("secrets", ())), "generated": True}}}
        command, args = self._sandbox_command(manifest)
        return McpServiceSettings(
            name=str(manifest["name"]),
            service_id=self.service_id(str(manifest["tool_id"])),
            transport="stdio",
            command=command,
            args=tuple(args),
            env={"PYTHONPATH": str(tool_root), **{str(secret): "${%s}" % secret for secret in manifest.get("secrets", ())}} if manifest["runtime"] == "python" else {str(secret): "${%s}" % secret for secret in manifest.get("secrets", ())},
            enabled=True,
            timeout_seconds=float(manifest.get("timeout_seconds", 30.0)),
            metadata=metadata,
        )

    @staticmethod
    def _npm_dependencies(dependencies: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in dependencies:
            if "@" in item[1:]:
                name, version = item.rsplit("@", 1)
            else:
                name, version = item, "latest"
            result[name] = version
        return result
