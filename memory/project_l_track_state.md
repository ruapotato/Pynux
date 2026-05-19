---
name: project-l-track-state
description: "Snapshot of Hamnix's L-series + U-series ABI tracks as of L1..L43 + U1..U8 (commit a45d72d)"
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

State of the L-series + U-series tracks as of 2026-05-16
(commit 58e845e + L48 + L49 uncommitted work in tree).
32/32 integration tests pass; build-lock fix (scripts/_build_lock.sh)
makes test invocations atomic against the shared
fs/initramfs_blob.S + build/hamnix-vmlinux.elf state.

**Major milestone (U5, 2026-05-16):** first end-to-end Linux ELF64
binary runs on Hamnix. `tests/u-binary/src/hello/hello.S` (pure asm
`write(1, msg, 27)` + `exit_group(0)` via Linux syscall numbers 1/231,
OSABI stamped to Linux via post-`ld` `dd`) loads via `_load_elf64` in
`fs/elf.ad`, the new task gets `is_linux_userspace=1`, syscalls route
through `linux_u_syscall_dispatch` in `linux_abi/u_syscalls.ad`,
output appears on the kernel console.

**U-series progress (Linux userspace ABI):**
  U1 — TaskStruct.is_linux_userspace flag + do_syscall dispatch
       fork. Native tasks unaffected.
  U2 — fs/elf.ad gains elf_is_linux_binary() + PT_INTERP reader.
  U3 — elf_load_blob's Linux-ABI detection separated from flag
       application: sets `elf_last_was_linux: int32`; SYS_SPAWN /
       SYS_EXECVE in arch/x86/kernel/syscall.ad apply it to the
       correct slot (child for SPAWN, current for EXECVE). The
       earlier bug — flipping the flag on the parent during SPAWN
       — was real and surfaced via U5's first run.
  U4 — Real handlers for read/write/close/lseek/exit/exit_group/
       brk/getpid/arch_prctl(ARCH_SET_FS)/set_tid_address/
       clock_gettime/chdir/getcwd/mkdir/unlink/dup/dup2/kill.
  U5 — ELFCLASS64 program-header parser in fs/elf.ad (`_load_elf64`,
       dispatched on `e_ident[4]`). Tests/u-binary/src/hello.
       First Linux ELF on Hamnix.
  U6 — Multi-syscall asm fixture exercises getpid (39),
       clock_gettime(CLOCK_MONOTONIC) (228), brk(NULL)+brk(grow)
       (12), write (1), exit_group (231). Verified the 4 GiB
       identity map (`arch/x86/boot/header.S` PDPT entry `0x87 =
       PS|US|RW|P`) makes kmalloc-backed memory U=1 for free —
       brk and anon-mmap need no separate user mapping pass.
  U7 — writev (20) walks struct iovec[]; mmap (9) anon|private
       kmalloc-backs + tracks in 16-slot table; munmap (11) frees
       by base. arch/x86/kernel/syscall_64.S widened to forward
       %r8/%r9 (a4/a5) so 6-arg Linux syscalls (mmap) work end to
       end.
  U8 — uname (63) fills 390-byte struct utsname (sysname=Hamnix,
       machine=x86_64, release=6.12.0-hamnix). fstat (5) builds
       Linux's 144-byte struct stat — st_size via lseek(SEEK_END)
       round-trip so it works on initramfs/tmpfs/ext4 without new
       VFS plumbing. newfstatat (262) honours AT_FDCWD.

