CC= gcc
GC= python gullian.py

all: hello_world book sdl2

hello_world:
	$(GC) examples/hello_world.gullian hello_world.c
	$(CC) hello_world.c -o hello_world.exe

book:
	$(GC) examples/book.gullian book.c
	$(CC) book.c -o book.exe

sdl2:
	$(GC) examples/sdl2.gullian sdl2.c
	$(CC) sdl2.c -o sdl2.exe -lSDL2

run:
	./hello_world.exe

run_book:
	./book.exe

run_sdl2:
	./sdl2.exe