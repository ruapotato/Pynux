PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m5_timer.o

all: m5_timer.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m5_timer.S: m5_timer.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m5-timer/m5_timer.ad \
	    -o kernel-modules/m5-timer/m5_timer.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m5_timer.S

.PHONY: all clean
