try:
    import json_fix
except Exception as error:
    pass

def indent(string, by):
    indent_string = (" "*by)
    return indent_string + string.replace("\n", "\n"+indent_string)

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

class MapKeys:
    class SecretKey: pass

    class Keys(SecretKey): pass
    class Values(SecretKey): pass
    class Merge(SecretKey): pass
    class Dict(SecretKey): pass
    class Default(SecretKey):
        def __init__(self, func):
            self.func = func
    
    class AutoGenerated(SecretKey): pass
    class Untouched(SecretKey): pass
    class ParentCallbacks(SecretKey): pass
    class UninitilizedChildren(SecretKey): pass
    
    def __call__(self, *args, **kwargs):
        return MapCls(*args, **kwargs)

class Map:
    def __init__(self, *args, **kwargs):
        super(MapCls, self).__init__()
        first_arg = args[0] if len(args) > 0 else None
        secrets = args[1] if first_arg == MapKeys.SecretKey and len(args) > 1 else {}
        secrets[MapKeys.Untouched] = len(kwargs) == 0
        secrets[MapKeys.UninitilizedChildren] = {}
        secrets[MapKeys.Default] = lambda key, *args: MapCls(MapKeys.SecretKey, {MapKeys.AutoGenerated:True, MapKeys.ParentCallbacks: [ (self, key) ], })
        if isinstance(first_arg, MapKeys.Default):
            secrets[MapKeys.Default] = first_arg.func
        super().__setattr__("d", ({}, secrets))
        data, secrets = super().__getattribute__("d")
        data.update(kwargs)
        if isinstance(first_arg, dict):
            data.update(first_arg)
        elif isinstance(first_arg, MapCls):
            data.update(first_arg[MapKeys.Dict])
        
    
    # this is "more powerful" than __getattr__
    def __getattribute__(self, attribute):
        data, secrets = super().__getattribute__("d")
        if attribute == '__dict__':
            return data
        # if its not like __this__ then use the dict directly
        elif len(attribute) < 5 or not (attribute[0:2] == '__' and attribute[-2:len(attribute)] == "__"):
            return self[attribute]
        else:
            return object.__getattribute__(self, attribute)
    
    def __setattr__(self, key, value):
        data, secrets = super().__getattribute__("d")
        if secrets[MapKeys.Untouched] and MapKeys.ParentCallbacks in secrets:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = self
                del each_parent[MapKeys.UninitilizedChildren][each_key]
                each_parent[MapKeys.SecretKey][MapKeys.Untouched] = False
        secrets[MapKeys.Untouched] = False
        data[key] = value
    
    def __setitem__(self, key, value):
        # FUTURE: have key be super-hashed, use ID's for anything that can't be yaml-serialized
        #         difficulty of implementation will be doing that^ without screwing up .keys()
        data, secrets = super().__getattribute__("d")
        if secrets[MapKeys.Untouched] and MapKeys.ParentCallbacks in secrets:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = self
                del each_parent[MapKeys.UninitilizedChildren][each_key]
                each_parent[MapKeys.SecretKey][MapKeys.Untouched] = False
        secrets[MapKeys.Untouched] = False
        data[key] = value
    
    def __getattr__(self, key):
        data, secrets = super().__getattribute__("d")
        if key in data:
            return data[key]
        else:
            if key not in secrets[MapKeys.UninitilizedChildren]:
                secrets[MapKeys.UninitilizedChildren][key] = secrets[MapKeys.Default](key)
            return secrets[MapKeys.UninitilizedChildren][key]
    
    def __getitem__(self, key):
        data, secrets = super().__getattribute__("d")
        if key == MapKeys.Keys:
            return list(data.keys())
        if key == MapKeys.Values:
            return list(data.values())
        if key == MapKeys.Dict:
            return data
        if key == MapKeys.Merge:
            return lambda *args: [ data.update(each) for each in args ] and self
        if key in MapKeys.SecretKey.__subclasses__():
            return secrets[key]
        if key == MapKeys.SecretKey:
            return secrets
        if key in data:
            return data[key]
        else:
            if key not in secrets[MapKeys.UninitilizedChildren]:
                secrets[MapKeys.UninitilizedChildren][key] = secrets[MapKeys.Default](key)
            return secrets[MapKeys.UninitilizedChildren][key]
    
    def __len__(self):
        data, secrets = super().__getattribute__("d")
        return len(data)
    
    def __contains__(self, key):
        data, secrets = super().__getattribute__("d")
        return key in data
    
    def __delattr__(self, key):
        data, secrets = super().__getattribute__("d")
        if key in data:
            del data[key]
        if key in secrets[MapKeys.UninitilizedChildren]:
            # detach self from the UninitilizedChild
            secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] = [
                (each_parent, each_key)
                    for each_parent, each_key in secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] 
                    if each_key != key
            ]
            del secrets[MapKeys.UninitilizedChildren][key]
    
    def __delitem__(self, key):
        data, secrets = super().__getattribute__("d")
        if key in data:
            del data[key]
        if key in secrets[MapKeys.UninitilizedChildren]:
            # detach self from the UninitilizedChild
            secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] = [
                (each_parent, each_key)
                    for each_parent, each_key in secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] 
                    if each_key != key
            ]
            del secrets[MapKeys.UninitilizedChildren][key]
        
    # the return value of if MapCls():
    def __nonzero__(self):
        data, secrets = super().__getattribute__("d")
        if secrets[MapKeys.AutoGenerated] and secrets[MapKeys.UninitilizedChildren]:
            return False
        else:
            return True
    
    def __iter__(self):
        data, secrets = super().__getattribute__("d")
        return data.items()
    
    def __reversed__(self):
        data, secrets = super().__getattribute__("d")
        return reversed(data.items())
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        data, secrets = super().__getattribute__("d")
        if len(data) == 0:
            return "{}"
        return stringify(data)
    
    def __eq__(self, other):
        data, secrets = super().__getattribute__("d")
        return data == other
    
    def __add__(self, other):
        data, secrets = super().__getattribute__("d")
        # this is what makes += work
        if secrets[MapKeys.Untouched] and secrets[MapKeys.AutoGenerated]:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = other
                return other
        else:
            if isinstance(other, dict):
                data.update(other)
                return self
            elif isinstance(other, MapCls):
                data.update(other[MapKeys.Dict])
                return self
            else:
                # TODO: should probably be an error
                pass
    
    def __json__(self):
        data, secrets = super().__getattribute__("d")
        return data

