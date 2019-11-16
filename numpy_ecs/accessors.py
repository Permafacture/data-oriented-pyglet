'''
Accessors provide an object oriented interface for a specific 
entity instance (guid) by providing an object with attributes
that access the array slices allocated to that guid under
the hood

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
from __future__ import absolute_import, division, print_function
import sys
#python version compatability
if sys.version_info < (3,0):
    from future_builtins import zip, map

import numpy as np

def build_references(allocator,guid):
    '''returns {component_name: slice or None, ...} for guid'''
    component_names = allocator.names
    get_slice = allocator._allocation_table.slices_from_guid
    slices = (s if s.start != s.stop else None for s in get_slice(guid))
    return dict(zip(component_names,slices))

#TODO, I would like for methods of Accessor only called by Accessor to
# be double underscored, but since they are used in the Factory, the
# double underscore gets expanded to be the Factory.  There might be
# too much meta to make them private to a class that is created 
# just in time.

class Accessor(object):
    '''    
    Accessors provide an object oriented interface for a specific 
    entity instance (guid) by providing an object with attributes
    that access the array slices allocated to that guid under
    the hood.'''

    def __init__(self,guid):
      # self._allocator is provided by the factory
      self._guid = guid
      self._dirty  = True #do slices need to be re-calculated?
      self._active = True #is this accessor deleteable?
      self._references = {} #{component_name:slice,...}
      #The factory gave us a property for every component in the Table
      # but any specific guid won't have values for all of those
      # so we delete them
      # TODO can't delete a class property from an instance :'(
      #for name,val in build_references(self._allocator,guid).items():
      #    if val is None:
      #        print("delete {}".format(name))
      #        print(dir(self))
      #        delattr(self,name)

    def _rebuild_references(self,build_ref = build_references):
        '''Get the up to date slices for all the attributes'''
        # the is not None is not necessary, but not harmful
        self._references = {k:v for k,v in build_ref(self._allocator,
            self._guid).items() if v is not None}
        self._dirty = False

    #def resize(self,new_size):
    #    self._domain.safe_realloc(self._id,new_size)

    #def close(self):
    #    self.__closed = True
    #    self._domain.safe_dealloc(self._id)

    #def __del__(self):
    #    if not self.__closed:
    #      self.close()

    def __repr__(self):
      return "<Accessor for guid #%s>"%(self._guid,)


class AccessorFactory(object):

    def __init__(self,allocator):
        self.allocator=allocator

    def attribute_getter_factory(self, component_name):
          '''generate a getter for this component_name into the Component data array'''
          comp_dict = self.allocator.component_dict
          def getter(accessor, name=component_name, comp_dict=comp_dict):
            if accessor._dirty:
                accessor._rebuild_references()
            selector = accessor._references[name]
            return comp_dict[name][selector]
          return getter

    def attribute_setter_factory(self, component_name):
          '''generate a setter using this object's index to the domain arrays
          attr is the domain's list of this attribute'''
          comp_dict = self.allocator.component_dict
          def setter(accessor, data, name=component_name,comp_dict=comp_dict):
            if accessor._dirty:
                accessor._rebuild_references()
            selector = accessor._references[name]
            comp_dict[name][selector] = data
          return setter

    def generate_accessor(self):
        '''return a DataAccessor class that can be instatiated with a
        guid to provide an object oriented interface with the data 
        associated with that guid'''
        NewAccessor = type('DataAccessor',(Accessor,),{})

        allocator = self.allocator
        getter = self.attribute_getter_factory
        setter = self.attribute_setter_factory
        comp_dict = allocator.component_dict
        for name in allocator.names:
            print("adding property: {}".format(name))
            setattr(NewAccessor,name,property(getter(name), setter(name)))
        NewAccessor._allocator = self.allocator
        return NewAccessor


