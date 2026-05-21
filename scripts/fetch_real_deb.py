#!/usr/bin/env python3
"""
scripts/fetch_real_deb.py — fetch a real Debian `.deb` from the live
mirror, caching it under build/cache/ so repeat runs are offline and
deterministic.

This is the "fetch real Debian data once, cache, bake onto a fixture"
pattern that scripts/build_realgz_img.py / build_realinrelease_img.py
use, narrowed to a single small `.deb` package. The cached package is
baked into the cpio initramfs as /tests/sample.deb by
scripts/test_dpkg_real_deb.sh, which then runs `dpkg -i` on it under
QEMU — proving the apt-path can install a genuine Debian package
(ar archive + xz-compressed control.tar / data.tar) end to end.

Default package: `hello` 2.10-5 — Debian's canonical tiny package.
Its `.deb` is ~52 KiB; control.tar.xz / data.tar.xz decompress to
~10 KiB / ~256 KiB, both inside dpkg.ad's single-shot decompress caps.

Usage:
    python3 scripts/fetch_real_deb.py <out-path> [--url URL]
            [--sha256 HEX]

Exits non-zero with a "SKIP" message if the package cannot be fetched
and is not already cached — the test script treats that as SKIP, not
FAIL, so an offline CI box does not spuriously fail.
"""

import hashlib
import shutil
import sys
import urllib.request
from pathlib import Path

# Debian `hello` — the canonical tiny package. Pinned to a specific
# version so the SHA-256 below is stable; if Debian drops this exact
# build from the pool the test falls back to whatever the cache holds,
# or SKIPs.
DEFAULT_URL = (
    "http://deb.debian.org/debian/pool/main/h/hello/"
    "hello_2.10-5_amd64.deb"
)

HERE  = Path(__file__).resolve().parent.parent
CACHE = HERE / "build" / "cache"


def _cache_path(url: str) -> Path:
    """Cache file name is the URL's basename under build/cache/."""
    return CACHE / url.rsplit("/", 1)[-1]


def fetch_deb(url: str) -> bytes:
    """Fetch the `.deb`, using build/cache/ as an offline cache."""
    cached = _cache_path(url)
    if cached.exists() and cached.stat().st_size > 0:
        print(f"[fetch_real_deb] using cached {cached} "
              f"({cached.stat().st_size} bytes)")
        return cached.read_bytes()
    print(f"[fetch_real_deb] fetching {url}")
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "hamnix-dpkg-repro/1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:                       # noqa: BLE001
        raise SystemExit(
            f"[fetch_real_deb] could not fetch {url}: {e}\n"
            f"[fetch_real_deb] (and no cache at {cached}) — SKIP")
    # An `ar` archive starts with the 8-byte magic "!<arch>\n".
    if len(data) < 8 or data[:8] != b"!<arch>\n":
        raise SystemExit(
            f"[fetch_real_deb] fetched data is not an ar archive "
            f"(got {len(data)} bytes, "
            f"magic {data[:8].hex() if data else 'empty'})")
    cached.write_bytes(data)
    print(f"[fetch_real_deb] cached {len(data)} bytes -> {cached}")
    return data


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: fetch_real_deb.py <out-path> [--url URL] "
              "[--sha256 HEX]", file=sys.stderr)
        return 2
    out_path = Path(args[0])
    url = DEFAULT_URL
    want_sha = None
    i = 1
    while i < len(args):
        if args[i] == "--url" and i + 1 < len(args):
            url = args[i + 1]
            i += 2
        elif args[i] == "--sha256" and i + 1 < len(args):
            want_sha = args[i + 1].lower()
            i += 2
        else:
            print(f"unknown argument: {args[i]}", file=sys.stderr)
            return 2

    data = fetch_deb(url)
    sha = hashlib.sha256(data).hexdigest()
    if want_sha is not None and sha != want_sha:
        raise SystemExit(
            f"[fetch_real_deb] SHA-256 mismatch for {url}\n"
            f"[fetch_real_deb]   expected {want_sha}\n"
            f"[fetch_real_deb]   got      {sha}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_cache_path(url), out_path)
    print(f"[fetch_real_deb] {out_path} ({len(data)} bytes) sha256={sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
