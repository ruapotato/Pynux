PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m11_ktime.o

all: m11_ktime.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m11_ktime.S: m11_ktime.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m11-ktime/m11_ktime.ad \
	    -o kernel-modules/m11-ktime/m11_ktime.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m11_ktime.S

.PHONY: all clean
