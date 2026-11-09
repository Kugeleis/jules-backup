import asyncio
import os
import shutil
from typing import Any

from app.diff_utils import apply_git_merge_diff


class ToolExecutor:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)

    def _resolve_path(self, filepath: str) -> str:
        # Resolve path relative to workspace root and prevent escaping
        if not filepath:
            return self.workspace_root
        if os.path.isabs(filepath):
            # Treat absolute paths starting with / as relative to workspace or allow if within workspace
            target = os.path.abspath(filepath)
            if target.startswith(self.workspace_root):
                return target
            rel = filepath.lstrip("/")
            return os.path.abspath(os.path.join(self.workspace_root, rel))
        target = os.path.abspath(os.path.join(self.workspace_root, filepath))
        return target

    def _validate_safe_path(self, path: str):
        if not (
            path == self.workspace_root or path.startswith(self.workspace_root + os.sep)
        ):
            raise PermissionError(
                f"Access denied: Path '{path}' is outside workspace root."
            )

    def list_files(self, path: str = "") -> dict[str, Any]:
        target_dir = self._resolve_path(path)
        self._validate_safe_path(target_dir)
        if not os.path.exists(target_dir):
            return {"error": f"Directory not found: {path}"}
        if not os.path.isdir(target_dir):
            return {"error": f"Path is not a directory: {path}"}

        entries = []
        for entry in sorted(os.listdir(target_dir)):
            full_p = os.path.join(target_dir, entry)
            is_dir = os.path.isdir(full_p)
            entries.append(f"{entry}/" if is_dir else entry)
        return {"result": entries}

    def read_file(self, filepath: str) -> dict[str, Any]:
        target = self._resolve_path(filepath)
        self._validate_safe_path(target)
        if not os.path.exists(target):
            return {"error": f"File does not exist: {filepath}"}
        if os.path.isdir(target):
            return {"error": f"Path is a directory: {filepath}"}
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"result": content}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def write_file(self, filepath: str, content: str) -> dict[str, Any]:
        target = self._resolve_path(filepath)
        self._validate_safe_path(target)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "result": f"File '{filepath}' written successfully ({len(content)} bytes)."
            }
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def replace_with_git_merge_diff(
        self, filepath: str, merge_diff: str
    ) -> dict[str, Any]:
        target = self._resolve_path(filepath)
        self._validate_safe_path(target)
        if not os.path.exists(target):
            return {"error": f"File does not exist: {filepath}"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                original = f.read()

            success, updated, err = apply_git_merge_diff(original, merge_diff)
            if not success:
                return {"error": f"Failed to apply merge diff: {err}"}

            with open(target, "w", encoding="utf-8") as f:
                f.write(updated)
            return {"result": f"Successfully applied merge diff to '{filepath}'."}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def delete_file(self, filepath: str) -> dict[str, Any]:
        target = self._resolve_path(filepath)
        self._validate_safe_path(target)
        if not os.path.exists(target):
            return {"error": f"File does not exist: {filepath}"}
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            return {"result": f"Deleted '{filepath}' successfully."}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def rename_file(self, filepath: str, new_filepath: str) -> dict[str, Any]:
        src = self._resolve_path(filepath)
        dst = self._resolve_path(new_filepath)
        self._validate_safe_path(src)
        self._validate_safe_path(dst)
        if not os.path.exists(src):
            return {"error": f"Source file does not exist: {filepath}"}
        if os.path.exists(dst):
            return {"error": f"Target destination already exists: {new_filepath}"}
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return {"result": f"Renamed '{filepath}' to '{new_filepath}' successfully."}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    async def run_in_bash(self, command: str, timeout: int = 120) -> dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.workspace_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                output = stdout.decode("utf-8", errors="replace")
                if stderr:
                    err_text = stderr.decode("utf-8", errors="replace")
                    if output:
                        output += "\n" + err_text
                    else:
                        output = err_text
                return {"returncode": proc.returncode, "output": output}
            except TimeoutError:
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001, S110
                    pass
                return {
                    "returncode": -1,
                    "output": f"Command timed out after {timeout} seconds.",
                }
        except Exception as e:  # noqa: BLE001
            return {"returncode": -1, "output": str(e)}
