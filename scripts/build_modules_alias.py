#!/usr/bin/env python3
"""
scripts/build_modules_alias.py — Linux-shape modules.alias generator.

Scans `kernel-modules/<name>/<name>.ko` (the convention every Linux
driver shipped through Hamnix's L-shim uses — one stock .ko per
directory) and emits a flat text table mapping each module's
`MODULE_DEVICE_TABLE(pci, ...)` aliases to the module name. The
in-kernel modprobe_auto_load() (kernel/modprobe.ad) walks this table
at boot to pick the right .ko for each enumerated PCI device.

Output line format mirrors Linux's `depmod -a`-emitted
/lib/modules/<ver>/modules.alias exactly:

    alias <pci-pattern> <module-name>

(One alias per line. The "alias " prefix is stripped by the in-kernel
parser since every line is an alias; we keep it so the file is
recognisable to a Linux sysadmin reading it.)

Example:
    alias pci:v00008086d000010D3sv*sd*bc*sc*i* e1000e
    alias pci:v000010ECd00008168sv*sd*bc*sc*i* r8169

This script is invoked by scripts/build_initramfs.py when
ENABLE_AUTO_MODULES=1 is set. It writes the table to a temp path the
caller passes in (default: build/modules.alias). Idempotent — re-runs
overwrite the output.

Requires `modinfo` from kmod (Debian: kmod package, /sbin/modinfo).
Skips any .ko whose modinfo lookup fails (logs a warning); the rest
of the table is still emitted.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_modinfo() -> str:
    """Locate the kmod modinfo binary. Debian installs it at /sbin
    /modinfo (not on PATH for non-root users on some configurations),
    so fall back to a couple of well-known paths before giving up."""
    for cand in ("modinfo", "/sbin/modinfo", "/usr/sbin/modinfo"):
        p = shutil.which(cand) if "/" not in cand else (
            cand if os.path.exists(cand) else None)
        if p:
            return p
    raise SystemExit(
        "build_modules_alias: modinfo not found. Install the kmod "
        "package (Debian: `apt install kmod`).")


def _module_name(modinfo: str, ko_path: Path) -> str | None:
    """modinfo -F name <path> prints the module's internal name (the
    one its alias table will be looked up by). Returns None on
    failure — the caller logs a warning and skips the module."""
    try:
        out = subprocess.run(
            [modinfo, "-F", "name", str(ko_path)],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"  WARN: modinfo -F name {ko_path} failed: "
              f"{e.stderr.strip() or e}", file=sys.stderr)
        return None
    if not out:
        # modinfo succeeded but printed no name; fall back to the
        # filename stem (matches Linux's depmod behaviour for a .ko
        # that omits MODULE_NAME but has aliases).
        return ko_path.stem
    return out


def _module_aliases(modinfo: str, ko_path: Path) -> list[str]:
    """modinfo -F alias <path> prints one alias per line. Returns an
    empty list if the module has no aliases or modinfo fails."""
    try:
        out = subprocess.run(
            [modinfo, "-F", "alias", str(ko_path)],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        print(f"  WARN: modinfo -F alias {ko_path} failed: "
              f"{e.stderr.strip() or e}", file=sys.stderr)
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def build_alias_table(modules_root: Path) -> str:
    """Walk every kernel-modules/<name>/<name>.ko (and any *.ko in
    such a directory; some modules ship multiple .ko siblings), emit
    one `alias <pattern> <module>` line per MODULE_DEVICE_TABLE entry,
    and return the joined text (trailing newline). The order is
    deterministic — sorted by directory name then by alias line — so
    re-runs produce byte-identical output (important for the cpio
    archive's hash stability)."""
    modinfo = _find_modinfo()
    lines: list[str] = []
    n_modules = 0
    n_aliases = 0
    if not modules_root.is_dir():
        # No kernel-modules/ tree — emit an empty table (the in-kernel
        # parser handles 0 entries fine; it just won't load anything).
        return ""
    for sub in sorted(modules_root.iterdir()):
        if not sub.is_dir():
            continue
        kos = sorted(sub.glob("*.ko"))
        if not kos:
            continue
        for ko in kos:
            name = _module_name(modinfo, ko)
            if name is None:
                continue
            aliases = _module_aliases(modinfo, ko)
            if not aliases:
                # No PCI/USB/etc. table — the module is either a
                # leaf utility (nothing to auto-bind to) or its
                # MODULE_DEVICE_TABLE got stripped. Skip silently.
                continue
            for alias in aliases:
                lines.append(f"alias {alias} {name}")
                n_aliases += 1
            n_modules += 1
    # Header comment is useful when grepping; trailing newline makes
    # cat-on-host friendly.
    if lines:
        header = (
            "# Hamnix auto-generated module alias table.\n"
            "# Source: kernel-modules/<name>/<name>.ko + "
            "`modinfo -F alias`.\n"
            f"# {n_modules} modules / {n_aliases} aliases.\n"
        )
    else:
        header = ("# Hamnix auto-generated module alias table.\n"
                  "# (No kernel-modules/<name>/*.ko present.)\n")
    return header + "\n".join(lines) + ("\n" if lines else "")


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    modules_root = here / "kernel-modules"
    # Default output: build/modules.alias. build_initramfs.py reads
    # it back to plant /lib/modules/modules.alias into the cpio.
    out_arg = sys.argv[1] if len(sys.argv) >= 2 else "build/modules.alias"
    out_path = Path(out_arg)
    if not out_path.is_absolute():
        out_path = here / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = build_alias_table(modules_root)
    out_path.write_text(text)
    print(f"  wrote {out_path} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
