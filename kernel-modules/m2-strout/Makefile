PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m2_strout.o

all: m2_strout.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m2_strout.S: m2_strout.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m2-strout/m2_strout.ad \
	    -o kernel-modules/m2-strout/m2_strout.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m2_strout.S

.PHONY: all clean
