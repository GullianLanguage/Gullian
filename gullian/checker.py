from dataclasses import dataclass
import os
import copy


from .type import *

from .source import Source
from .lexer import Lexer, Name, Literal, Token, TokenKind, Comment
from .parser import Ast, TypeDeclaration, Expression
from .parser import Parser, FunctionDeclaration, FunctionHead, Extern, Import, EnumDeclaration, StructDeclaration, UnionDeclaration, VariableDeclaration, Assignment, Body, While, If, Return, Comptime, Call, Attribute, Subscript, StructLiteral, UnaryOperator, BinaryOperator, TestGuard
from .interpreter import Interpreter

from .type import *

@dataclass
class Scope:
    module: "Module"
    variables: dict[Name, VariableDeclaration | FunctionArgument]
    type_variables: dict[Name, Type]
    type_guards: list[Attribute]

    def get_variable(self, name: Name) -> VariableDeclaration | FunctionArgument:
        if type(name) is not Name:
            raise TypeError(f"parameter name must be a Name, got {name.format}. at line {name.line}. in module {self.module.name}")
        
        if name in self.variables:
            return self.variables[name]

        raise NameError(f'variable {name.value} not found in current scope. at line {name.line} in module {self.module.name}')
    
    def get_type_variable(self, name: Name) -> VariableDeclaration | FunctionArgument:
        if type(name) is not Name:
            raise TypeError(f"parameter name must be a Name, got {name.format}. at line {name.line}. in module {self.module.name}")
        
        if name in self.type_variables:
            return self.type_variables[name]

        raise NameError(f'type variable {name.value} not found in current scope. at line {name.line} in module {self.module.name}')

    def copy(self):
        return type(self)(self.module, dict(self.variables), dict(self.type_variables), list(self.type_guards))

    @classmethod
    def new(cls, module: "Module"):
        return cls(module, dict(), dict(), list())
    
