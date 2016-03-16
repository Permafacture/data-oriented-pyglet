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
        self._domain.safe_realloc(self._id,new_size)

    def close(self):
        self._domain.safe_realloc(self._id,None)

    def __del__(self):
      try: 
        self.close()
      except Exception as e:
        import traceback
        print traceback.print_exc()

    def __repr__(self):
      return "<Accessor #%s of %s>"%(self._id,self.domain)

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

def resize_any_attribute(attribute,new_size):
    attribute.resize(new_size)

def data_accessor_factory(name,domain,attributes,allocators):
    '''return a new class to instantiate DataAcessors for this DataDomain'''
    NewAccessor = type(name,(DataAccessor,),{})

    getter = attribute_getter_factory
    setter = attribute_setter_factory
    for attr, allocator in zip(attributes,allocators):
      try:
        setattr(NewAccessor,attr.name,property(getter(domain,attr,allocator), 
                                             setter(domain,attr,allocator)))
      except AttributeError:
        #attribute doesn't have a name, so don't provide access to it
        pass
    return NewAccessor

