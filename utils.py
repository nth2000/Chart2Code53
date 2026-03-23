import re
import ast
import matplotlib.pyplot as plt
from ast import AST
import copy
from pprint import pprint
from collections import OrderedDict

def is_integer_in_range(sorted_list, lower_bound, upper_bound):
    if not sorted_list or lower_bound > upper_bound:
        return False
    from bisect import bisect_left
    index = bisect_left(sorted_list, lower_bound)
    if index < len(sorted_list) and sorted_list[index] <= upper_bound:
        return True
    return False

def extract_next_identifier(text):
    match = re.search('variable\\.\\s*([a-zA-Z_][a-zA-Z_0-9]*)', text)
    if match:
        return match.group(1)
    return None

def extract_def_for_if(code_text):
    tree = ast.parse(code_text)
    def_dict = {}
    for_dict = {}
    if_dict = {}
    class_dict = {}

    def visit_node(node, parent=None, depth=0):
        if isinstance(node, ast.ClassDef):
            class_dict[node.name] = [node.lineno, find_end_line(node)]
        if isinstance(node, ast.FunctionDef):
            if depth == 2:
                if parent and isinstance(parent, ast.ClassDef):
                    if node.name == '__init__':
                        def_dict[parent.name] = [node.lineno, find_end_line(node)]
                    else:
                        def_dict[f'{parent.name}.{node.name}'] = [node.lineno, find_end_line(node)]
            if depth == 1:
                def_dict[node.name] = [node.lineno, find_end_line(node)]
        elif isinstance(node, ast.For):
            if hasattr(node, 'lineno'):
                for_dict[node.lineno] = [node.lineno, find_end_line(node)]
        elif isinstance(node, ast.If):
            if hasattr(node, 'lineno'):
                if_dict[node.lineno] = [node.lineno, find_end_line(node)]
        for child in ast.iter_child_nodes(node):
            visit_node(child, parent=node, depth=depth + 1)

    def find_end_line(node):
        """
        通过遍历子节点，估算每个节点的结束行号
        """
        end_line = node.lineno
        for child in ast.iter_child_nodes(node):
            if hasattr(child, 'lineno'):
                child_end = find_end_line(child)
                if child_end > end_line:
                    end_line = child_end
        return end_line

    class ParentVisitor(ast.NodeVisitor):

        def visit(self, node):
            for child in ast.iter_child_nodes(node):
                child.parent = node
            super().visit(node)
    ParentVisitor().visit(tree)
    visit_node(tree, depth=0)
    return (def_dict, for_dict, if_dict, class_dict)

def find_uncalled_functions(func_dict):
    all_called_functions = set()
    func_chains = {}
    for func, calls in func_dict.items():
        for callee in calls:
            all_called_functions.add(callee)
        func_chains[func] = calls
    root_functions = [func for func in func_dict.keys() if func not in all_called_functions]
    result = []

    def collect_called(func, visited):
        if func in visited:
            return
        visited.add(func)
        for callee in func_chains.get(func, []):
            collect_called(callee, visited)
    for root in root_functions:
        visited = set()
        collect_called(root, visited)
        result.append(list(visited))
    all_functions = set(func_dict.keys())
    visited_functions = set((func for group in result for func in group))
    remaining_functions = list(all_functions - visited_functions)
    return (result, remaining_functions)

def rev_extract_all_command(node: ast.AST):
    if isinstance(node, ast.Expr) and node.lineno == 607:
        print('hit')
    if 'body' not in node._fields:
        return node
    else:
        result = []
        for sub_node in node.body:
            r_sub_node = rev_extract_all_command(sub_node)
            if isinstance(r_sub_node, list):
                result.extend(r_sub_node)
            else:
                result.append(r_sub_node)
        return result

def handle_node(node, target_lib, variable_list, verbose=False):
    if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
        variable_list += handle_node_import(node, target_lib=target_lib, verbose=verbose)
        return (False, [], list(set(variable_list)))
    else:
        if not check_node_with_variable_list(node, variable_list, verbose=verbose):
            return (False, [], variable_list)
        contain_flag = False
        result = []
        if isinstance(node, ast.Expr):
            result_expr = handle_node_Expr(node, variable_list, verbose=verbose)
            result.append(result_expr)
            contain_flag = True
        elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
            result_asign, new_variable_list = handle_node_Assign(node, variable_list, verbose=verbose)
            variable_list += new_variable_list
            result.extend(result_asign)
            contain_flag = True
        for item in result:
            if item:
                item['target_lib'] = target_lib
        return (contain_flag, result, list(set(variable_list)))

def handle_node_Call(node):
    assert isinstance(node, ast.Call)
    if isinstance(node.func, ast.Name):
        func_name = node.func.id
        variable_name_call = None
    elif isinstance(node.func, ast.Attribute):
        func_name = node.func.attr
        variable_name_call = rev_get_variable_func_call(node.func.value)
    else:
        return {}
    return OrderedDict({'var_call': variable_name_call, 'func_name': func_name})

