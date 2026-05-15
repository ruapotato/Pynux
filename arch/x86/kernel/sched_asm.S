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
    iretq                              /* land in task entry, IF=1   */

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
    popq    %r15
    popq    %r14
    popq    %r13
    popq    %r12
    popq    %rbx
    popq    %rbp
    ret                                /* tail into kthread_bootstrap */
