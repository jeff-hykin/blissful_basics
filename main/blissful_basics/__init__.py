from .__dependencies__ import json_fix
from .__dependencies__ import file_system_py as FS
from .__dependencies__.super_map import LazyDict, Map, SemiLazyMap, LazyIterable
from .__dependencies__.super_hash import super_hash, hash_file, consistent_hash

from time import time as now
from random import shuffle
import numbers
import os
import atexit

# 
# python sucks and requires global variables for stuff like pickling, this is the best workaround for that
# 
class Settings:
    serialization_id = None

def blissful_basics_collision_avoidance_namespace():
    if Settings.serialization_id == None:
        Settings.serialization_id = consistent_hash(FS.read(__file__))[0:8] # 8 chars is enough for as-likely-has-hardware-failing-from-cosmic-event
        # Why not hash __name__?
        # - because this value should be the same even if this file is imported from different __main__ files (e.g. relative path shouldnt matter)
        # Why not use random id?
        # 1. this value should be stable for serialization load/unload reasons
        # 2. two different versions of blissful basics imported to the same project should have different hashes
    return Settings.serialization_id

# 
# checkers
# 
if True:
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
    
    import collections.abc
    def is_dict(thing):
        return isinstance(thing, collections.abc.Mapping)
    
    def is_number(thing):
        return isinstance(thing, numbers.Number)

# 
# data structures
# 
if True:
    def singleton(a_class):
        """
        @singleton
        SomeClass:
            thing = 10
            @property
            def double_thing(self):
                return self.thing * 2
        
        print(SomeClass.double_thing) # >>> 20
        """
        return a_class()
    
    class Object: # just an empty object for assigning attributes of
        def __init__(self, **kwargs):
            for each_key, each_value in kwargs.items():
                setattr(self, each_key, each_value)
        
        def __json__(self):
            return self.__dict__
        
        def __repr__(self):
            if len(self.__dict__) == 0:
                return 'Object()'
            else:
                entries = "Object(\n"
                for each_key, each_value in self.__dict__.items():
                    entries += "    "+str(each_key)+" = "+repr(each_value)+",\n"
                return entries+")"
    
    def create_named_list_class(names):
        """
        Example:
            Position = create_named_list_class(['x','y','z'])
            a = Position([1,2,3])
            print(a.x)   # 1
            a.x = 4
            print(a[0])  # 4
            a[0] = 9
            print(a.x)   # 9
        """
        
        names_to_index = {}
        if isinstance(names, dict):
            names_to_index = names
        if isinstance(names, (tuple, list)):
            for index, each in enumerate(names):
                names_to_index[each] = index
        
        hash_id = blissful_basics_collision_avoidance_namespace()+consistent_hash(tuple(names))[0:8]
        # this is done in an exec for python pickling reasons
        exec(
            f"""
            \nclass NamedList{hash_id}(list):
            
            names_to_index = {repr(names_to_index)}
            def __getitem__(self, key):
                if isinstance(key, (int, slice)):
                    return super(NamedList{hash_id}, self).__getitem__(key)
                # assume its a name
                else:
                    try:
                        index = NamedList{hash_id}.names_to_index[key]
                    except:
                        raise KeyError(f'''key={{key}} not in named list: {{self}}''')
                    if index >= len(self):
                        return None
                    return self[index]
            
            def __getattr__(self, key):
                if key in NamedList{hash_id}.names_to_index:
                    return self[key]
                else:
                    super(NamedList{hash_id}, self).__getattribute__(key)
            
            def __setattr__(self, key, value):
                if key in NamedList{hash_id}.names_to_index:
                    index = NamedList{hash_id}.names_to_index[key]
                    while index >= len(self):
                        super(NamedList{hash_id}, self).append(None)
                    super(NamedList{hash_id}, self).__setitem__(index, value)
                else:
                    super(NamedList{hash_id}, self).__setattr__(key, value)
            
            def __setitem__(self, key, value):
                if isinstance(key, int):
                    super(NamedList{hash_id}, self).__setitem__(key, value)
                # assume its a name
                else:
                    index = NamedList{hash_id}.names_to_index[key]
                    while index >= len(self):
                        super(NamedList{hash_id}, self).append(None)
                    super(NamedList{hash_id}, self).__setitem__(index, value)
                    
            def keys(self):
                return list(NamedList{hash_id}.names_to_index.keys())
            
            def values(self):
                return self
            
            def get(self, key, default):
                try:
                    return self[key]
                except Exception as error:
                    return default
            
            def items(self):
                return zip(self.keys(), self.values())
            
            def update(self, other):
                for each_key in NamedList{hash_id}.names_to_index:
                    if each_key in other:
                        self[each_key] = other[each_key]
                return self
            
            def __repr__(self):
                import itertools
                out_string = '['
                named_values = 0
                
                reverse_lookup = {{}}
                for each_name, each_index in NamedList{hash_id}.names_to_index.items():
                    reverse_lookup[each_index] = reverse_lookup.get(each_index, []) + [ each_name ]
                    
                for each_index, value in enumerate(self):
                    name = "=".join(reverse_lookup.get(each_index, []))
                    if name:
                        name += '='
                    out_string += f' {{name}}{{value}},'
                
                out_string += ' ]'
                return out_string
            """,
            globals(),
            globals()
        )
                
        return globals()[f"NamedList{hash_id}"]
    
    from collections import deque
    class CappedQue(deque):
        def __init__(self, max_size):
            self.max_size = max_size
        
        def push(self, value):    return self.append(value)
        def add(self, value):     return self.append(value)
        def append(self, value):
            super().append(value)
            if len(self) > self.max_size:
                return self.pop()
        def pop(self):
            return self.popleft()
        def __getitem__(self, index):
            if isinstance(index, numbers.Number):
                return super().__getitem__(int(index))
            if isinstance(index, slice):
                start = index.start
                stop = index.stop if index.stop != None else len(self)
                step = index.step if index.step != None else 1
                return [ self[index] for index in range(start, stop, step) ]
    
    class CappedBuffer(list):
        """
            Summary:
                buffer that auto-clears when a cap is hit
                and calls a callback when that cap is hit
                Note: the buffer will only auto-clear if 
                the callback doesnt remove any items.
                (E.g. the callback can do manual/partial
                clearing, and the buffer respect it)
            
            Example:
                buffer = CappedBuffer(cap=3)
                @buffer.when_overflowing
                def do_stuff(buffer_data):
                    print(buffer_data)
                
                buffer.append(1)
                buffer.append(1)
                buffer.append(1)
                # prints [1,1,1] at this point
                
                print(len(buffer))
                # prints 0
        """
        def __init__(self, cap):
            self.cap = cap
            self._callback = lambda a: None
        
        def append(self, value):
            super().append(value)
            if len(self) >= self.threshold:
                self._callback(self)
                # if no items were removed (e.g. callback didn't clean up)
                # then flush the buffer
                if len(self) >= self.threshold:
                    self.clear()
        
        def when_overflowing(self, function_being_wrapped):
            self._callback = function_being_wrapped

