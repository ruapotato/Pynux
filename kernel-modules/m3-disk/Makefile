PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m3_disk.o

all: m3_disk.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m3_disk.S: m3_disk.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m3-disk/m3_disk.ad \
	    -o kernel-modules/m3-disk/m3_disk.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m3_disk.S

.PHONY: all clean
