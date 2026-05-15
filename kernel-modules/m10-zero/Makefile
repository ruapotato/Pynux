PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m10_zero.o

all: m10_zero.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m10_zero.S: m10_zero.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m10-zero/m10_zero.ad \
	    -o kernel-modules/m10-zero/m10_zero.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m10_zero.S

.PHONY: all clean
