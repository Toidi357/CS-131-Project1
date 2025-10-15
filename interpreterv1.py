from typing import List, Union
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element
Value = int | float | str | bool

class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        
    def run(self, program):
        program_root = parse_program(program)
        
        # maintain a mapping of all function names to their respective Element; this will be global so any Expression can look it up
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
        self.functions[function.dict['name']] = function
    
    
    '''
    This function runs the function. Takes in 'fcall' type node and runs the appropriate 'func'
    Args should be a list of Values (pre compute everything before calling this)
    '''
    def call_function(self, func_name: str, args: List[Value]) -> Union[None, Value]:
        LOCAL_VARIABLES = {}
        
        # special print function
        if func_name == 'print':
            output_string = ''
                
            # go through all args and concatenate them
            for arg in args:
                output_string += str(arg)
            
            super().output(output_string)
            
        # special inputi function
        elif func_name == 'inputi':
            if len(args) == 1:
                self.call_function('print', args)
            if len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR,
                    "No inputi() function found that takes > 1 parameter",
                )
            
            return int(super().get_input())
    
        else:
            if func_name not in self.functions:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Function " + str(func_name) + " undefined"
                )
                
            function = self.functions[func_name]
            for statement in function.dict['statements']:
                self.run_statement(statement, LOCAL_VARIABLES)
            
    
    '''
    This function runs a statement.
    Statement can be either:
       - simple variable definition
       - variable assignment (requires calling run_expression())
       - calling a function (out of scope rn for not print/inputi)
    '''
    def run_statement(self, statement: Element, LOCAL_VARIABLES: dict) -> None:
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
            
            self.call_function(func_name, args)
            
        else:
            raise Exception('Invalid statement passed: ' + str(statement))
    
    
    '''
    This functions runs a valid Expression element recursively
    '''
    def run_expression(self, expression: Element, LOCAL_VARIABLES: dict) -> Value:
        if expression.elem_type == InterpreterBase.STRING_NODE:
            return expression.dict['val']
        
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
        
        elif expression.elem_type == InterpreterBase.INT_NODE:
            return expression.dict['val']
        
        elif expression.elem_type == '+':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            if type(val1) == str or type(val2) == str:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Addition expression has type string. Val1: " + str(val1) + '. Val2: ' + str(val2)
                )
            else:
                return int(val1) + int(val2)
        elif expression.elem_type == '-':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES)
            if type(val1) == str or type(val2) == str:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Subtraction expression has type string. Val1: " + str(val1) + '. Val2: ' + str(val2)
                )
            else:
                return int(val1) - int(val2)
            
        elif expression.elem_type == InterpreterBase.FCALL_NODE:
            func_name = expression.dict['name']
            args = expression.dict['args']
            
            args = [self.run_expression(e, LOCAL_VARIABLES) for e in args] # evaluate all arguments first
            
            return self.call_function(func_name, args)
            
        else:
            raise Exception('Unknown Expression ' + str(expression))
        
PROG = """
def main() {
  print(3 - (3 + (2 + inputi())));
}
"""
        
if __name__ == '__main__':
    i = Interpreter()
    
    i.run(PROG)