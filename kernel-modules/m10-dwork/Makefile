PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m10_dwork.o

all: m10_dwork.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m10_dwork.S: m10_dwork.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m10-dwork/m10_dwork.ad \
	    -o kernel-modules/m10-dwork/m10_dwork.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m10_dwork.S

.PHONY: all clean
