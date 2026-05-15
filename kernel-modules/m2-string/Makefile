PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m2_string.o

all: m2_string.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m2_string.S: m2_string.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m2-string/m2_string.ad \
	    -o kernel-modules/m2-string/m2_string.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m2_string.S

.PHONY: all clean
