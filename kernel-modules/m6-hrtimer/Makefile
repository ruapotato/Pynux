PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m6_hrtimer.o

all: m6_hrtimer.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m6_hrtimer.S: m6_hrtimer.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m6-hrtimer/m6_hrtimer.ad \
	    -o kernel-modules/m6-hrtimer/m6_hrtimer.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m6_hrtimer.S

.PHONY: all clean
