#!/usr/bin/env python3
"""
scripts/build_realinrelease_img.py — build the virtio-blk ext4 disk
image that scripts/test_apt_inrelease_real.sh attaches to QEMU.

The image contains exactly two files:

  /InRelease   — the genuine, inline-clearsigned `InRelease` of a real
                 Debian suite, fetched from deb.debian.org.
  /keyring.gpg — the genuine `debian-archive-keyring.gpg` (the raw
                 `gpg --export` blob of the Debian archive keys).

The Hamnix kernel auto-mounts any ext4 virtio-blk disk at /ext, so the
files are readable from userland as /ext/InRelease and /ext/keyring.gpg.

WHY THIS TEST EXISTS

  scripts/test_apt_inrelease.sh and test_apt_inrelease_sha512.sh prove
  apt's OpenPGP verification against *synthetic* gpg-clearsigned
  fixtures. Those pass — but the real `deb.debian.org` `InRelease`
  failed to verify, because a real Debian `InRelease` is NOT signed by
  the primary archive keys: it is signed by the dedicated `[S]` signing
  SUBKEYS those primary keys carry (Tag 14 Public-Subkey packets in the
  keyring). A verifier that collected only Tag 6 primaries held none of
  the keys that actually signed the index.

  This test bakes the genuine InRelease + the genuine keyring onto a
  disk and runs the REAL lib/pgp + lib/rsa verification path over them
  inside Hamnix — a deterministic, offline reproduction of the
  real-Debian verification, with no live internet needed per run.

WHY A DISK IMAGE (not the cpio initramfs): same rationale as
build_realgz_img.py — keeps the kernel/initramfs small; a -drive image
holds the fixture at zero kernel cost.

The real files are fetched once, then cached under build/cache/ so
repeat runs are offline + deterministic.

Usage:
    python3 scripts/build_realinrelease_img.py [--suite SUITE]

Exits non-zero (with a clear message) if a file cannot be fetched and
is not cached — the test script treats that as SKIP, not FAIL, so an
offline CI box does not spuriously fail.
"""

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# bookworm is a stable, long-lived suite; its InRelease is dual-signed
# by RSA-4096 signing subkeys (plus an Ed25519 signature) — exactly the
# real-world shape the verifier must handle.
DEFAULT_SUITE = "bookworm"
INRELEASE_URL = "https://deb.debian.org/debian/dists/{suite}/InRelease"

# The Debian archive keyring — the trust root. Fetched from the
# debian-archive-keyring package's canonical location on the mirror so
# the test does not depend on the host having the package installed.
KEYRING_URL = (
    "https://deb.debian.org/debian/pool/main/d/debian-archive-keyring/"
)

HERE         = Path(__file__).resolve().parent.parent
BUILD        = HERE / "build"
CACHE        = BUILD / "cache"
CACHED_IR    = CACHE / "real_InRelease"
CACHED_KR    = CACHE / "debian-archive-keyring.gpg"
OUT_IMG      = BUILD / "realinrelease.img"

# A host-installed keyring is the simplest cache seed when present.
HOST_KEYRINGS = (
    "/usr/share/keyrings/debian-archive-keyring.gpg",
    "/usr/share/keyrings/debian-archive-keyring.pgp",
    "/etc/apt/trusted.gpg.d/debian-archive-keyring.gpg",
)


