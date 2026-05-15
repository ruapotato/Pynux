PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m4_virtio_net.o

all: m4_virtio_net.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m4_virtio_net.S: m4_virtio_net.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m4-virtio-net/m4_virtio_net.ad \
	    -o kernel-modules/m4-virtio-net/m4_virtio_net.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m4_virtio_net.S

.PHONY: all clean
