from typing import TYPE_CHECKING
from typing import Generic, TypeVar
from dataclasses import dataclass
from random import randint

from .lexer import Name
from .parser import Ast, TypeDeclaration, FunctionDeclaration, Subscript

if TYPE_CHECKING:
    from .checker import Module

T = TypeVar('T')

@dataclass(repr=False)
class Type(Generic[T]):
    name: T
    uid: int
    associated_functions: dict[Name, FunctionDeclaration]
    declaration: TypeDeclaration=None
    module: "Module"=None

    def __repr__(self) -> str:
        return f"Type({self.uid}) {self.name.format}"

    def __hash__(self):
        return self.uid
    
    def __eq__(self, value: "Type"):
        if type(value) is Type:
            return self.uid == value.uid
        
        return False
    
    def import_any(self, name: Name):
        if type(name) is not Name:
            raise TypeError(f'argument name of Module.import_any(...) must be a Name')
        
        if name.value in self.associated_functions:
            return self.associated_functions[name]

        if self.declaration is not None:
            if name.value in self.declaration.fields:
                return self.declaration.fields[self.declaration.fields.index(name)]

            elif name.value in (fields_dict := dict(self.declaration.fields)):
                return fields_dict[name]
        
        if self.uid == PTR.uid:
            if type(self.name) is Subscript:
                return self.name.items[0].import_any(name)
        
        raise AttributeError(f'Type {self.name.format} does not contains a member called {name}')

    @property
    def type_(self):
        return TYPE

    @property
    def format(self):
        return self.name.format
    
    @property
    def line(self):
        return self.name.line

    @classmethod
    def new(cls, name: Name | str, declaration: TypeDeclaration=None, module: "Module"=None):
        if type(name) is str:
            return cls(Name(name, 0), cls.gen_uid(), dict(), declaration, module)
        
        return cls(name, cls.gen_uid(), dict(), declaration, module)
    
    @classmethod
    def gen_uid(cls):
        return randint(1000, 9999)

@dataclass(repr=False)
class GenericType:
    name: Name

    def __repr__(self):
        return f'GenericType({self.name})'
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, value: str):
        return self.name == value

    @property
    def format(self):
        return self.name.format
    
    @property
    def line(self):
        return self.name.line

@dataclass
class Typed(Generic[T]):
    value: T
    type_: Type

    def __hash__(self):
        return hash(self.value)

    def __getattr__(self, name: str):
        return getattr(self.value, name)

@dataclass
class AssociatedFunction:
    owner: Type
    declaration: FunctionDeclaration

    def __getattr__(self, name: str):
        return getattr(self.declaration, name)
    
TYPE = Type.new('type')
MODULE = Type.new('module')
VOID = Type.new('void')
BOOL = Type.new('bool')
U8 = Type.new('u8')
U16 = Type.new('u16')
U32 = Type.new('u32')
INT = Type.new('int')
FLOAT = Type.new('float')
STR = Type.new('str')
BYTE = Type.new('byte')
CHAR = Type.new('char')
PTR = Type.new('ptr')
FUNCTION = Type.new('function')
ANY = Type.new('ANY')

BASIC_TYPES = {
    'type': TYPE,
    'module': MODULE,
    'void': VOID,
    'bool': BOOL,
    'int': INT,
    'u8': U8,
    'u16': U16,
    'u32': U32,
    'float': FLOAT,
    'str': STR,
    'byte': BYTE,
    'char': CHAR,
    'ptr': PTR,
    'function': FUNCTION,
    'any': ANY
}

@dataclass
class FunctionArgument:
    value: Name
    type_: Type