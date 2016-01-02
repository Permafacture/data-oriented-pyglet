'''
quick test to compare numpy math vs list comprehensions as a function
of size of data.
'''
import numpy as np
from math import pi, sin, cos,atan2,sqrt
import time

def gen_initiald(n):

    pts = np.random.random((n,2)).astype(np.float32)
    list_data = [(pt[0],pt[1],sqrt(pt[0]**2+pt[1]**2),cos(atan2(pt[1],pt[0])),sin(atan2(pt[1],pt[0]))) for pt in pts]
    array_data = np.array(list_data)
    return list_data, array_data

def list_rotate(initiald):
    px, py = (10,10)
    cost, sint = cos(.5), sin(.5)
    #here's a mouthfull.  see contruction of initial_data in init.  sum-difference folrmula applied 
    #and simplified.  work it out on paper if you don't believe me.
    pts = [(px+x+r*(xhelper*(cost-1)-sint*yhelper),py+y+r*(yhelper*(cost-1)+sint*xhelper)) for x,y,r,xhelper,yhelper in initiald]
    #flatten and return as a tuple for vertbuffer
    return tuple(map(int,[val for subl in pts for val in subl]))

def array_rotate(initiald):
    px, py = (0,0)
    cost, sint = cos(.5), sin(.5)
    xs, ys, rs, xhelpers, yhelpers = (initiald[:,x] for x in range(5))
   
    pts = np.empty((len(xs),2),dtype=np.float32)

    pts[:,0] = xhelpers*(cost-1)  
    pts[:,1] = yhelpers*sint      
    pts[:,0] -= pts[:,1]                 
    pts[:,0] *= rs                
    pts[:,0] += xs                
    pts[:,0] += px                

    pts[:,1] = yhelpers*(cost-1)
    tmp = xhelpers*sint
    pts[:,1] += tmp
    pts[:,1] *= rs
    pts[:,1] += ys
    pts[:,1] += py

    #flatten and return as a tuple for vertbuffer
    #return tuple(map(int,[val for subl in pts for val in subl]))
    pts.shape = ( reduce(lambda xx,yy: xx*yy, pts.shape), )
    return pts.astype(np.int32)

for n in [5,10,25,50,100,500,1000]:
  lst,arr = gen_initiald(n)
  
  start = time.time()
  trash = list_rotate(lst)
  end = time.time()
  print "did list of %s in %s" % (n, end-start)

  start = time.time()
  trash = array_rotate(arr)
  end = time.time()
  print "did array of %s in %s" % (n, end-start)

  print "\n"
