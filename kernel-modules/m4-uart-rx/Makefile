PYNUX     ?= python3 -m compiler.adder
KDIR      ?= $(HOME)/hamnix-kernel/linux
PWD       := $(shell pwd)
PROJ_ROOT := $(abspath $(PWD)/../..)

obj-m := m4_uart_rx.o

all: m4_uart_rx.S
	$(MAKE) -C $(KDIR) M=$(PWD) modules

m4_uart_rx.S: m4_uart_rx.ad
	cd $(PROJ_ROOT) && $(PYNUX) compile \
	    --target=x86_64-linux-kernel-module \
	    kernel-modules/m4-uart-rx/m4_uart_rx.ad \
	    -o kernel-modules/m4-uart-rx/m4_uart_rx.S

clean:
	-$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f m4_uart_rx.S

.PHONY: all clean
