PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m8_netdev.o

all: m8_netdev.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m8_netdev.S: m8_netdev.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m8-netdev/m8_netdev.ad \
	    -o kernel-modules/m8-netdev/m8_netdev.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m8_netdev.S

.PHONY: all clean
