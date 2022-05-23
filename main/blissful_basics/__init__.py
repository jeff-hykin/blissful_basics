import json_fix
import file_system_py as FS
from time import time as now
from random import shuffle

def unix_time():
    return int(now()/1000)

class Object: # just an empty object for assigning attributes of
    def __init__(self, **kwargs):
        for each_key, each_value in kwargs.items():
            setattr(self, each_key, each_value)
    
    def __repr__(self):
        entries = ""
        for each_key, each_value in self.__dict__.items():
            entries += f"    {each_key} = {repr(each_value)},\n"
        if len(entries) == 0:
            return 'Object()'
        else:
            return f"""Object(\n{entries})"""

def is_iterable(thing):
    # https://stackoverflow.com/questions/1952464/in-python-how-do-i-determine-if-an-object-is-iterable
    try:
        iter(thing)
    except TypeError:
        return False
    else:
        return True

def is_generator_like(thing):
    return is_iterable(thing) and not isinstance(thing, (str, bytes))

def flatten(value):
    flattener = lambda *m: (i for n in m for i in (flattener(*n) if is_generator_like(n) else (n,)))
    return list(flattener(value))

def flatten_once(items):
    for each in items:
        if is_generator_like(each):
            yield from each
        else:
            yield each

def product(iterable):
    from functools import reduce
    import operator
    return reduce(operator.mul, iterable, 1)

def max_index(iterable):
    max_value = max(iterable)
    return to_pure(iterable).index(max_value)

def average(iterable):
    from statistics import mean
    from trivial_torch_tools.generics import to_pure
    return mean(tuple(to_pure(each) for each in iterable))

def median(iterable):
    from statistics import median
    from trivial_torch_tools.generics import to_pure
    return median(tuple(to_pure(each) for each in iterable))

def stats(number_iterator):
    import math
    from statistics import stdev, median, quantiles
    
    minimum = math.inf
    maximum = -math.inf
    total = 0
    values = [] # for iterables that get consumed
    for each in number_iterator:
        values.append(to_pure(each))
        total += each
        if each > maximum:
            maximum = each
        if each < minimum:
            minimum = each
    
    count = len(values)
    range = maximum-minimum
    average     = total / count     if count != 0 else None
    median      = median(values)    if count != 0 else None
    stdev       = stdev(values)     if count  > 1 else None
    normalized  = tuple((each-minimum)/range for each in values) if range != 0 else None
    (q1,_,q3),_ = quantiles(values) if count  > 1 else (None,None,None),None
    
    return Object(
        max=maximum,
        min=minimum,
        range=range,
        count=count,
        sum=total,
        average=average,
        stdev=stdev,
        median=median,
        q1=q1,
        q3=q3,
        normalized=normalized,
    )    


import collections.abc
def merge(old_value, new_value):
    # if not dict, see if it is iterable
    if not isinstance(new_value, collections.abc.Mapping):
        if is_iterable(new_value):
            new_value = { index: value for index, value in enumerate(new_value) }
    
    # if still not a dict, then just return the current value
    if not isinstance(new_value, collections.abc.Mapping):
        return new_value
    # otherwise get recursive
    else:
        # if not dict, see if it is iterable
        if not isinstance(old_value, collections.abc.Mapping):
            if is_iterable(old_value):
                old_value = { index: value for index, value in enumerate(old_value) }
        # if still not a dict
        if not isinstance(old_value, collections.abc.Mapping):
            # force it to be one
            old_value = {}
        
        # override each key recursively
        for key, updated_value in new_value.items():
            old_value[key] = merge(old_value.get(key, {}), updated_value)
        
        return old_value

def indent(string, by):
    indent_string = (" "*by)
    return indent_string + string.replace("\n", "\n"+indent_string)

