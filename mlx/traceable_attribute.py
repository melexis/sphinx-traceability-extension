'''
Storage class for traceable item attribute
'''

import re
from mlx.traceable_base_class import TraceableBaseClass


class TraceableAttribute(TraceableBaseClass):
    '''
    Storage for an attribute to a traceable documentation item
    '''
    regex = None

    def __init__(self, attrid, value):
        '''
        Initialize a new attribute

        Args:
            attrid (str): Attribute identification
            value (str): Pattern string to which the attribute values should match
        '''
        super(TraceableAttribute, self).__init__(attrid)
        self.value = value

    @staticmethod
    def to_id(identifier):
        '''
        Convert a given identification to a storable id

        Args:
            id (str): input identification
        Returns:
            str - Converted storable identification
        '''
        return identifier.lower()

    def update(self, other):
        '''
        Update with new object

        Store the sum of both objects
        '''
        super(TraceableAttribute, self).update(other)
        if other.value is not None:
            self.value = other.value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.regex = re.compile(new_value)

    def can_accept(self, value):
        '''
        Check whether a certain value can be accepted as attribute value

        Args:
            value (str): Value to check the validity of
        '''
        return self.regex.match(value)
