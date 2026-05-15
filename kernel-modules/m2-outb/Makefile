PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m2_outb.o

all: m2_outb.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m2_outb.S: m2_outb.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m2-outb/m2_outb.ad \
	    -o kernel-modules/m2-outb/m2_outb.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m2_outb.S

.PHONY: all clean
