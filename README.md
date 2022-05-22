# What is this?

The tools I find myself copying and pasting between every python project.

# How do I use this?

`pip install blissful_basics`


```python
from blissful_basics import print, flatten, to_pure, stringify, stats, product, countdown, large_pickle_save, large_pickle_load, FS, Object

# how you'd expect it
with print.indent:
    print("howdy1")
    with print.indent:
        print("howdy2")
    print("howdy3")

# recursively indent's function calls
@print.indent.function 
def my_func():
    print("this will be indented")

import numpy
import torch

to_pure(numpy.array([1,2,3,4,5]))   # [1,2,3,4,5]
to_pure(torch.tensor([1,2,3,4,5]))  # [1,2,3,4,5] # even if its on a GPU device

stats([1,2,3,4,5])
# Object(
#     max = 5,
#     min = 1,
#     range = 4,
#     count = 5,
#     sum = 15,
#     average = 3.0,
#     stdev = 1.5811388300841898,
#     median = 3,
#     q1 = 1.5,
#     q3 = 4.5,
#     normalized = (0.0, 0.25, 0.5, 0.75, 1.0),
# )

a = Object(thing=10)
a.thing # 10
a.thing = 99
a.thing # 99
```
