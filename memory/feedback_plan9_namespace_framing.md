---
name: plan9-namespace-framing
description: "When describing Hamnix namespaces, avoid Linux-container vocabulary (\"rootfs\", \"host\", \"sandbox\", \"view of the real /\"); use file-server + per-process-binding framing instead."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

In Plan 9, there is **no global root and no kernel-level "real /"**. The
kernel only knows about file servers (disk filesystem drivers, device
drivers, 9P servers). A namespace is a per-process binding of paths to
those servers. Init's namespace is built at boot by mounting hamnixfs
at /; later processes inherit and can modify their own copy. No
namespace is privileged over another — init's just exists first.

A distro-shape namespace is the same kind of thing as init's
namespace; both are just namespaces. There's no "real Hamnix /"
that the distro namespace is a sandboxed view of.

**Why:** When I wrote up the distro-shape-namespaces spec, I used
phrases like "host Hamnix rootfs," "native rootfs," "Linux compat
is sandboxed," and "what schroot does." Each smuggles in the
Linux-with-extra-steps trap — a privileged global FS that namespaces
hide from binaries. The user (2026-05-17) called this out: "schroot
creates a chroot that hides 'the real /'; Hamnix's distrorun creates a
namespace that's no more or less 'real' than init's." A user could
legitimately boot Hamnix and immediately mount a remote 9P export at
/ instead of the local disk — that's a valid Hamnix configuration,
not an escape from anything.

**How to apply:** When describing namespaces, mounts, or filesystem
layout in Hamnix docs/specs/commit-messages:

- **Avoid:** "rootfs", "host", "sandbox", "view of the real /", "isolate
  from /", "the system's /", "underlying filesystem", "outside the
  namespace nothing changes", "privileged FS".
- **Use:** "init's namespace", "file server", "binding", "this
  namespace mounts X at /", "the file server backing /", "the
  convention init follows at boot is to mount hamnixfs at /".
- Linux's schroot/containers are NOT the closest analog in spirit
  even if they look superficially similar — the analogy misleads.
  9front's `auth/none` and `none(1)` are the right inspiration.
- The distinction matters because Hamnix's Plan 9 surface (Layer 1
  per [[plan9-layered-architecture]]) is the moat — getting the
  framing right is what keeps it from being "Linux containers with
  extra steps."
