# What is this?

A pip module that let you define a `__json__` method, that works like the `toJSON` from JavaScript.<br>
(e.g. it magically gets called whenever someone does `json.dumps(your_object)`)

From a technical perspective, this module is a safe, backwards-compatible, reversable patch to the built-in python `json` object that allows classes to specify how they should be serialized.

# Why?

Because sometimes external code uses something like
```python
import json
json.dumps(list_containing_your_object)
```
And it simply throws an error no matter how you customize your object

# How do I use this for my class?

`pip install json-fix`

```python
import json_fix # import this before the JSON.dumps gets called

# same file, or different file
class YOUR_CLASS:
    def __json__(self):
        # YOUR CUSTOM CODE HERE
        #    you probably just want to do:
        #        return self.__dict__
        return "a built-in object that is natually json-able"
```

# How do I change how someone elses class is jsonified?

There's 2 ways; the aggressive `override_table` or the more collaboration-friendly `fallback_table`. Some really powerful stuff can be done safely with the fallback table.

## Override Table

If a pip module defines a class, you can control how it is json-dumped, even if they defined a `.__json__()` method, by using `json.override_table`.
- Note! The "when" (in when-a-rule-is-added) can be very important. Whatever rule was most-recently added will have the highest priority. So, even if a pip module uses the override table, you can override their override by doing `import that_module` and THEN adding your rule to the override table.
- Note 2! The override table is capable of changing how built-in types are dumped, be careful! 

```python
import json_fix # import this before the JSON.dumps gets called
import json
import pandas as pd

SomeClassYouDidntDefine = pd.DataFrame

# create a boolean function for identifying the class
class_checker = lambda obj: isinstance(obj, SomeClassYouDidntDefine)
# then assign it to a function that does the converting
json.override_table[class_checker] = lambda obj_of_that_class: json.loads(obj_of_that_class.to_json())

json.dumps([ 1, 2, SomeClassYouDidntDefine() ], indent=2) # dumps as expected
```

## Fallback Table

Let's say we want all python classes to be jsonable by default, well we can easily do that with the fallback table. The logic is `if notthing in override table, and no .__json__ method, then check the fallback table`. 

```python
import json_fix # import this before the JSON.dumps gets called
import json

# a checker for custom objects
checker = lambda obj: hasattr(obj, "__dict__")
# use the __dict__ when they don't specify a __json__ method 
json.fallback_table[checker] = lambda obj_with_dict: obj_with_dict.__dict__

class SomeClass:
    def __init__(self):
        self.thing = 10

json.dumps([ 1, 2, SomeClass() ], indent=2) # dumps as expected
```

Like the override table, the most recently-added checker will have the highest priority. 
