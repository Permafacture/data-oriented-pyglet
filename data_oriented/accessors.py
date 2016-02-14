'''
For creating DataAccessors. DataDomains give these out when new objects are
added to let the user get and set that objects properties within the 
DataDomain

This file is part of Data Oriented Python.
Copyright (C) 2016 Elliot Hallmark (permfacture@gmail.com)

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

    def __del__(self):
      self._domain.dealloc(self._id)

#TODO: instead of using datadomain.index_from_id, find a way of giving the
# accessor more direct access to the function that gives it the index. Right
# now, the function is several pointers away.  Probably not worth bothering
# with though.
def singleattribute_getter_factory(domain,attr):
      '''generate a getter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def getter(self,index_from_id=domain.index_from_id,attr=attr):
        index = index_from_id(self._id)
        return attr[index]
      return getter

def singleattribute_setter_factory(domain,attr):
      '''generate a setter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def setter(self, data, index_from_id = domain.index_from_id,attr=attr):
        index = index_from_id(self._id)
        attr[index] = data
      return setter

def multiattribute_getter_factory(domain,attr):
      '''generate a getter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def getter(self,index_from_id=domain.slice_from_id,attr=attr):
        index = index_from_id(self._id)
        return attr[index]
      return getter

def multiattribute_setter_factory(domain,attr):
      '''generate a setter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def setter(self, data, index_from_id = domain.slice_from_id,attr=attr):
        index = index_from_id(self._id)
        attr[index] = data
      return setter

def data_accessor_factory(name,domain,plural_attributes,single_attributes):
    '''return a new class to instantiate DataAcessors for this DataDomain'''
    NewAccessor = type(name,(DataAccessor,),{})

    getter = singleattribute_getter_factory
    setter = singleattribute_setter_factory
    for attr in single_attributes:
      setattr(NewAccessor,attr.name,property(getter(domain,attr), setter(domain,attr)))

    getter = multiattribute_getter_factory
    setter = multiattribute_setter_factory
    for attr in plural_attributes:
      setattr(NewAccessor,attr.name,property(getter(domain,attr), setter(domain,attr)))


    return NewAccessor

