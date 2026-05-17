/* U27 simplest-case fixture: ONE thread, no contention.
 * If this hangs, the bug is in the basic clone(CLONE_THREAD) path
 * or in pthread_join / __pthread_exit, not mutex contention. */
#include <stdio.h>
#include <pthread.h>

void *worker(void *arg) {
    printf("U27.1: thread enter\n");
    fflush(stdout);
    return NULL;
}

int main(void) {
    pthread_t t;
    pthread_create(&t, NULL, worker, NULL);
    pthread_join(t, NULL);
    printf("U27.1: main reaped\n");
    fflush(stdout);
    return 0;
}
