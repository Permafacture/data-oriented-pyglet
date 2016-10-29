'''
Allocating Entity values in contiguous Component arrays, providing Systems
with access to simple slices of components.

This file is part of Numpy-ECS.
Copyright (C) 2016 Elliot Hallmark (permafacture@gmail.com)

Numpy-ECS is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

Data Oriented Python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# Systems require slices, not index arrays or multiple slices, to access data
# in components.  Naively allocating spaces in arrays without regard for this 
# will not work. For instance:
# 
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#               01,         1,        0,         0,        0
#               02,         1,        0,         1,        0
#               03,         1,        0,         1,        1
#               04,         1,        1,         0,        0
#               05,         1,        1,         1,        0
#               06,         1,        1,         1,        1
# 
# ]
# 
# Trying to apply update_verts(positions, velocities), one cannot get a single
# slice on positions.  This table can be re-arranged to work:
# 
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#               01,         1,        0,         0,        0
#               02,         1,        0,         1,        0
#               03,         1,        0,         1,        1
#               06,         1,        1,         1,        1
#               05,         1,        1,         1,        0
#               04,         1,        1,         0,        0
# ]
# 
# Now velocities can update a single slice of positions, and postions can
# update a single slice of vertices (including those that are also animated).
#
# If the entity_class_id is a binary representation of the components it 
# requires, then given an addition of any arbitrary collection of 
# attributes, we can determine what entity_class it belongs to and add
# the values to sections of the array that maintain ideal contiguity.
#
# [
# 
#   entity_class_id, vertices, animated, positions, velocity
# 
#             1000,         1,        0,         0,        0
#             1010,         1,        0,         1,        0
#             1011,         1,        0,         1,        1
#             1111,         1,        1,         1,        1
#             1110,         1,        1,         1,        0
#             1100,         1,        1,         0,        0
# ]
#
#
from __future__ import absolute_import, division, print_function
import sys
#python version compatability
if sys.version_info < (3,0):
    from future_builtins import zip, map

import numpy as np
from .table import Table, INDEX_SEPERATOR

def verify_component_schema(allocation_schema):
    '''given an allocation schema as a list of lists, return True if the schema
    keeps all Component arrays contiguous.  Else return False'''
    started = [False] * len(allocation_schema[0])
    ended   = [False] * len(allocation_schema[0])
    for row in allocation_schema:
        for i,val in enumerate(row):
            if val: 
               if not started[i]:
                  started[i] = True
               else: 
                  if ended[i]:
                    return False
            elif started[i]:
              ended[i] = True
    return True


class GlobalAllocator(object):
    '''Decides how data is added or removed from Components, allocating and 
    deallocting Entities/guids.  Components better be allocated by only one
    of these.

    see comments at top of file for details'''

    def __init__(self,components,allocation_scheme):
        self.component_dict = {component.name:component for component in components}
        self._memoized = {} #for selectors_from_component_names 

        names = tuple(comp.name for comp in components) 
        self.names = names 
        self._allocation_table = Table(names, tuple(allocation_scheme))
 
        self._cached_adds = list()
        self._next_guid = 0
   

    @property
    def next_guid(self):
        self._next_guid += 1
        return self._next_guid

    @property
    def guids(self):
        return tuple(self._allocation_table.guids)
    #def _class_id_from_guid(guid):
    #    #assumes entity has non-zero size for every component that 
    #    #  defines it's class.  This is the definition of a class_id and is
    #    #  a result of how add works
    #    row = row_for_guid(guid)
    #    return int(''.join(x!=0 for x in row),base=2)


    #def allocation_schema_from_truth_table(self,truth_table):
    #    '''
    #    an allocation schema may be defined as a list of lists.
    #   
    #    convert that to a list of integers where (0,0,1,1) -> 3, etc'''
    #    return map(self.entity_class_from_tuple,truth_table)

    #def entity_class_from_dict(self,component_dict):
    #    '''takes a component dict like {'comp_name1':value}

    #    returns the integer that is this entity class'''
    #    names = self._allocation_table.column_names
    #    for name in component_dict.keys():
    #      assert name in names, "%s is not a known component name"% (name,)
    #    entity_tuple = tuple(0 if (component_dict.get(name,None) is None) \
    #        else 1 for name in names)
    #    return self.entity_class_from_tuple(entity_tuple)

    def add(self,values_dict,guid=None):
        component_dict = self.component_dict

        def convert_to_component_array(component,value):
            '''converts value to a numpy array with appropriate shape for 
            component'''
            value = np.array(value,dtype = component.datatype)

            shape = value.shape or (1,)
            dim = component._dim
            assert shape == dim or (len(shape)>1 and shape[1:] == dim), \
                "component '%s' expected shape %s, but got %s" % (
                component.name,component._dim,value.shape)
                #len(shape) is a look before I leap. No exceptions please
            return value

        result = {'guid': guid or self.next_guid}
        for name, value in values_dict.items():
            result[name] = convert_to_component_array(component_dict[name],value)
        assert result['guid'] not in {d['guid'] for d in self._cached_adds}, \
            "cannot add a guid twice"
        self._cached_adds.append(result)
        return result['guid']

    def delete(self,guid):
        alloc_table = self._allocation_table
        alloc_table.stage_delete(guid)

    def _defrag(self):
       alloc_table = self._allocation_table
       component_dict  = self.component_dict
       adds_dict  = self._cached_adds
       if (not adds_dict) and (None not in alloc_table.guids):
           return  #nothing to do

       #delete_set = self._cached_deletes
       def safe_len(item):
           if item is None:
               return 0
           shape = item.shape
           if len(shape) > 1:
               #TODO only supports arrays like [n] and [1,n] !!!
               #TODO Can't think of fix or what one would be expecting but I 
               #TODO must note this limitation
               return shape[0]
           else:
               return 1

       for add in self._cached_adds:
           guid = add['guid']
           add = tuple(safe_len(add.get(name,None)) \
                     for name in alloc_table.column_names)
           alloc_table.stage_add(guid,add)

       #defrag
       #print "defrag"
       for name, (new_size, sources, targets) in zip(alloc_table.column_names,alloc_table.compress()):
           #if name == 'component_1': print "working on component_1"
           component = component_dict[name]
           component.assert_capacity(new_size)
           for source,target in zip(sources,targets):
               #if name == "component_1":
               #  print "moving",component[source],"to",target
               component[target] = component[source]
 
       #apply adds
       for add in self._cached_adds:
           guid = add['guid']
           for name, this_slice in zip(alloc_table.column_names,alloc_table.slices_from_guid(guid)):
               if name in add:
                 component_dict[name][this_slice] = add[name]

       #reset
       self._cached_adds = list()
       self._memoized = dict()

    def is_valid_query(self,query,sep=INDEX_SEPERATOR):
        known_names = self.names
        for x in query:
            if (sep not in x) and (x not in known_names):
                print(x, "in query is not valid")
                return False
        return True

    def selectors_from_component_query(self,query,sep=INDEX_SEPERATOR):
        #TODO add indicies to doc string
        '''takes: ['comp name 1', 'comp name 3', ...] #list tuple or set
           returns {'component name 1': component1[selector] ...}
           where selector is for the section where all components
           are defined'''
        assert isinstance(query,tuple), 'argument must be hashable'
        known_names = self.names
        assert self.is_valid_query(query), \
            'col_names must be valid component names and index names'
        cache = self._memoized
        if query not in cache:
          indices = tuple(filter(lambda x: sep in x, query))
          col_names = tuple(filter(lambda x: x not in indices, query))
          table = self._allocation_table
          selectors, indices = table.mask_slices(col_names,indices)
          cdict = self.component_dict
          result = {n:cdict[n][s] for n,s in selectors.items()}
          result.update({n:np.array(lst) for n,lst in indices.items()})
          cache[query] = result
        else:
          result = cache[query]
        return dict(result) #return copy of cached result




