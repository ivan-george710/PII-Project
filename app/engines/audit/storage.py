"""Restricted local JSON snapshots, atomic replacement; no multi-user database semantics."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .models import AuditStorageError

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AuditStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else PROJECT_ROOT / ".private_audit"

    def _prepare(self):
        requested = self.directory.absolute()
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
               for p in [requested, *requested.parents]):
            raise AuditStorageError("Audit storage may not traverse symlinks or junctions")
        path = requested.resolve()
        if os.name == "nt" and path.drive.startswith("\\\\"):
            raise AuditStorageError("Audit storage must be local, not a network share")
        if path in {PROJECT_ROOT, Path(path.anchor), Path.home()} or any(part.lower() in {"public", "wwwroot", "static", ".git", ".venv"}
                                       for part in path.parts):
            raise AuditStorageError("Choose a dedicated private audit directory")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "nt":
            literal = "'" + str(path).replace("'", "''") + "'"
            script = (
                "$ErrorActionPreference='Stop'; $target=" + literal + ";"
                "$identity=[System.Security.Principal.WindowsIdentity]::GetCurrent();"
                "$acl=[System.IO.Directory]::GetAccessControl($target,"
                "[System.Security.AccessControl.AccessControlSections]::Access);"
                "$acl.SetAccessRuleProtection($true,$false);"
                "foreach($rule in $acl.GetAccessRules($true,$false,"
                "[System.Security.Principal.SecurityIdentifier])){$acl.RemoveAccessRuleSpecific($rule)};"
                "$acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new("
                "$identity.User,'FullControl','ContainerInherit,ObjectInherit','None','Allow'));"
                "$acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new("
                "[System.Security.Principal.SecurityIdentifier]::new('S-1-5-18'),'FullControl',"
                "'ContainerInherit,ObjectInherit','None','Allow'));"
                "[System.IO.Directory]::SetAccessControl($target,$acl);"
            )
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           check=True, capture_output=True, timeout=30)
        else:
            path.chmod(0o700)
        self.directory = path
        self._atomic(path / ".gitignore", {"ignore": True}, raw="*\n!.gitignore\n")

    def _path(self, document_id):
        if not isinstance(document_id, str) or not re.fullmatch(r"[0-9a-f]{64}", document_id):
            raise AuditStorageError("Invalid internal document identifier")
        return self.directory / ("audit_" + document_id + ".json")

    @staticmethod
    def _atomic(path, data, raw=None):
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=".audit-", suffix=".tmp", delete=False) as stream:
                name = stream.name
                if os.name != "nt":
                    os.fchmod(stream.fileno(), 0o600)
                stream.write(raw if raw is not None else json.dumps(data, default=str, ensure_ascii=False, indent=2))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if name and Path(name).exists():
                Path(name).unlink()

    def write(self, document_id, payload, expected_revision=None):
        try:
            payload = json.loads(json.dumps(payload, default=str))
            self._prepare()
            path = self._path(document_id)
            if path.is_symlink():
                raise AuditStorageError("Audit snapshot may not be a symlink")
            if path.exists():
                old = json.loads(path.read_text(encoding="utf-8"))
                if old == payload:
                    return path
                if old.get("baseline_fingerprint") != payload["baseline_fingerprint"]:
                    raise AuditStorageError("Original audit baseline differs; use a separate store for a new detection run")
                if expected_revision is None or old["revision"] != expected_revision:
                    raise AuditStorageError("Existing snapshot changed; supply its expected revision")
            elif expected_revision is not None:
                raise AuditStorageError("Expected existing audit snapshot was not found")
            self._atomic(path, payload)
            return path
        except AuditStorageError:
            raise
        except Exception as exc:
            raise AuditStorageError(f"Audit persistence failed ({type(exc).__name__})") from None

    def read(self, document_id):
        try:
            self._prepare()
            path = self._path(document_id)
            if path.is_symlink():
                raise AuditStorageError("Audit snapshot may not be a symlink")
            return json.loads(path.read_text(encoding="utf-8"))
        except AuditStorageError:
            raise
        except Exception as exc:
            raise AuditStorageError(f"Audit reload failed ({type(exc).__name__})") from None
