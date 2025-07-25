'''
Storage class for traceable item attribute
'''

import re
from .traceable_base_class import TraceableBaseClass


class TraceableAttribute(TraceableBaseClass):
    '''
    Storage for an attribute to a traceable documentation item
    '''
    regex = None

    def __init__(self, attrid, value, **kwargs):
        '''
        Initialize a new attribute

        Args:
            attrid (str): Attribute identification
            value (str): Pattern string to which the attribute values should match
        '''
        super(TraceableAttribute, self).__init__(attrid, **kwargs)
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
        ''' str: Pattern string to which the attribute values should match '''
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
        if self.regex is None:
            # Rebuild regex if it's None (can happen after unpickling)
            if hasattr(self, '_value') and self._value is not None:
                self.regex = re.compile(self._value)
            else:
                return False
        return self.regex.match(value)

    @property
    def is_placeholder(self):
        """bool: True if this attribute is a placeholder from configuration; False if defined by directive."""
        # Placeholders are created from configuration and have no document location, directive, or content
        # Real definitions have at least one of: docname (from directive), directive (for parsing), or content (processed)
        has_location = hasattr(self, 'docname') and self.docname
        has_directive = hasattr(self, 'directive') and self.directive is not None
        has_content = hasattr(self, '_content') and self._content
        return not (has_location or has_directive or has_content)

    def __getstate__(self):
        """Custom pickling to exclude unpicklable objects like directive references."""
        state = self.__dict__.copy()
        # Remove directive if it exists (it contains unpicklable module references)
        if 'directive' in state:
            del state['directive']
        return state

    def __setstate__(self, state):
        """Custom unpickling to restore state."""
        self.__dict__.update(state)
        # directive will be None after unpickling, which is fine
        # Ensure regex is restored if we have a value
        if hasattr(self, '_value') and self._value is not None:
            self.regex = re.compile(self._value)
