'''
For creating DataAccessors. DataDomains give these out when new objects are
added to let the user get and set that objects properties within the 
DataDomain
'''
class DataAccessor(object):
    '''An accessor for an object that is managed by a DataDomain'''
    
    def __init__(self,domain,id):
      '''Knows what domain it came from and its unique id within that domain'''
      self._domain = domain
      self._id=id

def singleattribute_getter_factory(domain,attr):
      '''generate a getter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def getter(self):
        index = domain.index_from_id(self._id)
        return attr[index]
      return getter

def singleattribute_setter_factory(domain,attr):
      '''generate a setter using this object's index to the domain arrays
      attr is the domain's list of this attribute'''
      def setter(self, data):
        index = domain.index_from_id(self._id)
        attr[index] = data
      return setter

def data_accessor_factory(name,domain):
    '''return a new class to instantiate DataAcessors for this DataDomain'''
    NewAccessor = type(name,(DataAccessor,),{})
    getter = singleattribute_getter_factory
    setter = singleattribute_setter_factory
    for attr in domain._single_attributes:
      setattr(NewAccessor,attr.name,property(getter(domain,attr), setter(domain,attr)))
    return NewAccessor

