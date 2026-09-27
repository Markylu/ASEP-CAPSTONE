"""Run an external command without blocking the UI, streaming its output.

Godot and ffmpeg both take long enough that a synchronous subprocess.run would
freeze the terminal with no way to tell whether anything is happening, so every
action goes through here: one line at a time, cancellable.
"""
from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from .model import REPO_ROOT

OnLine = Callable[[str], None]


class Runner:
    """Owns at most one child process, so cancel has something to cancel."""

    def __init__(self) -> None:
        self._process = None  # type: Optional[asyncio.subprocess.Process]

    @property
    def busy(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def run(self, command: Sequence[str], on_line: OnLine,
                  cwd: Optional[Path] = None,
                  timeout: Optional[float] = None) -> int:
        if self.busy:
            raise RuntimeError("a command is already running")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(cwd or REPO_ROOT),
            start_new_session=True,  # so cancel kills Godot's children too
        )
        self._process = process
        try:
            await asyncio.wait_for(self._pump(process, on_line), timeout=timeout)
            return await process.wait()
        except asyncio.TimeoutError:
            on_line("TIMEOUT after {0}s — killing".format(timeout))
            self.cancel()
            await process.wait()
            return 124
        except asyncio.CancelledError:
            self.cancel()
            await process.wait()
            raise
        finally:
            self._process = None

    async def _pump(self, process, on_line: OnLine) -> None:
        assert process.stdout is not None
        while True:
            raw = await process.stdout.readline()
            if not raw:
                break
            on_line(raw.decode("utf-8", "replace").rstrip("\n"))

    def cancel(self) -> None:
        """Kill the whole process group: Godot's movie writer spawns helpers."""
        process = self._process
        if process is None or process.returncode is not None:
            return
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                process.kill()
            except ProcessLookupError:
                pass


async def capture(command: Sequence[str], cwd: Optional[Path] = None,
                  timeout: float = 60.0) -> "tuple":
    """For short commands whose output is wanted whole, such as ffprobe."""
    lines = []  # type: List[str]
    code = await Runner().run(command, lines.append, cwd=cwd, timeout=timeout)
    return code, "\n".join(lines)


def decider_health(url: str = "http://127.0.0.1:8000", timeout: float = 1.5) -> Optional[str]:
    """None when the decider answers; otherwise the reason it did not.

    Checked before a verify because replay.py records the replay's poses through
    the decider — without it the comparison reports a mismatch that is an
    artefact of the missing service, not of the trajectory.
    """
    import json
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok", True):
            return "decider reports not ok: {0}".format(body)
        return None
    except urllib.error.URLError as exc:
        return "no decider at {0} ({1}). Start it with: python3 -m uvicorn " \
               "server.decider.app:app --port 8000".format(url, exc.reason)
    except Exception as exc:  # noqa: BLE001 - any failure means "do not verify"
        return "decider check failed: {0}".format(exc)