# 
# warnings
# 
if True:
    import warnings
    real_warn_910932842088502 = warnings.warn
    recent_stack_level = None
    def warn(*args, **kwargs):
        global recent_stack_level
        recent_stack_level = kwargs.get("stacklevel", None)
        return real_warn_910932842088502(*args, **kwargs)
    warnings.warn = warn
    
    @singleton
    class Warnings:
        _original_filters = list(warnings.filters)
        _original_showwarning = warnings.showwarning
        def show_full_stack_trace(self):
            # show full traceback of each warning
            import traceback
            import sys
            
            def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
                global recent_stack_level
                log = file if hasattr(file,'write') else sys.stderr
                level = 1
                if recent_stack_level:
                    level = max(recent_stack_level, level)
                traceback_strings = []
                while 1:
                    try:
                        level += 1
                        output = traceback_to_string(
                            get_trace(level=level)
                        )
                        if "return real_warn_910932842088502(*args, **kwargs)" in output:
                            continue
                        traceback_strings.append(
                            output
                        )
                    except Exception as error:
                        break
                
                traceback_string = indent("".join(traceback_strings))
                lines = traceback_string.split("\n")
                traceback_string = "\n".join(tuple(each for each in lines if not each.startswith('      File "<')))
                main_message = warnings.formatwarning(message, category, filename, lineno, line)
                if log == sys.stderr:
                    main_message = Console.color(main_message, foreground="yellow")
                    lines = traceback_string.split("\n")
                    new_lines = []
                    for each_line in lines:
                        if not each_line.startswith('      File "'):
                            new_lines.append(
                                Console.color(each_line, foreground="cyan", dim=True)
                            )
                        else:
                            end_index = None
                            try:
                                end_index = each_line.index('", line ')
                            except Exception as error:
                                pass
                            if not end_index:
                                new_lines.append(
                                    each_line
                                )
                            else:
                                file_path = each_line[len('      File "'):end_index]
                                new_lines.append(
                                    Console.color('      File "', dim=True)+Console.color(file_path, foreground="yellow", dim=True)+Console.color(each_line[end_index:], dim=True)
                                )
                    traceback_string = "\n".join(new_lines)
                    
                log.write(
                    main_message+traceback_string+'\n'
                )
            warnings.showwarning = warn_with_traceback
            warnings.simplefilter("always")
        
        def show_normal(self):
            warnings.filters = self._original_filters
            warnings.showwarning = self._original_showwarning
        
        def disable(self):
            warnings.simplefilter("ignore")
            warnings.filterwarnings('ignore')
        
        class disabled:
            # TODO: in future allow specify which warnings to disable
            def __init__(with_obj, *args, **kwargs):
                pass
            
            def __enter__(with_obj):
                with_obj._original_filters = list(warnings.filters)
                with_obj._original_showwarning = warnings.showwarning
            
            def __exit__(with_obj, _, error, traceback):
                # normal cleanup HERE
                warnings.filters = with_obj._original_filters
                warnings.showwarning = with_obj._original_showwarning
                
                with_obj._original_filters = list(warnings.filters)
                with_obj._original_showwarning = warnings.showwarning
                
                if error is not None:
                    raise error
    # show full stack trace by default instead of just saying "something wrong happened somewhere I guess"
    Warnings.show_full_stack_trace()

#
# errors
# 
    def traceback_to_string(traceback):
        import traceback as traceback_module
        from io import StringIO
        string_stream = StringIO()
        traceback_module.print_tb(traceback, limit=None, file=string_stream)
        return string_stream.getvalue()
    
    def get_trace(level=0):
        import sys
        import types
        try:
            raise Exception(f'''''')
        except:
            traceback = sys.exc_info()[2]
            back_frame = traceback.tb_frame
            for each in range(level+1):
                back_frame = back_frame.f_back
        traceback = types.TracebackType(
            tb_next=None,
            tb_frame=back_frame,
            tb_lasti=back_frame.f_lasti,
            tb_lineno=back_frame.f_lineno
        )
        return traceback
    
    class CatchAll:
        """
        Example:
            with CatchAll():
                # prints error but keeps going
                raise Exception(f'''Howdy''')


            with SuppressAll():
                # prints nothing and keeps going
                raise Exception(f'''Howdy''')
            
            with CatchAll(suppress_errors=True):
                # prints error but keeps going
                raise Exception(f'''Howdy''')
            
            print("code gets here")
        """
        
        def __init__(self, *args, suppress_errors=False, **kwargs):
            self.suppress_errors = suppress_errors
        
        def __enter__(self):
            pass
        
        def __exit__(self, _, error, the_traceback):
            if error is not None:
                if not self.suppress_errors:
                    print(
                        f"CatchAll caught:\n    {repr(error)}\n"+indent(traceback_to_string(the_traceback), by="    ")
                    )
            return True
    
    SuppressAll = lambda *args, **kwargs: CatchAll(*args, suppress_errors=True, **kwargs)
            
#
# string related
# 
if True:
    def indent(string, by="    ", ignore_first=False):
        indent_string = (" "*by) if isinstance(by, int) else by
        string = string if isinstance(string, str) else stringify(string)
        start = indent_string if not ignore_first else ""
        return start + string.replace("\n", "\n"+indent_string)

    def remove_largest_common_prefix(list_of_strings):
        def all_equal(a_list):
            if len(a_list) == 0:
                return True
            
            prev = a_list[0]
            for each in a_list:
                if prev != each:
                    return False
                prev = each
            
            return True
        
        shortest_path_length = min([ len(each_path) for each_path in list_of_strings ])
        longest_common_path_length = shortest_path_length
        while longest_common_path_length > 0:
            # binary search would be more efficient but its fine
            longest_common_path_length -= 1
            if all_equal([ each[0:longest_common_path_length] for each_path in list_of_strings ]):
                break
        
        return [ each[longest_common_path_length:] for each_path in list_of_strings ]
            
    def pascal_case_with_spaces(string, valid_word_contents="1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"):
        digits = "1234567890"
        new_string = " "
        # get pairwise elements
        for each_character in string:
            prev_character = new_string[-1]
            prev_is_lowercase = prev_character.lower() == prev_character
            each_is_uppercase = each_character.lower() != each_character
            
            # remove misc characters (handles snake case, kebab case, etc)
            if each_character not in valid_word_contents:
                new_string += " "
            # start of word
            elif prev_character not in valid_word_contents:
                new_string += each_character.upper()
            # start of number
            elif prev_character not in digits and each_character in digits:
                new_string += each_character
            # end of number
            elif prev_character in digits and each_character not in digits:
                new_string += each_character.upper()
            # camel case
            elif prev_is_lowercase and each_is_uppercase:
                new_string += " "+each_character.upper()
            else:
                new_string += each_character
        
        # flatten out all the whitespace
        new_string = new_string.strip()
        while "  " in new_string:
            new_string = new_string.replace("  "," ")
        
        return new_string

    def levenshtein_distance(s1, s2):
        # https://stackoverflow.com/questions/2460177/edit-distance-in-python
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        
        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2+1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]
    
    def levenshtein_distance_sort(*, word, other_words):
        word = word.lower() # otherwise this totally screws up distance
        prioritized = sorted(other_words, key=lambda each_other: levenshtein_distance(word, each_other))
        return prioritized