def stringify(value):
    length = 0
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, dict):
        if len(value) == 0:
            return "{}"
        items = value if isinstance(value, Map) else value.items()
        output = "{\n"
        for each_key, each_value in items:
            element_string = stringify(each_key) + ": " + stringify(each_value)
            length += len(element_string)+2
            output += indent(element_string, by=4) + ", \n"
        output += "}"
        if length < stringify.onelineify_threshold:
            output = output.replace("\n    ","").replace("\n","")
        return output
    elif isinstance(value, list):
        if len(value) == 0:
            return "[]"
        output = "[\n"
        for each_value in value:
            element_string = stringify(each_value)
            length += len(element_string)+2
            output += indent(element_string, by=4) + ", \n"
        output += "]"
        if length < stringify.onelineify_threshold:
            output = output.replace("\n    ","").replace("\n","")
        return output
    elif isinstance(value, set):
        if len(value) == 0:
            return "set([])"
        output = "set([\n"
        for each_value in value:
            element_string = stringify(each_value)
            length += len(element_string)+2
            output += indent(element_string, by=4) + ", \n"
        output += "])"
        if length < stringify.onelineify_threshold:
            output = output.replace("\n    ","").replace("\n","")
        return output
    elif isinstance(value, tuple):
        if len(value) == 0:
            return "tuple()"
        output = "(\n"
        for each_value in value:
            element_string = stringify(each_value)
            length += len(element_string)+2
            output += indent(element_string, by=4) + ", \n"
        output += ")"
        if length < stringify.onelineify_threshold:
            output = output.replace("\n    ","").replace("\n","")
        return output
    else:
        try:
            debug_string = value.__repr__()
        except Exception as error:
            from io import StringIO
            import builtins
            string_stream = StringIO()
            builtins.print(*args, **kwargs, file=string_stream)
            debug_string = string_stream.getvalue()
        
        # TODO: handle "<slot wrapper '__repr__' of 'object' objects>"
        if debug_string.startswith("<class") and hasattr(value, "__name__"):
            return value.__name__
        if debug_string.startswith("<function <lambda>"):
            return "(lambda)"
        if debug_string.startswith("<function") and hasattr(value, "__name__"):
            return value.__name__
        if debug_string.startswith("<module") and hasattr(value, "__name__"):
            _, *file_path, _, _ = debug_string.split(" ")[-1]
            file_path = "".join(file_path)
            return f"module(name='{value.__name__}', path='{file_path}')"
        
        space_split = debug_string.split(" ")
        if len(space_split) >= 4 and debug_string[0] == "<" and debug_string[-1] == ">":
            
            if space_split[-1].startswith("0x") and space_split[-1] == "at":
                _, *name_pieces = space_split[0]
                *parts, name = "".join(name_pieces).split(".")
                parts_str = ".".join(parts)
                return f'{name}(from="{parts_str}")'
        
        return debug_string
stringify.onelineify_threshold = 50 # chars


def bundle(iterable, bundle_size):
    next_bundle = []
    for each in iterable:
        next_bundle.append(each)
        if len(next_bundle) >= bundle_size:
            yield tuple(next_bundle)
            next_bundle = []
    # return any half-made bundles
    if len(next_bundle) > 0:
        yield tuple(next_bundle)


def recursively_map(an_object, function, is_key=False):
    # base case 1 (iterable but treated like a primitive)
    if isinstance(an_object, str):
        return_value = an_object
    # base case 2 (exists because of scalar numpy/pytorch/tensorflow objects)
    if hasattr(an_object, "tolist"):
        return_value = an_object.tolist()
    else:
        # base case 3
        if not is_iterable(an_object):
            return_value = an_object
        else:
            if isinstance(an_object, dict):
                return_value = { recursively_map(each_key, function, is_key=True) : recursively_map(each_value, function) for each_key, each_value in an_object.items() }
            else:
                return_value = [ recursively_map(each, function) for each in an_object ]
    
    # convert lists to tuples so they are hashable
    if is_iterable(return_value) and not isinstance(return_value, dict) and not isinstance(return_value, str):
        return_value = tuple(return_value)
    
    return function(return_value, is_key=is_key)