# Patch up isinstance() and type() so that Map can appear to have class-attributes without then becoming instance attributes
MapCls = Map
Map = MapKeys()
import builtins
real_isinstance = builtins.isinstance
def isinstance(value, types):
    if types == Map:
        return real_isinstance(value, MapCls)
    elif real_isinstance(types, tuple) and MapCls in types:
        return real_isinstance(value, tuple((each if each != Map else MapCls) for each in types))
    else:
        return real_isinstance(value, types)
isinstance.__doc__ = real_isinstance.__doc__
builtins.isinstance = isinstance
real_type = builtins.type
def type(*args,**kwargs):
    normal_output = real_type(*args, **kwargs)
    return normal_output if normal_output != MapCls else Map
type.__doc__ = real_type.__doc__
builtins.type = type

class LazyIterable:
    def __init__(self, iterable, length):
        self.iterable = iterable
        self.length = length
    
    def __iter__(self):
        return (each for each in self.iterable)
    
    def __len__(self):
        return self.length

class SemiLazyMap:
    def __init__(self, *args, **kwargs):
        super(SemiLazyMap, self).__init__()
        first_arg = args[0] if len(args) > 0 else None
        secrets = args[1] if first_arg == MapKeys.SecretKey and len(args) > 1 else {}
        secrets[MapKeys.Untouched] = len(kwargs) == 0
        secrets[MapKeys.UninitilizedChildren] = {}
        secrets[MapKeys.Default] = lambda key, *args: Map(MapKeys.SecretKey, {MapKeys.AutoGenerated:True, MapKeys.ParentCallbacks: [ (self, key) ], })
        if isinstance(first_arg, MapKeys.Default):
            secrets[MapKeys.Default] = first_arg.func
        super().__setattr__("d", ({}, secrets, {}))
        data, secrets, cache = super().__getattribute__("d")
        data.update(kwargs)
        if isinstance(first_arg, dict):
            data.update(first_arg)
        elif isinstance(first_arg, Map):
            data.update(first_arg[MapKeys.Dict])
        
    
    # this is "more powerful" than __getattr__
    def __getattribute__(self, attribute):
        data, secrets, cache = super().__getattribute__("d")
        output = None
        if attribute == '__dict__':
            output = data
        # if its not like __this__ then use the dict directly
        elif len(attribute) < 5 or not (attribute[0:2] == '__' and attribute[-2:len(attribute)] == "__"):
            output = self[attribute]
        else:
            output = object.__getattribute__(self, attribute)
            
        return output
    
    def __setattr__(self, key, value):
        data, secrets, cache = super().__getattribute__("d")
        if secrets[MapKeys.Untouched] and MapKeys.ParentCallbacks in secrets:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = self
                del each_parent[MapKeys.UninitilizedChildren][each_key]
                each_parent[MapKeys.SecretKey][MapKeys.Untouched] = False
        secrets[MapKeys.Untouched] = False
        data[key] = value
    
    def __setitem__(self, key, value):
        # FUTURE: have key be super-hashed, use ID's for anything that can't be yaml-serialized
        #         difficulty of implementation will be doing that^ without screwing up .keys()
        data, secrets, cache = super().__getattribute__("d")
        if secrets[MapKeys.Untouched] and MapKeys.ParentCallbacks in secrets:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = self
                del each_parent[MapKeys.UninitilizedChildren][each_key]
                each_parent[MapKeys.SecretKey][MapKeys.Untouched] = False
        secrets[MapKeys.Untouched] = False
        data[key] = value
    
    def __getattr__(self, key):
        data, secrets, cache = super().__getattribute__("d")
        output = None
        if key in data:
            output = data[key]
        else:
            if key not in secrets[MapKeys.UninitilizedChildren]:
                secrets[MapKeys.UninitilizedChildren][key] = secrets[MapKeys.Default](key)
            output = secrets[MapKeys.UninitilizedChildren][key]
        return output(key) if callable(output) else output
    
    def __getitem__(self, key):
        data, secrets, cache = super().__getattribute__("d")
        if key == MapKeys.Keys:
            return list(data.keys())
        if key == MapKeys.Values:
            return LazyIterable(
                iterable=(self[each] for each in data.keys()),
                length=len(self),
            )
        if key == MapKeys.Dict:
            return data
        if key == MapKeys.Merge:
            return lambda *args: [ data.update(each) for each in args ] and self
        if key in MapKeys.SecretKey.__subclasses__():
            return secrets[key]
        if key == MapKeys.SecretKey:
            return secrets
        if key in data:
            output = data[key]
            if callable(output):
                if key not in cache:
                    cache[key] = output(key)
                return cache[key]
            else:
                return output
        else:
            if key not in secrets[MapKeys.UninitilizedChildren]:
                secrets[MapKeys.UninitilizedChildren][key] = secrets[MapKeys.Default](key)
            return secrets[MapKeys.UninitilizedChildren][key]
    
    def __len__(self):
        data, secrets, cache = super().__getattribute__("d")
        return len(data)
    
    def __contains__(self, key):
        data, secrets, cache = super().__getattribute__("d")
        return key in data
    
    def __delattr__(self, key):
        data, secrets, cache = super().__getattribute__("d")
        if key in data:
            del data[key]
        if key in secrets[MapKeys.UninitilizedChildren]:
            # detach self from the UninitilizedChild
            secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] = [
                (each_parent, each_key)
                    for each_parent, each_key in secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] 
                    if each_key != key
            ]
            del secrets[MapKeys.UninitilizedChildren][key]
    
    def __delitem__(self, key):
        data, secrets, cache = super().__getattribute__("d")
        if key in data:
            del data[key]
        if key in secrets[MapKeys.UninitilizedChildren]:
            # detach self from the UninitilizedChild
            secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] = [
                (each_parent, each_key)
                    for each_parent, each_key in secrets[MapKeys.UninitilizedChildren][key][MapKeys.ParentCallbacks] 
                    if each_key != key
            ]
            del secrets[MapKeys.UninitilizedChildren][key]
        
    # the return value of if Map():
    def __nonzero__(self):
        data, secrets, cache = super().__getattribute__("d")
        if secrets[MapKeys.AutoGenerated] and secrets[MapKeys.UninitilizedChildren]:
            return False
        else:
            return True
    
    def __iter__(self):
        data, secrets, cache = super().__getattribute__("d")
        return LazyIterable(
            iterable=zip(
                data.keys(),
                (self[each] for each in data.keys()),
            ),
            length=len(self),
        )
    
    def __reversed__(self):
        data, secrets, cache = super().__getattribute__("d")
        return LazyIterable(
            iterable=zip(
                reversed(data.keys()),
                (self[each] for each in reversed(data.keys())),
            ),
            length=len(self),
        )
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        data, secrets, cache = super().__getattribute__("d")
        if len(data) == 0:
            return "{}"
        return stringify(data)
    
    def __eq__(self, other):
        data, secrets, cache = super().__getattribute__("d")
        return data == other
    
    def __add__(self, other):
        data, secrets, cache = super().__getattribute__("d")
        # this is what makes += work
        if secrets[MapKeys.Untouched] and secrets[MapKeys.AutoGenerated]:
            for each_parent, each_key in secrets[MapKeys.ParentCallbacks]:
                each_parent[each_key] = other
                return other
        else:
            if isinstance(other, dict):
                data.update(other)
                return self
            elif isinstance(other, Map):
                data.update(other[MapKeys.Dict])
                return self
            else:
                # TODO: should probably be an error
                pass
    
    def __json__(self):
        return dict(self.__iter__())

