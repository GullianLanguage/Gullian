GC= python "$(GULLIAN_HOME)/gullian.py"
CC= gcc

all:
	$(GC) src/main.gullian target/main.c
	$(CC) target/main.c -o target/main.exe

run:
	./target/main.exe