#########
#
#  Components
#
#########



if __name__ == '__main__':
    from components import DefraggingArrayComponent as Component
    import numpy as np

    #TODO tests should include: when there is nothing in the first class,
    # when there is nothing in the last class.  When there is nothing
    # in one or many in between classes.  When the allocation scheme has repeat
    # entries.  When the allocation scheme is not contiguous.  component 
    # dimensions of (1,),(n,),(n,m) and when incorrect dimensions are added.
    # also, when components have complex data types (structs)

    d1 = Component('component_1',(1,),np.int32)
    d2 = Component('component_2',(2,),np.int32)
    d3 = Component('component_3',(3,),np.int32)
    allocation_scheme = (
      (1,1,1),
      (1,0,1),
      (1,0,0),)

    allocator = GlobalAllocator([d1,d2,d3],allocation_scheme)

    to_add = []
    to_add.append({'component_1':1,'component_3':(1,2,3),'component_2':((1,10),(2,20)),})
    to_add.append({'component_1':2,'component_3':(4,5,6),'component_2':((3,30),(4,40)),})
    to_add.append({'component_1':3,'component_3':(7,8,9),'component_2':((5,50),(6,60)),})
    to_add.append({'component_1':4,'component_3':(10,11,12),'component_2':((7,70),(8,80)),})
    to_add.append({'component_1':7,'component_3':(19,20,21),})
    trash = list(map(allocator.add,to_add))
    #allocator.add(to_add2)
    allocator._defrag()
    #print "d1:",d1[:]

    to_add = []
    to_add.append({'component_1':8,'component_3':(22,23,24),})
    trash = list(map(allocator.add,to_add))
    #allocator.add(to_add2)
    allocator._defrag()
    #print "d1:",d1[:]

    to_add = []
    to_add.append({'component_1':5,'component_3':(13,14,15),'component_2':((9,90),(10,100)),})
    to_add.append({'component_1':6,'component_3':(16,17,18),'component_2':((11,110),(12,120)),})
    to_add.append({'component_1':9,'component_3':(25,26,27),})
    trash = list(map(allocator.add,to_add))
    #allocator.add(to_add2)
    allocator._defrag()
    assert np.all(d1[:9] == np.array([1,2,3,4,5,6,7,8,9]))

    #to_add1 = {'component_1':2,'component_3':8,'component_2':7,}
    #to_add2 = {'component_1':5,'component_3':2,}
    #allocator.add(to_add1)
    #allocator.add(to_add2)
    #allocator._defrag() 
    #to_add1 = {'component_1':3,'component_3':8,'component_2':7,}
    #to_add2 = {'component_1':6,'component_3':2,}
    #allocator.add(to_add1)
    #allocator.add(to_add2)
    #allocator._defrag() 

