from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .checker import Module, Scope

from .type import *

from .lexer import Literal
from .parser import Expression
from .parser import Comptime, Extern, Return, Call, Body, VariableDeclaration

@dataclass
class Interpreter:
    module: "Module"

    def interpret_variable_declaration(self, variable_declaration: VariableDeclaration):
        variable_declaration.value = self.interpret_expression(variable_declaration.value)
        self.module.scope.variables[variable_declaration.name] = variable_declaration

        return variable_declaration

    def interpret_body(self, body: Body):
        result = Typed(Literal(0, body.line), VOID)

        for line in body.lines:
            if type(line.value) is VariableDeclaration:
                self.interpret_variable_declaration(line.value)

            result = self.interpret_expression(line)

            if type(result) is Return:
                return result
            else:
                raise NotImplementedError(line)

        return result

    def interpret_extern(self, function: Extern, args: tuple[Expression]):
        if function.head.name == "puts":
            print(*(arg for arg in args))

            return Typed(Literal(0, function.line), INT)
        
        return Typed(Literal(0, function.line), INT)

    def interpret_call(self, call: Call):
        old_module_scope = self.module.scope

        function = self.module.import_function(call.name)

        for argument_name, argument_type in function.head.arguments:
            self.module.scope.variables[argument_name] = FunctionArgument(argument_name, argument_type)

        if type(function) is Extern:
            result = self.interpret_extern(function, [self.interpret_expression(argument) for argument in call.arguments])
        else:
            result = self.interpret_body(function.body)

        self.module.scope = old_module_scope

        return result

    def interpret_expression(self, expression: Expression):
        if type(expression.value) is Call:
            return self.interpret_call(expression.value)
        elif type(expression.value) is Literal:
            return expression
        
        raise NotImplementedError(expression)

    def interpret(self, comptime: Comptime):
        if type(comptime.value.value) is Body:
            return self.interpret_body(comptime.value.value)
        
        return self.interpret_expression(comptime.value)