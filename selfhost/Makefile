GC= python "$(GULLIAN_HOME)/gullian.py"
CC= clang

all:
	$(GC) src/lexer.gullian target/lexer.c
	$(CC) target/lexer.c -o target/lexer.exe

run:
	./target/lexer.exe