/*
 * arch/x86/kernel/sched_asm.S - context switch + task bootstrap.
 *
 * Mirrors the roles of:
 *   __switch_to_asm     - arch/x86/entry/entry_64.S (context switch)
 *   ret_from_fork       - arch/x86/entry/entry_64.S (new-task trampoline)
 *
 * Design (M16.9, preemptive):
 *
 *   The kernel switches tasks ONLY from inside the timer ISR's
 *   common_irq path. Every running task therefore has, when paused, a
 *   uniform stack layout above its saved RSP:
 *
 *      ┌─ high address ──────────────────────────────┐
 *      │ iret frame (SS, RSP, RFLAGS, CS, RIP)       │ <- pushed by CPU
 *      │ vec, error_code                             │ <- pushed by trap_stub
 *      │ 9 caller-saved regs (rax/rcx/rdx/rsi/rdi/r8/r9/r10/r11) │ <- common_irq
 *      │ (timer_interrupt + do_irq + schedule frames) │
 *      │ 6 callee-saved regs (rbp/rbx/r12/r13/r14/r15) │ <- __switch_to_asm
 *      │ return-addr-from-__switch_to_asm            │
 *      └─ low address ───────────────────────────────┘  <- task->sp
 *
 *   When we switch INTO a task we just `pop` the 6 callee-saved regs
 *   and `ret` — control resumes inside that task's previously paused
 *   schedule() call, which unwinds back through timer_interrupt and
 *   do_irq into common_irq's tail (pop 9 + drop vec/ec + iretq).
 *
 *   For a freshly-created task there's no previous schedule() to
 *   unwind into. kthread_create instead pre-builds the new task's
 *   stack so the return-address-from-__switch_to_asm slot points at
 *   kthread_bootstrap (below), which IS common_irq's tail: it pops
 *   the 9 zeroed caller-saved regs, drops the fake vec/ec, and
 *   `iretq`s into the entry function with IF=1.
 *
 *   The first task to run is launched via enter_first_task(): it
 *   loads task->sp into %rsp and tail-jumps into the trampoline
 *   chain, without ever saving the boot context. start_kernel never
 *   returns from enter_first_task — that's intentional, the boot
 *   stack is reclaimable as soon as task 0 starts executing.
 *
 * --- M16.154 [eft] step diagnostics --------------------------------
 *   The Asus real-hw triple-fault survives every static diag we've
 *   surfaced (GDT/TSS/CR3/CR4/MSRs/iret-frame all match QEMU). The
 *   fault must therefore be inside the instruction stream of
 *   enter_first_task → kthread_bootstrap → iretq. We embed three
 *   sequential markers so the serial capture pinpoints which segment
 *   triple-faults:
 *
 *     [eft] step1  : reached after  movq 0(%rdi), %rsp
 *                    (proves the task-sp load itself succeeded)
 *     [eft] step2  : reached right BEFORE iretq
 *                    (proves the 15-register pop chain + addq survived)
 *     [eft] step3  : reached AFTER  iretq
 *                    (must never print — if it does, iretq returned
 *                     to ring 0, which is a kernel-stack underflow bug)
 *
 *   Mechanics: at each step we save the live %rsp into the callee-
 *   saved %r15, swap to a dedicated 4-KiB diag stack, call early_puts,
 *   restore %rsp from %r15, then re-zero %r15. early_puts is SysV-ABI
 *   and clobbers only caller-saved regs (rax, rcx, rdx, rsi, rdi,
 *   r8..r11). For step2 we additionally push/pop rdi+rsi on the diag
 *   stack so the user task's argc/argv (planted into those iret-frame-
 *   adjacent slots by _build_initial_kstack and popped by the 9-popq
 *   chain just above) reach _start with the values the kernel chose.
 *   r15 is callee-saved by SysV: early_puts is guaranteed not to
 *   trash it, so it's safe as the rsp-stash.
 *   At step1 r15 is immediately overwritten by `popq %r15` so no
 *   re-zero is needed there.
 */

    .code64
    .section .text, "ax"

/* ---------- __switch_to_asm: standard SysV callee-saved swap ----- *
 * %rdi = prev task_struct ptr,  %rsi = next task_struct ptr.
 * task_struct->sp is at offset 0.                                    */
    .align 16
    .globl __switch_to_asm
__switch_to_asm:
    pushq   %rbp
    pushq   %rbx
    pushq   %r12
    pushq   %r13
    pushq   %r14
    pushq   %r15

    movq    %rsp, 0(%rdi)              /* prev->sp = current rsp     */
    movq    0(%rsi), %rsp              /* rsp = next->sp             */

    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx
    popq    %rbp
    ret

