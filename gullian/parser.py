from typing import TYPE_CHECKING
from dataclasses import dataclass

from .source import Source
from .lexer import TOKENKIND_UNARYOPERATORS, TOKENKIND_BINARYOPERATORS, TOKENKIND_ASSIGNMENTOPERATORS
from .lexer import Token, Keyword, TokenKind, KeywordKind, Name, Literal, Comment

if TYPE_CHECKING:
    from .checker import Module

@dataclass
class Body:
    lines: list["Ast"]

    @property
    def format(self):
        return '{ ... }'
    
    @property
    def line(self):
        if self.lines:
            return self.lines[0].line
        
        return 0

@dataclass
class FunctionHead:
    name: "Name | Subscript"
    arguments: list[tuple[Name, "Expression"]]
    return_hint: Name
    generic: list
    module: "Module"

    @property
    def format(self):
        return f'fun {self.name.format}(...) : {self.return_hint.format}'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class StructDeclaration:
    name: Name
    fields: list[tuple[Name, "Expression"]]
    generic: list

    @property
    def format(self):
        return f'struct {self.name.format} {{ ... }}'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class UnionDeclaration:
    name: Name
    fields: list[tuple[Name, "Expression"]]
    generic: list

    @property
    def format(self):
        return f'union {self.name.format} {{ ... }}'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class Extern:
    head: FunctionHead

    @property
    def format(self):
        return f'extern {self.head.format}'
    
    @property
    def line(self):
        return self.head.line

@dataclass
class Import:
    module_name: "Name | Attribute"

    @property
    def format(self):
        return f'import {self.module_name.format}'
    
    @property
    def line(self):
        return self.module_name.line

@dataclass
class EnumDeclaration:
    name: Name
    fields: tuple[Name]

    @property
    def format(self):
        return f'enum {self.name.format} {{ ... }}'
    
    @property
    def line(self):
        return self.name.line
    
    @property
    def generic(self):
        return []

@dataclass
class FunctionDeclaration:
    head: FunctionHead
    body: Body

    @property
    def format(self):
        return f'{self.head.format} {{ ... }}'
    
    @property
    def line(self):
        return self.head.line

@dataclass
class VariableDeclaration:
    name: Name
    value: "Expression"
    hint: "Expression"=None

    @property
    def format(self):
        if self.hint is None:
            return f'let {self.name.format} = ...'
        
        return f'let {self.name.format}: {self.hint.format} = ...'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class If:
    condition: "Expression"
    true_body: Body
    false_body: "If | Body"=None

    @property
    def format(self):
        if self.false_body is None:
            return f'if {self.condition.format} {{ ... }}'
        
        return f'if {self.condition.format} {{ ... }} else {{ ... }}'
    
    @property
    def line(self):
        return self.condition.line

@dataclass
class While:
    condition: "Expression"
    body: Body

    @property
    def format(self):
        return f'while {{ ... }}'
    
    @property
    def line(self):
        return self.condition.line

@dataclass
class Return:
    value: "Expression"

    @property
    def format(self):
        return f'return {self.value.format}'
    
    @property
    def line(self):
        return self.value.line

@dataclass
class Comptime:
    value: "Expression"

    @property
    def format(self):
        return f'comptime {self.value.format}'
    
    @property
    def line(self):
        return self.value.line
    
@dataclass
class Switch:
    expression: "Expression"
    branches: dict["Expression", "Expression"]

    @property
    def format(self):
        return f'switch {self.expression.format} {{ ... }}'
    
    @property
    def default_branch(self):
        return self.branches['_'] if '_' in self.branches else list(self.branches.keys())[-1] 
    
    @property
    def line(self):
        return self.expression.line

@dataclass
class Call:
    name: Name
    arguments: list["Expression"]
    generics: list
    declaration: FunctionDeclaration=None

    @property
    def format(self):
        if len(self.arguments) == 0:
            return f'{self.name.format}()'
        
        return f'{self.name.format}(...)'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class StructLiteral:
    name: Name
    arguments: list["Expression"]
    structure: StructDeclaration=None

    @property
    def format(self):
        return f'{self.name.format} {{ ... }}'
    
    @property
    def line(self):
        return self.name.line

