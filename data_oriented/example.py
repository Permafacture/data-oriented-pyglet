'''

Hard coded example of the following Entity_class_id table:
 
  entity_class_id, vertices, tex_coords, poly_coords, animated, positions, velocity
 
          110000,      1,         1,          0,        0,         0,        0
          111100,      1,         1,          1,        1,         0,        0
          111110,      1,         1,          1,        1,         1,        0
          111111,      1,         1,          1,        1,         1,        1
          111011,      1,         1,          1,        0,         1,        1
          111010,      1,         1,          1,        0,         1,        0

'''
from global_allocator import GlobalAllocator, Index
from components import DefraggingArrayComponent as Component

dtype_tuple = namedtuple('Dtype',('np','gl'))
vert_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)
tex_dtype = dtype_tuple(np.float32,gl.GL_FLOAT)

counter_type = np.type(('max_val',np.int32), ...

allocator = GlobalAllocator((Component('vertices',   (3,),vert_dtype.np),
                             Component('tex_coords', (3,),tex_dtype.np),
                             Component('poly_coords',(2,),vert_dtype.np),
                             Component('animated',   (1,),vert_dtype.np),
                             Component('position',   (2,),vert_dtype.np),
                             Component('velocity',   (2,),vert_dtype.np)),
                             allocation_scheme = (
                                                  (1,1,0,0,0,0), 
                                                  (1,1,1,1,0,0), 
                                                  (1,1,1,1,1,0), 
                                                  (1,1,1,1,1,1),
                                                  (1,1,1,0,1,1), 
                                                  (1,1,1,0,1,0), 
                                                 )
                           )

@Entity('vertices','tex_coords')
class Background(object):

    def add(center,width,height,sprite_index):
        result = {'vertices'  : wind_verts(rect_verts(center,width,height)),
                  'tex_coords': wind_verts(tex_coords_from_index(sprite_index))
                 }
        return result


System = allocator.register_system
@System('animated',call_interval=.01)
def inc_animation_counter(**kwargs):
        counter = kwargs['counter']
        accumulator = counter['accumulator']  #fancy dtype
        interval    = counter['interval']   
        max_value   = counter['max_value']  
        min_value   = counter['min_value']  

        accumulator += interval

        underflow = accumulator < min_value #must not be <= 
        accumulator[underflow] =  max_value[underflow]

        overflow = accumulator > max_value  #must be >, not >=
        accumulator[overflow] =  min_value[overflow]
    

@System('position','velocity')
def update_position(**kwargs):
    kwargs['position'] += kwargs['velocity']

@System('vertices','poly_coords','position',index = Broadcaster('position','poly_coords'))
def translate_to_render(vertices, poly_coords,position,index): #can this be done without **kwargs?
    vertices[:] = poly_coords  #reuse array rather than create temp
    vertices += position[index] 

@System('vertices','tex_coords')
def draw(vertices,tex_coords,texture=texture):  #without **kwargs?
      v_dtype = vert_dtype
      t_dtype = tex_dtype

      #set state
      gl.glClearColor(0.2, 0.4, 0.5, 1.0)
      gl.glEnable(texture.target)
      gl.glBindTexture(texture.target, texture.id)
      gl.glPushAttrib(gl.GL_COLOR_BUFFER_BIT)
      gl.glEnable (gl.GL_BLEND)                                                            
      gl.glBlendFunc (gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)                             
      gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
      gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)

      n=len(vertices) #because of numpy, this is the number of (x,y,z) vertices
      gl.glVertexPointer(3, v_dtype.gl, 0, vertsices.ctypes.data)
      gl.glTexCoordPointer(3, t_dtype.gl, 0, tex_coords.ctypes.data)
      gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, n)

      #unset state
      gl.glPopAttrib()
      gl.glDisable(texture.target)


