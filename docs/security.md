# Hamnix security model — Plan 9-shape, namespace-as-authority

## TL;DR

Hamnix's native security model is **Plan 9**'s, not POSIX's. There is
**one hostowner** (uid 1) per installed system who owns everything and
runs privileged tools like `hpm`. Other accounts are **regular users**
(uid > 1) who get a restricted namespace at login — they literally
can't address dangerous file servers or partitions, so no permission
check needs to fire for the most important boundaries. **No setuid
binaries**, no `sudo`, no `su`. The elevation idiom is `newshell
hostowner` — a factotum-shape authenticated re-login, not a permission
flag on a binary.

POSIX-shape security (real `sudo`, `/etc/sudoers`, setuid bits) lives
**inside the Linux namespace** where Debian's own machinery runs
unmodified. The two worlds don't borrow each other's idioms.

## Why Plan 9, not POSIX

setuid binaries are responsible for an enormous share of historical
Unix CVEs (every parsing bug in a setuid utility is a privilege
escalation). Plan 9 deliberately rejected the model: authority should
be **namespace-shaped, not binary-shaped**. A regular user CAN'T
escalate by tricking a privileged binary because no binary holds
elevated authority in the first place — the user's namespace simply
doesn't bind the file servers a privileged operation would need.

Hamnix already has the substrate: per-process Pgrp + bind freeze +
named file servers via sentinel + `#by-id/<partuuid>` aliases. The
security model is the natural use of those primitives.

## Two worlds

**Hamnix-native side** — hostowner + namespace-restricted regular
users. No setuid. No sudo. Authority via namespace. This document.

**Linux namespace side** (inside `enter debian-12 { ... }` etc.) —
real Debian POSIX. Real `/etc/shadow`, real `sudoers`, real `sudo`
binary, real setuid bits. Hamnix doesn't reimplement; Debian's own
machinery runs unmodified. The two security models coexist because
they apply to different namespaces.

## Users

A user is an entry in `/etc/passwd`:

```
hostowner:1:1:/home/hostowner:/bin/hamsh
alice:1000:1000:/home/alice:/bin/hamsh
```

Format: `name:uid:gid:home:shell` (no GECOS field; KISS).

- **`hostowner`** (uid 1) — the machine owner. Owns `/`, `/etc`,
  `/bin`, `/var/lib/hpm/`, the rootfs partition, all `#hamnix-system`
  file servers. Runs `hpm`. Only one per installed system.
- **Regular users** (uid >= 1000) — own their `/home/<name>` only.
  See a restricted namespace at login.
- **System users** (uid 2..999) — reserved for services. Run by `svc`
  with a declared uid in the service definition. No login shell.

uid 0 is **unused**. The "root" idiom doesn't exist. uid 1 is the
hostowner because Plan 9 historically uses 1 for `glenda` / first
user; we follow.

### Authentication

Passwords live in `/etc/shadow`:

```
hostowner:$6$<salt>$<sha-512-crypt-hash>:<last-change-days>
alice:$6$<salt>$<sha-512-crypt-hash>:<last-change-days>
```

- Format mirrors Linux's `shadow(5)` so a future migration to/from a
  POSIX system stays mechanical.
- `$6$` = SHA-512-crypt (Linux default; we already have SHA-512 from
  the TLS stack). Iteration count baked at 5000 (Linux default).
- `<last-change-days>` is days since epoch; lets a future policy
  expire stale passwords.
- File is mode 0600, owned by hostowner. Regular users can't read it.

`bcrypt` / `argon2` are deferred — adding them would require new lib
code without changing the threat model materially for v1.

### The `auth` cdev