@dataclass
class UnaryOperator:
    operator: Token
    expression: "Expression"

    @property
    def format(self):
        return f'{self.operator.format}{self.expression.format}'
    
    @property
    def line(self):
        return self.operator.line

@dataclass
class TestGuard:
    expression: "Expression"

    @property
    def format(self):
        return f'{self.expression.format}?'
    
    @property
    def line(self):
        return self.expression.line  

@dataclass
class BinaryOperator:
    left: "Expression"
    operator: Token
    right: "Expression"

    @property
    def format(self):
        return f'{self.left.format} {self.operator.format} {self.right.format}'
    
    @property
    def line(self):
        return self.left.line

@dataclass
class Subscript:
    head: "Name | Attribute | Subscript"
    items: tuple["Name | Attribute | Subscript"]

    def __hash__(self):
        return hash((self.head, self.items))
    
    @property
    def format(self):
        return f'{self.head.format}[{", ".join(item.format for item in self.items)}]'
    
    @property
    def line(self):
        return self.head.line

@dataclass
class Attribute:
    left: "Name | Attribute"
    right: "Name | Attribute"

    def __hash__(self):
        return hash((self.left, self.right))

    @property
    def format(self):
        return f'{self.left.format}.{self.right.format}'
    
    @property
    def line(self):
        return self.left.line

    @property
    def rightest(self):
        if type(self.right) is Attribute:
            return self.right.rightest
        
        return self.right
    
    @property
    def least(self):
        if type(self.right) is Attribute:
            return self.right.least
        
        return self.left

@dataclass
class Assignment:
    name: "Name | Attribute"
    operator: Token
    value: "Name | Attribute"

    @property
    def format(self):
        return f'{self.name.format} = {self.value.format}'
    
    @property
    def line(self):
        return self.name.line

Expression = Name | Literal | Call | StructLiteral | Attribute | BinaryOperator
TypeDeclaration = EnumDeclaration | StructDeclaration | UnionDeclaration
Ast = Expression | TypeDeclaration | FunctionDeclaration | VariableDeclaration | Assignment | While | If

