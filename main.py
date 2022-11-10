from argparse import ArgumentParser

from gullian.source import Source
from gullian.lexer import Lexer
from gullian.parser import Parser
from gullian.checker import Checker, Module
from gullian.codegen.cgen import CGen

argparser = ArgumentParser('gullian')
argparser.add_argument('infile', type=str)
argparser.add_argument('outfile', type=str)

def compile_file(infile: str, outfile: str):
    file_string = open('examples/hello_world.gullian').read()
    module = Module.new()

    tokens = tuple(Lexer(Source(file_string), module).lex())
    asts = tuple(Parser(Source(tokens), module).parse())
    checker = Checker(asts, module)

    for checked in checker.check():
        continue

    cgen = CGen(module)

    out = open(outfile, 'w')

    for code in cgen.gen():
        out.write(code + '\n')
    
    return


def main():
    arguments = argparser.parse_args()

    if arguments.infile:
        return compile_file(arguments.infile, arguments.outfile)

    return argparser.print_usage()

if __name__ == '__main__':
    main()