# 
# generic (any value)
# 
if True:
    dev_null = open(os.devnull, "w")
    def explain(a_value):
        import os
        # import inspect
        
        # # https://stackoverflow.com/questions/28021472/get-relative-path-of-caller-in-python
        # file_name = ""
        # line_number = ""
        # try:
        #     stack_level = 1
        #     frame = inspect.stack()[1+stack_level]
        #     module = inspect.getmodule(frame[0])
        #     # directory = os.path.dirname(module.__file__)
        #     file_name = os.path.basename(module.__file__)
        #     line_number = frame.lineno
        # # if inside a repl (error =>) assume that the working directory is the path
        # except (AttributeError, IndexError) as error:
        #     pass
        
        # prefix = ""
        # if file_name != "":
        #     prefix = f"{file_name}:{line_number} "
        
        names = dir(a_value)
        normal_attributes  = []
        normal_methods     = []
        magic_attributes   = []
        magic_methods      = []
        private_attributes = []
        private_methods    = []
        for each in names:
            is_method = False
            try:
                with Console.output_redirected_to(file=dev_null):
                    is_method = callable(getattr(a_value, each, None))
            except Exception as error:
                print(error)
            if not each.startswith("_"):
                if not is_method:
                    normal_attributes.append(each)
                else:
                    normal_methods.append(each)
            elif each.startswith("__"):
                if not is_method:
                    magic_attributes.append(each)
                else:
                    magic_methods.append(each)
            else:
                if not is_method:
                    private_attributes.append(each)
                else:
                    private_methods.append(each)
        for each in normal_attributes: print(f"    {each}")
        for each in normal_methods: print(f"    {each}()")
        for each in magic_attributes: print(f"    {each}")
        for each in magic_methods: print(f"    {each}()")
        for each in private_attributes: print(f"    {each}")
        for each in private_methods: print(f"    {each}()")
    
    def attributes(a_value):
        if a_value == None:
            return []
        all_attachments = dir(a_value)
        return [
            each for each in all_attachments if not (each.startswith("__") and each.endswith("__")) and not callable(getattr(a_value, each))
        ]
    
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

    def stringify(value, onelineify_threshold=None):
        if onelineify_threshold is None: onelineify_threshold = stringify.onelineify_threshold
        
        length = 0
        if isinstance(value, str):
            return repr(value)
        elif isinstance(value, dict):
            if len(value) == 0:
                return "{}"
            else:
                # if all string keys and all identifiers
                if all(isinstance(each, str) and each.isidentifier() for each in value.keys()):
                    items = value.items()
                    output = "dict(\n"
                    for each_key, each_value in items:
                        element_string = each_key + "=" + stringify(each_value)
                        length += len(element_string)+2
                        output += indent(element_string, by=4) + ", \n"
                    output += ")"
                    if length < onelineify_threshold:
                        output = output.replace("\n    ","").replace("\n","")
                    return output
                # more complicated mapping
                else:
                    items = value.items()
                    output = "{\n"
                    for each_key, each_value in items:
                        element_string = stringify(each_key) + ": " + stringify(each_value)
                        length += len(element_string)+2
                        output += indent(element_string, by=4) + ", \n"
                    output += "}"
                    if length < onelineify_threshold:
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
            if length < onelineify_threshold:
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
            if length < onelineify_threshold:
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
            if length < onelineify_threshold:
                output = output.replace("\n    ","").replace("\n","")
            return output
        else:
            try:
                debug_string = value.__repr__()
            except Exception as error:
                from io import StringIO
                import builtins
                string_stream = StringIO()
                builtins.print(value, file=string_stream)
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
    stringify.onelineify_threshold = 50
    
    def is_required_by(*args, **kwargs):
        """
            Summary:
                A way to know why a method function exists, and know if it can be renamed
                (A way of mapping out dependencies)
            
            Example:
                import custom_json_thing
                
                class Thing:
                    @is_required_by(custom_json_thing)
                    def to_json(self):
                        return "something"
                        
        """
        def decorator(function_being_wrapped):
            return function_being_wrapped
        return decorator
    
    def is_used_by(*args, **kwargs):
        """
            Summary:
                A way to know why a method function exists, and know if it can be renamed
                (A way of mapping out dependencies)
            
            Example:
                import custom_json_thing
                
                class Thing:
                    @is_used_by(custom_json_thing)
                    def to_json(self):
                        return "something"
                        
        """
        def decorator(function_being_wrapped):
            return function_being_wrapped
        return decorator

