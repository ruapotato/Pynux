PYNUX     ?= python3 -m compiler.pynux
KDIR      ?= $(HOME)/pynux-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m13_utsname.o

all: m13_utsname.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m13_utsname.S: m13_utsname.py
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m13-utsname/m13_utsname.py \
	    -o kernel-modules/m13-utsname/m13_utsname.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m13_utsname.S

.PHONY: all clean
