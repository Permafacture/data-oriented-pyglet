'''
For creating DataAccessors. DataDomains give these out when new objects are
added to let the user get and set that objects properties within the 
DataDomain

This file is part of Data Oriented Python.
Copyright (C) 2016 Elliot Hallmark (permafacture@gmail.com)

Data Oreinted Python is free software: you can redistribute it and/or modify
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
class DataAccessor(object):
    '''An accessor for an object that is managed by a DataDomain'''
    
    def __init__(self,domain,id):
      '''Knows what domain it came from and its unique id within that domain'''
      self._domain = domain
      self._id=id

    def resize(self,new_size):
        self._domain.realloc(self._id,new_size)

    def __del__(self):
      self._domain.dealloc(self._id)


#TODO: instead of using datadomain.index_from_id, find a way of giving the
# accessor more direct access to the function that gives it the index. Right
# now, the function is several pointers away.  Probably not worth bothering
# with though.

#TODO: single and multi are the sameish now that there is only ArrayAttribute
# is it worth it providing an optimization (is it even an optimization?) for
# index vs slice getting and setting?

#def singleattribute_getter_factory(domain,attr):
#      '''generate a getter using this object's index to the domain arrays
#      attr is the domain's list of this attribute'''
#      def getter(self,index_from_id=domain.index_from_id,attr=attr):
#        index = index_from_id(self._id)
#        return attr[index]
#      return getter
#
#def singleattribute_setter_factory(domain,attr):
#      '''generate a setter using this object's index to the domain arrays
#      attr is the domain's list of this attribute'''
#      def setter(self, data, index_from_id = domain.index_from_id,attr=attr):
#        index = index_from_id(self._id)
#        attr[index] = data
#      return setter

def attribute_getter_factory(domain,attr,allocator):
      '''generate a getter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def getter(self,selector_from_id=allocator.selector_from_id,attr=attr):
        selector = selector_from_id(self._id)
        return attr[selector]
      return getter

def attribute_setter_factory(domain,attr,allocator):
      '''generate a setter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def setter(self, data, selector_from_id = allocator.selector_from_id,attr=attr):
        selector = selector_from_id(self._id)
        attr[selector] = data
      return setter

def data_accessor_factory(name,domain,attributes,allocators):
    '''return a new class to instantiate DataAcessors for this DataDomain'''
    NewAccessor = type(name,(DataAccessor,),{})

    getter = attribute_getter_factory
    setter = attribute_setter_factory
    for attr, allocator in zip(attributes,allocators):
      setattr(NewAccessor,attr.name,property(getter(domain,attr,allocator), 
                                             setter(domain,attr,allocator)))

    return NewAccessor

