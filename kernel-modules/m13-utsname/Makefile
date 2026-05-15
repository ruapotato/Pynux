PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m13_utsname.o

all: m13_utsname.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m13_utsname.S: m13_utsname.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m13-utsname/m13_utsname.ad \
	    -o kernel-modules/m13-utsname/m13_utsname.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m13_utsname.S

.PHONY: all clean
