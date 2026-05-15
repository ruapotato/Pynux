PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m12_null.o

all: m12_null.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m12_null.S: m12_null.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m12-null/m12_null.ad \
	    -o kernel-modules/m12-null/m12_null.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m12_null.S

.PHONY: all clean
