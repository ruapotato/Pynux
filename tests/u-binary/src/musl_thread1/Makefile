MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

hello: hello.c
ifeq ($(MUSL_GCC),)
	@echo "[musl_thread1] SKIP: musl-gcc not installed."
else
	$(MUSL_GCC) -static-pie -O2 -pthread -o hello hello.c
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: hello
ifeq ($(MUSL_GCC),)
	@echo "[musl_thread1] SKIP install (no musl-gcc, nothing built)"
else
	cp hello ../../u_musl_thread1
endif

clean:
	rm -f hello hello.o