@dataclass
class Module:
    name: str
    functions: dict[Name, FunctionDeclaration]
    types: dict[Name, TypeDeclaration]
    imports: dict[Name, "Module"]
    scope: Scope
    
    def import_type(self, name: Name | UnaryOperator):
        if type(name) is UnaryOperator and name.operator.kind is TokenKind.Ampersand:
            return Type(Subscript(PTR, (name.expression,)), PTR.uid, PTR.associated_functions)

        if type(name) is Name:
            if name in BASIC_TYPES:
                return BASIC_TYPES[name]
            
            elif name in self.scope.type_variables:
                return self.scope.get_type_variable(name)
                
            elif name not in self.types:
                raise NameError(f'{name} is not a type of module {self.name}. at line {name.line}. in module {self.name}')
            
            return self.types[name]
        elif type(name) is Attribute:
            if name.left not in self.imports:
                raise NameError(f'{name.left} is not an import of module {self.name}. at line {name.line}. in module {self.name}')
            
            return self.imports[name.left].import_type(name.right)
        
        # Creates a new type based in its generic form or return the already created specialized version
        elif type(name) is Subscript:
            if name in self.types:
                return self.types[name]
            
            if name.head in self.types:
                type_ = self.import_type(name.head)

                if name in type_.module.types:
                    return type_.module.types[name]

                if not type_.declaration.generic:
                    raise TypeError(f"type {type_.name} is not a generic type. at line {name.line}. in module {self.name}")
                
                struct_declaration: StructDeclaration = type_.declaration

                def apply_generic(field_type: Type):
                    if type(field_type) is Subscript:
                        return self.import_type(Subscript(field_type.head, tuple(apply_generic(item) for item in field_type.items)))
                    
                    if field_type in struct_declaration.generic:
                        hint_or_type = name.items[struct_declaration.generic.index(field_type)]

                        if type(hint_or_type) is Type:
                            return hint_or_type

                        return self.import_type(hint_or_type)
                    
                    return self.import_type(field_type)
                
                if type(type_.declaration) is StructDeclaration:
                    new_type_declaration = StructDeclaration(name, [(field_name, apply_generic(field_type)) for field_name, field_type in struct_declaration.fields], list())
                else:
                    new_type_declaration = UnionDeclaration(name, [(field_name, apply_generic(field_type)) for field_name, field_type in struct_declaration.fields], list())

                generated_type = Type(name, Type.gen_uid(), dict(), new_type_declaration, self)
                generated_type.associated_functions = {name: AssociatedFunction(generated_type, function) for name, function in type_.associated_functions.items()}

                
                self.types[name] = generated_type

                return generated_type
            elif type(name.head) is Attribute:
                type_ = self.import_type(name.head)

                return type_.module.import_type(Subscript(name.head.rightest, name.items))

            if type(name.head) is Type:
                type_ = name.head
            else:
                type_ = self.import_type(name.head)

            return Type(Subscript(name.head, tuple(item if type(item) is Type else self.import_type(item) for item in name.items)), type_.uid, type_.associated_functions, type_.declaration)
        
        raise TypeError(f"argument 'name' must be a Name or Attribute, found {type(name)}")

    def import_function(self, name: Name | Attribute):

        def apply_generic_function(name, function):
            if not function.head.generic:
                raise TypeError(f"function {function.head.name} is not a generic function. at line {name.line}. in module {self.name}")

            def apply_generic(field_type: Type):
                if type(field_type) is Subscript:
                    return Subscript(field_type.head, tuple(apply_generic(item) for item in field_type.items))

                if field_type in function.head.generic:
                    return name.items[function.head.generic.index(field_type)]
                
                return field_type

            old_scope = function.head.module.scope
            function.head.module.scope = old_scope.copy()
                                                                                 
            temporary_checker = Checker(tuple(), function.head.module)
            new_function_head = FunctionHead(name, [(argument_name, apply_generic(argument_type)) for argument_name, argument_type in function.head.arguments], apply_generic(function.head.return_hint), list(), function.head.module)

            # Make type aliases for check_body()
            for type_alias, parametric_type in zip(function.head.generic, name.items):
                function.head.module.scope.type_variables[type_alias] = parametric_type

            for argument_name, argument_type in new_function_head.arguments:
                function.head.module.scope.variables[argument_name] = FunctionArgument(argument_name, argument_type)                                              
            new_function = FunctionDeclaration(new_function_head, copy.deepcopy(function.body))

            # This is important to check_call() for methods to work properlyiif
            if type(fun) is AssociatedFunction:
                new_function = AssociatedFunction(function.owner, new_function)

            new_function = temporary_checker.check_function_declaration(new_function)

            function.head.module.scope = old_scope

            return new_function_head

        if type(name) is Name:
            if name not in self.functions:
                raise NameError(f'{name} is not a function of module {self.name}. at line {name.line}')
            
            return self.functions[name]
        elif type(name) is Attribute:
            if type(name.left) is Subscript and name.left.head == PTR:
                return self.import_function(Attribute(name.left.items[0], name.right))

            if type(name.left) is Attribute:
                temporary_checker = Checker(None, self)

                name.left = temporary_checker.check_attribute(name.left)

                if name.left.type_.module is None:
                    return self.import_function(Attribute(name.left.type_.name, name.right))

                return name.left.type_.module.import_function(Attribute(name.left.type_.name, name.right))

            if name.left in self.scope.variables:
                variable = self.scope.get_variable(name.left)

                if variable.type_.module is None:
                    return self.import_function(Attribute(variable.type_.name, name.right))

                return variable.type_.module.import_function(Attribute(variable.type_.name, name.right))
                
            elif name.left in self.types or name.left in BASIC_TYPES:
                name_left_type = self.import_type(name.left)

                if name.right in name_left_type.associated_functions:
                    return name_left_type.associated_functions[name.right]
                
                raise NameError(f'{name.right} is not an associated function of {name.left}. at line {name.right.line} in module {self.name}')
            elif name.left in self.imports:
                return self.imports[name.left].import_function(name.right)

            raise NameError(f'{name.left} is not an import of module {self.name}. at line {name.line}')
        
        # Creates a new function based in its generic form or return the already created specialized version
        elif type(name) is Subscript:
            if name in self.functions:
                return self.functions[name]
            
            function: FunctionDeclaration = self.import_function(name.head)

            if not function.head.generic:
                if function.head.name == name:
                    return function

                raise TypeError(f"function {function.head.name.format} is not a generic function, got {name.format}. at line {name.line}. in module {self.name}")
            
            def apply_generic(field_type: Type):
                if type(field_type) is Subscript:
                    return Subscript(field_type.head, tuple(apply_generic(item) for item in field_type.items))
                
                if field_type in function.head.generic:
                    return name.items[function.head.generic.index(field_type)]
                
                return field_type

            old_scope = function.head.module.scope
            function.head.module.scope = old_scope.copy()


            temporary_checker = Checker(tuple(), function.head.module)
            new_function_head = FunctionHead(name, [(argument_name, apply_generic(argument_type)) for argument_name, argument_type in function.head.arguments], apply_generic(function.head.return_hint), list(), function.head.module)

            # Make type aliases for check_body()
            for type_alias, parametric_type in zip(function.head.generic, name.items):
                function.head.module.scope.type_variables[type_alias] = parametric_type
            
            for argument_name, argument_type in new_function_head.arguments:
                function.head.module.scope.variables[argument_name] = FunctionArgument(argument_name, argument_type)
            
            new_function = FunctionDeclaration(new_function_head, copy.deepcopy(function.body))
            
            # This is important to check_call() for methods to work properly
            if type(function) is AssociatedFunction:
                new_function = AssociatedFunction(function.owner, new_function)
                fun_name = new_function.head.name.head.rightest

                new_function.owner.associated_functions[fun_name] = new_function
            
            new_function = temporary_checker.check_function_declaration(new_function)

            function.head.module.scope = old_scope

            return new_function
        
        raise TypeError(f"argument 'name' must be a Name or Attribute, found {type(name)}")

    @classmethod
    def new(cls, name='main'):
        module = cls(name, dict(), dict(), dict(), None)
        module.scope = Scope.new(module)

        return module