def to_pure(an_object, recursion_help=None):
    # 
    # infinte recursion prevention
    # 
    top_level = False
    if recursion_help is None:
        top_level = True
        recursion_help = {}
    class PlaceHolder:
        def __init__(self, id):
            self.id = id
        def eval(self):
            return recursion_help[key]
    object_id = id(an_object)
    # if we've see this object before
    if object_id in recursion_help:
        # if this value is a placeholder, then it means we found a child that is equal to a parent (or equal to other ancestor/grandparent)
        if isinstance(recursion_help[object_id], PlaceHolder):
            return recursion_help[object_id]
        else:
            # if its not a placeholder, then we already have cached the output
            return recursion_help[object_id]
    # if we havent seen the object before, give it a placeholder while it is being computed
    else:
        recursion_help[object_id] = PlaceHolder(object_id)
    
    parents_of_placeholders = set()
    
    # 
    # optional torch tensor converter
    # 
    if hasattr(an_object, "__class__") and hasattr(an_object.__class__, "__name__"):
        if an_object.__class__.__name__ == "Tensor":
            try:
                import torch
                if isinstance(an_object, torch.Tensor):
                    an_object = an_object.detach().cpu()
            except Exception as error:
                pass
    # 
    # main compute
    # 
    return_value = None
    # base case 1 (iterable but treated like a primitive)
    if isinstance(an_object, str):
        return_value = an_object
    # base case 2 (exists because of scalar numpy/pytorch/tensorflow objects)
    elif hasattr(an_object, "tolist"):
        return_value = an_object.tolist()
    else:
        # base case 3
        if not is_iterable(an_object):
            return_value = an_object
        else:
            if isinstance(an_object, dict):
                return_value = {
                    to_pure(each_key, recursion_help) : to_pure(each_value, recursion_help)
                        for each_key, each_value in an_object.items()
                }
            else:
                return_value = [ to_pure(each, recursion_help) for each in an_object ]
    
    # convert iterables to tuples so they are hashable
    if is_iterable(return_value) and not isinstance(return_value, dict) and not isinstance(return_value, str):
        return_value = tuple(return_value)
    
    # update the cache/log with the real value
    recursion_help[object_id] = return_value
    #
    # handle placeholders
    #
    if is_iterable(return_value):
        # check if this value has any placeholder children
        children = return_value if not isinstance(return_value, dict) else [ *return_value.keys(), *return_value.values() ]
        for each in children:
            if isinstance(each, PlaceHolder):
                parents_of_placeholders.add(return_value)
                break
        # convert all the placeholders into their final values
        if top_level == True:
            for each_parent in parents_of_placeholders:
                iterator = enumerate(each_parent) if not isinstance(each_parent, dict) else each_parent.items()
                for each_key, each_value in iterator:
                    if isinstance(each_parent[each_key], PlaceHolder):
                        each_parent[each_key] = each_parent[each_key].eval()
                    # if the key is a placeholder
                    if isinstance(each_key, PlaceHolder):
                        value = each_parent[each_key]
                        del each_parent[each_key]
                        each_parent[each_key.eval()] = value
    
    # finally return the value
    return return_value

def normalize(values, max, min):
    """
    all elements of the output should be between 0 and 1
    """
    reward_range = max - min
    return tuple((each - min)/reward_range for each in values)

def rolling_average(a_list, window):
    results = []
    if len(a_list) < window * 2:
        return a_list
    near_the_end = len(a_list) - 1 - window 
    for index, each in enumerate(a_list):
        # at the start
        if index < window:
            average_items = a_list[0:index]+a_list[index:index+window]
        # at the end
        elif index > near_the_end:
            average_items = a_list[index-window:index]+a_list[index:len(a_list)]
        else:
            # this could be done a lot more efficiently with a rolling sum, oh well! ¯\_(ツ)_/¯ 
            average_items = a_list[index-window:index+window+1]
        # fallback
        if len(average_items) == 0:
            average_items = [ a_list[index] ]
        results.append(sum(average_items)/len(average_items))
    return results

def log_scale(number):
    import math
    if number > 0:
        return math.log(number+1)
    else:
        return -math.log((-number)+1)

def wrap_around_get(number, a_list):
    list_length = len(a_list)
    return a_list[((number % list_length) + list_length) % list_length]

def large_pickle_load(file_path):
    """
    This is for loading really big python objects from pickle files
    ~4Gb max value
    """
    import pickle
    import os
    max_bytes = 2**31 - 1
    bytes_in = bytearray(0)
    input_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f_in:
        for _ in range(0, input_size, max_bytes):
            bytes_in += f_in.read(max_bytes)
    output = pickle.loads(bytes_in)
    return output

def large_pickle_save(variable, file_path):
    """
    This is for saving really big python objects into a file
    so that they can be loaded in later
    ~4Gb max value
    """
    import file_system_py as FS
    import pickle
    bytes_out = pickle.dumps(variable, protocol=4)
    max_bytes = 2**31 - 1
    FS.clear_a_path_for(file_path, overwrite=True)
    with open(file_path, 'wb') as f_out:
        for idx in range(0, len(bytes_out), max_bytes):
            f_out.write(bytes_out[idx:idx+max_bytes])

def permute(a_list):
    from random import sample
    return sample(a_list, k=len(tuple(a_list)))

def countdown(size=None, offset=0, delay=0, seconds=None):
    """
        Returns a function
        That function will return False until it has been called `size` times
        Then it auto resets/repeats
    """
    if seconds:
        def _countdown():
                
            now = time.time()
            # init
            if _countdown.marker is None:
                _countdown.marker = now
            # enough time has passed
            if _countdown.marker + seconds <= now:
                _countdown.marker = now
                return True
            else:
                return False
        _countdown.marker = None
        return _countdown
    else:
        remaining = size
        def _countdown():
            _countdown.remaining -= 1
            if _countdown.remaining + offset <= 0:
                # restart
                _countdown.remaining = size - offset
                return True
            else:
                return False
        _countdown.remaining = size + delay
        _countdown.size = size
        return _countdown


