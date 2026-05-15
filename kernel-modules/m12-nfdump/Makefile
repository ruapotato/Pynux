PYNUX     ?= python3 -m compiler.pynux
KDIR      ?= $(HOME)/pynux-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m12_nfdump.o

all: m12_nfdump.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m12_nfdump.S: m12_nfdump.py
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m12-nfdump/m12_nfdump.py \
	    -o kernel-modules/m12-nfdump/m12_nfdump.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m12_nfdump.S

.PHONY: all clean
