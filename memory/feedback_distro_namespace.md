---
name: feedback-distro-namespace
description: Linux-binary shims (dpkg/apt/httpd/etc.) must run inside a distro-shaped namespace served by a userland distrofs 9P daemon — never global filesystem paths.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

The apt/dpkg/httpd userland work drifted into writing GLOBAL absolute
paths (`/var/lib/dpkg/`, `/var/cache/apt/`, `/var/www`). The
writable-`/var` commit `86a13bd` made `/var` a global tmpfs subtree.
On 2026-05-20 the user flagged this as wrong: it contradicts the Plan 9
namespace model the project committed to (no global root; per-process
namespaces; bindings to file servers).

**The decided architecture (user, 2026-05-20):**
- Linux-binary shims run inside a **distro-shaped namespace**.
- That namespace's filesystem (`/var`, `/usr`, `/etc`, …) is exported by
  a **userland 9P file server daemon — `distrofs`** — in the same spirit
  as `rio` / `hamwd` (Plan 9-pure: a daemon, not kernel-baked).
- The shim launcher does `rfork(RFNAMEG)` → mount/bind the distrofs 9P
  server into the new private namespace → then exec the Linux binary.
  `dpkg` still *sees* `/var/lib/dpkg`, but it's a per-process binding to
  the distrofs server — NOT a global route. Different distros / package
  roots never collide; nothing leaks into the host namespace.
- `86a13bd` (global `/var` tmpfs) is **superseded** by this — not a
  standalone revert (dpkg/apt currently depend on `/var`); it gets
  replaced as the namespace path lands and the shims migrate.

**How to apply:**
- Never dispatch shim/distro work that writes global paths. Any task
  prompt touching dpkg/apt/distro storage must say: the storage is the
  distrofs 9P tree, accessed inside the shim's namespace.
- Possible prerequisite: 9P V4.1 (kernel-side `_p9_send`/`_p9_recv`
  through `fs/pipe.ad` real-fd dispatch) — flagged pending in
  [[project-plan9-pivot]] as the thing that lets the kernel consume a
  userland 9P server. distrofs can be built + tested standalone against
  a 9P client first; the mount-into-namespace step needs V4.1.
- Algorithm/logic work (apt dependency resolution, dpkg dedup) is
  storage-location-agnostic and fine to keep — only the WHERE moves.

Related: [[project-plan9-pivot]], [[feedback-plan9-namespace-framing]],
[[project-endgame]].
