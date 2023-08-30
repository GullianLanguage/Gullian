from dataclasses import dataclass

from ..parser import Ast, TypeDeclaration, Expression, Name, Literal, Attribute, Subscript, FunctionHead, StructDeclaration, UnionDeclaration, EnumDeclaration, FunctionDeclaration, VariableDeclaration, Call, Extern, Switch, If, While, Return, TestGuard, StructLiteral, Assignment, BinaryOperator, UnaryOperator
from ..checker import BASIC_TYPES, Module, Type, Typed, Body
from ..type import TYPE, PTR, ANY

NEWLINE = '\n'

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
    
    def refer_type(self, type_: Type):
        return f"{('struct ' if type(type_) is Type and (type(type_.declaration) is StructDeclaration or type(type_.declaration) is UnionDeclaration) else '')}{self.gen_name(type_)}"

    def gen_function_head(self, function_head: FunctionHead):
        generated_parameters = ", ".join(f"{self.refer_type(argument_type)} {argument_name}" for argument_name, argument_type in function_head.arguments)
        
        return f"{self.refer_type(function_head.return_hint)} {self.gen_name(function_head.name)}({generated_parameters})"
    
    def gen_literal(self, literal: StructLiteral):
        generated_arguments = ", ".join(self.gen_expression(argument.value[1]) if type(argument.value) is tuple else  self.gen_expression(argument) for argument in literal.arguments)

        if type(literal.structure.declaration) is UnionDeclaration:
            x = tuple(field for _, field in literal.structure.declaration.fields).index(literal.arguments[0].type_)

            return f'({self.refer_type(literal.structure)}) {{ {x}, {{.{self.gen_name(literal.structure.declaration.fields[x][0])}={generated_arguments}}} }}'

        return f'({self.refer_type(literal.structure)}) {{ {generated_arguments} }}'

    def gen_variable_declaration(self, variable_declaration: Typed[VariableDeclaration], indent=0):
        if type(variable_declaration.value.value.value) is Switch:
            return [
                self.gen_switch(variable_declaration.value.value, varname=self.gen_name(variable_declaration.name), indent=indent +1),
            ]

        return f'{self.refer_type(variable_declaration.type_)} {self.gen_name(variable_declaration.name)} = {self.gen_expression(variable_declaration.value.value)};'
    
    def gen_expression(self, expression: Expression):
        if type(expression) is Typed:
            if type(expression.value) is Attribute:
                if expression.left.type_ is TYPE:
                    return f'{self.gen_name(expression.left)}__{self.gen_name(expression.right)}'
        
        # NOTE: This is a hack, something is wrong with the typechecker
        if type(expression) is not Typed:
            return self.gen_expression(Typed(expression, ANY))

        if type(expression.value) is Type:
            return f'sizeof({self.gen_name(expression.value)})'

        if type(expression.value) is Literal:
            if type(expression.value.value) is str:
                return f'"{expression.value.value}"'
            elif type(expression.value.value) is bool:
                if expression.value.value:
                    return "true"
                
                return "false"
            
            return expression.value.format
        elif type(expression.value) is Name:
            return expression.format
        elif type(expression.value) is TestGuard:
            return f'{self.gen_expression(expression.value.expression.left)}.tag == {self.gen_name(expression.value.expression.left.type_)}__{self.gen_name(expression.value.expression.right)}'
        elif type(expression.value) is Attribute:
            if expression.value.left.type_ == PTR:
                return f'{self.gen_name(expression.value.left)}->{self.gen_name(expression.value.right)}'

            return f'{self.gen_name(expression.value.left)}.{self.gen_name(expression.value.right)}'
        elif type(expression.value) is Subscript:
            return f'{self.gen_expression(expression.value.head)}[{", ".join(self.gen_expression(item) for item in expression.value.items)}]'

        elif type(expression.value) is StructLiteral:
            return self.gen_literal(expression.value)
        elif type(expression.value) is Call:
            return self.gen_call(expression.value)
        elif type(expression.value) is BinaryOperator:
            return f'{self.gen_expression(expression.value.left)}{expression.value.operator.format}{self.gen_expression(expression.value.right)}'
        elif type(expression.value) is Switch:
            raise RuntimeError(f'switch is special, and must be generated before gen_expression()')
        elif type(expression.value) is UnaryOperator:
            return f'{expression.value.operator.format}{self.gen_expression(expression.value.expression)}'
        return expression.format
    
    def gen_call(self, call: Call):
        generated_args = ", ".join(self.gen_expression(argument) for argument in call.arguments)

        if type(call.declaration) is Extern:
            return f'{self.gen_name(call.declaration.head.name)}({generated_args})'
        
        return f'{self.gen_name(call.declaration.head.name)}({generated_args})'
    
    def gen_assignment(self, assignment: Assignment):
        return f'{self.gen_expression(assignment.name)} {assignment.operator.format} {self.gen_expression(assignment.value)};'
    
    def gen_if(self, if_: If, indent=0):
        if type(if_.false_body) is If:
            return [
                f'if ({self.gen_expression(if_.condition)}) {self.gen_body(if_.true_body, indent)}',
                f'else {self.gen_if(if_.false_body, indent=indent)}'
            ]
        
        return f'if ({self.gen_expression(if_.condition)}) {self.gen_body(if_.true_body, indent)}'
    
    def gen_switch(self, switch: Switch, varname='gull_expr_result', indent=0):
        tab = '  ' * indent
        tab_next = '  ' * (indent +1)

        generated_switch_body = ''.join(f'{NEWLINE}{tab_next}{"default" if type(branch) is Name and branch.value == "_" else("case " + self.gen_expression(branch)) }: {varname} = {self.gen_expression(expr)}; break;' for branch, expr in switch.value.branches.items())

        return ''.join([
            f'{tab}{self.gen_name(switch.type_.name)} {varname};{NEWLINE}',
            f'{tab}switch ({self.gen_expression(switch.value.expression)}) {{ {generated_switch_body}{NEWLINE}{tab}}}'
        ])
    
    def gen_body(self, body: Body, indent=0):
        tab = '  ' * indent
        tab_next = '  ' * (indent +1)

        def gen_line(line: Ast):
            if type(line) is If:
                return self.gen_if(line, indent +1)
            elif type(line) is Return:
                if type(line.value.value) is Switch:
                    return [
                        self.gen_switch(line.value, indent=indent +1),
                        'return gull_expr_result;'
                    ]
                
                return f'return {self.gen_expression(line.value)};'
            elif type(line) is While:
                return f'while ({self.gen_expression(line.condition)}) {self.gen_body(line.body, indent +1)}'

            if type(line.value) is VariableDeclaration:
                return self.gen_variable_declaration(line, indent)
            elif type(line.value) is Call:
                return f'{self.gen_call(line.value)};'
            elif type(line.value) is Assignment:
                return self.gen_assignment(line.value)
            
            return self.gen_expression(line.value) + ';'
        
        lines_generated = []

        for line in body.lines:
            line_generated = gen_line(line)

            if type(line_generated) is list:
                lines_generated.extend(line_generated)
            else:
                lines_generated.append(line_generated)

        return '{\n'+ "".join([tab_next + line_generated + '\n' for line_generated in lines_generated]) + tab + '}'
    
    def gen_type(self, type_: Type):
        if type(type_.declaration) is StructDeclaration:
            generated_fields = "; ".join(f'{self.refer_type(field_type)} {self.gen_name(field_name)}' for field_name, field_type in type_.declaration.fields)

            return f'struct {self.gen_name(type_)} {{{generated_fields}; }};'
        elif type(type_.declaration) is UnionDeclaration:
            generated_name =  self.gen_name(type_)

            generated_enum_fields = ", ".join(f'{generated_name}__{self.gen_name(field_name)}' for field_name, _ in type_.declaration.fields)
            generated_fields = "; ".join(f'{self.refer_type(field_type)} {self.gen_name(field_name)}' for field_name, field_type in type_.declaration.fields)

            return '\n'.join([
                f'typedef enum {{ {generated_enum_fields} }} {generated_name}_FIELDS;',
                f'struct {generated_name} {{int tag; union {{{generated_fields}; }}; }};'
            ])
        elif type(type_.declaration) is EnumDeclaration:
            generated_name =  self.gen_name(type_)
            generated_fields = ", ".join(f'{generated_name}__{self.gen_name(field_name)}' for field_name in type_.declaration.fields)
            
            return f'typedef enum {{ {generated_fields} }} {generated_name};'


        raise NotImplementedError(type_)

    def gen_extern(self, extern_):
        return f'// extern: {extern_.format}'
    
    def gen_function_prototype(self, function_declaration: FunctionDeclaration):
        return f'{self.gen_function_head(function_declaration.head)};'

    def gen_function(self, function_declaration: FunctionDeclaration):
        return f'{self.gen_function_head(function_declaration.head)} {self.gen_body(function_declaration.body)}'

    def gen(self, generated_modules: list[str]=[]):
        if self.module.name in generated_modules:
            return
        
        generated_modules.append(self.module.name)

        for include in self.module.includes:
            yield include

        if self.module.name == 'main':
            yield '#include <stddef.h>'
            yield '#include <stdint.h>'
            yield '#include <stdbool.h>'
            yield '#include <malloc.h>'
            yield '#include <string.h>'
            yield '#include <stdlib.h>'
            yield '#include <stdio.h>'

            yield '#define u8 uint8_t'
            yield '#define u16 uint16_t'
            yield '#define u32 uint32_t'
            yield '#define str char*'
            yield '#define ptr char*'
        
        for type_ in self.module.types.values():
            if not type_.declaration.generic:
                yield self.gen_type(type_)

            for function in type_.associated_functions.values():
                if type(function.head.return_hint) is Type:
                    yield self.gen_function_prototype(function)
        
        if self.module.name == 'main':
            for basic_type in BASIC_TYPES.values():
                for function in basic_type.associated_functions.values():
                    yield f'// associated method of type`{basic_type.format}`'
                    yield self.gen_function_prototype(function)

        for function in self.module.functions.values():
            if type(function.value) is not Extern:
                if not function.head.generic:
                    yield self.gen_function_prototype(function)
        
        for module in self.module.imports.values():
            cgen = CGen(module)
            yield from cgen.gen(generated_modules)

        if self.module.name == 'main':
            for basic_type in BASIC_TYPES.values():
                for function in basic_type.associated_functions.values():
                    yield self.gen_function(function)
        
        for type_ in self.module.types.values():
            for function in type_.associated_functions.values():
                if type(function.head.return_hint) is Type:
                    yield self.gen_function(function)

        for function in self.module.functions.values():
            if type(function.value) is Extern:
                yield self.gen_extern(function)
            else:
                if not function.head.generic:
                    yield self.gen_function(function)
        
        return
