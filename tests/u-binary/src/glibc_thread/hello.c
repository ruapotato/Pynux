/* tests/u-binary/src/glibc_thread/hello.c -- U27 fixture.
 *
 * Exercises pthread_create + pthread_mutex + pthread_join over the
 * U27 clone(CLONE_VM|CLONE_THREAD|...) path. Two workers each bump a
 * shared counter 100 times under a mutex; the main thread joins them
 * both and asserts counter == 200 (no lost updates, no deadlocks).
 *
 * PASS: three markers land on serial:
 *   - "U27: thread 1 done"
 *   - "U27: thread 2 done"
 *   - "U27: counter=200 (expect 200)"
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

static int counter = 0;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

void *worker(void *arg) {
    long id = (long)arg;
    for (int i = 0; i < 100; i++) {
        pthread_mutex_lock(&lock);
        counter++;
        pthread_mutex_unlock(&lock);
    }
    printf("U27: thread %ld done\n", id);
    fflush(stdout);
    return NULL;
}

int main(void) {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, worker, (void *)1L);
    pthread_create(&t2, NULL, worker, (void *)2L);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    printf("U27: counter=%d (expect 200)\n", counter);
    fflush(stdout);
    return counter == 200 ? 0 : 1;
}