Authentication goes through a kernel-side `#auth` device (mounted at
`/dev/auth` per init's recipe). Userland never reads `/etc/shadow`
directly. Pattern:

```
fd = open("/dev/auth", ORDWR)
write(fd, "user hostowner\n")
write(fd, "pass " + plaintext + "\n")
read(fd, response)
# response = "ok" or "denied"
close(fd)
```

The kernel-side handler reads `/etc/shadow`, hashes the supplied
password with the recorded salt, constant-time compares. Userland
never gets the hash, never has direct shadow access. This is the
factotum-shape primitive — credential handling lives in a single
audited kernel path.

## Permissions

Files carry owner uid + group gid + 9 mode bits (`rwxrwxrwx`).
Stored in:
- Hamnix-native cdev returns: encode in the 9P-stat record
- ext4 on disk: the existing ext4 owner/group/mode fields (Hamnix
  already parses them on read; v1 will start writing them on create)

VFS open/create checks at every syscall boundary:
1. Path resolves to a file/directory with owner U, group G, mode M.
2. Caller has uid u, gid g.
3. If u == U: use owner bits.
4. Else if g == G: use group bits.
5. Else: use other bits.
6. Open request specifies OREAD/OWRITE/ORDWR; mode must permit it.
7. On denial: `-EPERM`, errstr "permission denied".

**No setuid / setgid / sticky.** These don't exist in the on-disk
format Hamnix writes. (The kernel ignores them on Debian-side files
inside the linux ns — that ns has its own VFS path.)

## Namespace as authority

The strongest layer: **regular users see a restricted namespace** at
login. Their hamsh inherits a namespace recipe (`/etc/users/<name>.ns`
— optional per-user override; falls back to `/etc/users/default.ns`)
that:

- Binds `/home/<their-name>` writable.
- Binds `/tmp` writable (per-user tmp, isolated).
- Binds `/bin`, `/usr/bin` from `#hamnix-system` READ-ONLY.
- Does **NOT** bind `/dev/blk/*` (raw block devices).
- Does **NOT** bind `#by-id/<partuuid>` (raw partition roots).
- Does **NOT** bind `/var/lib/hpm/` (hpm's state).
- Does **NOT** bind named-server creation paths.

This means a regular user can't even `cat /dev/blk/vda` (the path
doesn't resolve in their namespace). The permission check is a
defense-in-depth fallback; the primary boundary is "you can't name
it, so you can't open it."

The hostowner gets the full namespace recipe (init's default) with
everything bound.

## The elevation idiom: `newshell <user>`

POSIX `sudo` = "elevate THIS command's authority temporarily."
Plan 9 / Hamnix = "open a new shell session AS that user, with their
full namespace."

```
$ newshell hostowner
password: ********
[hostowner@hamnix ~]$ hpm install linux-debian-12
[hostowner@hamnix ~]$ exit
$ # back to your regular-user shell
```

`newshell` is a hamsh builtin (not a binary at all, so it can't be
tampered with). It:
1. Reads the target uid from `/etc/passwd`.
2. Prompts for password.
3. Writes to `/dev/auth` to authenticate.
4. On success: `rfork(RFPROC|RFNAMEG)`, switch task uid/gid in the
   child, load the target user's namespace recipe, `exec /bin/hamsh`.
5. Parent (your original shell) sees a child it can wait on.

No setuid binary. No environment leak. No setuid path-search game.
Authority is granted by the kernel after password auth, not stolen
from a binary's setuid bit.

A second idiom for one-shots: `newshell hostowner -c '<command>'` —
runs `<command>` as hostowner and exits. Same auth path.

## hpm + authority

hpm refuses to run if `uid != 1`. Single check at start; clean error:

```
$ hpm install linux-debian-12
hpm: package installation requires hostowner. Try `newshell hostowner`.
```

Combined with namespace restriction: regular users can't open
`/var/lib/hpm/installed.json` to read state, can't open `/dev/blk/*`
to write to partitions, can't address `#by-id/...` to bypass. The
uid check is documentation; the namespace is the actual gate.

## Services and uids

`/etc/svc/<name>.hamsh` gains an optional `uid:` field:

```
name: postgres
uid: 50           # system uid for postgres
ns: postgres-svc  # the namespace recipe with #postgres-data bound
exec: /usr/bin/postgres
```

`svc` starts the service in the supervisor (init's namespace,
hostowner-owned), then before `exec` switches uid + applies the
service's namespace recipe. Service files live in a namespace where
ONLY their state directories are writable. Compromise of one service
doesn't grant access to another's data.

System uids 2..999 are baked in `/etc/passwd`:

```
sshd:2:2:/var/empty:/bin/false
hamsh-svc:3:3:/var/empty:/bin/false
postgres:50:50:/var/lib/postgres:/bin/false
nginx-svc:80:80:/var/empty:/bin/false
```

`/bin/false` shell means no interactive login.

## Live ISO

The live ISO ships with hostowner `live` / password `hamnix`:

```
# /etc/passwd
live:1:1:/home/live:/bin/hamsh

# /etc/shadow
live:$6$<salt>$<hash of 'hamnix'>:<days>
```

No regular users on the live system; everything runs as `live`. The
installer replaces this with the user's choice before laying down
`/etc/passwd` on the installed system.

## Installer prompts

Following Debian's UX (different model underneath):

```
[install] Hostowner username: hamnix
[install] Hostowner password: ********
[install] Confirm password:   ********

[install] Create additional regular users? [y/N] n

[install] Install Linux runtime? [Y/n] y
[install]   Debian distro: [1] debian-12 (bookworm) [2] debian-13 (trixie)
[install]   Selection: 1
[install]   Debian-side POSIX-root password: ********
[install]   (this is the root password INSIDE `enter debian-12`; separate
[install]    from your Hamnix hostowner password)
[install]   Confirm: ********

[install] Writing /etc/passwd + /etc/shadow on target...
[install] Done. Reboot from disk to continue.
```

If the user opts out of installing a Linux runtime, the second
password prompt is skipped. They can `hpm install linux-debian-12`
later, at which point that package's `install.hamsh` will prompt
for the Debian-side root password.

## Linux namespace uid mapping

Inside `enter debian-12 { /bin/bash }`:
- Hamnix hostowner (uid 1) → Debian root (uid 0).
- Hamnix regular user `alice` (uid 1000) → Debian uid 1000 (mapped 1:1).
- The Linux namespace's own `/etc/passwd` is the Debian rootfs's
  passwd; Hamnix's `/etc/passwd` is not bound into the linux ns.
- `sudo` inside the linux ns prompts the Debian-side root password.
  This is **independent** from the Hamnix hostowner password.

This split keeps things safe: a Debian binary compromised inside
the linux ns can escalate to Debian-root inside that ns but can't
touch Hamnix-side state (the linux ns is `clean` and doesn't bind
Hamnix's privileged paths).

## What this document does NOT include

- **Capabilities** (Linux fine-grained privilege). The hostowner-or-not
  binary distinction is enough for v1. If a future need surfaces,
  add per-namespace capability binds rather than a Linux-shape
  capability set.
- **SELinux / AppArmor / TOMOYO**. Mandatory access control on top
  of DAC — much heavier infrastructure than v1 needs. Namespace
  restriction is already mandatory-ish (you can't grant authority
  you don't have).
- **ACLs**. Owner/group/other is the v1 ceiling. If real
  multi-collaborator setups need finer control, revisit.
- **Quotas**. No per-user disk quota in v1.
- **PAM**. Authentication is one path (`/dev/auth` → SHA-512-crypt
  against `/etc/shadow`); no pluggable modules.
- **Containers / cgroups**. Plan 9 namespaces are the substitute;
  per-process namespace is the only isolation surface.

## Implementation surface (one sweeping agent, after hpm + installer)

Phases:
1. `uid`/`gid` fields on TaskStruct; inherit on fork; passed through
   `rfork`.
2. `/etc/passwd` + `/etc/shadow` formats; parser library in `lib/`.
3. SHA-512-crypt (`lib/crypt/sha512_crypt.ad`) — re-use existing
   `lib/sha2/sha512.ad`.
4. `#auth` cdev (`sys/src/9/cdev/auth.ad`) — credential check; never
   exposes hashes to userland.
5. VFS permission check on `open`/`create`/`exec`.
6. ext4 + cdev owner/group/mode on write paths.
7. `newshell` hamsh builtin.
8. hpm uid==1 gate.
9. `svc` uid switching before exec.
10. `/etc/users/<name>.ns` recipe loading at login.
11. Live ISO bakes `live:hamnix`.
12. Installer prompts.

Test coverage:
- A regular user can't open `/dev/blk/vda`.
- A regular user can't open `/var/lib/hpm/installed.json`.
- A regular user can run `hpm list` (read-only commands? probably
  permit; but `hpm install` is denied).
- `newshell hostowner` with right password succeeds; wrong password
  fails; rate-limited (1 attempt/second to thwart brute force).
- Service running as uid 50 can't read another service's state dir.

## Cross-refs

- [`docs/packages.md`](packages.md) — hpm; gates on uid==1
- [`docs/architecture.md`](architecture.md) — namespace + file
  server primitives this builds on
- [`docs/rootfs_partition.md`](rootfs_partition.md) — `#by-id/...`
  and named server semantics; restricted users don't see these
- `init/svc.ad` — service supervision; will gain `uid:` support