**L-series progress (Linux kernel ABI):**
  L1..L40 — see earlier history. L36 was first Debian .ko init==0;
       L37 dependency chain; L38 stack-protector + crypto runtime
       symbols; L39 12 pre-emptive data symbols (cpu_online_mask,
       __per_cpu_offset, etc.).
  L40-prep — real ACPI RSDP/XSDT/MADT/MCFG parsing wired and
       verified (acpi: 2 enabled CPU(s) in MADT).
  L41 — nf_defrag_ipv4.ko loads with init=0 — first netfilter
       module. New `linux_abi/api_pernet.ad`:
       register_pernet_subsys, unregister_pernet_subsys, ip_defrag,
       __local_bh_enable_ip, nf_defrag_v4_hook (data),
       pcpu_hot (64-byte zero buffer). 4-slot pernet table.
       112 relocs, 0 unresolved.
  L42 — crc16.ko (Bluetooth HCI / T10-PI / SCSI ULD) library-only
       load. Zero-gap (only UND was __x86_return_thunk, already
       in exports.ad).
  L43 — crc7.ko (MMC/SD command CRC) + crc-itu-t.ko (V.41 CRC for
       HDLC/PPP/ISDN) both library-only. Zero-gap.
  L44 — lib80211.ko (802.11 crypto-ops registration core), first
       non-zero-gap distro module. New `linux_abi/api_lib80211.ad`
       (~330 lines): __list_add_valid_or_report,
       __list_del_entry_valid_or_report, __x86_indirect_thunk_rax,
       module_put, add_timer, init_timer_key, __kmalloc_cache_noprof,
       jiffies (DATA), kmalloc_caches (DATA, 832-byte zero buffer).
  L45 — raid6_pq.ko (RAID6 P+Q syndrome math), 9th distro module.
       New `linux_abi/api_raid6.ad` (~215 lines):
       get_free_pages_noprof, free_pages, __SCT__preempt_schedule,
       kernel_fpu_begin_mask, kernel_fpu_end,
       __x86_indirect_thunk_rcx, __x86_indirect_thunk_r8.
       Surfaced two real bugs: insmod path-length cap + IRQ-masked
       init for the jiffies-bench tick wait — both fixed in
       loader.ad.
  L46 — xor.ko (RAID5 XOR-arithmetic library), 10th distro module.
       Only 2 new symbols vs raid6_pq: appended into api_raid6.ad
       (now 254 lines): __x86_indirect_thunk_r9,
       __x86_indirect_thunk_r11 — both `pop %rbp; jmp *%rN`
       retpoline thunks. Init returns 0.
  L47 — nf_log_syslog.ko (netfilter syslog-logger backend), 11th
       distro module. New `linux_abi/api_nf_log.ad` (~362 lines)
       closes a 14-symbol gap:
       nf_log_register/unregister/set/unset (init+exit paths),
       nf_log_buf_open/_add/_close (runtime), dev_get_by_index_rcu,
       skb_copy_bits, from_kuid_munged, from_kgid_munged,
       _raw_read_lock_bh, _raw_read_unlock_bh,
       init_net (DATA, 64-byte placeholder),
       init_user_ns (DATA, 64-byte placeholder),
       sysctl_nf_log_all_netns (DATA, int32 = 0).
       Init path registers a logger per protocol family
       (IPv4/IPv6/ARP/BRIDGE/NETDEV), all return 0 → init=0.
       Module not modified: register_pernet_subsys already from L41.
  L48 — nfnetlink.ko (netfilter <-> netlink message bus), 12th
       distro module. New `linux_abi/api_netlink.ad` (~428 lines)
       closes a 22-symbol gap.
  L49 — Hash-module batch shipping FIVE stock Debian .ko's at once
       (13th..17th distro module loads). New `linux_abi/api_l49.ad`
       (226 lines) closes a 5-symbol gap shared across the batch:
         memcpy                 — exposes the kernel's C-runtime
                                  memcpy under the Linux ABI name.
                                  Reached by md4/rmd160/blake2b's
                                  shash update path (runtime only).
         __warn_printk          — printk-backed WARN() handler.
                                  Variadic tail dropped (same pattern
                                  as _linux_printk_shim). Runtime only.
         gf128mul_init_4k_lle   — ghash setkey runtime; returns address
                                  of a 64-byte zero placeholder so the
                                  caller's NULL-check passes.
         gf128mul_4k_lle        — ghash per-block multiply; no-op body.
         kfree_sensitive        — secure-erase wrapper around kfree;
                                  best-effort 64-byte memset(0) before
                                  freeing (Hamnix's slab can't lookup
                                  object size yet — same blocker as
                                  krealloc).
       Module-by-module:
         crc32_generic.ko       — zero-gap; all 5 UND already in
                                  exports.ad (crc32_le, crypto_register_
                                  shash[es]/unregister_*, fentry, thunk).
         md4.ko                 — needs memcpy + __warn_printk; init
                                  tail-jumps to crypto_register_shash.
         rmd160.ko              — same shims as md4.
         blake2b_generic.ko     — same shims as md4; uses bulk
                                  crypto_register_shashes (count=4).
         ghash-generic.ko       — needs the three gf128mul_*/kfree_
                                  sensitive shims; init tail-jumps to
                                  crypto_register_shash.
       All five init paths return 0 → init=0. Test scripts:
       scripts/test_l49_{crc32_generic,md4,rmd160,blake2b_generic,
       ghash_generic}.sh — each PASSes.

