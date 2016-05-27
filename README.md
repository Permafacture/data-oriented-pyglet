Numpy-ECS
====================

Data oriented programming with numpy through an Entity-Component-System model.

This project was inspired by lack luster performance of rotating a bunch of
polygons in tests towards a game engine.  The concept was inspired by:
  http://gamesfromwithin.com/data-oriented-design

Further information on Data Oriented Design:
  http://www.dataorienteddesign.com/dodmain/dodmain.html 

Details
=======

The Allocator is the user's interface with Components, Entities and Systems.

Components are numpy arrays of the attributes that will make up Entities. 
They have a shape and a datatype and once given to the Allocator, they are 
abstracted away. ie, an RGB color Component might be:

    colors = Component('color', (3,), np.float32)

Entities are "instances" defined through composition of Components.
Each instance is actually just an integer (guid) that the Allocator can
use to look up the instance's slice of the Components.  Thus Entities are 
constructed by allocating values to some subset of Components in the Allocator.
ie, instead of having a class with an `__init__` functions, instances are 
created by calling `allocator.add` with some component values defined:

    def add_regular_polygon(n_sides,radius,pos,velocity,
                              color=(.5,.5,.5),allocator=allocator):
        pts = polyOfN(n_sides,radius)
        poly_verts = wind_vertices(pts)
        pos = position
        polygon = {
          'render_verts': [(x+pos[0],y+pos[1],pos[2]) for x,y in poly_verts],
          'color'       : [color]*len(poly_verts),
          'position'    : pos, 
          'velocity'    : velocity,
          }
        guid = allocator.add(polygon)
        return guid

The allocator groups all the entity instances that are composed of the same 
Components into "entity classes" so their attributes can be accessed as 
continuous slices.

Systems are functions that operate on the Components entity classes.  
These can be implemented through Numpy ufuncs, cython, or 
numba.vectorize. Thus, Systems can be fast and CPU multithreaded without 
multiprocessing. To apply velocity to every entity that has a velocity:

    def apply_velocity(velocities,positions,dt=1./600): 
        positions *= velocities*dt

And a System to render everything that has verts and colors:

    def update_display(render_verts,colors):
        gl.glClearColor(0.2, 0.4, 0.5, 1.0)
        gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
        gl.glEnable (gl.GL_BLEND)                                                            
        gl.glEnable (gl.GL_LINE_SMOOTH);                                                     
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)

        n = len(render_verts[:])
        #TODO verts._buffer.ctypes.data is awkward
        gl.glVertexPointer(3, vert_dtype.gl, 0, render_verts[:].ctypes.data)
        gl.glColorPointer(3,  color_dtype.gl, 0, colors[:].ctypes.data)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)

And without any convinience functions, this can be called with the appropriate 
sections of the `render_verts` and `color` numpy arrays by doing:

    get_sections = allocator.selectors_from_component_query
    draw =('render_verts','color')
    sections = get_sections(draw)
    update_display(*(sections[name] for name in draw))

Performance
===========

The difference between `examples/first.py` and `examples/polygons.py` increases
with number of polygons drawn.  On my Celeron 2 CPU laptop I get 250 vs 500 
FPS with 150 polygons, and 30 vs 150 FPS with 1000 polygons.

In a more complete game example with pymunk running 2D physics, the original
version ran at 50 FPS and the Numpy-ECS version at 150 FPS.  Having pyglet 
treat positions and angles as write-only arrays, and rendering treat them as 
read-only, the components were created in shared memory and multiprocessing was
used to run the physics and rendering as seperate processes.  The shared  
memory made up most of the inter process communication (IPC).  The result was 
180 FPS for the physics and 600 FPS for the rendering.

examples: https://vimeo.com/65989831 https://vimeo.com/66736654

History
=======

The examples directory shows the evolution of this concept:

first.py shows my best attempt at using pure python, OOP, and pyglet batches. 
Rotation of the polygons consumes 90% of the run time.

compare.py shows that using numpy on an array has some overhead, but that
the size of the array has much less of an effect on execution time than
with python lists.  There is a break even point in the length of data to
be processed. Below this, list comprehensions are faster. Above this,
numpy quickly surpasses pure Python.

second.py shows that by batching all of the rotation math into one array,
there are substantial performance benefits.  But it becomes cumbersome 
to interact with instances of the polygons once they are all thrown 
together.

polygons.py implements this same example through the ECS.  The overhead
from the higher level interface compared to `second.py` is negligable. 

