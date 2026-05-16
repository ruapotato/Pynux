# tests/linux-modules/src/virtio/Makefile — stock Linux kbuild.
#
# Build with `make -C tests/linux-modules/src/virtio`. The result is
# virtio.ko in this directory; `make install` copies it up to
# tests/linux-modules/virtio.ko (the L23 test fixture).
#
# KDIR points at a Linux source tree built against the pinned ABI
# target (Linux 6.12.48; see linux_abi/TARGET_ABI.md). Override on
# the command line to retarget:
#     make KDIR=/path/to/linux-6.12.48

KDIR ?= /lib/modules/$(shell uname -r)/build

obj-m += virtio.o

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install: all
	cp virtio.ko ../../virtio.ko
