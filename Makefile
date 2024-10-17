.PHONY: all dist emu clean

all:

dist:
	./buildall.sh

emu:
	TD=0 ./run_td.sh
run:
	./run_td.sh

clean:
	git clean -xdff