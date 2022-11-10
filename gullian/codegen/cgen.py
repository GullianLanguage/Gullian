from dataclasses import dataclass

from ..parser import Ast, TypeDeclaration, Expression, Name, Literal, Attribute, Subscript, FunctionHead, StructDeclaration, UnionDeclaration, FunctionDeclaration, VariableDeclaration, Call, Extern, If, While, Return, TestGuard, StructLiteral, Assignment, BinaryOperator
from ..checker import BASIC_TYPES, Module, Type, Typed, Body
from ..type import PTR, ANY

@dataclass
class CGen:
    module: Module

    def gen_name(self, name: Name | Attribute | Subscript):
        if type(name) is Type:
            if type(name.name) is Subscript:
                if name == PTR:
                    return f'{"_".join(self.gen_name(item) for item in name.name.items)}*'

                return f'I_{name.uid}_S_{self.gen_name(name.name.head)}_{"_".join(self.gen_name(item) for item in name.name.items)}'
            elif type(name.name) is Attribute:
                return f'I_{name.uid}_A_{self.gen_name(name.name.left)}_{self.gen_name(name.name.right)}'
            
            return self.gen_name(name.name)

        elif type(name) is Subscript:
            return f'S_{self.gen_name(name.head)}_{"_".join(self.gen_name(item) for item in name.items)}'
        elif type(name) is Attribute:
            return f'A_{self.gen_name(name.left)}_{self.gen_name(name.right)}'
        
        return name.format

    def gen_function_head(self, function_head: FunctionHead):
        generated_parameters = ", ".join(f"{self.gen_name(argument_type)} {argument_name}" for argument_name, argument_type in function_head.arguments)
        
        return f'{self.gen_name(function_head.return_hint)} {self.gen_name(function_head.name)}({generated_parameters})'
    
    def gen_literal(self, literal: StructLiteral):
        generated_arguments = ", ".join(self.gen_expression(argument) for argument in literal.arguments)

        if type(literal.structure.declaration) is UnionDeclaration:
            x = tuple(field for _, field in literal.structure.declaration.fields).index(literal.arguments[0].type_)

            return f'({self.gen_name(literal.structure)}) {{ {x}, {{.{self.gen_name(literal.structure.declaration.fields[x][0])}={generated_arguments}}} }}'

        return f'({self.gen_name(literal.structure)}) {{ {generated_arguments} }}'

    def gen_variable_declaration(self, variable_declaration: Typed[VariableDeclaration]):
        return f'{self.gen_name(variable_declaration.type_)} {self.gen_name(variable_declaration.name)} = {self.gen_expression(variable_declaration.value.value)};'
    
    def gen_expression(self, expression: Expression):
        # NOTE: This is a hack, something is wrong with the typechecker
        if type(expression) is not Typed:
            return self.gen_expression(Typed(expression, ANY))

        if type(expression.value) is Type:
            return f'sizeof({self.gen_name(expression.value)})'

        if type(expression.value) is Literal:
            if type(expression.value.value) is str:
                return f'"{expression.value.value}"'
            
            return expression.value.format
        elif type(expression.value) is TestGuard:
            return f'{self.gen_expression(expression.value.expression.left)}.tag == {self.gen_name(expression.value.expression.left.type_)}__{self.gen_name(expression.value.expression.right)}'
        elif type(expression.value) is Attribute:
            return f'{self.gen_name(expression.value.left)}.{self.gen_name(expression.value.right)}'
        elif type(expression.value) is StructLiteral:
            return self.gen_literal(expression.value)
        elif type(expression.value) is Call:
            return self.gen_call(expression.value)
        elif type(expression.value) is BinaryOperator:
            return f'{self.gen_expression(expression.value.left)}{expression.value.operator.format}{self.gen_expression(expression.value.right)}'

        return expression.format
    
    def gen_call(self, call: Call):
        generated_args = ", ".join(self.gen_expression(argument) for argument in call.arguments)

        if type(call.declaration) is Extern:
            return f'{self.gen_name(call.declaration.head.name)}({generated_args})'
        
        return f'{self.gen_name(call.declaration.head.name)}({generated_args})'
    
    def gen_assignment(self, assignment: Assignment):
        return f'{self.gen_expression(assignment.name)} = {self.gen_expression(assignment.value)};'
    
    def gen_if(self, if_: If, indent=1):
        return f'if ({self.gen_expression(if_.condition)}) {self.gen_body(if_.true_body, indent)}'
    
    def gen_body(self, body: Body, indent=0):
        tab = '  ' * indent
        tab_next = '  ' * (indent +1)

        def gen_line(line: Ast):
            if type(line) is If:
                return self.gen_if(line, indent +1)
            elif type(line) is Return:
                return f'return {self.gen_expression(line.value)};'
            elif type(line) is While:
                return f'while ({self.gen_expression(line.condition)}) {self.gen_body(line.body, indent +1)}'

            if type(line.value) is VariableDeclaration:
                return self.gen_variable_declaration(line)
            elif type(line.value) is Call:
                return f'{self.gen_call(line.value)};'
            elif type(line.value) is Assignment:
                return self.gen_assignment(line.value)
            
            return self.gen_expression(line.value) + ';'

        return '{\n'+ "".join([tab_next + gen_line(line) + '\n' for line in body.lines]) + tab + '}'
    
    def gen_type(self, type_: Type):
        if type(type_.declaration) is StructDeclaration:
            generated_fields = "; ".join(f'{self.gen_name(field_type)} {self.gen_name(field_name)}' for field_name, field_type in type_.declaration.fields)

            return f'typedef struct {{{generated_fields}; }} {self.gen_name(type_)};'
        elif type(type_.declaration) is UnionDeclaration:
            generated_name =  self.gen_name(type_)

            generated_enum_fields = ", ".join(f'{generated_name}__{self.gen_name(field_name)}' for field_name, _ in type_.declaration.fields)
            generated_fields = "; ".join(f'{self.gen_name(field_type)} {self.gen_name(field_name)}' for field_name, field_type in type_.declaration.fields)

            return '\n'.join([
                f'typedef enum {{ {generated_enum_fields} }} {generated_name}_FIELDS;',
                f'typedef struct {{int tag; union {{{generated_fields}; }}; }} {generated_name};'
            ])

        raise NotImplementedError(type_)

    def gen_extern(self, extern_):
        return f'// extern: {extern_.format}'

    def gen_function(self, function_declaration: FunctionDeclaration):
        return f'{self.gen_function_head(function_declaration.head)} {self.gen_body(function_declaration.body)}'

    def gen(self):
        if self.module.name == 'main':
            yield '#include <stdbool.h>'
            yield '#include <malloc.h>'
            yield '#include <string.h>'
            yield '#include <stdlib.h>'
            yield '#include <stdio.h>'
            
            yield '#define str char*'
            yield '#define ptr char*'

            for basic_type in BASIC_TYPES.values():
                for function in basic_type.associated_functions.values():
                    yield self.gen_function(function)
        
        for module in self.module.imports.values():
            cgen = CGen(module)
            yield from cgen.gen()
        
        for type_ in self.module.types.values():
            if not type_.declaration.generic:
                yield self.gen_type(type_)

                for function in type_.associated_functions.values():
                    if type(function.head.return_hint) is Typed:
                        yield self.gen_function(function)

        for function in self.module.functions.values():
            if type(function) is Extern:
                yield self.gen_extern(function)
            else:
                if not function.head.generic:
                    yield self.gen_function(function)
                else:
                    print('ignoring...', function.head.format)
        
        return
