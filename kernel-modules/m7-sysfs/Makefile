PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m7_sysfs.o

all: m7_sysfs.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m7_sysfs.S: m7_sysfs.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m7-sysfs/m7_sysfs.ad \
	    -o kernel-modules/m7-sysfs/m7_sysfs.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m7_sysfs.S

.PHONY: all clean
