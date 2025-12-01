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
        maintain a mapping of all function names and interfaces to their respective Element; this will be global so any Expression can look it up
        function object is like this
            func_name: [Function]
        interfacde object is like this
            interface_letter: [Interface Node]
        '''
        self.INTERFACES = {}
        self.FUNCTIONS = {}
        
        # load interfaces
        if 'interfaces' in program_root.dict:
            for interface in program_root.dict['interfaces']:
                self.def_interface(interface)
        
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
    
    
    def def_interface(self, interface: Element) -> None:
        '''
        This function defines an interface, loads it into self.INTERFACES
        '''
        name = interface.dict['name']
        
        if len(name) != 1 or not name.isupper():
            super().error(
                ErrorType.NAME_ERROR,
                f'Interface {name} not single uppercase letter'
            )
        
        if name in self.INTERFACES:
            super().error(
                ErrorType.NAME_ERROR,
                f'Interface {name} already declared'
            )
            
        try:
            validate_interface(interface, self.INTERFACES)
        except Exception as e:
            if str(e) == 'Refer to interface not defined':
                super().error(
                    ErrorType.NAME_ERROR,
                    f'Interface {name} refers to interface not defined'
                )
            if str(e) == 'Duplicate Field Name':
                super().error(
                    ErrorType.NAME_ERROR,
                    f'Interface {name} has duplicate fields'
                )
            if str(e) == 'Invalid Field Name':
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Interface {name} has invalid field name'
                )

        self.INTERFACES[name] = interface
        
    
    '''
    This function DEFINES a function. It does not run anything. Takes in 'func' type node
    '''
    def def_function(self, function: Element) -> None:
        f = self.create_function(function)
        
        func_name = function.dict['name']
        
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
    This function runs the function. Takes in a function name and possibly the local/block variables
    Args should be a list of Values/Refs (pre compute everything before calling this)
    '''
    def call_function(self, func_name: str, args: List[Value | Reference], CALLER_LOCAL=None, CALLER_BLOCK=None) -> Value | Reference:
        if not CALLER_LOCAL:
            CALLER_LOCAL = {}
        if not CALLER_BLOCK:
            CALLER_BLOCK = {}
        
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
    
        elif func_name == 'repr':
            return Value(str, repr(args[0]))
    
        # actual function
        else:
            function = None
            
            # if function name is an object path, go through a whole series of resolutions
            fields = func_name.split('.')
            if len(fields) != 1: # not an object
                var_base_name = fields[0]
                function = self.object_qname_lookup(fields, var_base_name, CALLER_BLOCK, CALLER_LOCAL, func_name)
                
                if function.kind is Nil:
                    super().error(
                        ErrorType.FAULT_ERROR,
                        f'Function {func_name} is nil'
                    )
                if function.kind is not Function:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Function {func_name} is not function'
                    )
                
                selfo = Value(Object, Object(function.env))
                function = function.value
            
            # else, check function name normally
            else:
                if func_name not in self.FUNCTIONS and func_name not in CALLER_LOCAL and func_name not in CALLER_BLOCK:
                    super().error(
                        ErrorType.NAME_ERROR,
                        "Function " + str(func_name) + " undefined"
                    )
                
                # find the correct function with num args
                try:
                    sign = generate_function_signature(args)
                except Exception as e:
                    if str(e) == 'NVART':
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Function {func_name} does not have valid parameter names'
                        )
                    raise
                
                # find the correct function to call, is either global function or variable
                # since there is no overloading of functions in variables, only one of these will return true
                if func_name in self.FUNCTIONS:
                    for func in self.FUNCTIONS[func_name]:  
                        if func.signature == sign:
                            function = func
                if func_name in CALLER_LOCAL:
                    if CALLER_LOCAL[func_name].kind is Nil:
                        super().error(
                            ErrorType.FAULT_ERROR,
                            f'Function {func_name} is nil'
                        )
                    if CALLER_LOCAL[func_name].kind is not Function:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Function {func_name} is not function'
                        )
                        
                    function = CALLER_LOCAL[func_name].value
                if func_name in CALLER_BLOCK:
                    if CALLER_BLOCK[func_name].kind is Nil:
                        super().error(
                            ErrorType.FAULT_ERROR,
                            f'Function {func_name} is nil'
                        )
                    if CALLER_BLOCK[func_name].kind is not Function:
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Function {func_name} is not function'
                        )
                    
                    function = CALLER_BLOCK[func_name].value
                
                if function is None:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f'Function {func_name} not found with signature: {sign}'
                    )
            
            # function variable is now of type Function
            
            # if function in variable name, there's no overloading so double check function param signatures
            if generate_function_signature(args) != generate_function_signature(function.function.dict['args']):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Function {func_name} called with wrong params'
                )
            
            # if lambda, load captured variables into LOCAL_VARIABLES
            if hasattr(function, 'environment'):
                LOCAL_VARIABLES = function.environment
                
            # load selfo into LOCAL_VARIABLES if func is from an object
            if len(fields) != 1:
                LOCAL_VARIABLES['selfo'] = selfo
            
            # load args into LOCAL_VARIABLES
            for i, argNode in enumerate(function.function.dict['args']):
                arg_name = argNode.dict['name']
                arg_val = args[i]
                arg_type = get_variable_type(arg_name)
                
                # check arg type errors
                if arg_type != arg_val.kind:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Argument assignment of {arg_name}: Attempted assign type {arg_val.kind} to variable type {arg_type}'
                    )
                    
                # if arg_name is an interface, check arg_val to make sure it has all required fields
                if fields[-1][-1].isupper():
                    
                    interface = self.INTERFACES[fields[-1][-1]]
                    if not interface:
                        super().error(
                            ErrorType.NAME_ERROR,
                            f'Interface {fields[-1][-1]} not found'
                        )
                    if not types_equal(arg_val.kind, Object) or not validate_object_with_interface(interface, arg_val):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Assignment to interface {fields[-1][-1]} failed'
                        )
                
                if argNode.dict['ref']: # pass by reference variable
                    if not isinstance(arg_val, Reference):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Argument {i + 1} to {func_name} must be a Reference, not Value'
                        )
                    
                    LOCAL_VARIABLES[arg_name] = arg_val # arg_val is type Reference in this case
                else:
                    if isinstance(arg_val, Reference):
                        val = arg_val.get()
                        # if parameter not supposed to be a Reference but was passed a Reference, create a deep copy
                        LOCAL_VARIABLES[arg_name] = Value(val.kind, val.value)
                    else:    
                        LOCAL_VARIABLES[arg_name] = args[i]
            
            # run each statement
            try:
                BLOCK_VARIABLES = LOCAL_VARIABLES
                for statement in function.function.dict['statements']:
                    self.run_statement(statement, LOCAL_VARIABLES, BLOCK_VARIABLES)
            except ReturnSignal as r:
                return_value = r.val
                
                # this is to handle empty returns
                if return_value == None:
                    return_value = get_default_value(function.return_type)
            else:
                # if no explicit return, return default value for function's declared return type
                return_value = get_default_value(function.return_type)
            
            if not types_equal(function.return_type, return_value.kind):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Function {function.name}: Expected return type {function.return_type} but got {return_value.kind}'
                )
                
            # if func return type is an interface, check returned value to make sure it has all required fields
            if function.name[-1].isupper():
                interface = self.INTERFACES[function.name[-1]]
                if not interface:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f'Interface {function.name[-1]} not found'
                    )
                if not types_equal(return_value.kind, Object) or not validate_object_with_interface(interface, return_value):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Assignment to interface {function.name[-1]} failed'
                    )
            
            return return_value
    
    '''
    This function runs a statement.
    '''
    def run_statement(self, statement: Element, LOCAL_VARIABLES: dict[str, Value], BLOCK_VARIABLES: dict[str, Value]) -> Union[None, Value]:
        if statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            var_base_name = statement.dict['name']
            try:
                var_type = get_variable_type(statement.dict['name'])
            except Exception as e:
                if str(e) == 'NVRT':
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Variable {var_base_name} does not have associated type with it'
                    )
                raise
            
            if var_base_name in LOCAL_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_base_name} defined more than once"
                )
            LOCAL_VARIABLES[var_base_name] = get_default_value(var_type)
            
        elif statement.elem_type == InterpreterBase.BVAR_DEF_NODE:
            var_base_name = statement.dict['name']
            try:
                var_type = get_variable_type(statement.dict['name'])
            except Exception as e:
                if str(e) == 'NVRT':
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Variable {var_base_name} does not have associated type with it'
                    )
                raise
            
            if var_base_name in BLOCK_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {var_base_name} defined more than once in current block"
                )
                
            BLOCK_VARIABLES[var_base_name] = get_default_value(var_type)
            
        elif statement.elem_type == InterpreterBase.ASSIGNMENT_NODE:
            fields = statement.dict['var'].split('.')
            
            if len(fields) == 1: # not an object
                var_base_name = statement.dict['var']
            else:
                var_base_name = fields[0]
            var_type = get_variable_type(fields[-1]) # type we care about is the last one in the dotted string
            
            if var_base_name not in LOCAL_VARIABLES and var_base_name not in BLOCK_VARIABLES:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Variable " + str(var_base_name) + " undefined"
                )
                
            new_value = self.run_expression(statement.dict['expression'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            
            # if new_value is a Reference, dereference one layer to prevent max recursion depth
            if isinstance(new_value, Reference):
                new_value = new_value.get()
                
            # check type errors
            if not types_equal(var_type, new_value.kind):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Variable assignment of {statement.dict["var"]}: Attempted assign type {new_value.kind} to variable type {var_type}'
                )
                
            # if LHS is an interface, check new_value to make sure it has all required fields
            if fields[-1][-1].isupper():
                interface = self.INTERFACES[fields[-1][-1]]
                if not interface:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f'Interface {fields[-1][-1]} not found'
                    )
                if not types_equal(new_value.kind, Object) or not validate_object_with_interface(interface, new_value):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Assignment to interface {fields[-1][-1]} failed'
                    )
            
            '''
            Object stuff
            '''
            if len(fields) > 1:
                base_val = BLOCK_VARIABLES[var_base_name] if var_base_name in BLOCK_VARIABLES else LOCAL_VARIABLES[var_base_name]
                if not types_equal(base_val.kind, Object):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f'Base variable {var_base_name} not of type object'
                    )
                if base_val.value == None:
                    super().error(
                        ErrorType.FAULT_ERROR,
                        f'Base variable {var_base_name} not defined yet'
                    )
                iterr = base_val.value
                
                for seg in fields[1:-1]:
                    if seg not in iterr.value:
                        super().error(
                            ErrorType.NAME_ERROR,
                            f'Requested field {seg} does not exist in object {statement.dict["var"]}'
                        )
                    next_val = iterr.value[seg]
                    if types_equal(next_val.kind, Nil) and next_val.value == None:
                        super().error(
                            ErrorType.FAULT_ERROR,
                            f'Dereferencing nil of {seg} for {var_base_name}'
                        )
                    if not types_equal(next_val.kind, Object):
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f'Intermediate dotted segment not ending with o: {seg} for {var_base_name}'
                        )
                    iterr = next_val.value
                
                # the last field gets assigned
                iterr.value[fields[-1]] = new_value
            
            # normal variable resolution
            else:
                # if this variable is a Reference to a callee's variable, update it as such
                if var_base_name in BLOCK_VARIABLES:
                    if isinstance(BLOCK_VARIABLES[var_base_name], Reference):
                        BLOCK_VARIABLES[var_base_name].set(new_value)
                    else:
                        BLOCK_VARIABLES[var_base_name] = new_value
                else:
                    if isinstance(LOCAL_VARIABLES[var_base_name], Reference):
                        LOCAL_VARIABLES[var_base_name].set(new_value)
                    else:
                        LOCAL_VARIABLES[var_base_name] = new_value
        
        elif statement.elem_type == InterpreterBase.FCALL_NODE:
            func_name = statement.dict['name']
            args = statement.dict['args']
            
            args = [self.run_expression(e, LOCAL_VARIABLES, BLOCK_VARIABLES) for e in args] # evaluate all arguments first
            
            return self.call_function(func_name, args, LOCAL_VARIABLES, BLOCK_VARIABLES)
            
        elif statement.elem_type == InterpreterBase.IF_NODE:
            condition = self.run_expression(statement.dict['condition'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if condition.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'If statement did not return a boolean, returned: {condition.kind}, Value: {condition.value}'
                )
                
            NEW_BLOCK_VARIABLES = {}
            NEW_LOCAL_VARIABLES = {**LOCAL_VARIABLES, **BLOCK_VARIABLES}

            if condition.value: 
                for s in statement.dict['statements']:
                    self.run_statement(s, NEW_LOCAL_VARIABLES, NEW_BLOCK_VARIABLES)
            else:
                if statement.dict['else_statements'] is not None:
                    for s in statement.dict['else_statements']:
                        self.run_statement(s, NEW_LOCAL_VARIABLES, NEW_BLOCK_VARIABLES)
                        
            # reset LOCAL_VARIABLES and BLOCK_VARIABLES to original state
            NEW_BLOCK_VARIABLES.clear()
            for key in NEW_LOCAL_VARIABLES:
                if key in BLOCK_VARIABLES:
                    BLOCK_VARIABLES[key] = NEW_LOCAL_VARIABLES[key]
                else:
                    LOCAL_VARIABLES[key] = NEW_LOCAL_VARIABLES[key]
                        
        elif statement.elem_type == InterpreterBase.WHILE_NODE:
            condition = self.run_expression(statement.dict['condition'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if condition.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'If statement did not return a boolean, returned: {condition.kind}, Value: {condition.value}'
                )
                
            NEW_BLOCK_VARIABLES = {}
            NEW_LOCAL_VARIABLES = {**LOCAL_VARIABLES, **BLOCK_VARIABLES}
                
            while condition.value:
                for s in statement.dict['statements']:
                    self.run_statement(s, NEW_LOCAL_VARIABLES, NEW_BLOCK_VARIABLES)
                
                NEW_BLOCK_VARIABLES.clear()
                condition = self.run_expression(statement.dict['condition'], NEW_LOCAL_VARIABLES, NEW_BLOCK_VARIABLES)
                
            # reset LOCAL_VARIABLES and BLOCK_VARIABLES to original state
            NEW_BLOCK_VARIABLES.clear()
            for key in NEW_LOCAL_VARIABLES:
                if key in BLOCK_VARIABLES:
                    BLOCK_VARIABLES[key] = NEW_LOCAL_VARIABLES[key]
                else:
                    LOCAL_VARIABLES[key] = NEW_LOCAL_VARIABLES[key]
                    
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            if statement.dict['expression']:
                val = self.run_expression(statement.dict['expression'], LOCAL_VARIABLES, BLOCK_VARIABLES)
                raise ReturnSignal(val=val)
            
            raise ReturnSignal(val=None)
            
        else:
            raise Exception('Invalid statement passed: ' + str(statement))
    
    
    '''
    This functions runs a valid Expression element recursively
    '''
    def run_expression(self, expression: Element, LOCAL_VARIABLES: dict[str, Value | Reference], BLOCK_VARIABLES: dict[str, Value | Reference]) -> Reference | Value:
        if expression.elem_type == InterpreterBase.STRING_NODE:
            return Value(str, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.INT_NODE:
            return Value(int, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.BOOL_NODE:
            return Value(bool, expression.dict['val'])
        
        elif expression.elem_type == InterpreterBase.NIL_NODE:
            return Value(Nil, None)
        
        elif expression.elem_type == InterpreterBase.EMPTY_OBJ_NODE:
            return Value(Object, Object())
        
        elif expression.elem_type == InterpreterBase.QUALIFIED_NAME_NODE:
            fields = expression.dict['name'].split('.')
            if len(fields) == 1: # not an object
                var_base_name = expression.dict['name']
            else:
                var_base_name = fields[0]

            if var_base_name not in LOCAL_VARIABLES and var_base_name not in BLOCK_VARIABLES and var_base_name not in self.FUNCTIONS:
                super().error(
                    ErrorType.NAME_ERROR,
                    "Variable " + str(var_base_name) + " undefined"
                )
            else:
                # if object dotted string
                if len(fields) > 1:
                    return self.object_qname_lookup(fields, var_base_name, BLOCK_VARIABLES, LOCAL_VARIABLES, expression.dict['name'])
                    
                # normal variable name resolution
                else:
                    if var_base_name in self.FUNCTIONS:
                        return Value(Function, self.FUNCTIONS[var_base_name][0])
                    elif var_base_name in BLOCK_VARIABLES:
                        if isinstance(BLOCK_VARIABLES[var_base_name], Reference):
                            return BLOCK_VARIABLES[var_base_name]
                        return Reference(BLOCK_VARIABLES, var_base_name)
                    else:
                        # prevent the max recursion depth Reference -> Reference -> Reference problem
                        if isinstance(LOCAL_VARIABLES[var_base_name], Reference):
                            return LOCAL_VARIABLES[var_base_name]
                        return Reference(LOCAL_VARIABLES, var_base_name)
            
        elif expression.elem_type == InterpreterBase.FCALL_NODE:
            func_name = expression.dict['name']
            args = expression.dict['args']
            
            args = [self.run_expression(e, LOCAL_VARIABLES, BLOCK_VARIABLES) for e in args] # evaluate all arguments first
            
            return self.call_function(func_name, args, LOCAL_VARIABLES, BLOCK_VARIABLES)
        
        elif expression.elem_type == InterpreterBase.CONVERT_NODE:
            to_convert = self.run_expression(expression.dict['expr'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if to_convert.kind == Object:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Attempted to convert type Object"
                )
            if to_convert.kind == None:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Attempted to convert type nil"
                )
            
            if expression.dict['to_type'] == 'int':
                if to_convert.kind == str:
                    if not to_convert.value.isdigit():
                        super().error(
                            ErrorType.TYPE_ERROR,
                            f"Attempted to convert non-digit string to int"
                        )
                    return Value(int, int(to_convert.value))
                elif to_convert.kind == bool:
                    if to_convert.value == True:
                        return Value(int, 1)
                    return Value(int, 0)
                elif to_convert.kind == int:
                    return to_convert
                else:
                    raise Exception(f"Attempted to convert to integer but some uncaught error occurred")
            elif expression.dict['to_type'] == 'str':
                if to_convert.kind == int:
                    return Value(str, str(to_convert.value))
                elif to_convert.kind == bool:
                    if to_convert.value == True:
                        return Value(str, "true")
                    return Value(str, "false")
                elif to_convert.kind == str:
                    return to_convert
                else:
                    raise Exception(f"Attempted to convert to integer but some uncaught error occurred")
            elif expression.dict['to_type'] == 'bool':
                if to_convert.kind == int:
                    if to_convert.value == 0:
                        return Value(bool, False)
                    return Value(bool, True)
                elif to_convert.kind == str:
                    if to_convert.value == '':
                        return Value(bool, False)
                    return Value(bool, True)
                elif to_convert.kind == bool:
                    return to_convert
                else:
                    raise Exception(f"Attempted to convert to integer but some uncaught error occurred")
                
            super().error(
                ErrorType.TYPE_ERROR,
                f"Somehow went through all the elifs and didn't get caught so take a look at this"
            )
        
        # for lambda functions
        elif expression.elem_type == InterpreterBase.FUNC_NODE:
            current_env = {**LOCAL_VARIABLES, **BLOCK_VARIABLES}

            captured_env = {}

            free_vars = current_env.keys()

            for var_name in free_vars:
                var = current_env[var_name]

                # primitive capture by value
                if var.kind in (int, bool, str, Nil):
                    if isinstance(var, Reference):
                        var = var.get()
                        captured_env[var_name] = Value(var.kind, var.value)
                    else:
                        captured_env[var_name] = var
                else:
                    captured_env[var_name] = var

            f = self.create_function(expression)
            
            f.environment = captured_env
            
            return Value(Function, f)
        
        #
        # Section for Binary Operation Expression Nodes
        #
        elif expression.elem_type == '+':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
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
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value - val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid subtraction operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '*':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)

            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value * val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid multiplication operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '/':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(int, val1.value // val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid division operation between {val1.kind} and {val2.kind}"
                )
                
        elif expression.elem_type == '<':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value < val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid < operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '<=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value <= val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid <= operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '>':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value > val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid > operation between {val1.kind} and {val2.kind}"
                )
        elif expression.elem_type == '>=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind == int and val2.kind == int:
                return Value(bool, val1.value >= val2.value)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid >= operation between {val1.kind} and {val2.kind}"
                )
                
        elif expression.elem_type == '==':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            # if 2 values are of different types, they are not equal
            if not types_equal(val1.kind, val2.kind):
                return Value(bool, False)
            return Value(bool, val1.value == val2.value)
        elif expression.elem_type == '!=':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            # if 2 values are of different types, they are not equal
            if not types_equal(val1.kind, val2.kind):
                return Value(bool, True)
            return Value(bool, val1.value != val2.value)
        
        elif expression.elem_type == '&&':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind != bool or val2.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid && operation between {val1.kind} and {val2.kind}"
                )
            return Value(bool, val1.value and val2.value)
        elif expression.elem_type == '||':
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            val2 = self.run_expression(expression.dict['op2'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
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
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind != int:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid - (unary negation) operation for {val1.kind}"
                )
            return Value(int, -1 * val1.value)
        elif expression.elem_type == InterpreterBase.NOT_NODE:
            val1 = self.run_expression(expression.dict['op1'], LOCAL_VARIABLES, BLOCK_VARIABLES)
            
            if val1.kind != bool:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid ! operation for {val1.kind}"
                )
            return Value(bool, not val1.value)
                
        else:
            raise Exception('Unknown Expression ' + str(expression))
      
    
    def object_qname_lookup(self, fields, var_base_name, BLOCK_VARIABLES, LOCAL_VARIABLES, expression_name):
        '''
        Modularizing this function, expression_name is expression.dict['name']
        '''
        base_val = BLOCK_VARIABLES[var_base_name] if var_base_name in BLOCK_VARIABLES else LOCAL_VARIABLES[var_base_name] 
        if not base_val or not types_equal(base_val.kind, Object):
            super().error(
                ErrorType.TYPE_ERROR,
                f'Base variable {var_base_name} not of type object'
            )
        if base_val.value == None:
            super().error(
                ErrorType.FAULT_ERROR,
                f'Base variable {var_base_name} not defined yet'
            )
            
        iterr = base_val.value
        for seg in fields[1:-1]:
            if seg not in iterr.value:
                super().error(
                    ErrorType.NAME_ERROR,
                    f'Requested field {seg} does not exist in object {expression_name}'
                )
            next_val = iterr.value[seg]
            if types_equal(next_val.kind, Nil) and next_val.value == None:
                super().error(
                    ErrorType.FAULT_ERROR,
                    f'Dereferencing nil of {seg} for {var_base_name}'
                )
            if not types_equal(next_val.kind, Object):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f'Intermediate dotted segment not ending with o: {seg} for {var_base_name}'
                )
            
            iterr = next_val.value
            
        # now we're on the last field
        if fields[-1] not in iterr.value:
            super().error(
                ErrorType.NAME_ERROR,
                f'Requested field {fields[-1]} does not exist in object {expression_name}'
            )
        else:
            return Reference(iterr.value, fields[-1])

    def create_function(self, function: Element) -> Function:
        """
        Takes in a function Element node and returns the Function object
        Throws error if function signature invalid
        """
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
            
        return f
        

PROG = """
interface B {
    vali;
}
interface A {
    xB;
}

def main() {
    var xo;
    xo = @;
    var xA;
    
    var xxo;
    xxo = @;
    xxo.vali = 5;
    
    xo.xB = xxo;
    xA = xo;
    print(xA.xB.vali);
}


"""

        
if __name__ == '__main__':
    i = Interpreter()
    
    i.run(PROG)