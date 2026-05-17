/* U27.2: TWO threads, NO contention. Each just prints once. */
#include <stdio.h>
#include <pthread.h>

void *worker(void *arg) {
    long id = (long)arg;
    printf("U27.2: thread %ld\n", id);
    fflush(stdout);
    return NULL;
}

int main(void) {
    pthread_t t1, t2;
    pthread_create(&t1, NULL, worker, (void *)1L);
    pthread_create(&t2, NULL, worker, (void *)2L);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    printf("U27.2: main done\n");
    fflush(stdout);
    return 0;
}