# 
# function helpers
# 
if True:
    def parameter_signature_string(func):
        import inspect
        return repr(inspect.signature(func))[11:-1]
    
    class ParameterInfo:
        def __init__(self, *, is_args_spread, is_kwargs_spread, is_required, has_default, default, must_be_positional, must_be_keyword, can_be_positional_or_keyword, can_be_positional, can_be_keyword):
            self.is_args_spread               = is_args_spread
            self.is_kwargs_spread             = is_kwargs_spread
            self.is_required                  = is_required
            self.has_default                  = has_default
            self.default                      = default
            self.must_be_positional           = must_be_positional
            self.must_be_keyword              = must_be_keyword
            self.can_be_positional_or_keyword = can_be_positional_or_keyword
            self.can_be_positional            = can_be_positional
            self.can_be_keyword               = can_be_keyword
        
        def __json__(self):
            return self.__dict__
        
        def __repr__(self):
            entries = "ParameterInfo(\n"
            for each_key, each_value in self.__dict__.items():
                entries += "    "+str(each_key)+" = "+repr(each_value)+",\n"
            return entries+")"
    
    def parameters_of(func):
        import inspect
        signature = inspect.signature(func)
        empty_inspect_object = signature.empty
        output = {}
        for each_key, each_parameter in signature.parameters.items():
            is_args_spread     = (each_parameter.kind == each_parameter.VAR_POSITIONAL)
            is_kwargs_spread   = (each_parameter.kind == each_parameter.VAR_KEYWORD)
            if is_args_spread or is_kwargs_spread:
                has_default                  = False
                is_required                  = False
                default                      = None
                can_be_positional_or_keyword = False
                must_be_positional           = False
                must_be_keyword              = False
                can_be_positional            = False
                can_be_keyword               = False
            else:
                has_default                  = (each_parameter.default != empty_inspect_object)
                is_required                  = not has_default
                default                      = (each_parameter.default if has_default else None)
                can_be_positional_or_keyword = each_parameter.kind == each_parameter.POSITIONAL_OR_KEYWORD
                must_be_positional           = each_parameter.kind == each_parameter.POSITIONAL_ONLY
                must_be_keyword              = each_parameter.kind == each_parameter.KEYWORD_ONLY
                can_be_positional            = can_be_positional_or_keyword or must_be_positional
                can_be_keyword               = can_be_positional_or_keyword or must_be_keyword
            
            output[each_key] = ParameterInfo(
                is_args_spread=is_args_spread,
                is_kwargs_spread=is_kwargs_spread,
                is_required=is_required,
                has_default=has_default,
                default=default,
                must_be_positional=must_be_positional,
                must_be_keyword=must_be_keyword,
                can_be_positional_or_keyword=can_be_positional_or_keyword,
                can_be_positional=can_be_positional,
                can_be_keyword=can_be_keyword,
            )
        return output
    
    def check_args_compatibility(func, args, kwargs):
        import inspect
        if not isinstance(args, (tuple, list)):
            args = tuple()
        if not isinstance(kwargs, dict):
            kwargs = {}
        
        remaining_positional_args_count = len(args)
        parameters = parameters_of(func).items()
        args_spread_exists = False
        kwargs_spread_exists = False
        actual_parameters = []
        for name, parameter_info in parameters.items():
            if parameter_info.is_args_spread:
                args_spread_exists = True
            elif parameter_info.is_kwargs_spread:
                kwargs_spread_exists = True
            else:
                actual_parameters.append((name, parameter_info))
        
        given_positional_names = []
        for index, (name, parameter_info) in enumerate(actual_parameters):
            # given a positional arg
            if remaining_positional_args_count > 0:
                remaining_positional_args_count -= 1
                given_positional_names.append(name)
                if not parameter_info.can_be_positional:
                    reason = f"Was given a positional arg at {index}, but that arg ({name}) isn't allowed to be positional"
                    return False
            break
        
        no_more_positional_args = remaining_positional_args_count == 0
        remaining_parameters = tuple(parameters.items())[index+1:]
        
        for each in kwargs.keys():
            if each in given_positional_names:
                reason = f"can't provide name arg as both a positional and keyword value for same argument ({repr(each)})"
                return False
        
        if no_more_positional_args:
            if len(remaining_parameters) == 0:
                if len(kwargs) == 0:
                    return True
                else:
                    reason = f"given kwargs {kwargs}, but the function doesn't take them"
                    return False
            # if there are more parameters
            else:
                name, parameter_info = remaining_parameters[0]
                # check if there are more required positional values
                if parameter_info.must_be_positional:
                    reason = f"Not given enough positional arguments"
                    return False
                # if there are more parameters, then fall through to the kwargs-checker case
                else:
                    pass
        else:
            if not args_spread_exists:
                reason = "Too many positional arguments"
                return False
            # we consume all remaining positional args and effectively dump them into the splat
            else:
                pass
        
        # at this point all positional-only arguments should be satisfied and no extra/too-many positional args have been given
        
        parameters_that_are_not_positionally_provided = [ (name, parameter_info) for name, parameter_info in remaining_parameters if name not in given_positional_names ]
        unused_kwargs = list(kwargs.keys())
        for name, parameter_info in parameters_that_are_not_positionally_provided:
            if name in kwargs:
                unused_kwargs.remove(name)
            elif parameter_info.is_required:
                reason = f"Not given argument {repr(name)}, which is a required argument"
                return False
        
        # at this point all required args (positional and named) have been given
        if len(unused_kwargs) != 0 and not kwargs_spread_exists:
            reason = f"There were given kwargs that were not part of the allowed kwargs for the function ({unused_kwargs})"
            return False
        
        # didn't violate any rules
        return True

#
# iterative helpers
#
if True:
    def flatten(value):
        flattener = lambda *m: (i for n in m for i in (flattener(*n) if is_generator_like(n) else (n,)))
        return list(flattener(value))

    def iteratively_flatten_once(items):
        for each in items:
            if is_generator_like(each):
                yield from each
            else:
                yield each
    
    def drop_end(quantity, iterable):
        """
            Example:
                assert [1, 2] == list(drop_end(2, [1,2,3,4]))
        """
        buffer = []
        for index, each in enumerate(iterable):
            buffer.append(each)
            if len(buffer) > quantity:
                yield buffer.pop(0)
    
    def flatten_once(items):
        return list(iteratively_flatten_once(items))
    
    def countdown(size=None, offset=0, delay=0, seconds=None):
        """
            Returns a function
                That function will return False until it has been called `size` times
                Then on the size-th time it returns True, and resets/repeats
        """
        import time
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

    def wrap_around_get(index, a_list):
        """
            given an in-bound index will return that element
            given an out-of-bound index, it will treat the list as if it were circular and infinite and get the corrisponding value
        """
        list_length = len(a_list)
        return a_list[((index % list_length) + list_length) % list_length]

    def shuffled(a_list):
        from random import shuffle
        new_list = list(a_list)
        shuffle(new_list)
        return new_list
    
    def combinations(elements, max_length=None, min_length=None):
        if max_length is None and min_length is None:
            min_length = 1
            max_length = len(elements)
        else:
            max_length = max_length or len(elements)
            min_length = min_length if min_length is not None else max_length
        
        if min_length != max_length:
            for index in range(min_length, max_length + 1):
                yield from combinations(elements, index, index)
        else:
            if max_length == 1:
                for each in elements:
                    yield [each]
            else:
                for index in range(len(elements)):
                    for each in combinations(elements[index + 1:], max_length - 1, max_length - 1):
                        yield [elements[index]] + each
    
    import itertools
    def permutate(possibilities, digits=None):
        # TODO:
            # possibilities-per-digit
            # combinations
            # powerset
            # fixed length
            # variable length
        
        # without repeats
        if type(digits) == type(None):
            yield from itertools.permutations(possibilities)
        # with repeats
        else:
            if digits == 1:
                for each in possibilities:
                    yield [ each ]
            elif digits > 1:
                for each_subcell in permutate(possibilities, digits-1):
                    for each in possibilities:
                        yield [ each ] + each_subcell
            # else: dont yield anything

    def randomly_pick_from(a_list):
        from random import randint
        index = randint(0, len(a_list)-1)
        return a_list[index]

    import collections.abc
    def merge(old_value, new_value):
        # if not dict, see if it is iterable
        if not isinstance(new_value, collections.abc.Mapping):
            if is_generator_like(new_value):
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

    def recursively_map(an_object, function, is_key=False):
        """
            inputs:
                the function should be like: lambda value, is_key: value if is_key else (f"{value}") # convert all values to strings
            explaination:
                this will be recursively called on all elements of iterables (and all key/values of dictionaries)
                - the deepest elements (primitives) are done first
                - there is no object-contains-itself checking yet (TODO)
            outputs:
                a copy of the original value
        """
        # base case 1 (iterable but treated like a primitive)
        if isinstance(an_object, (str, bytes)):
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

    def all_equal(a_list):
        if len(a_list) == 0:
            return True
        
        prev = a_list[0]
        for each in a_list[1:]:
            if prev != each:
                return False
            prev = each
        
        return True

    def all_different(a_list):
        if len(a_list) == 0:
            return True
        
        prev = a_list[0]
        for each in a_list[1:]:
            if prev == each:
                return False
            prev = each
        
        return True

