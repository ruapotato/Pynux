PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m5_netfilter.o

all: m5_netfilter.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m5_netfilter.S: m5_netfilter.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m5-netfilter/m5_netfilter.ad \
	    -o kernel-modules/m5-netfilter/m5_netfilter.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m5_netfilter.S

.PHONY: all clean