# 
# print that can be indented or temporarily disabled
# 
real_print = print
def print(*args, to_string=False, **kwargs): # print(value, ..., sep=' ', end='\n', file=sys.stdout, flush=False)
    from io import StringIO
    if to_string:
        string_stream = StringIO()
        # dump to string
        real_print(*args, **{ "flush": True, **kwargs, "file":string_stream })
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str
        
    if hasattr(print, "disable") and print.disable.always:
        return
        
    if hasattr(print, "indent"):
        if print.indent.size > 0:
            indent = print.indent.string*print.indent.size
            # dump to string
            output_str = print(*args, **{ **kwargs, "to_string":True})
            # indent it
            output_str = indent+output_str.replace("\n", "\n"+indent)[0:-len(indent)]
            # print it
            return real_print(output_str, **{ "flush": print.flush.always, **kwargs, "end":""}) 
    
    return real_print(*args, **{ "flush": print.flush.always, **kwargs})

class _Indent(object):
    """
    with print.indent:
        print("howdy1")
        with print.indent:
            print("howdy2")
        print("howdy3")
    """
    def __init__(self, *args, **kwargs):
        self.indent_before = []
    
    def __enter__(self):
        self.indent_before.append(print.indent.size)
        print.indent.size += 1
        return print
    
    def __exit__(self, _, error, traceback):
        # restore prev indent
        print.indent.size = self.indent_before.pop()
        if error is not None:
            # error cleanup HERE
            raise error
    
    def function(self, function_being_wrapped):
        """
        Example:
            @print.indent.function
            def some_function(arg1):
                print("this is indented")
        """
        def wrapper(*args, **kwargs):
            original_value = print.indent.size
            print.indent.size += 1
            output = function_being_wrapped(*args, **kwargs)
            print.indent.size = original_value
            return output
        return wrapper
    
    def block(self, *args):
        """
        with block("staring iterations"):
            print("this is indented")
        """
        print(*args)
        return print.indent
    
    def function_block(self,function_being_wrapped):
        """
        Example:
            @print.indent.function_block
            def some_function(arg1):
                print("this is indented, and has the name of the function above it")
        """
        def wrapper(*args, **kwargs):
            original_value = print.indent.size
            if hasattr(function_being_wrapped, "__name__"):
                print(function_being_wrapped.__name__)
            print.indent.size += 1
            output = function_being_wrapped(*args, **kwargs)
            print.indent.size = original_value
            return output
        return wrapper
    
print.indent  = _Indent()
print.flush   = Object()
print.disable = Object()
print.indent.string = "    "
print.indent.size = 0
print.flush.always = True
print.disable.always = False

def apply_to_selected(func, which_args, args, kwargs):
    if which_args == ...:
        new_args = tuple(func(each) for each in args)
        new_kwargs = { each_key : func(each_value) for each_key, each_value in kwargs.items() }
        return new_args, new_kwargs
    else:
        # todo: probably make this more flexible
        which_args = tuple(which_args)
        
        new_args = []
        for index, each in enumerate(args):
            if index in which_args:
                new_args[index].append(func(each))
            else:
                new_args[index].append(each)
            
        new_kwargs = {}
        for key, value in kwargs.items():
            if key in which_args:
                new_kwargs[key].append(func(value))
            else:
                new_kwargs[key].append(value)
        
        return new_args, new_kwargs


# 
# 
# json fixes
# 
# 
import json_fix # import this before the JSON.dumps gets called
import json

# fallback method
json.override_table[lambda obj: True ] = lambda obj: to_pure(obj)

# 
# pandas
# 
try:
    import pandas as pd
    json.override_table[lambda obj: isinstance(obj, pd.DataFrame)] = lambda obj: json.loads(obj.to_json())
except Exception as error:
    pass

# 
# 
# value conversion
# 
# 
def to_numpy(value):
    try:
        import numpy
    except Exception as error:
        pass
    
    # torch tensor
    if hasattr(value, "__class__") and hasattr(value.__class__, "__name__"):
        if value.__class__.__name__ == "Tensor":
            try:
                import torch
                if isinstance(value, torch.Tensor):
                    return value.detach().cpu().numpy()
            except Exception as error:
                pass
    return numpy.array(to_pure(value))