def _which(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for prefix in ("/sbin", "/usr/sbin", "/usr/local/sbin"):
        cand = Path(prefix) / name
        if cand.exists():
            return str(cand)
    raise SystemExit(f"required tool '{name}' not found")


def _http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "hamnix-inrelease-repro/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_inrelease(suite: str) -> bytes:
    """Fetch the real InRelease, using build/cache/ as an offline cache."""
    if CACHED_IR.exists() and CACHED_IR.stat().st_size > 0:
        print(f"[build_realinrelease_img] using cached {CACHED_IR} "
              f"({CACHED_IR.stat().st_size} bytes)")
        return CACHED_IR.read_bytes()
    url = INRELEASE_URL.format(suite=suite)
    print(f"[build_realinrelease_img] fetching {url}")
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        data = _http_get(url)
    except Exception as e:                       # noqa: BLE001
        raise SystemExit(
            f"[build_realinrelease_img] could not fetch {url}: {e}\n"
            f"[build_realinrelease_img] (and no cache at {CACHED_IR}) "
            f"— SKIP")
    if not data.startswith(b"-----BEGIN PGP SIGNED MESSAGE-----"):
        raise SystemExit(
            f"[build_realinrelease_img] fetched data is not a "
            f"clearsigned document ({len(data)} bytes)")
    CACHED_IR.write_bytes(data)
    print(f"[build_realinrelease_img] cached {len(data)} bytes "
          f"-> {CACHED_IR}")
    return data


def fetch_keyring() -> bytes:
    """Obtain the real debian-archive-keyring, using build/cache/.

    Order: build/cache, then a host-installed copy, then the mirror's
    debian-archive-keyring .deb (unpacked).
    """
    if CACHED_KR.exists() and CACHED_KR.stat().st_size > 0:
        print(f"[build_realinrelease_img] using cached {CACHED_KR} "
              f"({CACHED_KR.stat().st_size} bytes)")
        return CACHED_KR.read_bytes()
    CACHE.mkdir(parents=True, exist_ok=True)

    # 1. A host-installed keyring — simplest, fully offline.
    for path in HOST_KEYRINGS:
        p = Path(path)
        if p.exists() and p.stat().st_size > 0:
            # The .gpg may be a symlink to a .pgp; resolve + read.
            data = p.read_bytes()
            if len(data) > 256:
                CACHED_KR.write_bytes(data)
                print(f"[build_realinrelease_img] seeded keyring cache "
                      f"from host {p} ({len(data)} bytes)")
                return data

    # 2. Fetch the debian-archive-keyring .deb off the mirror and
    #    extract the keyring file from it.
    print(f"[build_realinrelease_img] fetching keyring .deb index "
          f"{KEYRING_URL}")
    try:
        listing = _http_get(KEYRING_URL).decode("latin1")
    except Exception as e:                       # noqa: BLE001
        raise SystemExit(
            f"[build_realinrelease_img] could not list {KEYRING_URL}: "
            f"{e}\n[build_realinrelease_img] (and no cache / host "
            f"keyring) — SKIP")
    # Pick the newest-looking all-arch .deb from the directory listing.
    debs = sorted(
        part.split('"')[0]
        for part in listing.split('href="')[1:]
        if part.split('"')[0].endswith("_all.deb"))
    if not debs:
        raise SystemExit(
            "[build_realinrelease_img] no debian-archive-keyring "
            "_all.deb on the mirror — SKIP")
    deb_url = KEYRING_URL + debs[-1]
    print(f"[build_realinrelease_img] fetching {deb_url}")
    try:
        deb = _http_get(deb_url)
    except Exception as e:                       # noqa: BLE001
        raise SystemExit(
            f"[build_realinrelease_img] could not fetch {deb_url}: {e} "
            f"— SKIP")
    tmp_deb = CACHE / "debian-archive-keyring.deb"
    tmp_deb.write_bytes(deb)
    extract_dir = CACHE / "kr_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        raise SystemExit(
            "[build_realinrelease_img] dpkg-deb not available to "
            "unpack the keyring .deb — SKIP")
    subprocess.run([dpkg_deb, "-x", str(tmp_deb), str(extract_dir)],
                   check=True, capture_output=True)
    # The keyring file ships at usr/share/keyrings/debian-archive-keyring.gpg
    for cand in (extract_dir / "usr/share/keyrings"
                 / "debian-archive-keyring.gpg",):
        if cand.exists():
            data = cand.read_bytes()
            CACHED_KR.write_bytes(data)
            print(f"[build_realinrelease_img] extracted keyring "
                  f"({len(data)} bytes) -> {CACHED_KR}")
            return data
    raise SystemExit(
        "[build_realinrelease_img] keyring file not found inside the "
        ".deb — SKIP")


def build_ext4_with_files(out_path: Path, files: list):
    """Create a raw ext4 image holding the given (name, body) files."""
    mkfs    = _which("mkfs.ext4")
    debugfs = _which("debugfs")

    total = sum(len(body) for _, body in files)
    img_bytes = ((total + 4 * 1024 * 1024) // (1024 * 1024) + 1)
    img_bytes *= 1024 * 1024

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.truncate(img_bytes)

    subprocess.run(
        [mkfs, "-F", "-q", "-b", "4096", "-t", "ext4",
         "-L", "HAMNIX_EXT", "-O", "^has_journal", str(out_path)],
        check=True, capture_output=True,
    )

    for name, body in files:
        tmp = out_path.with_suffix(f".{name}.tmp")
        tmp.write_bytes(body)
        try:
            subprocess.run(
                [debugfs, "-w", "-f", "/dev/stdin", str(out_path)],
                input=f"write {tmp} {name}\n",
                text=True, check=True, capture_output=True,
            )
        finally:
            tmp.unlink(missing_ok=True)
        print(f"[build_realinrelease_img] wrote /{name} "
              f"({len(body)} bytes)")
    print(f"[build_realinrelease_img] image {out_path} "
          f"({img_bytes} bytes)")


def main() -> int:
    suite = DEFAULT_SUITE
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--suite" and i + 1 < len(args):
            suite = args[i + 1]; i += 2
        else:
            print(f"[build_realinrelease_img] unknown arg: {args[i]}",
                  file=sys.stderr)
            return 2

    inrelease = fetch_inrelease(suite)
    keyring   = fetch_keyring()

    build_ext4_with_files(
        OUT_IMG,
        [("InRelease", inrelease), ("keyring.gpg", keyring)],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
