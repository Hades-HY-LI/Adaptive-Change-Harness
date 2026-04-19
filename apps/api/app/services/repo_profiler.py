from __future__ import annotations

from pathlib import Path

from app.models.schemas import RepoProfile, SourceType


class RepoProfiler:
    def profile(self, codebase_id: str, workspace_path: Path, source_type: SourceType) -> RepoProfile:
        python_files = list(workspace_path.rglob("*.py"))
        language = "python" if python_files else "unknown"
        framework = self._detect_framework(workspace_path, python_files)
        package_manager = self._detect_package_manager(workspace_path)
        install_command = self._detect_install_command(workspace_path, package_manager)
        test_command = self._detect_test_command(workspace_path)
        source_dirs = self._detect_source_dirs(workspace_path, python_files)
        test_dirs = self._detect_test_dirs(workspace_path)
        entrypoints = self._detect_entrypoints(workspace_path, python_files)
        risk_areas = self._detect_risk_areas(workspace_path)
        return RepoProfile(
            id=codebase_id,
            source_type=source_type,
            workspace_path=str(workspace_path),
            language=language,
            framework=framework,
            package_manager=package_manager,
            install_command=install_command,
            test_command=test_command,
            source_dirs=source_dirs,
            test_dirs=test_dirs,
            entrypoints=entrypoints,
            risk_areas=risk_areas,
        )

    def _detect_framework(self, workspace_path: Path, python_files: list[Path]) -> str:
        for file_path in python_files[:50]:
            try:
                content = file_path.read_text()
            except UnicodeDecodeError:
                continue
            if "from fastapi import" in content or "FastAPI(" in content:
                return "fastapi"
        if (workspace_path / "app").exists():
            return "python_service"
        return "unknown"

    def _detect_package_manager(self, workspace_path: Path) -> str | None:
        if (workspace_path / "uv.lock").exists():
            return "uv"
        if (workspace_path / "poetry.lock").exists():
            return "poetry"
        if (workspace_path / "requirements.txt").exists():
            return "pip"
        if (workspace_path / "pyproject.toml").exists():
            return "pyproject"
        return None

    def _detect_install_command(self, workspace_path: Path, package_manager: str | None) -> str | None:
        if package_manager == "uv":
            return "uv sync"
        if package_manager == "poetry":
            return "poetry install"
        if package_manager == "pip" and (workspace_path / "requirements.txt").exists():
            return "python -m pip install -r requirements.txt"
        if (workspace_path / "pyproject.toml").exists():
            return "python -m pip install -e ."
        return None

    def _detect_test_command(self, workspace_path: Path) -> str | None:
        if (workspace_path / "pytest.ini").exists() or (workspace_path / "tests").exists():
            return "python -m pytest"
        if list(workspace_path.rglob("test_*.py")):
            return "python -m pytest"
        return None

    def _detect_source_dirs(self, workspace_path: Path, python_files: list[Path]) -> list[str]:
        candidates: list[str] = []
        for directory_name in ("app", "src"):
            if (workspace_path / directory_name).exists():
                candidates.append(directory_name)
        packages = {
            path.parent.relative_to(workspace_path).parts[0]
            for path in python_files
            if path.parent != workspace_path and "tests" not in path.parts
        }
        for package in sorted(packages):
            if package not in candidates:
                candidates.append(package)
        return candidates

    def _detect_test_dirs(self, workspace_path: Path) -> list[str]:
        test_dirs = [path.relative_to(workspace_path).as_posix() for path in workspace_path.glob("tests*") if path.is_dir()]
        return sorted(test_dirs)

    def _detect_entrypoints(self, workspace_path: Path, python_files: list[Path]) -> list[str]:
        entrypoints: list[str] = []
        for file_path in python_files[:50]:
            try:
                content = file_path.read_text()
            except UnicodeDecodeError:
                continue
            if "FastAPI(" in content or "__main__" in content:
                entrypoints.append(file_path.relative_to(workspace_path).as_posix())
        return sorted(set(entrypoints))

    def _detect_risk_areas(self, workspace_path: Path) -> list[str]:
        risk_keywords = ("billing", "checkout", "subscription", "payment", "discount", "retry")
        risk_areas: list[str] = []
        for path in workspace_path.rglob("*"):
            if any(part.startswith(".") for part in path.parts):
                continue
            relative = path.relative_to(workspace_path).as_posix()
            lower = relative.lower()
            if any(keyword in lower for keyword in risk_keywords):
                risk_areas.append(relative)
        return sorted(set(risk_areas))[:20]
