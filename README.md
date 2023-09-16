<div align="center">
<div>
    <img src="logo.png">
    <p>pre-alpha</p>
</div>
</div>

# The Gullian Programming Language
A very experimental and small systems programming language, created to be simple, fast and easy.

[MIT License](./LICENSE)

---
### [DO NOT USE IN PRODUCTION YET]
**BE AWARE THAT**,

This is a early work. It may be unstable, unsafe (memory unsafety) and may contain impactful bugs that could harm your production use case.

Found a bug? Please open a **ISSUE** describing your problem.

## Requirements
* A C Compiler (gcc or clang)
* Makefile (Optional)
* Python3 >= 3.11

## Example
Write
```
# examples/hello_world.gullian

import std.io

fun main() : int {
    io.puts("hello, world")
}
```
Compile
```
$ python gullian.py examples/hello_world.gullian hello_world.c
$ gcc hello_world.c -o hello_world.elf
```
Execute
```
$ ./hello_world.elf
```

## Goals
* Minimalism
* Speed
* Predictability
* Productive

## Features
Ready
* [X] Methods
* [x] Generics & Type Inference
* [x] Interators

Planned
* [ ] Self-Hostes Compiler (High Priority)
* [ ] Lifetimes
* [ ] Async & Promises
* [ ] LLVM Backend

#### Copyright (c) 2023 Marcel Guinhos De Menezes
###### The Gullian Programming Lanague trademark, their name and logos are intelectual property of Marcel Guinhos.

Maceio - AL - Brasil