---
name: project-plan9-pivot
description: 2026-05-18 Plan 9-only freeze SUPERSEDED 2026-05-19 by refocused-scope cron (real-hw boot + Python/apt). V4.1/V4.2 still pending but no longer block non-9P merges.
metadata: 
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

On 2026-05-18 user redirected the Hamnix build:

  > "We definitely need to fix this. The root namespace should expose Plan 9 services at known paths (/n/, /srv/, /proc/<pid>/ns/-equivalent) by default. We need to do wide sweeping adjustments here... cancel the non-9P related agents and make sure that we get our plan nine base solidified before we continue forward in any other direction. This needs to function like a Plan 9 system. Where namespaces are inherited and can be constrained further and further down. Where you can mount 9P file systems wherever and use their files."

**Why:** what shipped through M16.122 (`distrorun`) and earlier was *not* Plan 9 namespaces — it was path-prefix rewriting against the in-kernel VFS via a global `mnttab`. `mount(srvfd, ...)` stored the fd but did not speak 9P; `bind` did `s/old/new/` on paths. Per-process `namespace_id` exists on `TaskStruct` but isn't consulted. See [[project-endgame]] for the destination this constrains.

**Status as of 2026-05-19:** The "no non-9P merges" rule was lifted in practice. Active orchestration is the refocused-scope cron (real-hardware boot, drivers, Python/apt). Stack canaries, atkbd handshake, hamsh $-expansion, TLS-CERT V5..5.4, HTTP gzip+redirects, e820 dynamic id-map, RTC reader, TCP rx-ring all merged after the freeze. V4.1 (kernel-side `_p9_send`/`_p9_recv` through `fs/pipe.ad`) and V4.2 (`hamwd` as rio-shape 9P server) are still pending.

**Re-prioritised 2026-05-20:** the user made "bash it into Plan 9 shape" a STANDING co-equal priority alongside the functional pushes. Each cron tick should consider dispatching Plan-9-shaping work, not only feature work. Plan-9-shaping = no global filesystem routes; real per-process namespaces (not global-`mnttab` path rewriting); services as file servers at known paths; 9P mounts everywhere; the `distrofs` daemon + shim-launcher (`rfork(RFNAMEG)`+mount) path; 9P V4.1 kernel↔userland-server real-fd dispatch. **Two hard invariants while doing this:** (1) must keep loading Linux kernel modules — the L-track `.ko` shim stays in-kernel, untouched; (2) must keep running Linux userspace binaries in Linux-shaped per-process distro namespaces (the distrofs work). Plan-9-shaping must not break either track.

**Original guidance (now archival):**
- No non-9P feature work merges to `main` until V0..V4 below land. This includes useful in-progress agents whose worktrees were shelved.
- Phased single-agent roadmap (user-approved):
  - **V0**: `docs/9p.md` spec + `lib/9p/9p.ad` codec + tests. (in flight at writing time as agent `ac72238e0b460fe0b`)
  - **V1**: kernel 9P client in `sys/src/9/port/`; `do_mount` does `Tversion`+`Tattach`; `resolve_path` dispatches `CHAN_KIND_SRV` chans via `Twalk`+`Topen`+`Tread`+`Twrite`.
  - **V2**: per-process `mnttab` — replace global table in `sys/src/9/port/chan.ad` with a per-`TaskStruct` table; `rfork(RFNAMEG)` actually clones; child constraints stick. This is where "namespaces" become real.
  - **V3**: root namespace defaults at boot — init wires `/n/`, `/srv/`, `/proc/<pid>/ns/`-equivalent (Plan 9 uses `/proc/$pid/ns` text file listing the bindings).
  - **V4 partial**: `sys_srv_post(275)` + `sys_srv_open(276)` + minimum userspace 9P server (`user/p9srv_demo.ad`) all landed by 2026-05-18 at `5233d18`.
- **V4.1 (pending)**: kernel-side `_p9_send` / `_p9_recv` in `sys/src/9/port/9p_client.ad` are stubbed for real-fd dispatch — they only work in V1's smoke-mode internal pipe path. Until V4.1 wires them through `fs/pipe.ad`'s underlying read/write, `sys_mount(userspace_srvfd, ...)` records the mount but the kernel client can't walk/open/read through it. **This blocks rio implementation**: rio needs the kernel to consume the rio process's 9P server, which goes through this stubbed path. Re-entrancy concern flagged by V1's agent applies — vfs_read/vfs_write may not be safe to call from inside a vfs_open dispatch on a different fd; safer to drop through to pipe.ad's internal API.
- **V4.2 (pending)**: `user/hamwd.ad` rewritten as a real rio-shape 9P server using `lib/9p/`. Blocked on V4.1 + the four user Qs in [[project-rio-open-questions]].
- Wide architectural changes (V2, V3) are single-agent jobs per [[feedback-agent-git-discipline]]. V0 and V4 are narrow enough for parallel slots if other 9P work is happening.
- ~~VTNext (Layer-4 display protocol)~~ **LEGACY 2026-05-20** — the user
  retired VTNext; the display layer is now "Rio-style" (the Plan 9 rio
  windowing model, consistent with the `rio`/`hamwd` direction in
  [[project-rio-open-questions]]). Do NOT resurrect or merge VTNext.

**Shelved worktrees** (mine for code later):
- `agent-aa0bd045ebe77def2` — VMA `/bin/true` #GP debug, mid-analysis. Identified: RIP=0xa41a4b is inside libc.so.6's mmap'd region (not in app at 0xc14000..0xc19000 or ld.so at 0xc19000..0xc50000). Suspected root cause: glibc's `_dl_map_segments` pattern (anon PROT_NONE reserve → MAP_FIXED overlay per PT_LOAD) interacting with `vma_alloc`'s alias-creation path. May involve `alloc_pages` returning a region whose actual size exceeds requested `length` so the VMA bound doesn't match what ld.so thinks it mapped. Re-investigate once Plan 9 base is in.
- `agent-abd29aadcd133f9a3` — DHCP renew/rebind, mid-compile.
- `agent-ad81b46a948cbe173` — TLS Finished + app-data, mid-edit of `_tls_drive_post_sh`.
- `agent-a106d779f566266ec` — GPT mkpart writes.
- ~~`agent-abaa05e205853d5bf` — VTNext-v2 lib~~ — VTNext is LEGACY
  (2026-05-20); this worktree was removed in the 2026-05-20 cleanup.
  Branch `worktree-agent-abaa05e205853d5bf` (`ebd9445`) still exists for
  archaeology but is not for merge — VTNext is replaced by Rio-style.

NOTE 2026-05-20: the ~150 stale agent worktrees were cleaned up — only
12 remain (the active agent + 11 with uncommitted work). Removed
worktree directories' branches are preserved; the shelved entries above
that still exist as worktrees are `aa0bd045`, `abd29aad`, `ad81b46a`,
`a106d779`.

See [[feedback-plan9-namespace-framing]] for the framing language to use throughout (no "rootfs", no "host", no "sandbox" — namespaces are per-process bindings to file servers).