# 
# math related
# 
if True:
    def log_scale(number):
        import math
        if number > 0:
            return math.log(number+1)
        else:
            return -math.log((-number)+1)

    def integers(*, start, end_before, step=1):
        return list(range(start, end_before, step))
    
    def clip(value, *, min, max):
        if value > max:
            return max
        elif value < min:
            return min
        return value
    
    def linear_steps(*, start, end, quantity, transform=lambda x: x):
        """
            Example:
                assert [4, 11, 18, 24, 31] == list(linear_steps(start=4, end=31, quantity=5, transform=round))
        """
        import math
        assert quantity > -1
        if quantity != 0:
            quantity = math.ceil(quantity)
            if start == end:
                for each in range(quantity):
                    yield transform(start)
            else:
                x0 = 1
                x1 = quantity
                y0 = start
                y1 = end
                interpolater = lambda x: y0 if (x1 - x0) == 0 else y0 + (y1 - y0) / (x1 - x0) * (x - x0)
                for x in range(quantity-1):
                    yield transform(interpolater(x+1))
                yield transform(end)

    def product(iterable):
        from functools import reduce
        import operator
        return reduce(operator.mul, iterable, 1)

    def max_index(iterable):
        iterable = tuple(iterable)
        if len(iterable) == 0:
            return None
        max_value = max(iterable)
        from random import sample
        options = tuple( each_index for each_index, each in enumerate(iterable) if each == max_value )
        return sample(options, 1)[0]
    
    def max_indices(iterable):
        iterable = tuple(iterable)
        if len(iterable) == 0:
            return None
        max_value = max(iterable)
        return tuple( each_index for each_index, each in enumerate(iterable) if each == max_value )
    
    def arg_max(*, args, values):
        values = tuple(values)
        if len(values) == 0:
            return None
        max_value = max(values)
        from random import sample
        options = tuple( arg for arg, value in zip(args, values) if value == max_value )
        return sample(options, 1)[0]
    
    def arg_maxs(*, args, values):
        values = tuple(values)
        if len(values) == 0:
            return None
        max_value = max(values)
        return tuple( arg for arg, value in zip(args, values) if value == max_value )

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

    def normalize(values, max, min):
        """
            all elements of the output should be between 0 and 1
            if there's no difference between the max an min, it outputs all 0's
        """
        reward_range = max - min
        if reward_range == 0:
            return tuple(0 for each in values)
        else:
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

    def points_to_function(x_values, y_values, are_sorted=False, smoothing=0, method="linear_interpolation"):
        assert method == "linear_interpolation", 'Sorry only linear_interpolation is supported at this time'
        
        number_of_values = len(x_values)
        if number_of_values != len(y_values):
            raise ValueError("x_values and y_values must have the same length")
        if number_of_values == 0:
            raise ValueError("called points_to_function() but provided an empty list of points")
        # horizontal line
        if number_of_values == 1:
            return lambda x_value: y_values[0]
        
        if not are_sorted:
            # sort to make sure x values are least to greatest
            x_values, y_values = zip(
                *sorted(
                    zip(x_values, y_values),
                    key=lambda each: each[0],
                )
            )
        from statistics import mean
        slopes = []
        minimum_x = x_values[0]
        maximum_x = x_values[-2] # not the true max, but, because of indexing, the 2nd-maximum
        def inner_function(x):
            if x >= maximum_x:
                # needs -2 because below will do x_values[x_index+1]
                x_index = number_of_values-2
            elif x <= minimum_x:
                x_index = 0
            else:
                # binary search for x
                low = 0
                high = number_of_values - 1

                while low < high:
                    mid = (low + high) // 2

                    if x_values[mid] < x:
                        low = mid + 1
                    else:
                        high = mid

                if low > 0 and x < x_values[low - 1]:
                    low -= 1
                
                x_index = low
            
            # Perform linear interpolation / extrapolation
            x0, x1 = x_values[x_index], x_values[x_index+1]
            y0, y1 = y_values[x_index], y_values[x_index+1]
            # verticle line
            if (x1 - x0) == 0:
                return y1
            slope = (y1 - y0) / (x1 - x0)
            slopes.push(slope)
            slope = mean(slopes)
            slopes = slopes[0:smoothing]
            y = y0 + slope * (x - x0)

            return y
        
        return inner_function
# 
# time
#
if True: 
    import time
    
    def unix_time():
        return int(time.time()*1000)
    
    @singleton
    class Time:
        prev = time.time()
        
        @property
        def unix(self):
            return int(time.time()*1000)
        
        @property
        def time_since_prev_call(self):
            current = time.time()
            output = current-Time.prev
            Time.prev = current
            return output
    
    class Timer:
        """
        Example:
            with Timer(name="thing"):
                do_something()
        """
        prev = None
        def __init__(self, name="", *, silence=False, **kwargs):
            self.name = name
            self.silence = silence
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, _, error, traceback):
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
            if not self.silence:
                print(f"{self.name} took {round(self.duration*1000)}ms")
            Timer.prev = self
            if error is not None:
                # error cleanup HERE
                return None

# 
# colors
# 
if True:
    class Colors:
        """
        Example:
            theme = Colors(dict(red="#000",blue="#000",))
            
            # index that wraps-around
            theme[0]      # returns red
            theme[1]      # returns blue
            theme[2]      # returns red
            theme[109320] # returns a valid color (keeps wrapping-around)
            
            # names
            theme.red     # returns the value for red
            
            # iteration
            for each_color in theme:
                 print(each_color) # outputs "#000"
        """
        def __init__(self, color_mapping):
            self._color_mapping = color_mapping
            for each_key, each_value in color_mapping.items():
                if isinstance(each_key, str) and len(each_key) > 0 and each_key[0] != '_':
                    setattr(self, each_key, each_value)
        
        def __getitem__(self, key):
            if isinstance(key, int):
                return wrap_around_get(key, list(self._color_mapping.values()))
            elif isinstance(key, str):
                return self._color_mapping.get(key, None)
        
        def __repr__(self):
            return stringify(self._color_mapping)
        
        def __iter__(self):
            for each in self._color_mapping.values():
                yield each
    
