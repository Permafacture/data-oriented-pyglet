Data Oriented Python
====================

Tests towards using data oriented programming with pyglet and numpy.

This project was inspired by lack luster performance of rotating a bunch of
polygons in tests towards a game engine.  The concept was inspired by:
  http://gamesfromwithin.com/data-oriented-design

Further information on Data Oriented Design:
  http://www.dataorienteddesign.com/dodmain/dodmain.html 

The examples directory shows the evolution of this concept:

first.py shows my best attempt at using pure python, OOP, and pyglet batches.
On my very modest laptop, it gets ~250 frames per second, with rotation
of the polygons consuming 90% of the run time.

second.py was an attempt to use numpy to make the rotation implementation
faster.  In actuality, it performs worse...

compare.py shows that using numpy on an array has some overhead, but that
the size of the array has much less of an effect on execution time than
with python lists.  There is a break even point in the length of data to
be processed. Below this, list comprehensions are faster. Above this,
numpy quickly surpasses pure Python.

third.py shows that by batching all of the rotation math into one array,
there are substantial performance benefits.  But it becomes cumbersome 
to interact with instances of the polygons once they are all thrown 
together.

data-oriented.py uses the data oriented ORM (what's a better name than 
ORM here?) that this project aims to elaborate to maintain the batched
performance of large contiguous sections of memory operated on at C
speeds, while also giving an object oriented interface for creating
and interacting with instances, perhaps even composing data domians
into Entities (ie: an entity-component system)

Performance
===========

first.py was my best attempt at an optimized algorithm in pure python.
It runs at 250 fps on my machine.  With Pypy, after JIT warmup, it runs
at 500 fps.  data-oriented.py runs at ~650 fps, and there is room for
further improvement using Cython or Numba's `vectorize` decorator.

Some thoughts and questions:

  * What is a better name for this project?
  * what is a better name for "arrayed" and "single" properties?
  * Should it be as easy for users to access arrayed properties through
      the data accessor as single properties?  Are arrayed properties just
      data domain implementation details while the data accessor mostly
      communicates single valued properties? 
  * Seems like composing Data Domains into complex Data Accessors would
      be important for an entity-component like system.  How to do this?
  * Composition should be favored over inheritance: decorate classes to 
      make them Entities spanning multiple data domains rather than 
      having a family tree of data domains.

Some TODOs:

  * Selectors will be important (layred slices and masks). 
      Provide clean functionality for them.
  * Single properties shouldn't be lists turned into array just in time
