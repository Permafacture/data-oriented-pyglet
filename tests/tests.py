from unittest import TestCase, TestSuite, TextTestRunner
import numpy as np

from data_oriented import DataDomain, BroadcastingDataDomain, ArrayAttribute

class DataDomainTestCase(TestCase):


   def setUp(self):

        class TestDataDomain(BroadcastingDataDomain):
            '''a DataDomain with one 1D Array, one 2D Array, and one Broadcastable 
            attribute to use in tests.'''
            def __init__(self):
              super(TestDataDomain,self).__init__()

              self.arrayed1D = ArrayAttribute('arrayed1D',1,np.float32)
              self.arrayed2D = ArrayAttribute('arrayed2D',2,np.float32)
              self.array_attributes.extend([self.arrayed1D,self.arrayed2D])

              self.broadcastable1D = ArrayAttribute('broadcastable1D',1,np.int32)
              self.broadcastable2D = ArrayAttribute('broadcastable2D',2,np.int32)
              self.broadcastable_attributes.extend([self.broadcastable1D,self.broadcastable2D])

              self.DataAccessor = self.generate_accessor('TestAccessor') 

            def add(self,oneD, twoD):
               assert isinstance(oneD,(int,float)), "must just be a number"
               assert len(twoD) == 2, "must have length 2"
               arrayed1D = [x+1 for x in range(5)]
               arrayed2D = [(x+1.1,x+1.3) for x in xrange(5)]
               kwargs = { 'arrayed1D':arrayed1D,
                          'arrayed2D':arrayed2D,
                          'broadcastable1D':oneD,
                          'broadcastable2D':twoD}
               return super(TestDataDomain,self).add(**kwargs)

        self.datadomain = TestDataDomain()
 
    
   def test_add_data_to_domain(self):
        '''Data can be added to domains and accessed through accessors'''
        accessor1 = self.datadomain.add(1,(0,0))
        accessor2 = self.datadomain.add(2,(3,4))
        accessor3 = self.datadomain.add(1,(0,0))
        self.assertTrue(np.all(accessor2.arrayed1D == np.array([1,2,3,4,5],
                         dtype=np.float32)),
                         "data accessor access wrong arrayed1D")
        self.assertTrue(np.all(accessor2.arrayed2D == np.array([[1.1,1.3],
                                                                [2.1,2.3],
                                                                [3.1,3.3],
                                                                [4.1,4.3],
                                                                [5.1,5.3]],
                                                          dtype=np.float32)),
                         "data accessor access wrong arrayed2D")
        self.assertEqual(accessor2.broadcastable1D,2,
                         "data accessor access wrong broadcastable1D")
        self.assertTrue(np.all(accessor2.broadcastable2D == np.array([3,4],dtype=np.int32)),
                         "data accessor access wrong broadcastable2D")

   def test_1D_to_1D_broadcast(self):
        '''1D BroadcastableAttribute correctly broadcasts to 1D ArrayAttribute'''
        accessor1 = self.datadomain.add(1,(0,0))
        accessor2 = self.datadomain.add(10,(0,0))
        accessor3 = self.datadomain.add(100,(0,0))
        as_array = self.datadomain.as_array
        datadomain = self.datadomain
        result = as_array(datadomain.arrayed1D) * as_array(datadomain.broadcastable1D)
        desired = np.array([1,2,3,4,5,10,20,30,40,50,100,200,300,400,500],
                            dtype=np.float32)
        self.assertTrue(np.all(result==desired),"Broadcast math works")

#TODO: test deallocs where some contigous portions are left after a deallocted region:
#  ie: ABCDEF after dealloc B and E

def suite():
    tests = ['test_add_data_to_domain',
             'test_1D_to_1D_broadcast']
    return TestSuite(map(DataDomainTestCase, tests))

if __name__=='__main__':
  TextTestRunner(verbosity=2).run(suite())
