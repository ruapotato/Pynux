# Pynux M10.2: delayed_work — timer-backed workqueue.
#
# struct delayed_work embeds a work_struct (32 bytes) + a timer_list
# (40 bytes) + wq pointer + cpu. INIT_DELAYED_WORK initializes both;
# queue_delayed_work_on schedules the timer to fire after `delay`
# jiffies, at which point the timer callback (delayed_work_timer_fn,
# exported) queues the embedded work_struct onto the workqueue.

extern def alloc_workqueue(fmt: Ptr[char], flags: uint32,
                           max_active: int32) -> Ptr[uint8]
extern def destroy_workqueue(wq: Ptr[uint8])
extern def __flush_workqueue(wq: Ptr[uint8])
extern def queue_delayed_work_on(cpu: int32, wq: Ptr[uint8],
                                 dwork: Ptr[uint8], delay: uint64) -> int32
extern def init_timer_key(timer: Ptr[uint8], fn: Ptr[uint8],
                          flags: uint32, name: Ptr[char],
                          key: Ptr[uint8])
extern def delayed_work_timer_fn() -> int32    # exported helper
extern def msleep(ms: uint32)
extern def _printk(fmt: str, val: int32) -> int32


# struct delayed_work (88 bytes; probed for 6.12.48). Layout:
#   bytes 0..32  embedded work_struct (data, entry.next, entry.prev, func)
#   bytes 32..72 embedded timer_list (hlist node, expires, function, flags)
#   bytes 72..88 wq pointer, cpu, padding
class DelayedWork:
    work_data:        int64
    work_list_next:   Ptr[uint8]
    work_list_prev:   Ptr[uint8]
    work_func:        Ptr[uint8]
    timer_hlist_next: Ptr[uint8]
    timer_hlist_pprev:Ptr[uint8]
    timer_expires:    uint64
    timer_function:   Ptr[uint8]
    timer_flags:      uint32
    timer_pad:        int32
    wq:               Ptr[uint8]
    cpu:              int32
    pad_end:          int32


WORK_STRUCT_NO_POOL_VAL: int64  = 0xfffffffe00000
WORK_CPU_UNBOUND:        int32  = 64       # NR_CPUS
TIMER_OFF_IN_DWORK:      int32  = 32


pynux_dwork:        DelayedWork
pynux_dwork_wq:     Ptr[uint8]
pynux_dwork_count:  int32
pynux_dwork_lkkey:  Array[32, uint8]


def pynux_dwork_fn(work: Ptr[uint8]):
    pynux_dwork_count = pynux_dwork_count + 1
    _printk("[DWORK] fired\n", 0)


def init_module() -> int32:
    pynux_dwork_wq = alloc_workqueue("pynux-dwq", 0, 1)
    if pynux_dwork_wq == 0:
        return -12

    # INIT_WORK part (matches M4.3a's hand-coded init).
    pynux_dwork.work_data = WORK_STRUCT_NO_POOL_VAL
    entry_addr: Ptr[uint8] = &pynux_dwork + 8       # &dwork.work.entry
    pynux_dwork.work_list_next = entry_addr
    pynux_dwork.work_list_prev = entry_addr
    pynux_dwork.work_func = pynux_dwork_fn

    # init_timer_key on the embedded timer (offset 32).
    init_timer_key(&pynux_dwork + TIMER_OFF_IN_DWORK,
                   delayed_work_timer_fn, 0, "pynux-dwork",
                   &pynux_dwork_lkkey)

    # Schedule for 10 jiffies (= 10 ms at HZ=1000).
    queue_delayed_work_on(WORK_CPU_UNBOUND, pynux_dwork_wq,
                          &pynux_dwork, 10)
    _printk("[DWORK] queued for 10 ms\n", 0)

    # Sleep briefly so the work has time to fire before init_module
    # returns — otherwise tail of init may print [DWORK] count = 0
    # before the work scheduled itself.
    msleep(50)
    return 0


def cleanup_module():
    if pynux_dwork_wq != 0:
        __flush_workqueue(pynux_dwork_wq)
        destroy_workqueue(pynux_dwork_wq)
    _printk("[DWORK] count = %d\n", pynux_dwork_count)
    _printk("[DWORK] unregistered\n", 0)
