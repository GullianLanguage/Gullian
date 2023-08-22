CC= gcc
GC= python gullian.py

all: hello_world book

hello_world:
	$(GC) examples/hello_world.gullian hello_world.c
	$(CC) hello_world.c -o hello_world.exe

book:
	$(GC) examples/book.gullian book.c
	$(CC) book.c -o book.exe

run:
	./hello_world.exe

run_book:
	./book.exe