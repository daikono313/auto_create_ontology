"""Claude Code のヘッドレスモード（claude -p）で構造化出力を得る。APIキー不要でサブスク枠を使う。"""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def call_structured(prompt: str, model_cls: type[T], cache_dir: Path | None = None, model: str | None = None) -> T:
    schema = model_cls.model_json_schema()
    key = hashlib.sha256((prompt + json.dumps(schema) + (model or "")).encode()).hexdigest()[:16]
    cache_file = cache_dir / f"{key}.json" if cache_dir else None
    if cache_file and cache_file.exists():
        return model_cls.model_validate_json(cache_file.read_text())

    cmd = ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(schema), "--tools", ""]
    if model:
        cmd += ["--model", model]
    # 残高のない ANTHROPIC_API_KEY がサブスクのログインより優先されるのを避ける
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    # プロジェクトの CLAUDE.md などを読み込ませないよう、空のディレクトリで実行する
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, cwd=cwd, timeout=900)
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"claude -p failed: {proc.stderr[-2000:]}")

    result = json.loads(proc.stdout)
    if result.get("is_error") or result.get("structured_output") is None:
        raise RuntimeError(f"claude -p error: {result.get('result')}")

    parsed = model_cls.model_validate(result["structured_output"])
    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(parsed.model_dump_json(indent=2))
    return parsed