def handle_node_import(node, target_lib='matplotlib', verbose=False):
    """
    Handle import statement
    if 'target_lib' in line, get the lib name or alias
    For example:
        import matplotlib.pyplot as plt --> ["plt"]
        import matplotlib --> ["matplotlib"]
        from os import path, makedirs --> ["path", "makedirs"]

    Return:
        list of all lib_name or their alias
    """
    variable_list = []
    if isinstance(node, ast.ImportFrom):
        if node.module is not None and target_lib in node.module:
            do = True
        else:
            do = False
    else:
        do = True
    if do:
        for name in node.names:
            if target_lib in name.name or target_lib in str(name.asname) or isinstance(node, ast.ImportFrom):
                variable_name = str(name.asname) if name.asname != None else name.name
                if variable_name == '_':
                    continue
                variable_list.append(variable_name)
        if verbose:
            print('New variable_list: ', variable_list)
            print('-' * 50)
    return variable_list

def check_node_with_variable_list(node, variable_list, verbose=False):
    for variable_name in variable_list:
        if check_node_with_variable_name(node, variable_name):
            return True
    if verbose:
        print('No variables in this node!')
    return False

def check_node_with_variable_name(node, variable_name):
    """
    Checking this node for whether it involves from "variable_name"
    For example: assume, variable_name = "plt"
        plt.subplots()      - Call a function

        abc = plt           - Assign to another variable_name
    """

    def rev_check(node):
        if not isinstance(node, AST) and (not isinstance(node, list)):
            return True if str(node) == variable_name else False
        elif isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                variable_name_call = None
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                variable_name_call = rev_get_variable_func_call(node.func.value)
            if func_name == variable_name or variable_name_call == variable_name:
                return True
            return False
        elif isinstance(node, list):
            return_bool = False
            for _node in node:
                return_bool = return_bool or rev_check(_node)
            return return_bool
        else:
            return_bool = False
            for name in node._fields:
                if name == 'arg':
                    continue
                try:
                    value = getattr(node, name)
                    return_bool = return_bool or rev_check(value)
                except:
                    continue
            return return_bool
    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return rev_check(node)

def rev_extract_target_names(node):
    if isinstance(node, list):
        result = []
        for item in node:
            result += rev_extract_target_names(item)
        return result
    elif not isinstance(node, ast.AST):
        return []
    elif isinstance(node, ast.Name):
        if node.id != '_':
            return [node.id]
        else:
            return []
    else:
        result = []
        for field in node._fields:
            next_node = getattr(node, field)
            result += rev_extract_target_names(next_node)
        return result

def rev_get_variable_func_call(node: ast.AST):
    if not isinstance(node, ast.AST):
        return None
    elif isinstance(node, ast.Name):
        return node.id
    elif len(node._fields) > 0:
        next_node = getattr(node, node._fields[0])
        return rev_get_variable_func_call(next_node)
    else:
        return None

def handle_node_call_args(args):
    args_value = []
    for arg in args:
        if isinstance(arg, ast.Constant):
            args_value.append(arg.value)
        else:
            args_value.append(str(type(arg)))
    return args_value

def handle_node_Assign(node, variable_list: list, verbose=False):
    assert isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign)
    node_targets = node.targets if 'targets' in node._fields else [node.target]
    targets_str = rev_extract_target_names(node_targets)
    values_str = []
    if isinstance(node.value, ast.Name):
        values_str.append({'var_call': node.value.id})
    elif isinstance(node.value, ast.Call):
        values_str.append(handle_node_Call(node.value))
    elif isinstance(node.value, ast.Subscript):
        if isinstance(node.value.value, ast.Name):
            values_str.append({'var_call': node.value.value.id})
    elif isinstance(node.value, ast.Tuple):
        for elt in node.value.elts:
            if isinstance(elt, ast.Name):
                values_str.append({'var_call': elt.id})
            elif isinstance(elt, ast.Call):
                values_str.append(handle_node_Call(elt))
            elif isinstance(elt, ast.Subscript):
                if getattr(elt, 'value', None) and getattr(elt.value, 'value', None) and isinstance(elt.value.value, ast.Name):
                    values_str.append({'var_call': elt.value.value.id})
    result = []
    new_variable_list = copy.deepcopy(variable_list)
    for value_str in values_str:
        value_str['target'] = targets_str
        result.append(value_str)
        var_call = value_str.get('var_call', None)
        if var_call and var_call in new_variable_list or ('func_name' in value_str and value_str['func_name'] in new_variable_list):
            new_variable_list.extend(targets_str)
    if verbose:
        pprint(result)
        print('-' * 50 + '\n')
    return (result, new_variable_list)

def handle_node_call_kargs(kargs):
    kargs_dict = {}
    for karg in kargs:
        karg_name = karg.arg
        if isinstance(karg.value, ast.Constant):
            karg_value = karg.value.value
        else:
            karg_value = str(type(karg.value))
        kargs_dict[karg_name] = karg_value
    return kargs_dict

def handle_node_Expr(node, variable_list, verbose=False):
    """
    When an expression, such as a function call.
    """
    assert isinstance(node, ast.Expr)
    result = {}
    if isinstance(node.value, ast.Call):
        result = handle_node_Call(node.value)
    elif verbose:
        print('Not a call Expr')
    return result
