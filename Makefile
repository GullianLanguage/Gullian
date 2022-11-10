CC= clang
GC= python main.py

all:
	$(GC) examples/hello_world.gullian hello_world.c
	$(CC) hello_world.c -o hello_world.exe

run:
	./hello_world.exe