@dataclass
class Parser:
    source: Source
    module: "Module"

    def parse_call(self, name: Name) -> Call:
        arguments = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightParenthesis:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            arguments.append(self.parse_expression(token))
        
        if type(name) is Subscript:
            return Call(name.head, arguments, name.items)

        return Call(name, arguments, list())
    
    def parse_struct_literal(self, name: Name):
        arguments = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            arguments.append(self.parse_expression(token))

        return StructLiteral(name, arguments)
    
    def parse_attribute(self, name: Name) -> Attribute:
        token = self.source.capture()

        if type(token) is Token and token.kind is TokenKind.Dot:
            next_name = self.source.capture()

            if type(next_name) is not Name:
                raise TypeError(f"expecting a Name asfter {name}, got {next_name}. at line {name.line}. in module {self.module.name}")

            return self.parse_attribute(Attribute(name, next_name))
        else:
            self.source.release()
        
        return name
    
    def parse_subscript(self, name: Name):
        token = self.source.capture()

        if not (type(token) is Token and token.kind is TokenKind.LeftBracket):
            raise SyntaxError(f"expected '[', got {token.format}. at line {token.line}. in module {self.module.name}")
        
        items = []

        for token in self.source:
            if type(token) is Token:
                if token.kind is TokenKind.RightBracket:
                    break
                elif token.kind is TokenKind.Comma:
                    continue

            items.append(self.parse_expression(token, terminals={TokenKind.RightBracket}))

        return Subscript(name, tuple(items))

    def parse_type_name(self, name: Name | Attribute | Subscript):
        if not (type(name) is Name or type(name) is Attribute or type(name) is Subscript):
            raise TypeError(f'name must be Name, Attribute or Subscript, found Token "{name.format}". in line {name.line}. at module {self.module.name}')
        
        token = self.source.capture()

        if type(token) is Token:
            if token.kind is TokenKind.Dot:
                self.source.release()
                
                return self.parse_type_name(self.parse_attribute(name))
            
            elif token.kind is TokenKind.LeftBracket:
                self.source.release()

                return self.parse_type_name(self.parse_subscript(name))

        self.source.release()

        return name

    def parse_expression(self, expression: Expression, terminals: set[TokenKind]=set()):
        if type(expression) is Token:
            if expression.kind in TOKENKIND_UNARYOPERATORS:
                return self.parse_expression(UnaryOperator(expression, self.parse_expression(self.source.capture(), terminals)), terminals)
            elif expression.kind is TokenKind.LeftParenthesis:
                right_parenthesis = self.source.capture()

                if type(right_parenthesis) is Token and right_parenthesis.kind is TokenKind.RightParenthesis:
                    raise SyntaxError(f"Empty parenthesized expression, at line {expression.line}. in module {self.module.name}")
                else:
                    self.source.release()

                expression = self.parse_expression(self.source.capture(), terminals={TokenKind.RightParenthesis} | terminals)

                right_parenthesis = self.source.capture()

                if not (type(right_parenthesis) is Token and right_parenthesis.kind is TokenKind.RightParenthesis):
                    raise SyntaxError(f"Empty parenthesized expression, at line {expression.line}. in module {self.module.name}")
                
                return self.parse_expression(expression, terminals)
            
            raise TypeError(f"expression must be Ast, found Token '{expression.format}'. in line {expression.line}. at module {self.module.name}")
        elif type(expression) is Keyword:
            if expression.kind is KeywordKind.Comptime:
                return self.parse_comptime()
            elif expression.kind is KeywordKind.Switch:
                return self.parse_switch()

            raise TypeError(f'expression must be Ast, found Keyword "{expression.format}". in line {expression.line}. at module {self.module.name}')
        
        token = self.source.capture()

        if type(token) is Token:
            if token.kind in terminals:
                self.source.release()
                return expression
            
            if token.kind in TOKENKIND_BINARYOPERATORS:
                return BinaryOperator(expression, token, self.parse_expression(self.source.capture(), terminals=terminals))
            
            elif token.kind is TokenKind.LeftParenthesis:
                return self.parse_expression(self.parse_call(expression), terminals=terminals)
            elif token.kind is TokenKind.LeftBrace:
                return self.parse_struct_literal(expression)
            elif token.kind is TokenKind.Dot:
                self.source.release()
                
                return self.parse_expression(self.parse_attribute(expression), terminals)
            
            elif token.kind is TokenKind.LeftBracket:
                self.source.release()

                return self.parse_expression(self.parse_subscript(expression), terminals)
            
            elif token.kind is TokenKind.Interrogation:
                return self.parse_expression(TestGuard(expression), terminals)

        self.source.release()

        return expression

    def parse_function_head(self) -> FunctionHead:
        name = self.source.capture()

        if type(name) is not Name:
            raise TypeError(f"expecting a Name, found '{name.format}'. at line {name.line}")

        name = self.parse_type_name(name)
        token = self.source.capture()

        if not (type(token) is Token and token.kind is TokenKind.LeftParenthesis):
            raise TypeError(f"expecting '(', found '{token.format}' before argument list of function {name}. at line {token.line}")
        
        arguments = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightParenthesis:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            if type(token) is not Name:
                raise TypeError(f'expecting a Name, found {token}. at line {token.line}')

            token = self.parse_expression(token)
            colon = self.source.capture()
            
            if not (type(colon) is Token and colon.kind is TokenKind.Colon):
                raise SyntaxError(f"expecting ':' before parameter type of {token}. in module {self.module.name}")
            
            arguments.append((token, self.parse_expression(self.source.capture())))
        
        colon = self.source.capture()
            
        if not (type(colon) is Token and colon.kind is TokenKind.Colon):
            raise SyntaxError(f"expecting ':' before parameter type of {colon}. in module {self.module.name}")

        return_hint = self.parse_expression(self.source.capture(), terminals={TokenKind.LeftBrace})

        if type(name) is Subscript:
            generic = name.items
        else:
            generic = list()

        return FunctionHead(name, arguments, return_hint, generic, self.module)
    
    def parse_assignment(self, name: Name | Attribute, operator: Token) -> Assignment:
        return Assignment(name, operator, self.parse_expression(self.source.capture()))
    
    def parse_body(self) -> Body:
        left_brace = self.source.capture()
            
        if not (type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace):
            raise SyntaxError(f"expecting '{{' before body, found {left_brace}")
        
        lines = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            if type(token) is Keyword:
                if token.kind is KeywordKind.Fun:
                    lines.append(self.parse_function_declaration())
                elif token.kind is KeywordKind.Let:
                    lines.append(self.parse_variable_declaration())
                elif token.kind is KeywordKind.If:
                    lines.append(self.parse_if())
                elif token.kind is KeywordKind.While:
                    lines.append(self.parse_while())
                elif token.kind is KeywordKind.Return:
                    lines.append(self.parse_return())
                elif token.kind is KeywordKind.Comptime:
                    lines.append(self.parse_comptime())
                elif token.kind is KeywordKind.Switch:
                    lines.append(self.parse_switch())
                else:
                    raise NotImplementedError(f'parsing for keyword {token} is not implemented yet')
            elif type(token) is Name:
                token = self.parse_expression(token)
                next_token = self.source.capture()
                
                if type(next_token) is Token and next_token.kind in TOKENKIND_ASSIGNMENTOPERATORS:
                    lines.append(self.parse_assignment(token, next_token))
                else:
                    self.source.release()
                    lines.append(token)
            else:
                raise NotImplementedError(f'parsing for {token} is not implemented yet')
        
        return Body(lines)

    def parse_extern(self) -> Extern:
        token = self.source.capture()

        if type(token) is Keyword and token.kind is KeywordKind.Fun:
            return Extern(self.parse_function_head())
        
        raise SyntaxError(f'missing keyword fun. at line {token.kind}. in module {self.module.name}')
    
    def parse_import(self) -> Import:
        return Import(self.parse_attribute(self.source.capture()))
    
    def parse_enum_declaration(self) -> EnumDeclaration:
        name = self.source.capture()

        if type(name) is not Name:
            raise TypeError(f"expecting a Name, found {type(name)}. at line {name.line}")

        left_brace = self.source.capture()
            
        if not (type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace):
            raise SyntaxError(f"expecting '{{' before body, found {left_brace}")
        
        fields = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            if type(token) is not Name:
                raise TypeError(f'expecting a Name, found {token}. at line {token.line}')

            fields.append(token)

        return EnumDeclaration(name, fields)
    
    def parse_struct_declaration(self) -> StructDeclaration:
        name = self.parse_type_name(self.source.capture())

        if type(name) is Name | type(name) is Subscript:
            raise TypeError(f"expecting a Name or Subscript, found {type(name)}. at line {name.line}")
        
        left_brace = self.source.capture()
            
        if not (type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace):
            raise SyntaxError(f"expecting '{{' before body, found {left_brace}")
        
        fields = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            if type(token) is not Name:
                raise TypeError(f'expecting a Name, found {token}. at line {token.line}')

            colon = self.source.capture()
            
            if not (type(colon) is Token and colon.kind is TokenKind.Colon):
                raise SyntaxError(f"expecting ':' before parameter type of {token}")
            
            fields.append((token, self.parse_expression(self.source.capture())))
        
        if type(name) is Subscript:
            generic = name.items
        else:
            generic = list()
        
        return StructDeclaration(name, fields, generic)
    
    def parse_union_declaration(self) -> UnionDeclaration:
        name = self.parse_type_name(self.source.capture())

        if type(name) is Name | type(name) is Subscript:
            raise TypeError(f"expecting a Name or Subscript, found {type(name)}. at line {name.line}")
        
        left_brace = self.source.capture()
            
        if not (type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace):
            raise SyntaxError(f"expecting '{{' before body, found {left_brace}")
        
        fields = []

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            if type(token) is not Name:
                raise TypeError(f'expecting a Name, found {token}. at line {token.line}')

            colon = self.source.capture()
            
            if not (type(colon) is Token and colon.kind is TokenKind.Colon):
                raise SyntaxError(f"expecting ':' before parameter type of {token}")
            
            fields.append((token, self.parse_expression(self.source.capture())))
        
        if type(name) is Subscript:
            generic = name.items
        else:
            generic = list()
        
        return UnionDeclaration(name, fields, generic)

    def parse_function_declaration(self) -> FunctionDeclaration:
        return FunctionDeclaration(self.parse_function_head(), self.parse_body())
    
    def parse_variable_declaration(self) -> VariableDeclaration:
        name = self.source.capture()

        if type(name) is not Name:
            raise TypeError(f"expecting a Name, found {type(name)}. at line {name.line}")

        hint = None
        colon = self.source.capture()
            
        if type(colon) is Token and colon.kind is TokenKind.Colon:
            hint = self.parse_expression(self.source.capture())
        else:
            self.source.release()
        
        equal = self.source.capture()
            
        if not (type(equal) is Token and equal.kind is TokenKind.Equal):
            raise SyntaxError(f"expecting '=' before parameter type of let {name.value}. at line {equal.line}. in {self.module.name}")

        return VariableDeclaration(name, self.parse_expression(self.source.capture()), hint)
    
    def parse_if(self) -> If:
        true_condition = self.parse_expression(self.source.capture(), terminals={TokenKind.LeftBrace})
        true_body = self.parse_body()
        false_body = None

        else_keyword = self.source.capture()

        if type(else_keyword) is Keyword and else_keyword.kind is KeywordKind.Else:
            false_body = self.parse_body()
        elif type(else_keyword) is Keyword and else_keyword.kind is KeywordKind.Elif:
            false_body = self.parse_if()
        else:
            self.source.release()

        return If(true_condition, true_body, false_body)

    def parse_while(self) -> While:
        return While(self.parse_expression(self.source.capture(), terminals={TokenKind.LeftBrace}), self.parse_body())
    
    def parse_return(self) -> Return:
        return Return(self.parse_expression(self.source.capture()))
    
    def parse_comptime(self) -> Comptime:
        left_brace = self.source.capture()
        self.source.release()

        if type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace:
            return Comptime(self.parse_body())

        return Comptime(self.parse_expression(self.source.capture()))
    
    def parse_switch(self) -> Switch:
        name = self.parse_expression(self.source.capture(), {TokenKind.LeftBrace})
        left_brace = self.source.capture()

        if not (type(left_brace) is Token and left_brace.kind is TokenKind.LeftBrace):
            raise SyntaxError(f"expecting '{{' after switch statement head, found {left_brace}. at line {left_brace.line}, in module {self.module.name}.")
        
        branches = dict()

        for token in self.source:
            if type(token) is Token and token.kind is TokenKind.RightBrace:
                break
            elif type(token) is Token and token.kind is TokenKind.Comma:
                continue

            expression = self.parse_expression(token, {TokenKind.Colon})
            colon = self.source.capture()
            
            if not (type(colon) is Token and colon.kind is TokenKind.Colon):
                raise SyntaxError(f"expecting ':' for brach of switch, found {colon.format}. at line {colon.line}, in module {self.module.name}.")
            
            branches[expression] = self.parse_expression(self.source.capture(), {TokenKind.Comma, TokenKind.RightBrace})

        return Switch(name, branches)
    
    def parse(self):
        for token in self.source:
            if type(token) is Keyword:
                if token.kind is KeywordKind.Extern:
                    yield self.parse_extern()
                elif token.kind is KeywordKind.Import:
                    yield self.parse_import()
                elif token.kind is KeywordKind.Enum:
                    yield self.parse_enum_declaration()
                elif token.kind is KeywordKind.Struct:
                    yield self.parse_struct_declaration()
                elif token.kind is KeywordKind.Union:
                    yield self.parse_union_declaration()
                elif token.kind is KeywordKind.Fun:
                    yield self.parse_function_declaration()
                elif token.kind is KeywordKind.Comptime:
                    yield self.parse_comptime()
                else:
                    raise NotImplementedError(f'parsing for keyword {token} is not implemented yet')
            elif type(token) is Comment:
                yield token
            else:
                raise NotImplementedError(f'parsing for {token} is not implemented yet')
        
        return