@dataclass
class Checker:
    asts: tuple[Ast]
    module: Module

    def check_type_compatibility(self, left: Type, right: Type, *, swap_order=True):
        if type(left) is not Type:
            raise TypeError(f"left must be a Type. got {left}. line {left.line}")
        elif type(right) is not Type:
            raise TypeError(f"right must be a Type. got {right}. line {right.line}")
        
        if left is ANY or right is ANY:
            return True

        if left is PTR:
            if right is STR:
                return True
            elif right is INT:
                return True

        elif left is INT:
            if right is BOOL:
                return True
            elif right is CHAR:
                return True
            elif right is TYPE:
                return True

        if swap_order:
            return self.check_type_compatibility(right, left, swap_order=False)
        
        return left == right

    def check_call(self, call: Call):
        function: FunctionDeclaration = self.module.import_function(call.name)
        function_arguments_dict = dict(function.head.arguments)

        call.name = self.check_expression(call.name)    
        call.arguments = [self.check_expression(argument) for argument in call.arguments]
        call.declaration = function


        if call.generics:
            if type(function) is AssociatedFunction:
                function = function.head.module.import_function(Subscript(Attribute(function.owner.name, function.head.name.head.rightest), tuple(call.generics)))
            else:
                function = function.head.module.import_function(Subscript(function.head.name.head, tuple(call.generics)))
        elif function.head.generic:
            raise ValueError(f"the called function is generic, you must specify its type parameters in the callee '{call.format}'. at line {call.line} in module {self.module.name}")

        function_arguments_dict = dict(function.head.arguments)

        # inserts self
        if type(function) is AssociatedFunction:
            if type(call.name) is Typed:
                print()
                print('xxxx', function_arguments_dict['self'])
                if function_arguments_dict['self'] == PTR:
                    call.arguments.insert(0, Typed(UnaryOperator(Token(TokenKind.Ampersand, 0), call.name.value.left), PTR))
                else:
                    call.arguments.insert(0, call.name.value.left)
        
        if len(call.arguments) > len(function.head.arguments):
            raise ValueError(f'too many arguments for function "{function.head.format}". expected {len(function.head.arguments)}, got {len(call.arguments)}. at line {call.name.line}. in module {self.module.name}')
        elif len(call.arguments) < len(function.head.arguments):
            raise ValueError(f'too few arguments for function "{function.head.format}". expected {len(function.head.arguments)}, got {len(call.arguments)}. at line {call.name.line}. in module {self.module.name}')

        for call_argument, (function_argument_name, function_argument_type) in zip(call.arguments, function.head.arguments):
            if not self.check_type_compatibility(call_argument.type_, function_argument_type):
                raise TypeError(f"argument '{function_argument_name.format}' of function '{function.head.format}' must be a '{function_argument_type}' but a '{call_argument.type_}' was provided. at line {call.name.line}. in module {self.module.name}")
        
        call.declaration = function

        return Typed(call, function.head.return_hint)
    
    def check_attribute(self, attribute: Attribute, guarantee=False):
        if type(attribute.left) is Call:
            attribute.left = self.check_call(attribute.left)
            

        # when attribute.left is a variable
        elif attribute.left in self.module.scope.variables:
            variable = self.module.scope.get_variable(attribute.left)
            attribute.left = Typed(attribute.left, variable.type_)

            if variable.type_.declaration is None:
                type_ = self.module.import_type(variable.type_.name)
            else:
                type_ = variable.type_
            
            if attribute.right in type_.associated_functions:
                return Typed(attribute, FUNCTION)

            if type(type_.name) is Subscript:
                return Typed(attribute, self.check_attribute(Attribute(type_, attribute.right), guarantee))
            elif type(type_.name) is Name:
                return Typed(attribute, self.check_attribute(Attribute(type_, attribute.right), guarantee))
                
            return Typed(attribute, self.check_attribute(Attribute(type_.name.name, attribute.right), guarantee))
        elif attribute.left in self.module.imports:
            return attribute
    
        if type(attribute.left) is Type:
            type_ = attribute.left
        
        elif type(attribute.left) is Typed:
            type_ = attribute.left.type_
        else:
            type_ = self.module.import_type(attribute.left)

        if type_ == PTR and type(type_.name) is Subscript:
            type_ = type_.name.items[0] if type(type_.name.items[0]) is Type else self.module.import_type(type_.name.items[0])
        
        print(type_)
        if type(type_.declaration) is EnumDeclaration:
            if attribute.right not in type_.declaration.fields:
                raise NameError(f'{attribute.right} is not a valid attribute of enum {type_.name.format}. at line {attribute.line}. in module {self.module.name}')
            
            return Typed(Attribute(Typed(attribute.left, TYPE), Typed(attribute.right, type_)), type_)
        elif type(type_.declaration) is StructDeclaration:
            type_declaration_fields_dict = dict(type_.declaration.fields)

            if attribute.right not in type_declaration_fields_dict:
                raise NameError(f'{attribute.right} is not a valid attribute of struct {type_.name.format}. at line {attribute.line}. in module {self.module.name}')
            
            return type_declaration_fields_dict[attribute.right]
        elif type(type_.declaration) is UnionDeclaration:
            type_declaration_fields_dict = dict(type_.declaration.fields)

            if attribute.right not in type_declaration_fields_dict:
                if attribute.right in type_.associated_functions:
                    return type_.associated_functions[attribute.right]

                raise NameError(f'{attribute.right} is not a valid attribute of union {type_.name.format}. at line {attribute.line}. in module {self.module.name}')
            
            if not guarantee:
                if Attribute(type_, attribute.right) not in self.module.scope.type_guards:
                    raise Exception(f"you can't access the union attribute '{attribute.right.format}' without a test_guard, it may be unitialized. at line {attribute.right.line}. in module {self.module.name}")

            return type_declaration_fields_dict[attribute.right]
        elif type_.name in BASIC_TYPES:
            if attribute.right not in type_.associated_functions:
                raise NameError(f'{attribute.right} is not a a associated function of type {type_.name.format}. at line {attribute.line}. in module {self.module.name}')
            
            # NOTE: May cause trouble
            return Typed(attribute, FUNCTION)
        else:
            raise NotImplementedError(type_)

        raise NotImplementedError
    
    #NOTE: Only works for indexing
    def check_subscript(self, subscript: Subscript):
        subscript.items = tuple(self.check_expression(item) for item in subscript.items)

        if type(subscript.head) is Attribute:
            subscript.head = self.check_attribute(subscript.head)
            type_ = subscript.head.type_
        else:
            variable = self.module.scope.get_variable(subscript.head)
            type_ = variable.type_

        if not self.check_type_compatibility(INT, subscript.items[0].type_):
            raise TypeError(f"indexing for variable {subscript.head.format} must provide a 'int', got {subscript.items[0].type_.format}. at line {subscript.line}. in module {self.module.name}")
        
        typed_subscript = Typed(subscript, VOID)

        if self.check_type_compatibility(STR, type_):
            typed_subscript.type_ = CHAR
        elif self.check_type_compatibility(PTR, type_):
            if type(type_.name) is Subscript:
                typed_subscript.type_ = type_.name.items[0] if type(type_.name.items[0]) is Type else self.module.import_type(type_.name.items[0])
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError(type_)

        return typed_subscript
    
    def check_struct_literal(self, struct_literal: StructLiteral):
        if type(struct_literal.name) is Subscript:
            struct_literal.name.items = tuple(self.module.import_type(hint) for hint in struct_literal.name.items)

        type_ = self.module.import_type(struct_literal.name)

        if type(type_.declaration) is UnionDeclaration:
            return self.check_union_literal(struct_literal)
        
        struct_literal.structure = type_
        struct_literal.arguments = [self.check_expression(argument) for argument in struct_literal.arguments]

        if len(struct_literal.arguments) > len(type_.declaration.fields):
            raise ValueError(f'too many arguments for struct literal "{struct_literal.format}", expected {len(type_.declaration.fields)}, got {len(struct_literal.arguments)}. at line {struct_literal.line}. in module {self.module.name}')
        elif len(struct_literal.arguments) < len(type_.declaration.fields):
            raise ValueError(f'too few arguments for struct literal "{struct_literal.format}", expected {len(type_.declaration.fields)}, got {len(struct_literal.arguments)}. at line {struct_literal.line}. in module {self.module.name}')
        
        for (field_name, field_type), argument in zip(type_.declaration.fields, struct_literal.arguments):
            if not self.check_type_compatibility(field_type, argument.type_):
                raise TypeError(f"incompatible type for struct literal field '{field_name.format}'. expected '{field_type.format}', got '{argument.type_}'")

        return Typed(struct_literal, type_)
    
    def check_union_literal(self, struct_literal: StructLiteral):
        type_ = self.module.import_type(struct_literal.name)

        struct_literal.structure = type_
        struct_literal.arguments = [self.check_expression(argument) for argument in struct_literal.arguments]

        if len(struct_literal.arguments) > 1:
            raise ValueError(f'too many arguments for union literal "{struct_literal.format}", expected 1, got {len(struct_literal.arguments)}. at line {struct_literal.line}. in module {self.module.name}')
        elif len(struct_literal.arguments) < 1:
            raise ValueError(f'too few arguments for union literal "{struct_literal.format}", expected 1, got {len(struct_literal.arguments)}. at line {struct_literal.line}. in module {self.module.name}')
        
        is_argument_compatible = False
        types_format = []

        for (_, field_type) in type_.declaration.fields:
            types_format.append(field_type.format)

            if self.check_type_compatibility(field_type, struct_literal.arguments[0].type_):
                is_argument_compatible = True
                break
        
        if not is_argument_compatible:
            raise TypeError(f"incompatible type for union literal. expected '{' | '.join(types_format)}', got '{struct_literal.arguments[0].type_}'")

        return Typed(struct_literal, type_)

    def check_unary_operator(self, unary_operator: UnaryOperator):
        unary_operator.expression = self.check_expression(unary_operator.expression)

        if unary_operator.operator.kind is TokenKind.Minus:
            return Typed(unary_operator, INT)
        elif unary_operator.operator.kind is TokenKind.Plus:
            return Typed(unary_operator, INT)
        elif unary_operator.operator.kind is TokenKind.Interrogation:
            return Typed(unary_operator, BOOL)

        raise NotImplementedError(f"unary operator '{unary_operator.operator.format}' is not implemented yet")
    
    def check_binary_operator(self, binary_operator: BinaryOperator):
        binary_operator.left = self.check_expression(binary_operator.left)
        binary_operator.right = self.check_expression(binary_operator.right)

        if not self.check_type_compatibility(binary_operator.left.type_, binary_operator.right.type_):
            raise TypeError(f"type mismatch for binary operation '{binary_operator.operator.format}', {binary_operator.left.type_} != {binary_operator.right.type_}. at line {binary_operator.line} in module {self.module.name}")
        
        if binary_operator.operator.kind is TokenKind.EqualEqual:
            return Typed(binary_operator, BOOL)
        elif binary_operator.operator.kind is TokenKind.NotEqual:
            return Typed(binary_operator, BOOL)
        elif binary_operator.operator.kind is TokenKind.GreaterThan:
            return Typed(binary_operator, BOOL)
        elif binary_operator.operator.kind is TokenKind.LessThan:
            return Typed(binary_operator, BOOL)
        
        elif binary_operator.operator.kind is TokenKind.Minus:
            return Typed(binary_operator, INT)
        elif binary_operator.operator.kind is TokenKind.Plus:
            return Typed(binary_operator, INT)
        elif binary_operator.operator.kind is TokenKind.Star:
            return Typed(binary_operator, INT)

        raise NotImplementedError(f"binary operator '{binary_operator.operator.format}' is not implemented yet")
    
    def check_test_guard(self, test_guard: TestGuard):
        if type(test_guard.expression) is Attribute:
            test_guard.expression = self.check_attribute(test_guard.expression, guarantee=True)
        else:
            test_guard.expression = self.check_expression(test_guard.expression)

        return Typed(test_guard, BOOL)

    def check_expression(self, expression: Expression):
        if type(expression) is Comptime:
            return self.check_comptime(expression)
        elif type(expression) is Body:
            return Typed(self.check_body(expression, VOID), VOID)

        if type(expression) is Name:
            if expression in self.module.types or expression in BASIC_TYPES:
                return Typed(self.module.import_type(expression), TYPE)
            elif expression in self.module.imports:
                return Typed(expression, MODULE)
            elif expression in self.module.functions:
                return Typed(expression, FUNCTION)
            
            if expression in self.module.scope.type_variables:
                type_variable = self.module.scope.get_type_variable(expression)
                type_variable = self.module.import_type(type_variable)

                return Typed(type_variable, type_variable.type_)

            variable = self.module.scope.get_variable(expression)

            return Typed(expression, variable.type_)
        elif type(expression) is Literal:
            if type(expression.value) is str:
                return Typed(expression, STR)
            elif type(expression.value) is int:
                return Typed(expression, INT)
            elif type(expression.value) is float:
                return Typed(expression, FLOAT)
        elif type(expression) is Call:
            return self.check_call(expression)
        elif type(expression) is Attribute:
            return self.check_attribute(expression)
        elif type(expression) is Subscript:
            return self.check_subscript(expression)
        elif type(expression) is StructLiteral:
            return self.check_struct_literal(expression)
        
        elif type(expression) is UnaryOperator:
            if expression.operator.kind is TokenKind.Ampersand:
                variable = self.module.scope.get_variable(expression.expression)

                # NOTE: May cause trouble
                return Typed(expression, Type(Subscript(PTR, (variable.type_,)), PTR.uid, PTR.associated_functions, variable.type_.declaration))
            
            return self.check_unary_operator(expression)
        elif type(expression) is BinaryOperator:
            return self.check_binary_operator(expression)
        elif type(expression) is TestGuard:
            return self.check_test_guard(expression)

        raise NotImplementedError(f"can't check the type of {expression}. at line {expression.line}. in module {self.module.name}")

    def check_return(self, return_: Return, return_type: Type):
        if type(return_type) is not Type:
            raise TypeError(f'return_type must be a Type')
        
        return_.value = self.check_expression(return_.value)

        if not self.check_type_compatibility(return_.value.type_, return_type):
            raise TypeError(f'incompatible types for return, function expectes {return_type} but a {return_.value.type_} was provided. at line {return_.line}. in module {self.module.name}')

        return return_
    
    def check_comptime(self, comptime: Comptime):
        comptime.value = self.check_expression(comptime.value)
        interpreter = Interpreter(self.module)

        return interpreter.interpret(comptime)
    
    def check_variable_declaration(self, variable_declaration: VariableDeclaration):
        variable_declaration.value = self.check_expression(variable_declaration.value)

        if variable_declaration.hint is None:
            variable_declaration.hint = variable_declaration.value.type_
        else:
            variable_declaration.hint = self.module.import_type(variable_declaration.hint)
        
        variable_declaration = Typed(variable_declaration, variable_declaration.hint)

        self.module.scope.variables[variable_declaration.name] = variable_declaration

        return variable_declaration
    
    def check_assignment(self, assignment: Assignment):
        if type(assignment.name) is Subscript:
            subscript = self.check_subscript(assignment.name)
            assignment.name = subscript
            type_ = subscript.type_
        elif type(assignment.name) is Attribute:
            attribute = self.check_attribute(assignment.name)
            assignment.name = attribute
            type_ = attribute.type_
        else:
            variable = self.module.scope.get_variable(assignment.name)
            type_ = variable.type_
        
        assignment.value = self.check_expression(assignment.value)

        if not self.check_type_compatibility(type_, assignment.value.type_):
            raise TypeError(f"type mismatch variable or field '{assignment.name.format}' expects '{type_.format}', got a {assignment.value.type_}. at line {assignment.line} in module {self.module.name}")

        return Typed(assignment, type_)

    def check_body(self, body: Body, return_type: Type):
        def check(line: Ast):
            if type(line) is Return:
                return self.check_return(line, return_type)
            elif type(line) is If:
                return self.check_if(line, return_type)
            elif type(line) is While:
                return self.check_while(line, return_type)
            elif type(line) is Comptime:
                return self.check_comptime(line)
            elif type(line) is VariableDeclaration:
                return self.check_variable_declaration(line)
            elif type(line) is Assignment:
                return self.check_assignment(line)
            elif type(line) is Call:
                return self.check_call(line)
            
            raise NotImplementedError(f'check() for {line} is not implemented yet')

        body.lines = [check(line) for line in body.lines]
        
        return body
    
    # NOTE: work here ...
    def check_function_declaration(self, function_declaration: FunctionDeclaration):
        old_scope = self.module.scope
        self.module.scope = old_scope.copy()

        generic = function_declaration.head.generic

        if not generic:
            function_declaration.head.return_hint = self.module.import_type(function_declaration.head.return_hint)
            function_declaration.head.arguments = [(argument_name, self.module.import_type(argument_hint)) for argument_name, argument_hint in function_declaration.head.arguments]

        if type(function_declaration.head.name) is Attribute:
            if function_declaration.head.name.left in self.module.types:
                type_ = self.module.import_type(function_declaration.head.name.left)
                type_.associated_functions[function_declaration.head.name.right] = AssociatedFunction(type_, function_declaration)
            elif function_declaration.head.name.left in BASIC_TYPES:
                type_ = self.module.import_type(function_declaration.head.name.left)
                type_.associated_functions[function_declaration.head.name.right] = AssociatedFunction(type_, function_declaration)
            else:
                raise Exception(f"associating functions to external types is forbidden. in module {self.module.name}")
        elif type(function_declaration.head.name) is Subscript:
            attribute = function_declaration.head.name.head
            
            if type(attribute) is Attribute:
                if attribute.left in self.module.types:
                    type_ = self.module.import_type(attribute.left)
                    type_.associated_functions[attribute.right] = AssociatedFunction(type_, function_declaration)
                else:
                    raise Exception(f"associating functions to external types is forbidden. tried to associate to '{attribute.left.format}' in module {self.module.name}")
            else:
                self.module.functions[function_declaration.head.name.head] = function_declaration
        else:
            self.module.functions[function_declaration.head.name] = function_declaration

        if not generic:
            for argument_name, argument_type in function_declaration.head.arguments:
                self.module.scope.variables[argument_name] = FunctionArgument(argument_name, argument_type)
        
            function_declaration.body = self.check_body(function_declaration.body, function_declaration.head.return_hint)

        self.module.scope = old_scope

        return function_declaration
    
    def check_if(self, if_: If, return_type: Type):
        old_scope = self.module.scope
        self.module.scope = old_scope.copy()

        if_.condition = self.check_expression(if_.condition)

        if type(if_.condition.value) is TestGuard:
            self.module.scope.type_guards.append(Attribute(if_.condition.value.expression.value.left.type_, if_.condition.value.expression.value.right))

        if_.true_body = self.check_body(if_.true_body, return_type)

        if if_.false_body is not None:
            if type(if_.false_body) is If:
                if_.false_body = self.check_if(if_.false_body, return_type)
            else:
                if_.false_body = self.check_body(if_.false_body, return_type)
        
        self.module.scope = old_scope

        return if_
    
    def check_while(self, while_: While, return_type: Type):
        while_.condition = self.check_expression(while_.condition)
        while_.body = self.check_body(while_.body, return_type)

        return while_
    
    def check_extern(self, extern: Extern):
        extern.head.return_hint = self.module.import_type(extern.head.return_hint)
        extern.head.arguments = [(argument_name, self.module.import_type(argument_hint)) for argument_name, argument_hint in extern.head.arguments]
        
        if type(extern.head.name) is Attribute:
            raise NameError(f'extern functions must have flat names')
        else:
            self.module.functions[extern.head.name] = extern

        return extern
    
    def check_import(self, import_: Import):
        os_module_name = import_.module_name.format.replace('.', os.sep) + '.gullian'

        if 'GULLIAN_HOME' in os.environ and not os.path.isfile(os_module_name):
            os_module_name = os.path.join(os.environ['GULLIAN_HOME'], os_module_name)

        if not os.path.isfile(os_module_name):
            if 'GULLIAN_HOME' in os.environ:
                raise ImportError(f"can't import gullian module {import_.module_name.format}, file not found.")
        
            raise ImportError(f"can't import gullian module {import_.module_name.format}, file not found. Make sure GULLIAN_HOME is set")

            
        file_string = open(os_module_name).read()
        module = Module.new(import_.module_name.format)

        tokens = tuple(Lexer(Source(file_string), module).lex())
        asts = tuple(Parser(Source(tokens), module).parse())
        checker = Checker(asts, module)

        for _ in checker.check():
            continue

        self.module.imports[import_.module_name.rightest] = checker.module

        return import_

    def check_enum_declaration(self, enum_declaration: EnumDeclaration):
        name = enum_declaration.name
        self.module.types[name] = Type.new(name, enum_declaration, self.module)

        return enum_declaration
    
    def check_struct_declaration(self, struct_declaration: StructDeclaration):
        name = struct_declaration.name

        if type(name) is Subscript:
            name = name.head
        
        if not struct_declaration.generic:
            struct_declaration.fields = [(field_name, self.module.import_type(field_hint)) for field_name, field_hint in struct_declaration.fields]
        
        self.module.types[name] = Type.new(struct_declaration.name, struct_declaration, self.module)

        return struct_declaration
    
    def check_union_declaration(self, union_declaration: UnionDeclaration):
        name = union_declaration.name

        if type(name) is Subscript:
            name = name.head
        
        generic = union_declaration.generic

        union_declaration.fields = [(field_name, GenericType(field_hint) if generic and field_hint in generic else self.module.import_type(field_hint)) for field_name, field_hint in union_declaration.fields]
        self.module.types[name] = Type.new(union_declaration.name, union_declaration, self.module)

        return union_declaration

    def check(self):
        for ast in self.asts:
            if type(ast) is Comment:
                yield ast
            elif type(ast) is Extern:
                yield self.check_extern(ast)
            elif type(ast) is Import:
                yield self.check_import(ast)
            elif type(ast) is EnumDeclaration:
                yield self.check_enum_declaration(ast)
            elif type(ast) is StructDeclaration:
                yield self.check_struct_declaration(ast)
            elif type(ast) is UnionDeclaration:
                yield self.check_union_declaration(ast)
            elif type(ast) is FunctionDeclaration:
                yield self.check_function_declaration(ast)
            else:
                raise NotImplementedError
        
        return
