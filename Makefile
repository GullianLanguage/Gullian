CC= gcc
GC= python gullian.py

all: hello_world book sdl2 iterator results bug

hello_world:
	$(GC) examples/hello_world.gullian hello_world.c
	$(CC) hello_world.c -o hello_world.exe

book:
	$(GC) examples/book.gullian book.c
	$(CC) book.c -o book.exe

sdl2:
	$(GC) examples/sdl2.gullian sdl2.c
	$(CC) sdl2.c -o sdl2.exe -lSDL2

iterator:
	$(GC) examples/iterator.gullian iterator.c
	$(CC) iterator.c -o iterator.exe

results:
	$(GC) examples/results.gullian results.c
	$(CC) results.c -o results.exe

bug:
	$(GC) examples/bug.gullian bug.c
	$(CC) bug.c -o bug.exe

run:
	./hello_world.exe

run_book:
	./book.exe

run_sdl2:
	./sdl2.exe

run_iterator:
	./iterator.exe

run_results:
	./results.exe

run_bug:
	./bug.exe