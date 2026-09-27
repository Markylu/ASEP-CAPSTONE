"""Start the decider, choosing which VLM provider answers.

    python -m server.decider --profile local
    python -m server.decider --profile remote --port 8000

`--profile` is only a friendlier spelling of `VLM_PROFILE=...`; it is set
before `config` is imported, because config resolves the profile at import
time. Everything else about the profile lives in `server/.env` under the
`REMOTE_`/`LOCAL_` prefixes.
"""
from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m server.decider")
    parser.add_argument("--profile", choices=("remote", "local"),
                        help="which VLM provider to call (default: $VLM_PROFILE, else remote)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if args.profile:
        os.environ["VLM_PROFILE"] = args.profile

    import uvicorn

    from . import config

    print("decider: profile={0} model={1} base_url={2}".format(
        config.VLM_PROFILE, config.VLM_MODEL, config.LITELLM_BASE_URL))

    uvicorn.run("server.decider.app:app", host=args.host, port=args.port,
                reload=args.reload)


if __name__ == "__main__":
    main()
