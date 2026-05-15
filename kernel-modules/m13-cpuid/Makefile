PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m13_cpuid.o

all: m13_cpuid.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m13_cpuid.S: m13_cpuid.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m13-cpuid/m13_cpuid.ad \
	    -o kernel-modules/m13-cpuid/m13_cpuid.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m13_cpuid.S

.PHONY: all clean