/* ---------- kthread_bootstrap: first-run trampoline -------------- *
 * Sits at the top of every freshly-created task's "previous saved"
 * stack frame. After __switch_to_asm pops 6 callee-saved regs and
 * rets, control lands here on the new task's own stack.
 *
 * Layout above %rsp at this point (low → high):
 *      9 caller-saved regs (zeroed by kthread_create)
 *      vec + error_code   (zeroed)
 *      iret frame         (RIP = entry, CS = 0x08, RFLAGS = 0x202,
 *                           RSP = task stack top, SS = 0x10)
 *
 * This sequence is byte-identical to common_irq's tail; keeping the
 * code in one place would force kthread_create to know the address
 * of an instruction inside common_irq, so we duplicate the few lines
 * here for clarity. If common_irq's tail ever changes, this must
 * change with it.                                                    */
    .align 16
    .globl kthread_bootstrap
kthread_bootstrap:
    popq    %r11
    popq    %r10
    popq    %r9
    popq    %r8
    popq    %rdi
    popq    %rsi
    popq    %rdx
    popq    %rcx
    popq    %rax
    addq    $16, %rsp                  /* drop vec + error_code      */

    /* --- [eft] step2: pre-iretq diagnostic ----------------------- *
     * All 9 caller-saved regs have been popped; vec/ec dropped; %rsp
     * now points at the 5-qword iret frame. Save %rsp → %r15, swap
     * to the diag stack, preserve %rdi/%rsi (carry argc/argv to
     * _start), call early_puts, restore everything, re-zero %r15,
     * iretq. r15 is callee-saved so early_puts can't trash it. */
    movq    %rsp, %r15
    leaq    _eft_diag_stack_top(%rip), %rsp
    pushq   %rdi                       /* preserve user argc         */
    pushq   %rsi                       /* preserve user argv         */
    leaq    _eft_step2_msg(%rip), %rdi
    call    early_puts
    popq    %rsi
    popq    %rdi
    movq    %r15, %rsp                 /* back to the iret-frame rsp */
    xorq    %r15, %r15                 /* user wakes with r15 = 0    */

    iretq                              /* land in task entry, IF=1   */

    /* --- [eft] step3: POST-iretq diagnostic ---------------------- *
     * Unreachable in the correct path. If this prints, iretq did
     * NOT switch to ring 3 — it returned linearly to the next
     * instruction, which means the iret frame was malformed in a
     * way the CPU silently accepted as a same-privilege iretq. That
     * would be a kernel bug, not the Asus triple-fault under test.
     * Use a clean stack switch so the diag print itself doesn't
     * compound the corruption that got us here. */
    movq    %rsp, %r15
    leaq    _eft_diag_stack_top(%rip), %rsp
    leaq    _eft_step3_msg(%rip), %rdi
    call    early_puts
    movq    %r15, %rsp
.Left_step3_hang:
    cli
    hlt
    jmp     .Left_step3_hang

/* ---------- enter_first_task: bootstrap the very first task ------ *
 * Called once from start_kernel after kthread_create has set up the
 * task stacks. No state save — we're never coming back to the boot
 * context. Mirrors what cpu_idle_thread does on Linux's secondary
 * CPUs after smp_init: load the task's stack pointer and dive in. */
    .align 16
    .globl enter_first_task
enter_first_task:
    /* %rdi = ptr to task_struct (sp at offset 0). */
    movq    0(%rdi), %rsp

    /* --- [eft] step1: post-rsp-load diagnostic -------------------- *
     * The `movq 0(%rdi), %rsp` above is the FIRST instruction that
     * uses a value sourced from the task struct. If task->sp is
     * bogus, the very next memory access (the call below) will
     * fault on real silicon. We stash the task rsp in %r15 (callee-
     * saved by SysV, so early_puts won't touch it), swap to the diag
     * stack, print, then restore %rsp from %r15 — exactly as the
     * popq sequence below expects. The first instruction after
     * restore is `popq %r15`, which overwrites our saved-rsp value
     * with the task's intended r15 (=0 for fresh tasks), so we don't
     * need to re-zero r15 here. */
    movq    %rsp, %r15
    leaq    _eft_diag_stack_top(%rip), %rsp
    leaq    _eft_step1_msg(%rip), %rdi
    call    early_puts
    movq    %r15, %rsp

    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx
    popq    %rbp
    ret                                /* tail into kthread_bootstrap */

/* ---------- [eft] diagnostic strings ------------------------------ */
    .section .rodata
    .align 8
_eft_step1_msg:
    .asciz "[eft] step1: post-rsp-load (enter_first_task body)\n"
_eft_step2_msg:
    .asciz "[eft] step2: pre-iretq (kthread_bootstrap tail)\n"
_eft_step3_msg:
    .asciz "[eft] step3: POST-iretq (impossible - iretq returned to ring 0)\n"

/* ---------- [eft] dedicated diagnostic stack ---------------------- *
 * Lives in .bss (zero-filled at boot by head_64.S's rep stosq). We
 * use it as a scratch call stack during the step1/step2/step3 prints
 * so early_puts's call frames never touch the live task / iret-frame
 * stack. 4 KiB is overkill for one early_puts call but matches the
 * cost of a single .bss page and gives us headroom if a future patch
 * wants to extend the diag to recursive prints.                      */
    .section .bss
    .align 16
_eft_diag_stack_base:
    .skip 4096
_eft_diag_stack_top:
