CC= cc
GC= python $(GULLIAN_HOME)/gullian.py

all:
	$(GC) src/main.gullian main.c
	$(CC) main.c -o cparser.elf

run:
	./cparser.elf
