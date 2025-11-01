from typing import List, Union, Type
from types import NoneType
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element

# Attach a type to every value
class Value:
    def __init__(
        self,
        kind: Type[int] | Type[str] | Type[bool] | NoneType | None,
        value: Union[int, str, bool, None]
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
        return f'{str(self.kind)}, {self.value}'
    
# Return type exception
class ReturnSignal(Exception):
    def __init__(self, *args, val: Value):
        super().__init__(*args)
        self.val = val

const_vals = int | float | str | bool

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        
    def run(self, program):
        program_root = parse_program(program)
        
        '''
        maintain a mapping of all function names to their respective Element; this will be global so any Expression can look it up
        function object is like this
        
        func_name: [{num_args: int, function: Function_Node}]
        '''
        
        self.functions = {}
        
        # load functions
        for func in program_root.dict['functions']:
            self.def_function(func)
        
        # run main
        if 'main' not in self.functions:
            super().error(
                ErrorType.NAME_ERROR,
                "no main() function was found"
            )
        
        # main is where we begin execution
        self.call_function('main', [])
    
    
    '''
    This function DEFINES a function. It does not run anything. Takes in 'func' type node
    '''
    def def_function(self, function: Element) -> None:
        if function.elem_type != InterpreterBase.FUNC_NODE:
            raise Exception(f"Element {function.dict['name']}, expected type 'func', but is {function.elem_type}")
        
        if function.dict['name'] in self.functions: # function overloading
            self.functions[function.dict['name']].append({
                'num_args': len(function.dict['args']),
                'function': function
            })
        else:
            self.functions[function.dict['name']] = [{
                'num_args': len(function.dict['args']),
                'function': function
            }]
    
    
    '''
    This function runs the function. Takes in 'fcall' type node and runs the appropriate 'func'
    Args should be a list of Values (pre compute everything before calling this)
    '''
    def call_function(self, func_name: str, args: List[Value]) -> Value:
        LOCAL_VARIABLES = {}
        
        # special print function
        if func_name == 'print':
            output_string = ''
                
            # go through all args and concatenate them
            for arg in args:                   
                output_string += str(arg)
            
            super().output(output_string)
            
            return Value(None, None)
            
        # special inputi function
        elif func_name == 'inputi':
            if len(args) == 1:
                self.call_function('print', args)
            if len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    "No inputi() function found that takes > 1 parameter",
                )
            
            return Value(int, int(super().get_input()))
        
        # special inputs function
        elif func_name == 'inputs':
            if len(args) == 1:
                self.call_function('print', args)
            if len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    "No inputs() function found that takes > 1 parameter",
                )
                
            return Value(str, str(super().get_input()))
    
        # actual function
        else:
            # check function name
            if func_name not in self.functions:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Function " + str(func_name) + " undefined"
                )
                
            # find the correct function with num args
            function = None
            for funcs in self.functions[func_name]:
                if funcs['num_args'] == len(args):
                    function = funcs['function']
            # function is now of type Element, elem_type = "func"
            
            # load args into LOCAL_VARIABLES
            for i, argNode in enumerate(function.dict['args']):
                LOCAL_VARIABLES[argNode.dict['name']] = args[i]
            # run each statement
            for statement in function.dict['statements']:
                try:
                    self.run_statement(statement, LOCAL_VARIABLES)
                except ReturnSignal as r:
                    return r.val
            
            return Value(None, None)
            
    
    '''
    This function runs a statement.
    '''
    def run_statement(self, statement: Element, LOCAL_VARIABLES: dict) -> Union[None, Value]:
        if statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            var_name = statement.dict['name']
            
            if var_name in LOCAL_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_name} defined more than once"
                )
                
            LOCAL_VARIABLES[var_name] = None
            
        elif statement.elem_type == InterpreterBase.ASSIGNMENT_NODE:
            var_name = statement.dict['var']
            
            if var_name not in LOCAL_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Variable " + str(var_name) + " undefined"
                )
            
            LOCAL_VARIABLES[statement.dict['var']] = self.run_expression(statement.dict['expression'], LOCAL_VARIABLES)
        
        elif statement.elem_type == InterpreterBase.FCALL_NODE:
            func_name = statement.dict['name']
            args = statement.dict['args']
            
            args = [self.run_expression(e, LOCAL_VARIABLES) for e in args] # evaluate all arguments first
            
            val = self.call_function(func_name, args)
            return val
            
        elif statement.elem_type == InterpreterBase.IF_NODE:
            condition = self.run_expression(statement.dict['condition'], LOCAL_VARIABLES)
            
            if condition.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'If statement did not return a boolean, returned: {condition.kind}, Value: {condition.value}'
                )

            if condition.value: 
                for s in statement.dict['statements']:
                    self.run_statement(s, LOCAL_VARIABLES)
            else:
                if statement.dict['else_statements'] is not None:
                    for s in statement.dict['else_statements']:
                        self.run_statement(s, LOCAL_VARIABLES)
                        
        elif statement.elem_type == InterpreterBase.WHILE_NODE:
            condition = self.run_expression(statement.dict['condition'], LOCAL_VARIABLES)
            
            if condition.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'If statement did not return a boolean, returned: {condition.kind}, Value: {condition.value}'
                )
            while condition.value:
                for s in statement.dict['statements']:
                    self.run_statement(s, LOCAL_VARIABLES)
                    
                condition = self.run_expression(statement.dict['condition'], LOCAL_VARIABLES)
                    
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            if statement.dict['expression']:
                val = self.run_expression(statement.dict['expression'], LOCAL_VARIABLES)
                raise ReturnSignal(val=val)
            
            return ReturnSignal(val=Value(None, None))
            
        else:
            raise Exception('Invalid statement passed: ' + str(statement))
    
    
    '''
    This functions runs a valid Expression element recursively
    '''
    def run_expression(self, expression: Element, LOCAL_VARIABLES: dict) -> Value:
        if expression.elem_type == InterpreterBase.STRING_NODE:
            return Value(str, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.INT_NODE:
            return Value(int, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.BOOL_NODE:
            return Value(bool, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.NIL_NODE:
            return Value(None, None)
        
        elif expression.elem_type == InterpreterBase.QUALIFIED_NAME_NODE:
            var_name = expression.dict['name']
            
            if var_name not in LOCAL_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Variable name " + str(var_name) + " undefined"
                )
            elif LOCAL_VARIABLES[var_name] == None:
                super().error(
                    ErrorType.FAULT_ERROR,
                    "Variable " + str(var_name) + " declared but unassigned"
                )
            else:
                return LOCAL_VARIABLES[var_name]
            
        elif expression.elem_type == InterpreterBase.FCALL_NODE:
            func_name = expression.dict['name']
            args = expression.dict['args']
            
            args = [self.run_expression(e, LOCAL_VARIABLES) for e in args] # evaluate all arguments first
            
            return self.call_function(func_name, args)
        
        
        #
        # Section for Binary Operation Expression Nodes
        #
        elif expression.elem_type == '+':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            # perform string concatenation operation
            if val1.kind == str and val2.kind == str:
                return Value(str, val1.value + val2.value)
            # perform integer addition
            elif val1.kind == int and val2.kind == int:
                return Value(int, val1.value + val2.value)
            # return error
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid addition operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '-':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value - val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid subtraction operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '*':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)

            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value * val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid multiplication operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '/':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value // val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid division operation between {val1.kind} and {val2.kind}"
                )
                
        elif expression.elem_type == '<':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value < val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid < operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '<=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value <= val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid <= operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '>':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value > val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid > operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '>=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value >= val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid >= operation between {val1.kind} and {val2.kind}"
                )
                
        elif expression.elem_type == '==':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            # if 2 values are of different types, they are not equal
            if val1.kind != val2.kind:
                return Value(bool, False)
            return Value(bool, val1.value == val2.value)
        elif expression.elem_type == '!=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            # if 2 values are of different types, they are not equal
            if val1.kind != val2.kind:
                return Value(bool, True)
            return Value(bool, val1.value != val2.value)
        
        elif expression.elem_type == '&&':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind != bool or val2.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid && operation between {val1.kind} and {val2.kind}"
                )
            return Value(bool, val1.value and val2.value)
        elif expression.elem_type == '||':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            
            if val1.kind != bool or val2.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid || operation between {val1.kind} and {val2.kind}"
                )
            return Value(bool, val1.value or val2.value)
        
        
        #
        # Begin Unary Negation Expression Nodes
        #
        elif expression.elem_type == InterpreterBase.NEG_NODE:
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            
            if val1.kind != int:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid - (unary negation) operation for {val1.kind}"
                )
            return Value(int, -1 * val1.value)
        elif expression.elem_type == InterpreterBase.NOT_NODE:
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            
            if val1.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid ! operation for {val1.kind}"
                )
            return Value(bool, not val1.value)
                
        else:
            raise Exception('Unknown Expression ' + str(expression))
        
PROG = """
def foo(c) { 
  if (c == 10) {
    c = "hi";  /* reassigning c from the outer-block */
    print(c);  /* prints "hi" */
  }
  print(c); /* prints “hi” */
}

def main() {
  foo(10);
}
"""
        
if __name__ == '__main__':
    i = Interpreter()
    
    i.run(PROG)