# 
# print helpers
# 
if True:
    real_print = print
    def print_to_string(*args, **kwargs):
        from io import StringIO
        string_stream = StringIO()
        # dump to string
        real_print(*args, **{ "flush": True, **kwargs, "file":string_stream })
        output_str = string_stream.getvalue()
        string_stream.close()
        return output_str
        
    # 
    # print that can be indented or temporarily disabled
    # 
    
    # FIXME: if there are multiple blissful basics in play, we need to keep their indent count centralized
    #        basically print needs a setter/getter that modifies a global indent value
    def print(*args, to_string=False, disable=False, **kwargs): # print(value, ..., sep=' ', end='\n', file=sys.stdout, flush=False)
        prev_end = print.prev_end
        print.prev_end = kwargs.get('end', '\n') or ''
        
        from io import StringIO
        if to_string:
            string_stream = StringIO()
            # dump to string
            real_print(*args, **{ "flush": True, **kwargs, "file":string_stream })
            output_str = string_stream.getvalue()
            string_stream.close()
            return output_str
            
        if disable or hasattr(print, "disable") and print.disable.always:
            return
            
        if hasattr(print, "indent"):
            if print.indent.size > 0:
                import json
                indent = print.indent.string*print.indent.size
                # dump to string
                output_str = print(*args, **{ **kwargs, "to_string":True})
                end_value = kwargs.get("end", '\n')
                if len(end_value) > 0:
                    output_str = output_str[0:-len(end_value)]
                # indent any contained newlines 
                if "\n" in output_str:
                    output_str = output_str.replace("\n", "\n"+indent)
                # starting indent depending on previous ending
                if len(prev_end) > 0 and prev_end[-1] in ('\n', '\r'):
                    output_str = indent + output_str
                
                # print it
                return real_print(output_str, **{ "flush": print.flush.always, **kwargs, }) 
        
        return real_print(*args, **{ "flush": print.flush.always, **kwargs})
    print.prev_end = '\n'

    class WithNothing(object):
        def __init__(*args, **kwargs):
            pass
        
        def __enter__(self):
            return None
        
        def __exit__(self, _, error, traceback):
            if error is not None:
                return None
    with_nothing = WithNothing()

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
                return None
        
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
        
        def block(self, *args, disable=False):
            """
            Examples:
                with block("staring iterations"):
                    print("this is indented")
                
                with block("staring iterations", disable=True):
                    print("this is indented")
            """
            print(*args, disable=disable)
            if not disable:
                return print.indent
            else:
                return with_nothing
        
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

    def _print_function(create_message=None, *, disable=False):
        """
        Examples:
            @print.function()
            def some_function(arg1):
                print("this is indented, and has the name of the function above it")
            
            @print.function(disable=True)
            def some_function(arg1):
                print("this will print, but wont be intended")
            
            @print.function(disable=lambda : True)
            def some_function(arg1):
                print("this will print, but wont be intended")
            
            @print.function(lambda func, arg1: f"{func.__name__}({arg1})")
            def some_function(arg1):
                print("this is indented, and above is func name and arg")
            
            @print.function(lambda func, *args: f"{func.__name__}{args}")
            def some_function(arg1, arg2, arg3):
                print("this is indented, and above is func name and all the args")
        """
        disable_check = disable if callable(disable) else lambda : disable
        def decorator_name(function_being_wrapped):
            def wrapper(*args, **kwargs):
                disabled = disable_check()
                if disabled:
                    return function_being_wrapped(*args, **kwargs)
                else:
                    original_value = print.indent.size
                    if not create_message:
                        if hasattr(function_being_wrapped, "__name__"):
                            print(f"{function_being_wrapped.__name__}(...)")
                    else:
                        print(create_message(function_being_wrapped, *args, **kwargs))
                    print.indent.size += 1
                    output = function_being_wrapped(*args, **kwargs)
                    print.indent.size = original_value
            return wrapper

    print.function = _print_function    
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
# serialization
# 
# 
if True:
    # 
    # bits
    # 
    if True:
        def bytes_to_binary(value, separator=""):
            return separator.join([f'{each:0<8b}' for each in value])
        
        def get_bit(n, bit):
            return (n >> bit) & 1

        def set_bit(n, bit, value=1):
            if value:
                return n | (1 << bit)
            else:
                return ~(~n | (1 << bit))

        seven = 7
        eight = 8
        def seven_to_eight_bits(seven_bytes):
            seven_bytes = bytearray(seven_bytes)
            new_bytes = bytearray(eight)
            for index, each in enumerate(seven_bytes):
                new_bytes[index] = set_bit(each, eight - 1, 0)
                if get_bit(each, eight - 1):
                    new_bytes[eight - 1] = set_bit(new_bytes[eight - 1], index)
            return bytes(new_bytes)

        def eight_to_seven_bits(eight_bytes):
            eight_bytes = bytearray(eight_bytes)
            seven_bytes = eight_bytes[:seven]
            final_byte = eight_bytes[seven]
            new_bytes = bytearray(seven)
            for index, each in enumerate(seven_bytes):
                new_bytes[index] = each
                if get_bit(final_byte, index):
                    new_bytes[index] = set_bit(new_bytes[index], seven)
            return bytes(new_bytes)

        def bytes_to_valid_string(the_bytes):
            the_bytes = bytearray(the_bytes)
            number_of_blocks = (len(the_bytes) + seven - 1) // seven
            buffer_size = (number_of_blocks * eight) + 1
            buffer = bytearray(buffer_size)
            last_slice = []
            for index in range(number_of_blocks):
                last_slice = the_bytes[index * seven:(index + 1) * seven]
                new_bytes = seven_to_eight_bits(
                    last_slice
                )
                offset = -1
                for byte in new_bytes:
                    offset += 1
                    buffer[(index * eight) + offset] = byte
            
            buffer[-1] = seven - len(last_slice)
            return buffer.decode(encoding='utf-8')

        def valid_string_to_bytes(string):
            ascii_numbers = bytearray(bytes(string, 'utf-8'))
            
            chunks_of_eight = ascii_numbers[:-1]
            slice_end = -ascii_numbers[-1]
            
            number_of_blocks = (len(chunks_of_eight) + eight - 1) // eight
            output = bytes()
            for index in range(number_of_blocks):
                output += eight_to_seven_bits(
                    chunks_of_eight[index * eight:(index + 1) * eight]
                )
            
            if slice_end == 0:
                slice_end = len(output)
            
            return output[:slice_end]

    # 
    # python pickle
    # 
    if True:
        def to_pickle_bytes(variable):
            """
            ~4Gb max value
            """
            import pickle
            bytes_out = pickle.dumps(variable, protocol=4)
            max_bytes = 2**31 - 1
            FS.clear_a_path_for(file_path, overwrite=True)
            with open(file_path, 'wb') as f_out:
                for idx in range(0, len(bytes_out), max_bytes):
                    f_out.write(bytes_out[idx:idx+max_bytes])
        
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
            import pickle
            bytes_out = pickle.dumps(variable, protocol=4)
            max_bytes = 2**31 - 1
            FS.clear_a_path_for(file_path, overwrite=True)
            with open(file_path, 'wb') as f_out:
                for idx in range(0, len(bytes_out), max_bytes):
                    f_out.write(bytes_out[idx:idx+max_bytes])
    
    # 
    # json
    # 
    if True: 
        import json

        # fallback method
        json.fallback_table[lambda obj: True ] = lambda obj: to_pure(obj)

        # 
        # pandas
        # 
        try:
            import pandas as pd
            json.fallback_table[lambda obj: isinstance(obj, pd.DataFrame)] = lambda obj: json.loads(obj.to_json())
        except:
            pass
        
        class Json:
            @staticmethod
            def read(path):
                with open(path, 'r') as in_file:
                    return json.load(in_file)
            
            @staticmethod
            def write(data, path):
                with open(path, 'w') as outfile:
                    json.dump(data, outfile)
    # 
    # csv
    # 
    class Csv:
        @staticmethod
        def detect_delimiter(path=None,*, string=None, line_view=10, possible_splitters=",\t|;~^.= -"):
            def using_line_iterator(line_iterator):
                splitter_is_in_line_views = {
                    each: True
                        for each in possible_splitters
                }
                for index, each_line in enumerate(line_iterator):
                    if index > line_view:
                        break
                    for each_key, each_value in splitter_is_in_line_views.items():
                        splitters[each_key] = splitters[each_key] and each_key in each_line
                
                for each_splitter_char, was_present in splitter_is_in_line_views.items():
                    if was_present:
                        return each_splitter_char
                
                return ","
            
            if path != None:
                with open(path,'r') as f:
                    return using_line_iterator(f)
            if string != None:
                return using_line_iterator(string.split("\n"))
            
            raise Exception(f'''When calling Csv.detect_delimiter, there either needs to be a path argument or a string argument, but I received neither''')
            
        # reads .csv, .tsv, etc 
        @staticmethod
        def read(path=None, *, string=None, separator=",", first_row_is_column_names=False, column_names=None, skip_empty_lines=True, comment_symbol=None):
            """
                Examples:
                    comments, column_names, rows = csv.read("something/file.csv", first_row_is_column_names=True, comment_symbol="#")
                    comments, _empty_list, rows = csv.read("something/file.csv", first_row_is_column_names=False)
                    comments, column_names_from_file, rows = csv.read(
                        "something/file.csv",
                        column_names=["column1_new_name"],
                        first_row_is_column_names=True,
                    )
                Summary:
                    Reads in CSV's
                    - Converts numbers, null, booleans, etc into those types in accordance with JSON
                    (e.g. null=>None, true=>True, 2.3e31=>float, "hi\n"=>str('hi\n'))
                    - Anything that is not json-parsable is kept as a string
                    - Comments can be enabled by with the comment_symbol arg
                    - Comments must start as the first character of a line, no trailing comments
                    - Blank spaces (e.g. ,,, ) are converted to None (e.g. ,null,null,)
                    - Read() will sill parse even if some lines are missing columns
                Returns:
                    value: tuple(comments, column_names, rows)
                    rows:
                        - Always returns a list
                        - Each element is a named list
                        - Named lists inherit from lists (full backwards compatibility)
                        - Named lists may also be accessed using column_names
                        for example: rows[0]["column1"] and rows[0].column1 are both valid
                    column_names:
                        - Will always return an empty list when first_row_is_column_names=False
                        - Will always be the column names according to the file (even if overridden)
                        - Every element in the list will be a string
                    comments:
                        - A list of strings
                        - One string per line
                        - The comment_symbol itself is removed from the string
                    
                Arguments:
                    path:
                        - Any string path or path-object
                        - Will throw error if file does not exist
                    first_row_is_column_names:
                        - Boolean, default is False
                        - If true all elements in the first row will be parsed as strings (even if they look like numbers/null)
                        - Not all columns need a name
                        - However using the same name twice or more will cause problems
                    column_names:
                        - Optional, a list of strings
                        - Will override the column_names within the file if provided
                        - Doesn't need to cover all columns (trailing columns can be unnamed)
                    skip_empty_lines:
                        - Boolean, default is True
                        - A line with spaces or tabs will still qualify as empty
                    
            """
            import json
            
            comments     = []
            rows         = []
            file_column_names = []
            is_first_data_row = True
            
            def handle_line(each_line):
                nonlocal comments, rows, file_column_names, is_first_data_row
                # remove all weird whitespace as a precaution
                each_line = each_line.replace("\r", "").replace("\n", "")
                
                # 
                # comments
                # 
                if comment_symbol:
                    if each_line.startswith(comment_symbol):
                        comments.append(each_line[len(comment_symbol):])
                        return
                
                # 
                # empty lines
                # 
                if skip_empty_lines and len(each_line.strip()) == 0:
                    return
                
                # 
                # cell data
                #
                cells = each_line.split(separator)
                cells_with_types = []
                skip_to = 0
                for index, each_cell in enumerate(cells):
                    # apply any "skip_to" (which would be set by a previous loop)
                    if index < skip_to:
                        continue
                    
                    stripped = each_cell.strip()
                    if len(stripped) == 0:
                        cells_with_types.append(None)
                    else:
                        first_char = stripped[0]
                        if not (first_char == '"' or first_char == '[' or first_char == '{'):
                            # this converts scientific notation to floats, ints with whitespace to ints, null to None, etc
                            try: cells_with_types.append(json.loads(stripped))
                            # if its not valid JSON, just treat it as a string
                            except Exception as error:
                                cells_with_types.append(stripped)
                        else: # if first_char == '"' or first_char == '[' or first_char == '{'
                            # this gets complicated because strings/objects/lists could contain an escaped separator
                            remaining_end_indicies = reversed(list(range(index, len(cells))))
                            skip_to = 0
                            for each_remaining_end_index in remaining_end_indicies:
                                try:
                                    cells_with_types.append(
                                        json.loads(separator.join(cells[index:each_remaining_end_index]))
                                    )
                                    skip_to = each_remaining_end_index
                                    break
                                except Exception as error:
                                    pass
                            # continue the outer loop
                            if skip_to != 0:
                                continue
                            else:
                                # if all fail, go with the default of the shortest cell as a string
                                cells_with_types.append(each_cell)
                
                # 
                # file_column_names
                # 
                if is_first_data_row:
                    is_first_data_row = False
                    if first_row_is_column_names:
                        file_column_names = [ str(each) for each in cells_with_types ]
                        return
                
                rows.append(cells_with_types)
            
            if path:
                with open(path,'r') as file:
                    for each_line in file.readlines():
                        handle_line(each_line)
            elif string: 
                for each_line in string.splitlines():
                    handle_line(each_line)
            
            # if file_column_names
            if first_row_is_column_names or column_names:
                RowItem = create_named_list_class(column_names or file_column_names)
                # tranform each into a named list (backwards compatible with regular list)
                rows = [ RowItem(each_row) for each_row in rows ]
            
            return comments, file_column_names, rows

        @staticmethod
        def write(path=None, *, rows=tuple(), column_names=tuple(), separator=",", eol="\n", comment_symbol=None, comments=tuple()):
            import json
            import sys
            assert comment_symbol or len(comments) == 0, "Comments were provided,"
            def contains_comment_symbol(string):
                if not comment_symbol:
                    return False
                else:
                    return comment_symbol in string
            
            def element_to_string(element):
                # strings are checked for separators, if no separators or whitespace, then unquoted
                if isinstance(element, str):
                    if not (
                        contains_comment_symbol(element) or
                        len(element.strip()) != len(element) or
                        separator in element or
                        eol in element or
                        '\n' in element or
                        '\r' in element or 
                        element.startswith("{") or # because of JSON objects
                        element.startswith("[")    # because of JSON objects
                    ):
                        # no need for quoting
                        return element
                # all other values are stored in json format
                try:
                    return json.dumps(element)
                except Exception as error:
                    return f"{element}"
            
            def break_up_comments(comments):
                for each in comments:
                    yield from f"{each}".replace("\r", "").split("\n")
            
            the_file = sys.stdout if not path else open(path, 'w+')
            def close_file():
                if the_file != sys.stdout and the_file != sys.stderr:
                    try: the_file.close()
                    except: pass
            try:
                # 
                # comments
                # 
                the_file.write(
                    eol.join([ f"{comment_symbol}{each}" for each in break_up_comments(comments) ])
                )
                if len(comments) > 0:
                    the_file.write(eol)
                
                # 
                # column_names
                # 
                if len(column_names) > 0:
                    the_file.write(
                        separator.join(tuple(
                            element_to_string(str(each)) for each in column_names 
                        ))+eol
                    )
                
                # 
                # rows
                # 
                for each_row in rows:
                    if isinstance(each_row, str):
                        the_file.write(each_row+eol)
                    else:
                        row_string_escaped = tuple(
                            element_to_string(each_cell)
                                for each_cell in each_row 
                        )
                        line = separator.join(row_string_escaped)+eol
                        the_file.write(
                            separator.join(row_string_escaped)+eol
                        )
            except Exception as error:
                # make sure to close the file
                close_file()
                raise error
            
            close_file()
    

