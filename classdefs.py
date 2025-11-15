'''
This file does class definitions for Interpreter V3 and V4
'''

from types import NoneType
from typing import List, Type, Union
from element import Element

class Object:
    def __init__(self):
        self.value = {}
    
    def __str__(self):
        return str(self.value)

class Value:
    def __init__(
        self,
        kind: Type[int] | Type[str] | Type[bool] | Type[Object] | NoneType | None,
        value: Union[int, str, bool, Object, None]
    ):
        if kind is not None and value is not None and not isinstance(value, kind):
            raise TypeError(f"value {value!r} is not an instance of {kind.__name__}")
        
        self.kind = kind
        self.value = value
        
    def __str__(self):
        if self.kind == bool:
            return 'true' if self.value else 'false'
        return str(self.value)
    
    def __repr__(self):
        return f'|{str(self.kind)}, {self.value}|'
    
    
class ReturnSignal(Exception):
    def __init__(self, *args, val: Value):
        super().__init__(*args)
        self.val = val
        
        
def generate_function_signature(args: Union[List[Element], List[Value]]) -> str:
    """
    Pass in a list of Arg Nodes or Values to this function, and it will generate a function signature you can use to match
    
    Returns:
        signature (str): function signature in this format: "ios", this means there are 3 args: int, object, string
        
    Throws:
        Exception("NVART"): No Valid Arg Return Type detected for an argument
    """
    _ = ''
    
    if len(args) > 0 and type(args[0]) == Element:
        for arg in args:
            if arg.dict['name'][-1] in ['i', 's', 'b', 'o']:
                _ += arg.dict['name'][-1]
            else:
                raise Exception("NVART")
    else:
        for arg in args:
            if arg.kind == int:
                _ += 'i'
            elif arg.kind == str:
                _ += 's'
            elif arg.kind == bool:
                _ += 'b'
            elif arg.kind == Object:
                _ += 'o'
            else: # this is a lil' hack for detecting errors when you have a getValuei(print(50)) going on here, the print(50) gets evaluated to a (None, None) Value arg and we need to ensure it never matches a valid getValuei() signature
                raise Exception('NVART')
    return _


def get_variable_type(var_name: str) -> Type[int] | Type[str] | Type[bool] | Type[Object]:
    """
    Takes in a variable name and returns what type it is
    
    Throws:
        Exception("NVRT"): No Valid Return Type detected for variable
    """
    match var_name[-1]:
        case "i":
            return int
        case "s":
            return str
        case "b":
            return bool
        case "o":
            return Object
        case _:
            raise Exception('NVRT')


def get_default_value(var_type: Type[int] | Type[str] | Type[bool] | Type[Object] | None) -> Value:
    """
    Takes in a type and outputs the default value that should be given to that variable
    """
    if var_type == int:
        return Value(int, 0)
    if var_type == str:
        return Value(str, "")
    if var_type == bool:
        return Value(bool, False)
    if var_type == Object:
        return Value(Object, None) # default value for newly initialized Object variable is nil
    
    return Value(None, None)


class Function():
    """
    Function object definition
    
    Attributes:
        name (str): Function name
        return_type Union[int, str, bool, dict, None]: Ret type
        function (Element): the function Element node
        signature (str): function signature in this format: "ios", this means there are 3 args: int, object, string
    """
    
    def __init__(self, function: Element):
        """
        Initializes.
        
        Throws:
            Exception("NVRT"): No Valid Return Type detected for function
        """
        self.name = function.dict['name']
        self.function = function
        self.signature = generate_function_signature(function.dict['args'])
        
        # detect return_type
        if self.name == 'main':
            self.return_type = None
        else:
            # get func return type
            match self.name[-1]:
                case "i":
                    self.return_type = int
                case "s":
                    self.return_type = str
                case "b":
                    self.return_type = bool
                case "o":
                    self.return_type = Object
                case "v":
                    self.return_type = None
                case _:
                    raise Exception('NVRT')
        
        
class Reference:
    def __init__(self, env: dict, name: str):
        self.env = env # holds the LOCAL_VARIABLES for the calling function (for pass by reference)
        self.name = name
        
    def get(self) -> Value:
        return self.env[self.name]
    
    def set(self, val: Value):
        self.env[self.name] = val
    
    @property
    def kind(self):
        return self.get().kind
    
    @property
    def value(self):
        return self.get().value
    
    def __str__(self):
        val = self.get()
        if val.kind == bool:
            return 'true' if val.value else 'false'
        return str(val.value)
    
    def __repr__(self):
        return f'Reference: {repr(self.get())}'