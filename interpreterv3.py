from typing import List, Union
from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element

from classdefs import *

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
        
        self.FUNCTIONS = {}
        
        # load functions
        for func in program_root.dict['functions']:
            self.def_function(func)
        
        # run main
        if 'main' not in self.FUNCTIONS:
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
        
        func_name = function.dict['name']
        
        try:
            f = Function(function)
        except Exception as e:
            if str(e) == 'NVRT':
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Function {func_name} does not have valid return type'
                )
            elif str(e) == 'NVART':
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Function {func_name} does not have valid parameter names'
                )
            else:
                raise
        
        if func_name in self.FUNCTIONS: # function overloading           
            if f.signature in [i.signature for i in self.FUNCTIONS[func_name]]:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Already defined function {func_name} with signature {f.signature}"
                )
            
            self.FUNCTIONS[func_name].append(f)
        else:
            self.FUNCTIONS[func_name] = [f]
    
    
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
            if func_name not in self.FUNCTIONS:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Function " + str(func_name) + " undefined"
                )
                
            # find the correct function with num args
            function = None
            for func in self.FUNCTIONS[func_name]:
                try:
                    sign = generate_function_signature(args)
                except Exception as e:
                    if str(e) == 'NVART':
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Function {func_name} does not have valid parameter names'
                        )
                    raise
                        
                if func.signature == sign:
                    function = func
            if function is None:
                super().error(
                    ErrorType.NAME_ERROR,
                    f'Function {func_name} not found with signature: {sign}'
                )
            # function is now of type Element, elem_type = "func"
            
            # load args into LOCAL_VARIABLES
            for i, argNode in enumerate(function.function.dict['args']):
                LOCAL_VARIABLES[argNode.dict['name']] = args[i]
                
            # run each statement
            try:
                for statement in function.function.dict['statements']:
                    self.run_statement(statement, LOCAL_VARIABLES)
            except ReturnSignal as r:
                return_value =  r.val
            else:
                # if no explicit return, return default value for function's declared return type
                if function.return_type == int:
                    return_value = Value(int, 0)
                elif function.return_type == str:
                    return_value = Value(str, "")
                elif function.return_type == bool:
                    return_value = Value(bool, False)
                else: # both object and void return types default to None
                    return Value(None, None)
                
            if function.return_type != return_value.kind:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Function {function.name}: Expected return type {function.return_type} but got {return_value.kind}'
                )
            
            return return_value
    
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
            
            raise ReturnSignal(val=Value(None, None))
            
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
def getValuei() { return 100; }
def getValuei(ai) { return ai + 50; }        /* int -> int */
def getValuei(ab)                            /* bool -> int */
  { if (ab) { return 200; } return 300; }  
def getValuei(ao, bs) { return 400; }  /* (obj,str) -> int */
def getValuei(as, bi)                  /* (str,int) -> int */
  { return bi + 10; } 

def main() {
    print(getValuei(inputi()));
}
"""
        
if __name__ == '__main__':
    i = Interpreter()
    
    i.run(PROG)