def recursive_lazy_dict(value):
    have_seen = set()
    def _inner_recursive_lazy_dict(value):
        # not perfect because there are other data structures, but its pretty useful
        if isinstance(value, (set, list, dict)):
            if id(value) in have_seen:
                return value
            else:
                have_seen.add(id(value))
                if isinstance(value, list):
                    return [ _inner_recursive_lazy_dict(each) for each in value ]
                elif isinstance(value, set):
                    return set(_inner_recursive_lazy_dict(each) for each in value)
                elif isinstance(value, dict):
                    new_dict = LazyDict()
                    for each_key, each_value in value.items():
                        new_dict[each_key] = _inner_recursive_lazy_dict(each_value)
                    return new_dict
        else:
            return value
    return _inner_recursive_lazy_dict(value)

defaulters = {}
class LazyDict(dict):
    
    def __init__(self, *args, **kwargs):
        # default vaue
        super(LazyDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
        defaulters[id(self)] = lambda key: None
    
    def __getitem__(self, key):
        # defaulter value
        defaulter = defaulters.get(id(self))
        if defaulter:
            if key not in self.__dict__:
                return defaulter(key)
        return self.__dict__.get(key)
        
    def __delitem__(self, key):
        try:
            del self.__dict__[key]
        except Exception as error:
            pass
    
    def __str__(self):
        if len(self.__dict__) == 0:
            return "{}"
        return stringify(self.__dict__)
    
    def __repr__(self):
        return self.__str__()
    
    def merge(self, other_dict=None, **kwargs):
        other_dict = other_dict or {}
        self.__dict__.update(other_dict)
        self.__dict__.update(kwargs)
        return self
    
    def update(self, other_dict):
        for each_key, each_value in other_dict.items():
            self[each_key] = each_value
        return self
    
    def setdefault(self, *args, **kwargs):
        if len(args) == 1:
            if callable(args[0]):
                defaulters[id(self)] = args[0]
            else:
                defaulters[id(self)] = lambda key: args[0]
            return self
        else:
            return super(LazyDict, self).setdefault(*args, **kwargs)
    
    def __copy__(self):
        return LazyDict(self.__dict__)
    
    def __deepcopy__(self, memo):
        from copy import deepcopy
        
        address = id(self)
        if address in memo:
            return memo[address]
        new = memo[address] = LazyDict(self.__dict__)
        for each_key, each_value in new.items():
            new[each_key] = deepcopy(each_value, memo)
        return new