**Counts:**
  - Linux kernel symbols exported under stock names: 274
    (linux_abi/exports.ad + 31 api_*.ad files)
  - Adder lines of linux_abi/ infrastructure: ~9700
  - GNU-style user binaries in /bin/: ~60
  - Linux test fixtures (host-built static ELF64): 4 (u_hello,
    u_multi, u_mmap, u_stat)
  - /etc baseline files: 20
  - Integration tests: 32+ (all green)
  - Stock Debian .ko load count: 17 (crc8, crc16, crc32c_generic,
    libcrc32c, nf_defrag_ipv4, crc7, crc-itu-t, lib80211,
    raid6_pq, xor, nf_log_syslog, nfnetlink, crc32_generic, md4,
    rmd160, blake2b_generic, ghash-generic)
  - MAX_EXPORTS budget: 274 / 512 used (238 remaining)

**Distro module backlog (real shim work each):**
  - nf_conntrack* helpers: blocked on nf_conntrack core (155 UND)
  - 8021q.ko (~118 UND, VLAN)
  - libphy.ko (~153 UND, Ethernet PHY)
  - chacha20poly1305.ko (~20-UND gap; needs aead_register_instance,
    skcipher_walk_*, scatterwalk_*, sg_init_one — medium)
  - crypto_null.ko (~10-UND gap; needs crypto_register_skcipher,
    skcipher_walk_*, _raw_spin_lock_bh — small/medium)
  - poly1305_generic.ko (~5-UND gap; needs poly1305_core_* —
    requires lib/crypto/poly1305-donna math import)
  - chacha_generic.ko (~6-UND gap; needs skcipher_walk_* + per-tfm
    chacha_crypt_generic implementation)
  - des_generic.ko (~8-UND gap; needs des_expand_key/encrypt/decrypt
    + crypto_register_algs)
  - curve25519-generic.ko (~10-UND gap; needs sg_copy_*,
    crypto_register_kpp, wait_for_random_bytes)
  - xxhash_generic.ko (~4-UND gap; needs lib/xxhash.c port)

**Next natural milestones (in priority order):**
  - U9 — `stat`/`lstat` (4/6), `openat` (257) wired to _u_open via
    AT_FDCWD shift, `access` (21), `readlink` (89) returning
    -EINVAL honestly.
  - U10 — ELF64 reloc-aware loader (.rela.dyn / .rela.plt
    processing) so binaries with absolute pointers in .rodata/.data
    work. This is the blocker before glibc-static binaries can run.
  - L44 — first non-zero-gap distro module: lib80211 likely,
    needing slab/timer/spinlock shim work in api_*.ad.
  - L45+ — usbcore, then xhci_hcd. Real-hardware drivers.
  - tests/linux-modules/Makefile linux_tree target — clone
    Linux 6.12.48 + build, then validate every M1..M15 .ko
    fixture against Hamnix's loader.

Related: [[project-endgame]] for L→U→NVIDIA→Debian-distro arc.

---

