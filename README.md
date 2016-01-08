Tests towards using data oriented programming with pyglet and numpy.

This project was inspired by lack luster performance of rotating a bunch of
polygons in tests towards a game engine.  The concept was inspired by:
  http://gamesfromwithin.com/data-oriented-design

Some thoughts and questions:

  * What is a better name for this project?
  * what is a better name for "arrayed" and "single" properties?
  * Should it be as easy for users to access arrayed properties through
      the data accessor as single properties?  Are arrayed properties just
      data domain implementation details while the data accessor mostly
      communicates single valued properties? 
  * Seems like composing Data Domains into complex Data Accessors would
      be important for an entity-component like system.  How to do this?

Some TODOs:

  * Selectors will likely be a big deal.  Provide clean functionality for them
  * Single properties shouldn't be lists turned into array just in time