# 
# 
# value conversion
# 
#
if True: 
    def to_numpy(value):
        import numpy
        
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

# 
# 
# Console
# 
# 
@singleton
class Console:
    
    @singleton
    class foreground:
        black          = 30
        red            = 31
        green          = 32
        yellow         = 33
        blue           = 34
        magenta        = 35
        cyan           = 36
        white          = 37
        bright_black   = 90
        bright_red     = 91
        bright_green   = 92
        bright_yellow  = 93
        bright_blue    = 94
        bright_magenta = 95
        bright_cyan    = 96
        bright_white   = 97
    
    @singleton
    class background:
        black          = 40
        red            = 41
        green          = 42
        yellow         = 43
        blue           = 44
        magenta        = 45
        cyan           = 46
        white          = 47
        bright_black   = 100
        bright_red     = 101
        bright_green   = 102
        bright_yellow  = 103
        bright_blue    = 104
        bright_magenta = 105
        bright_cyan    = 106
        bright_white   = 107
    
    def color(self, string, foreground=None, background=None, bold=False, dim=False):
        import sys
        # if outputing to a file, dont color anything
        if not sys.stdout.isatty():
            return string
        
        # TODO: detect windows/WSL and disable colors (because powershell and CMD are problematic)
        
        if foreground:
            foreground_number = getattr(Console.foreground, foreground, None)
        if background:
            background_number = getattr(Console.background, background, None)
        
        if foreground and foreground_number == None:
            raise Exception(f"couldn't find foreground color {foreground}\nAvailable colors are: {attributes(Console.foreground)}")
        if background and background_number == None:
            raise Exception(f"couldn't find background color {background}\nAvailable colors are: {attributes(Console.background)}")
        
        code = ""
        if foreground:
            code = code + f"\u001b[{foreground_number}m"
        if background:
            code = code + f"\u001b[{background_number}m"
        if bold:
            code = code + f"\u001b[{1}m"
        if dim:
            code = code + f"\u001b[{2}m"
            
        reset_code = f"\u001b[0m"
        return code+str(string)+reset_code
    
    def clear(self,):
        print(chr(27) + "[2J")      # erase everything
        print(chr(27) + "[1;1f")    # reset cursor position
    
    def run(self, *args, timeout_sec=None):
        """
            Example:
                stdout, stderr, exit_code = Console.run("echo", "hello", timeout_sec=30)
        """
        from subprocess import Popen, PIPE
        from threading import Timer
        
        proc = Popen(list(args), stdout=PIPE, stderr=PIPE)
        timer = None
        if timeout_sec:
            timer = Timer(timeout_sec, proc.kill)
        try:
            if timer:
                timer.start()
            stdout, stderr = proc.communicate()
            stdout = stdout.decode('utf-8')[0:-1]
            stderr = stderr.decode('utf-8')[0:-1]
            return stdout, stderr, proc.returncode
        finally:
            if timer:
                timer.cancel()
        return None, None, None

    
    class output_redirected_to:
        def __init__(self, file=None, filepath=None):
            import sys
            
            self.filepath = filepath
            
            if self.filepath:
                FS.ensure_is_folder(FS.dirname(self.filepath))
                self.file = open(self.filepath, "w")
            else:
                self.file = file
                
            self.real_stdout = sys.stdout
            self.real_stderr = sys.stderr
        
        def __enter__(self):
            import sys
            sys.stdout = self.file
            sys.stderr = self.file
            return self
        
        def __exit__(self, _, error, traceback):
            import sys
            if error is not None:
                import traceback
                traceback.print_exc()
            
            sys.stdout = self.real_stdout
            sys.stderr = self.real_stderr
            if self.filepath:
                self.file.close()