**L59 delta (2026-05-17):** nf_conntrack.ko + udf.ko both load with
`init returned 0`. New file `linux_abi/api_l59.ad` (~1140 lines)
closes a 117-symbol gap split across two modules:

  * nf_conntrack.ko (28th distro module to load) — 75 UND symbols
    new in L59, grouped in 21 sections. The big-ticket additions are
    Linux's BPF/BTF kfunc registration (register_btf_kfunc_id_set,
    bpf_log, btf_type_by_id), the workqueue globals
    (system_wq/system_power_efficient_wq DATA + delayed_work_timer_fn
    + mod_delayed_work_on + queue_delayed_work_on), schedule/msleep/
    synchronize_net/synchronize_rcu_expedited, the IPv6 helpers
    (__ipv6_addr_type, ipv6_skip_exthdr, nf_ct_frag6_gather), the
    netfilter checksum family (nf_checksum/_partial, nf_ip{,6}_checksum,
    inet_proto_csum_replace4), nf_conntrack's own hook tables
    (nf_ct_hook, nf_nat_hook, nf_ct_zone_dflt — all DATA), the
    nf_defrag enable/disable refcount API (nf_defrag_ipv{4,6}_{enable,
    disable}), proc/sysctl machinery (register_net_sysctl_sz +
    unregister_net_sysctl_table + sysctl_vals DATA +
    proc_dointvec{,_jiffies,_minmax} + proc_dou8vec_minmax), netlink
    attribute helpers (nla_memcpy, nla_policy_len, nla_put_64bit),
    siphash + crc32c hash placeholders, security/LSM secctx stubs,
    socket lock/sockopt, __do_once macro bracket, the net namespace
    list + rwsem + _totalram_pages (DATA), __x86_indirect_thunk_r13,
    and a krealloc_noprof clone.

  * udf.ko (29th distro module; bonus delivery on top of nf_conntrack)
    — 43 UND symbols new in L59, all VFS plumbing: folio runtime
    (__filemap_get_folio, __folio_lock, folio_unlock,
    folio_mark_dirty, folio_wait_stable, read_cache_folio,
    write_cache_pages), inode lifecycle (insert_inode_locked, ihold,
    is_bad_inode/make_bad_inode, discard_new_inode, inode_init_owner,
    inode_permission, inode_add_bytes/inode_sub_bytes), block-write
    helpers (block_commit_write, __block_write_begin), CDROM stub
    (cdrom_get_last_written), CRC ITU-T placeholder (crc_itu_t),
    dcache helpers (d_instantiate_new, d_tmpfile + dotdot_name DATA),
    file/path ops (file_update_time, finish_open, generic_file_open,
    generic_file_fsync, generic_llseek_cookie, page_get_link),
    from_kgid/from_kuid + overflowgid/overflowuid (DATA) + nop_mnt_idmap
    (DATA), __get_user_8, hex_asc_upper (DATA — uppercase variant of
    L57's hex_asc), ktime_get_real_ts64, logfc, rcuwait_wake_up,
    __percpu_down_read, memscan, utf32_to_utf8, and __bitmap_weight.

**L59 infrastructure side-effects:**
  * `user/insmod.ad` CAP bumped 256 KiB → 1 MiB. nf_conntrack.ko is
    432 KiB after xz decompression (largest distro .ko to date);
    insmod was failing with "file exceeds insmod buffer". 1 MiB gives
    headroom for usbcore.ko + future jumbo modules.

**Counts (post-L59):**
  - Stock Debian .ko load count: 29 (was 27 after L58)
  - Linux kernel symbols exported under stock names: ~902
    (785 after L58 + 117 new in L59 = 902 across exports.ad + 36 api_*.ad files)
  - MAX_EXPORTS budget: 902 / 1024 used (122 remaining — usbcore
    needs ~250 UND beyond this so the next major batch will bump to
    2048; nf_conntrack's nephew modules nf_conntrack_proto_tcp / _udp
    / _icmp + xt_state / xt_conntrack are each ~10-30 UND gaps now
    that the nf_conntrack core is in)

**L59 next-natural follow-ups:**
  - nf_conntrack_proto_tcp.ko + nf_conntrack_proto_udp.ko (each ~10-
    20 UND beyond L59 — most of their surface is nf_conntrack's own
    exports which L59 brought in via the loaded module's ksymtab)
  - xt_state.ko + xt_conntrack.ko (the iptables -m state / -m
    conntrack matches; ~5 UND each)
  - usbcore.ko (will require MAX_EXPORTS bump to 2048 + ~250 new shims)
  - 9p.ko / nfs.ko / overlay.ko remain as smaller VFS deferrals
