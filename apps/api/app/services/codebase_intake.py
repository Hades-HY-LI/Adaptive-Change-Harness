from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4
import zipfile

from fastapi import UploadFile

from app.models.schemas import CodebaseDetail, SourceType
from app.services.repo_profiler import RepoProfiler
from app.storage.repository import RunRepository


class CodebaseIntakeService:
    def __init__(self, artifact_root: Path, repository: RunRepository, profiler: RepoProfiler) -> None:
        self.artifact_root = artifact_root
        self.repository = repository
        self.profiler = profiler

    async def ingest_zip(self, upload: UploadFile) -> CodebaseDetail:
        codebase_id = str(uuid4())
        codebase_root = self.artifact_root / "codebases" / codebase_id
        archive_path = codebase_root / "source.zip"
        extracted_path = codebase_root / "repo"
        if codebase_root.exists():
            shutil.rmtree(codebase_root)
        extracted_path.mkdir(parents=True, exist_ok=True)

        payload = await upload.read()
        archive_path.write_bytes(payload)
        self._extract_zip(archive_path, extracted_path)

        repo_profile = self.profiler.profile(
            codebase_id=codebase_id,
            workspace_path=extracted_path,
            source_type=SourceType.zip_upload,
        )
        label = Path(upload.filename or "uploaded-codebase.zip").stem
        return self.repository.create_codebase(
            label=label,
            source_type=SourceType.zip_upload,
            archive_path=str(archive_path),
            extracted_path=str(extracted_path),
            repo_profile=repo_profile,
        )

    def _extract_zip(self, archive_path: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            for member in members:
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError(f"Unsafe zip member path: {member.filename}")
            archive.extractall(destination)

        child_items = list(destination.iterdir())
        if len(child_items) == 1 and child_items[0].is_dir():
            nested_root = child_items[0]
            temp_destination = destination.parent / f"{destination.name}_tmp"
            if temp_destination.exists():
                shutil.rmtree(temp_destination)
            shutil.move(str(nested_root), temp_destination)
            shutil.rmtree(destination)
            shutil.move(str(temp_destination), destination)
