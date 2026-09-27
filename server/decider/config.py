"""Environment-backed settings for the decider service.

Nothing here is a secret by default: the real values live in `server/.env`,
which the root .gitignore already excludes. `server/.env.example` documents them.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# server/decider/config.py -> server/decider -> server -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_dotenv(path: Path) -> None:
    """Minimal .env loader so the service runs without an extra dependency."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(REPO_ROOT / "server" / ".env")

# --- Which provider answers /decide -------------------------------------
#
# Two of them, and a run must say which one it used: the off-site LiteLLM
# router (reached over the SSH tunnel to sctsvr6) and a model served on this
# laptop by LM Studio / llama.cpp / Ollama. They are not interchangeable as
# evidence — the local server does not count image tokens, so anything
# cost-shaped in metrics.json is meaningless for a `local` run — so the profile
# name lands in run.json and /health rather than only in someone's shell
# history.
#
# Each profile reads its own prefixed vars; a bare, unprefixed var still wins
# over both, which keeps older .env files and one-off overrides working:
#
#   VLM_PROFILE=remote  -> REMOTE_LITELLM_BASE_URL, REMOTE_VLM_MODEL, ...
#   VLM_PROFILE=local   -> LOCAL_LITELLM_BASE_URL,  LOCAL_VLM_MODEL,  ...

PROFILES = ("remote", "local")

_PROFILE_DEFAULTS = {
    # sctsvr6's vLLM, reached through `ssh -N -L 8004:127.0.0.1:8004 sctsvr6`.
    # Not the LiteLLM router on :4000: that proxy's model_list routes only to
    # the text models on :8000-:8003 and has no entry for the VL container, so
    # every vision request through it 404s on the model name. vLLM's own
    # OpenAI-compatible server is the same interface one hop earlier, and it
    # counts image tokens, which the router would too but LM Studio does not.
    "remote": {
        "LITELLM_BASE_URL": "http://127.0.0.1:8004",
        "LITELLM_API_KEY": "sk-local",
        "VLM_MODEL": "Qwen3-VL-30B-A3B",
        "VLM_TIMEOUT_S": "120",
        "VLM_MAX_TOKENS": "1024",
    },
    # LM Studio's OpenAI-compatible server. Just-in-time loading means the
    # first call can take a minute, hence the much longer timeout.
    "local": {
        "LITELLM_BASE_URL": "http://127.0.0.1:1234",
        "LITELLM_API_KEY": "",
        "VLM_MODEL": "qwen/qwen3-vl-30b",
        "VLM_TIMEOUT_S": "300",
        "VLM_MAX_TOKENS": "1024",
    },
}


def _resolve_profile() -> str:
    name = _env("VLM_PROFILE", "remote").lower()
    if name not in PROFILES:
        raise SystemExit(
            "VLM_PROFILE={0!r} is not one of {1}".format(name, ", ".join(PROFILES)))
    return name


def _setting(name: str, profile: str) -> str:
    """Bare var wins, then <PROFILE>_<NAME>, then the profile's default."""
    bare = _env(name)
    if bare:
        return bare
    prefixed = _env("{0}_{1}".format(profile.upper(), name))
    if prefixed:
        return prefixed
    return _PROFILE_DEFAULTS[profile][name]


VLM_PROFILE = _resolve_profile()

LITELLM_BASE_URL = _setting("LITELLM_BASE_URL", VLM_PROFILE).rstrip("/")
LITELLM_API_KEY = _setting("LITELLM_API_KEY", VLM_PROFILE)
VLM_MODEL = _setting("VLM_MODEL", VLM_PROFILE)
VLM_TIMEOUT_S = float(_setting("VLM_TIMEOUT_S", VLM_PROFILE))
MAX_TOKENS = int(_setting("VLM_MAX_TOKENS", VLM_PROFILE))
TEMPERATURE = float(_env("VLM_TEMPERATURE", "0"))

# Streaming buys the latency breakdown: without it there is one wall-clock
# number and no way to say whether a slow step was the tunnel or the GPU. The
# reply is reassembled into the same shape a non-streamed one has, so nothing
# downstream of `_extract` can tell the difference. Set 0 to force the plain
# path; vlm.py also falls back on its own if a provider rejects the stream.
VLM_STREAM = _env("VLM_STREAM", "1") not in ("0", "false", "no")

# One small GET before each decision, on the already-open connection, to
# measure the round trip with no compute behind it. That is the only honest way
# to separate transport from the model: subtracting a measured floor beats
# guessing one. Costs a few ms per step over the tunnel.
VLM_RTT_PROBE = _env("VLM_RTT_PROBE", "1") not in ("0", "false", "no")

RUNS_DIR = Path(_env("RUNS_DIR", str(REPO_ROOT / "eval" / "runs")))


def git_sha() -> str:
    """Short SHA of the tree that produced a run, or 'unknown' outside git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


#: Recorded run data, not code. Runs land here while a phase is in progress, so
#: counting them would mark every run after the first as dirty.
_DATA_PATHS = ("eval/runs", "eval/phase1")


def git_dirty() -> bool:
    """Uncommitted changes to anything that could change a run's behaviour."""
    excludes = [":(exclude){0}".format(p) for p in _DATA_PATHS]
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", "."] + excludes,
            capture_output=True, text=True, timeout=5,
        )
        return bool(out.stdout.strip())
    except Exception:
        return False
