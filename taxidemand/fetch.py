"""Download the raw TLC files listed in params.toml and verify their SHA-256.

    python -m taxidemand.fetch
"""
from __future__ import annotations

import hashlib
import urllib.request

from .settings import RAW, params, prepare_dirs


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = params()["data"]
    prepare_dirs()
    urls = {f"{p['service']}_tripdata_{m}.parquet": f"{p['base_url']}/{p['service']}_tripdata_{m}.parquet"
            for m in p["months"]}
    urls["taxi_zone_lookup.csv"] = p["zone_lookup_url"]
    for name, url in urls.items():
        dest = RAW / name
        if not dest.exists():
            print(f"downloading {name}")
            urllib.request.urlretrieve(url, dest)
        got = sha256(dest)
        if got != p["sha256"][name]:
            raise SystemExit(f"checksum mismatch for {name}: {got}")
        print(f"ok  {name}")


if __name__ == "__main__":
    main()
