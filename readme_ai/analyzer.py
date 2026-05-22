"""Analyze a local or GitHub repository to extract context for README generation."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RepoContext:
    # Identity
    name: str
    description: str = ""
    # Language / stack
    primary_language: str = ""
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    # Files
    has_tests: bool = False
    has_docker: bool = False
    has_ci: bool = False
    has_license: bool = False
    license_type: str = ""
    entry_points: List[str] = field(default_factory=list)
    # Package info
    package_name: str = ""
    package_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    # Git
    git_remote: str = ""
    recent_commits: List[str] = field(default_factory=list)
    # File tree (top level)
    file_tree: str = ""
    # Key source snippets (truncated)
    key_files: Dict[str, str] = field(default_factory=dict)
    # Existing README (for improvement mode)
    existing_readme: str = ""


FRAMEWORK_PATTERNS = {
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "React": ["react", "react-dom"],
    "Next.js": ["next"],
    "Vue": ["vue"],
    "Express": ["express"],
    "NestJS": ["@nestjs"],
    "Hardhat": ["hardhat"],
    "Anchor": ["@project-serum/anchor", "@coral-xyz/anchor"],
    "PyTorch": ["torch"],
    "TensorFlow": ["tensorflow"],
    "Transformers": ["transformers"],
    "Solana web3": ["@solana/web3.js"],
    "Flutter": ["flutter"],
    "Actix": ["actix-web"],
    "Axum": ["axum"],
    "Tokio": ["tokio"],
}

LANG_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".sol": "Solidity",
    ".cpp": "C++",
    ".c": "C",
    ".rb": "Ruby",
    ".swift": "Swift",
}


def _count_extensions(root: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in root.rglob("*"):
        if p.is_file() and not any(
            part.startswith(".") or part in ("node_modules", "__pycache__", "dist", "build", ".git")
            for part in p.parts
        ):
            ext = p.suffix.lower()
            if ext in LANG_EXTENSIONS:
                counts[ext] = counts.get(ext, 0) + 1
    return counts


def _read_safe(path: Path, max_bytes: int = 3000) -> str:
    try:
        return path.read_text(errors="replace")[:max_bytes]
    except Exception:
        return ""


def _file_tree(root: Path, depth: int = 2) -> str:
    lines = []

    def _walk(p: Path, prefix: str, current_depth: int):
        if current_depth > depth:
            return
        children = sorted(
            [c for c in p.iterdir() if not c.name.startswith(".") and c.name not in (
                "node_modules", "__pycache__", "dist", "build", ".git", "venv", ".venv"
            )],
            key=lambda x: (x.is_file(), x.name),
        )
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{child.name}")
            if child.is_dir():
                extension = "    " if is_last else "│   "
                _walk(child, prefix + extension, current_depth + 1)

    lines.append(root.name + "/")
    _walk(root, "", 1)
    return "\n".join(lines)


def analyze_local(repo_path: str) -> RepoContext:
    root = Path(repo_path).resolve()
    ctx = RepoContext(name=root.name)

    # File tree
    ctx.file_tree = _file_tree(root)

    # Language detection
    ext_counts = _count_extensions(root)
    if ext_counts:
        sorted_exts = sorted(ext_counts.items(), key=lambda x: -x[1])
        ctx.languages = list(dict.fromkeys(
            LANG_EXTENSIONS[e] for e, _ in sorted_exts if e in LANG_EXTENSIONS
        ))
        ctx.primary_language = ctx.languages[0] if ctx.languages else ""

    # Python: requirements.txt / pyproject.toml / setup.py
    for req_file in ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg"]:
        rp = root / req_file
        if rp.exists():
            content = _read_safe(rp)
            ctx.key_files[req_file] = content
            # Extract package name/version from setup.py
            if req_file == "setup.py":
                m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    ctx.package_name = m.group(1)
                m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    ctx.package_version = m.group(1)
            # Deps
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("["):
                    dep = re.split(r"[>=<!~^]", line)[0].strip().lower()
                    if dep:
                        ctx.dependencies.append(dep)

    # Node: package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        import json
        try:
            pkg = json.loads(pkg_json.read_text())
            ctx.package_name = pkg.get("name", ctx.package_name)
            ctx.package_version = pkg.get("version", ctx.package_version)
            ctx.description = pkg.get("description", ctx.description)
            all_deps = list(pkg.get("dependencies", {}).keys()) + list(pkg.get("devDependencies", {}).keys())
            ctx.dependencies.extend(all_deps)
            ctx.key_files["package.json"] = pkg_json.read_text()[:2000]
        except Exception:
            pass

    # Rust: Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        content = _read_safe(cargo)
        ctx.key_files["Cargo.toml"] = content
        m = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            ctx.package_name = m.group(1)

    # Framework detection
    for framework, keywords in FRAMEWORK_PATTERNS.items():
        for dep in ctx.dependencies:
            if any(kw.lower() in dep.lower() for kw in keywords):
                if framework not in ctx.frameworks:
                    ctx.frameworks.append(framework)
                break

    # Tests
    ctx.has_tests = any(
        (root / d).exists() for d in ["tests", "test", "__tests__", "spec"]
    ) or bool(list(root.rglob("test_*.py"))) or bool(list(root.rglob("*.test.ts")))

    # Docker
    ctx.has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()

    # CI
    ci_dirs = [".github/workflows", ".gitlab-ci.yml", ".circleci", "Jenkinsfile"]
    ctx.has_ci = any((root / d).exists() for d in ci_dirs)

    # License
    for lic in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
        lp = root / lic
        if lp.exists():
            ctx.has_license = True
            content = lp.read_text(errors="replace")
            if "MIT" in content:
                ctx.license_type = "MIT"
            elif "Apache" in content:
                ctx.license_type = "Apache-2.0"
            elif "GPL" in content:
                ctx.license_type = "GPL"
            elif "BSD" in content:
                ctx.license_type = "BSD"
            break

    # Entry points
    for ep in ["main.py", "app.py", "index.ts", "index.js", "src/main.rs", "cmd/main.go"]:
        if (root / ep).exists():
            ctx.entry_points.append(ep)

    # Git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            ctx.git_remote = result.stdout.strip()
    except Exception:
        pass

    # Recent commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            ctx.recent_commits = result.stdout.strip().splitlines()
    except Exception:
        pass

    # Existing README
    for rn in ["README.md", "README.rst", "README.txt", "README"]:
        rp = root / rn
        if rp.exists():
            ctx.existing_readme = _read_safe(rp, max_bytes=5000)
            break

    # Key source files (first main file found)
    for ep in ctx.entry_points:
        fp = root / ep
        if fp.exists():
            ctx.key_files[ep] = _read_safe(fp, max_bytes=2000)

    return ctx