# 
# threading
# 
if True:
    import threading
    
    # 
    # thread helper
    # 
    _threads = []
    @atexit.register
    def _thread_exit_handler():
        for index,each in enumerate(_threads):
            if hasattr(each, 'stop'):
                try:
                    each.stop()
                except Exception as error:
                    pass
        for index,each in enumerate(_threads):
            each.join()

    # killable threads
    class Thread(threading.Thread):
        threads = _threads
        on_exit = _thread_exit_handler
        def __init__(self, *args, **kwargs):
            if len(kwargs)==0 and len(args)==1 and callable(args[0]):
                threading.Thread.__init__(self, target=args[0])
            else:
                threading.Thread.__init__(self, *args, **kwargs)
            self.name = getattr(kwargs.get("target", {}), '__name__', None)
            _threads.append(self)
        
        def _bootstrap(self, stop_thread=False):
            def stop():
                nonlocal stop_thread
                stop_thread = True
            self.stop = stop

            def tracer(*_):
                if stop_thread:
                    raise KeyboardInterrupt()
                return tracer
            sys.settrace(tracer)
            super()._bootstrap()
    
    def run_main_hooks_if_needed(name):
        """
        Summary:
            call this function `run_main_hooks_if_needed(__name__)` at the bottom
            of all files in a project to allow main hooks to be run from anywhere
        """
        if name == '__main__':
            for each in globals().get("__main_callbacks__", []):
                each()
    
    def run_in_main(function_being_wrapped):
        """
        Summary:
            use this in a module to ensure that some section of code
            gets run inside the main module. Requires the main module to call
            `run_main_hooks_if_needed(__name__)`
        Example:
            @run_in_main
            def _():
                manager = Manager()
                shared_thread_data = manager.dict()
        """
        global_vars = globals()
        global_vars.setdefault("__main_callbacks__", [])
        global_vars["__main_callbacks__"].append(function_being_wrapped)
        def wrapper(*args, **kwargs):
            modify_args_somehow
            output = function_being_wrapped(*args, **kwargs)
            modify_output_somehow
            return output
        return wrapper

@atexit.register
def _():
    dev_null.close()