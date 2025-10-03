from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DEFAULT_FILES = {
    'README.md': '# Sandbox Repository\n\nThis repository is managed by the Ops Copilot sandbox.',
    'src/app.py': 'print("hello from sandbox")
',
}


class SandboxRepo:
    "Manages a local sandbox directory used by mock GitHub actions."

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _initialise(self) -> None:
        for relative, content in DEFAULT_FILES.items():
            file_path = self.path / relative
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text(content, encoding='utf-8')
        (self.path / '.sandbox-meta.json').write_text(json.dumps({'status': 'ready'}), encoding='utf-8')

    def write_diff(self, branch: str, summary: str) -> Path:
        diff_path = self.path / f"diff_{branch.replace('/', '_')}.txt"
        diff_path.write_text(summary, encoding='utf-8')
        return diff_path

    def metadata(self) -> Dict[str, str]:
        meta_path = self.path / '.sandbox-meta.json'
        return json.loads(meta_path.read_text(encoding='utf-8'))
