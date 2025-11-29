'''
This file does class definitions for Interpreter V3 and V4
'''

from typing import List, Type, Union
from element import Element

class Object:
    def __init__(self):
        self.value = {}
    
    def __str__(self):
        return str(self.value)
  
class Function:
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
        self.extended_signature = generate_extended_function_signature(function.dict['args'])

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
                case "f":
                    self.return_type = Function
                case _:
                    raise Exception('NVRT')
 
class Nil(Object, Function):
    def __repr__(self):
        return "Nil" 

class Value:
    def __init__(
        self,
        kind: Type[int] | Type[str] | Type[bool] | Type[Object] | Type[Nil] | None,
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


class ReturnSignal(Exception):
    def __init__(self, *args, val: Value):
        super().__init__(*args)
        self.val = val
        
        
def generate_function_signature(args: List[Element | Value | Reference ]) -> str:
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
            # interface type counts as Object in signature
            if arg.dict['name'][-1].isupper():
                _ += 'o'
            elif arg.dict['name'][-1] in ['i', 's', 'b', 'o', 'f']:
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
            elif arg.kind == Object: # add OR interface to here
                _ += 'o'
            elif arg.kind == Function:
                _ += 'f'
            else: # this is a lil' hack for detecting errors when you have a getValuei(print(50)) going on here, the print(50) gets evaluated to a (None, None) Value arg and we need to ensure it never matches a valid getValuei() signature
                raise Exception('NVART')
    return _


def generate_extended_function_signature(args: List[Element | Value | Reference]) -> str:
    """
    Pass in a list of Arg Nodes to this function, and it will generate an extended function signature you can use to match for interface fields
    
    Returns:
        signature (str): function signature in this format: "io&s", this means there are 3 args: int, object, ref string
        
    Throws:
        Exception("NVART"): No Valid Arg Return Type detected for an argument
    """
    _ = ''
    
    if len(args) > 0:
        for arg in args:
            # pass by ref
            if arg.dict['ref']:
                _ += '&'
                
            # use exact interface type
            if arg.dict['name'][-1].isupper():
                _ += arg.dict['name'][-1]
            elif arg.dict['name'][-1] in ['i', 's', 'b', 'o', 'f']:
                _ += arg.dict['name'][-1]
            else:
                raise Exception("NVART")
    return _


def get_variable_type(var_name: str) -> Type[int] | Type[str] | Type[bool] | Type[Object] | Type[Function]:
    """
    Takes in a variable name and returns what type it is
    
    Throws:
        Exception("NVRT"): No Valid Return Type detected for variable
    """
    # interface typing
    if var_name[-1].isupper():
        return Object
    
    match var_name[-1]:
        case "i":
            return int
        case "s":
            return str
        case "b":
            return bool
        case "o":
            return Object
        case "f":
            return Function
        case _:
            raise Exception('NVRT')


def get_default_value(var_type: Type[int] | Type[str] | Type[bool] | Type[Object] | Type[Function] | None) -> Value:
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
    if var_type == Function:
        return Value(Function, None) # TODO: work on nil representatino
    
    return Value(None, None)
        
        
def validate_interface(interface: Element, existing_interfaces: dict):
    '''
    Returns nothing if no errors
    
    Throws:
        Exception('Refer to interface not defined')
        Exception('Duplicate Field Name')
        Exception('Invalid Field Name)
    '''
    field_names = set()
    for field in interface.dict['fields']:
        name = field.dict['name']
        
        if name in field_names:
            raise Exception('Duplicate Field Name')
        
        try:
            get_variable_type(name)
        except Exception as e:
            if str(e) == 'NVRT':
                raise Exception('Invalid Field Name')

        if name[-1].isupper():
            if name[-1] not in existing_interfaces:
                raise Exception('Refer to interface not defined')
            
        field_names.add(name)


def types_equal(t1: type, t2: type) -> bool:
    if (t1 is Nil and (t2 is Object or t2 is Function)) or \
       (t2 is Nil and (t1 is Object or t1 is Function)):
        return True

    return t1 is t2