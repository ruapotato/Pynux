/* tests/u-binary/src/glibc_system/hello.c -- U26 fixture.
 *
 * Exercises the SIGCHLD/fork+wait pattern that glibc's system() /
 * popen() / posix_spawn() all build on. Child does its work and
 * _exit()s; parent reaps via waitpid() and validates the exit code.
 *
 * PASS: three markers land on serial:
 *   - "U26: parent before fork"
 *   - "U26: child running"
 *   - "U26: parent reaped child status=42"
 *
 * Vfork-style note: the child does _exit(42) immediately after one
 * printf — it never re-enters glibc state that the parent will
 * touch afterwards, so the shared address space is safe.
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    printf("U26: parent before fork\n");
    fflush(stdout);
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 1; }
    if (pid == 0) {
        printf("U26: child running\n");
        fflush(stdout);
        _exit(42);
    }
    int wstatus = 0;
    pid_t reaped = waitpid(pid, &wstatus, 0);
    if (reaped != pid) {
        printf("U26: waitpid returned %d (expected %d)\n", reaped, pid);
        return 2;
    }
    if (!WIFEXITED(wstatus) || WEXITSTATUS(wstatus) != 42) {
        printf("U26: child exit status wrong: %d\n", wstatus);
        return 3;
    }
    printf("U26: parent reaped child status=%d\n", WEXITSTATUS(wstatus));
    return 0;
}
