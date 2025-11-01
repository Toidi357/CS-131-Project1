'''
This file does class definitions for Interpreter V3 and V4
'''

from types import NoneType
from typing import List, Type, Union
from element import Element


class Value:
    def __init__(
        self,
        kind: Type[int] | Type[str] | Type[bool] | Type[dict] | NoneType | None,
        value: Union[int, str, bool, dict, None]
    ):
        if kind is not None and value is not None and not isinstance(value, kind):
            raise TypeError(f"value {value!r} is not an instance of {kind.__name__}")
        
        self.kind = kind
        self.value = value
        
    def __str__(self):
        if self.kind == bool:
            if self.value == True:
                return 'true'
            return 'false'
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
            if arg.kind == str:
                _ += 's'
            if arg.kind == bool:
                _ += 'b'
            if arg.kind == dict:
                _ += 'o'
            else: # this is a lil' hack for detecting errors when you have a getValuei(print(50)) going on here, the print(50) gets evaluated to a (None, None) Value arg and we need to ensure it never matches a valid getValuei() signature
                raise Exception('NVART')
    return _


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
                    self.return_type = dict
                case "v":
                    self.return_type = None
                case _:
                    raise Exception('NVRT')
        