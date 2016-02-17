import os
import unittest

from cStringIO import StringIO

from gis_metadata.xml.element_utils import DEFAULT_ENCODING, Element, ElementTree, ElementType
from gis_metadata.xml.element_utils import iselement, fromstring, tostring

from gis_metadata.xml.element_utils import create_element_tree, clear_children, clear_element, copy_element
from gis_metadata.xml.element_utils import get_element_tree, get_element, get_remote_element, get_elements
from gis_metadata.xml.element_utils import element_exists, elements_exist, element_is_empty
from gis_metadata.xml.element_utils import insert_element, remove_element, remove_elements, remove_empty_element
from gis_metadata.xml.element_utils import get_element_name, get_element_attribute, get_element_attributes
from gis_metadata.xml.element_utils import set_element_attributes, remove_element_attributes
from gis_metadata.xml.element_utils import get_element_tail, get_elements_tail, get_element_text, get_elements_text
from gis_metadata.xml.element_utils import set_element_tail, set_elements_tail, set_element_text, set_elements_text
from gis_metadata.xml.element_utils import dict_to_element, element_to_dict, element_to_object, element_to_string
from gis_metadata.xml.element_utils import iter_elements, iterparse_elements, strip_namespaces, write_element


ELEM_NAME = 'tag'
ELEM_TEXT = 'text'
ELEM_TAIL = 'tail'
ELEM_ATTRIBS = 'attrib'

ELEM_PROPERTIES = (ELEM_NAME, ELEM_TEXT, ELEM_TAIL, ELEM_ATTRIBS)


class ElementUtilTestCase(unittest.TestCase):

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')

        self.elem_data_file_path = '/'.join((self.data_dir, 'elem_data.xml'))
        self.namespace_file_path = '/'.join((self.data_dir, 'namespace_data.xml'))
        self.test_file_path = '/'.join((self.data_dir, 'test_data.xml'))

        self.elem_data_file = open(self.elem_data_file_path)
        self.namespace_file = open(self.namespace_file_path)

        with open('/'.join((self.data_dir, 'elem_data.xml'))) as data:
            self.elem_data_str = data.read()

        self.elem_data_dict = element_to_dict(self.elem_data_str, True)
        self.elem_data_reader = StringIO(self.elem_data_str)

        self.elem_data_inputs = (
            fromstring(self.elem_data_str), ElementTree(fromstring(self.elem_data_str)),
            self.elem_data_file, self.elem_data_str, self.elem_data_dict, self.elem_data_reader
        )

        self.elem_xpath = 'c'

    def _reduce_property(self, value):
        """ Ensure property values trim strings and reduce lists with single values to the value itself """

        if isinstance(value, list) and len(value) == 1:
            value = value[0]

        if isinstance(value, basestring):
            value = value.strip()

        return value

    def _wrap_property(self, value):
        """ Ensure property values trim strings and reduce lists with single values to the value itself """
        return value if isinstance(value, list) else [value]

    def assert_element_function(self, elem_func, elem_xpath=None, **elem_kwargs):
        """
        Ensures elem_func returns None for None, and that the element returned by elem_func is equal to base_elem.
        """
        self.assertIsNone(elem_func(None, **elem_kwargs), 'None check failed for {0}'.format(elem_func.__name__))

        base_elem = fromstring(self.elem_data_str)
        elem_name = base_elem.tag

        if elem_xpath is not None:
            elem_name = '/'.join((elem_name, self.elem_xpath))
            base_elem = base_elem.find(elem_xpath)

        for data in self.elem_data_inputs:
            self.assert_elements_are_equal(elem_func(data, **elem_kwargs), base_elem, elem_name)

    def assert_element_is_type(self, element, elem_name=None, elem_type=ElementType):
        """ Ensures the element is of the type specified by element_utils.ElementType """

        if elem_name is None:
            elem_name = getattr(element, ELEM_NAME, 'None')

        self.assertIsInstance(
            element, elem_type,
            '{0} is not of type {1}: {2}'.format(elem_name, elem_type.__name__, type(element))
        )

    def assert_element_properties_equal(self, this_elem, that_elem, prop, elem_name=None):
        """ Ensures the element property specified matches for both elements """

        prop1 = self._reduce_property(getattr(this_elem, prop))
        prop2 = self._reduce_property(getattr(that_elem, prop))

        self.assertEqual(prop1, prop2,
            'Element {0} properties are not equal at /{1}: "{2}" ({3}) != "{4}" ({5})'.format(
                prop, elem_name, prop1, type(prop1).__name__, prop2, type(prop2).__name__
            )
        )

    def assert_element_trees_are_equal(self, this_tree, that_tree, elem_name=None):
        """ Ensures both element trees are comparable, and their properties are equal """

        if this_tree is None and that_tree is None:
            return

        self.assert_element_is_type(this_tree, 'elem_tree_1', ElementTree)
        self.assert_element_is_type(that_tree, 'elem_tree_2', ElementTree)

        self.assert_elements_are_equal(this_tree.getroot(), that_tree.getroot(), elem_name)

    def assert_elements_are_comparable(self, this_elem, that_elem, elem_name=None, elem_type=ElementType):
        """ Ensures both elements are None, or both are of the type element_utils.ElementType """

        if elem_name is None:
            elem_name = getattr(this_elem, ELEM_NAME, getattr(that_elem, ELEM_NAME, 'None'))

        if this_elem is None and that_elem is not None:
            self.assertIsNone(that_elem, 'None does not equal "{0}"'.format(elem_name))

        if this_elem is not None and that_elem is None:
            self.assertIsNone(this_elem, 'None does not equal "{0}"'.format(elem_name))

        self.assert_element_is_type(this_elem, elem_name, elem_type)
        self.assert_element_is_type(that_elem, elem_name, elem_type)

    def assert_elements_are_equal(self, this_elem, that_elem, elem_name=None):
        """ Ensures both elements are comparable, and their properties are equal """

        if this_elem is None and that_elem is None:
            return

        if elem_name is None:
            elem_name = getattr(this_elem, ELEM_NAME, getattr(that_elem, ELEM_NAME, 'None'))

        self.assert_elements_are_comparable(this_elem, that_elem, elem_name)

        for prop in ELEM_PROPERTIES:
            self.assert_element_properties_equal(this_elem, that_elem, prop, elem_name)

        last_tags = set()

        for next_one in this_elem:

            next_tag = getattr(next_one, ELEM_NAME)
            next_name = '/'.join((elem_name, next_tag))

            if next_tag in last_tags:
                continue

            last_tags.add(next_tag)

            these_elems = this_elem.findall(next_tag)
            those_elems = that_elem.findall(next_tag)

            len_these, len_those = len(these_elems), len(those_elems)

            self.assertEqual(len_these, len_those,
                'Elements {0} have differing numbers of children: {1} != {2}'.format(
                    next_name, len_these, len_those
                )
            )

            for idx, child in enumerate(these_elems):
                self.assert_elements_are_equal(child, those_elems[idx], next_name)

    def tearDown(self):

        self.elem_data_file.close()
        self.elem_data_reader.close()
        self.namespace_file.close()

        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)


class ElementUtilTests(ElementUtilTestCase):

    def test_create_element_tree(self):
        """ Tests create_element_tree with None, and for equality with different params """

        self.assertIsNone(create_element_tree().getroot(), 'None check failed for create_element_tree')

        self.assert_element_trees_are_equal(
            create_element_tree('root', ELEM_TEXT, a='aaa', b='bbb'),
            create_element_tree(fromstring('<root a="aaa" b="bbb">text</root>'))
        )

    def test_clear_children(self):
        """ Tests clear_children with different element data, including None """

        self.assertIsNone(clear_children(None), 'None check failed for clear_children')

        for data in self.elem_data_inputs:
            data = clear_children(data)
            self.assertEqual(
                data.getchildren(), [], 'Clear children failed for input type {0}'.format(type(data).__name__)
            )

    def test_clear_children_xpath(self):
        """ Tests clear_children at an XPATH location with different element data """

        for data in self.elem_data_inputs:
            data = clear_children(data, self.elem_xpath)
            self.assertEqual(
                data.getchildren(), [], 'Clear children XPATH failed for input type {0}'.format(type(data).__name__)
            )

    def assert_element_cleared(self, elem, elem_type, msg='Clear element'):
        """ Ensures an element has been cleared by testing text, tail, attributes and children """

        self.assertFalse(bool(elem.text), '{0} failed for {1}: text == "{2}"'.format(msg, elem_type, elem.text))
        self.assertFalse(bool(elem.tail), '{0} failed for {1}: tail == "{2}"'.format(msg, elem_type, elem.tail))
        self.assertFalse(bool(elem.attrib), '{0} failed for {1}: attrib == "{2}"'.format(msg, elem_type, elem.attrib))
        self.assertFalse(
            bool(elem.getchildren()),
            '{0} failed for {1}: children == "{2}"'.format(msg, elem_type, elem.getchildren())
        )

    def test_clear_element(self):
        """ Tests clear_element with different element data, including None """

        self.assertIsNone(clear_element(None), 'None check failed for clear_element')

        for data in self.elem_data_inputs:
            self.assert_element_cleared(clear_element(data), type(data).__name__)

    def test_clear_element_xpath(self):
        """ Tests clear_element at an XPATH location with different element data """

        for data in self.elem_data_inputs:
            self.assert_element_cleared(
                clear_element(data, self.elem_xpath), type(data).__name__, 'Clear element XPATH'
            )

    def test_copy_element(self):
        """ Tests copy_element with different element data, including None """
        self.assert_element_function(copy_element)

    def test_copy_element_to(self):
        """ Tests copy_element to a destination element with different element data """
        self.assert_element_function(copy_element, to_element='<a />')

    def test_copy_element_xpath(self):
        """ Tests copy_element at an XPATH location to a destination element with different element data """

        self.assert_element_function(
            copy_element, self.elem_xpath, to_element='<a />', path_to_copy=self.elem_xpath
        )

    def test_get_element_tree(self):
        """ Tests get_element_tree with None, and for equality with different params """

        self.assertIsNone(get_element_tree(None).getroot(), 'None check failed for get_element_tree')

        base_elem = get_element(self.elem_data_str)
        base_tree = ElementTree(base_elem)

        for data in self.elem_data_inputs:
            self.assert_element_trees_are_equal(get_element_tree(data), base_tree, base_elem.tag)

    def test_get_element(self):
        """ Tests get_element with None, and for equality with different params """
        self.assert_element_function(get_element)

    def test_get_element_xpath(self):
        """ Tests get_element at an XPATH location with different element data """
        self.assert_element_function(get_element, self.elem_xpath, element_path=self.elem_xpath)

    def test_get_remote_element(self):
        """ Tests get_remote_element with None and a well-known URL with and without an XPATH location """

        self.assertIsNone(get_remote_element(None), 'None check failed for get_remote_element')

        remote_url = 'http://en.wikipedia.org/wiki/XML'
        self.assertIsNotNone(
            get_remote_element(remote_url), 'Remote element returns None'
        )
        self.assertIsNotNone(
            get_remote_element(remote_url, 'head'), 'Remote element returns None for "head"'
        )

    def test_get_elements(self):
        """ Tests get_elements for single and multiple XPATHs parsed from different data sources """

        self.assertEqual(get_elements(None, None), [], 'None check failed for get_elements')
        self.assertEqual(get_elements('<a />', ''), [], 'Empty check failed for get_elements')

        xml_content = (
            '<b/>', '<b></b>', '<b b="bbb">btext<c />ctail</b>',
            '<b/><b></b>', '<b/><b></b><b b="bbb">btext<c />ctail</b>'
        )

        for xml in xml_content:
            elements = get_elements('<a>{0}</a>'.format(xml), 'b')
            targeted = fromstring('<x>{0}</x>'.format(xml)).findall('b')

            for idx, elem in enumerate(elements):
                self.assert_elements_are_equal(elem, targeted[idx], 'a/b')

        xpath = 'c/d'
        targeted = fromstring(self.elem_data_str).findall(xpath)

        for data in self.elem_data_inputs:
            for idx, elem in enumerate(get_elements(data, xpath)):
                self.assert_elements_are_equal(elem, targeted[idx], 'a/' + xpath)

    def test_dict_to_element(self):
        """ Tests dictionary to element conversion on elements converted from different data sources """

        self.assertIsNone(dict_to_element(None), 'None check failed for test_dict_to_element')
        self.assertIsNone(dict_to_element(ElementTree()), 'ElementTree check failed for test_dict_to_element')
        self.assertIsNone(dict_to_element(Element), 'Element check failed for test_dict_to_element')

        base_elem = fromstring(self.elem_data_str)
        dict_elem = dict_to_element(self.elem_data_dict)

        self.assert_elements_are_equal(base_elem, dict_elem)

        for data in self.elem_data_inputs:
            if isinstance(data, dict):
                self.assert_elements_are_equal(base_elem, dict_to_element(self.elem_data_dict))
            else:
                self.assertIsNone(
                    dict_to_element(data), 'Invalid dictionary check failed for {0}'.format(type(data).__name__)
                )

    def test_element_to_dict(self):
        """ Tests element to dictionary conversion on elements converted from different data sources """

        base_dict = element_to_dict(self.elem_data_str, True)

        for data in self.elem_data_inputs:
            test_dict = element_to_dict(data, True)

            self.assertEqual(
                base_dict, test_dict,
                'Converted dictionary equality check failed for {0}'.format(type(data).__name__)
            )
            self.assert_elements_are_equal(dict_to_element(base_dict), dict_to_element(test_dict))

    def test_element_to_object(self):
        self._test_element_to_object(False)

    def test_element_to_object_flat(self):
        self._test_element_to_object(True)

    def _test_element_to_object(self, is_flat):
        """ Tests element to object conversion on elements converted from different data sources """

        def assert_element_equals_object(elem, obj):
            """ Internal helper to flexibly compare flattened and non-flattened objects to element """

            ename, etext = elem.tag, (elem.text or '').strip()
            otype, ovalue = obj.get('type', ename), (obj.get('value', obj.get(ename, etext)) or '')
            otext = ovalue[:len(etext)] if isinstance(ovalue, basestring) else ''

            self.assertEqual(ename, otype, 'Invalid object type: {0} != {1}'.format(ename, otype))
            self.assertEqual(etext, otext, 'Invalid object value: {0} != {1}'.format(etext, otext))

            if len(elem) or len(elem.attrib):
                next_obj = obj[otype]

                for attrib in elem.attrib:
                    eprop, oprop = next_obj[attrib], get_element_attribute(elem, attrib)
                    self.assertEqual(eprop, oprop, 'Invalid object property: {0} != {1}'.format(eprop, oprop))

                idx = 0
                for child in elem:
                    if child.tag in next_obj:
                        assert_element_equals_object(child, next_obj)
                    else:
                        assert_element_equals_object(child, next_obj['children'][idx])
                        idx += 1

        base_obj = element_to_object(self.elem_data_str, is_flat)
        assert_element_equals_object(get_element(self.elem_data_str), base_obj)

        for data in self.elem_data_inputs:
            self.assertEqual(
                base_obj, element_to_object(data, is_flat),
                'Converted object equality check failed for {0}'.format(type(data).__name__)
            )

    def test_element_to_string(self):
        """ Tests element conversion from different data sources to XML, with and without a declaration line """

        self.assertEqual('', element_to_string(None), 'None check failed for element_to_string')
        self.assertEqual('', element_to_string([]), 'Empty check failed for element_to_string')

        base_elem = fromstring(self.elem_data_str)

        converted_wout_dec = element_to_string(base_elem, None, None)
        converted_with_dec = element_to_string(base_elem)

        # Requires double quotes and consistent spacing in source file
        self.assertEqual(self.elem_data_str, converted_wout_dec, 'Raw string check failed for element_to_string')

        for data in self.elem_data_inputs:
            data_type = type(data).__name__
            element = get_element(data)

            self.assertEqual(
                tostring(element), converted_wout_dec,
                'With declaration check failed for element_to_string for {0}'.format(data_type)
            )
            self.assertEqual(
                tostring(element, encoding=DEFAULT_ENCODING, method='xml'), converted_with_dec,
                'Without declaration check failed for element_to_string for {0}'.format(data_type)
            )

    def test_iter_elements(self):
        """ Tests iter_elements with a custom function on elements from different data sourcs """

        self.assertIsNone(iter_elements(None, None), 'None check failed for iter_elements')
        self.assert_elements_are_equal(fromstring('<a/>'), iter_elements(set_element_attributes, '<a/>'))

        base_elem = fromstring('<a><b /><c /></a>').find(self.elem_xpath)
        base_elem.attrib = {'x': 'xxx', 'y': 'yyy', 'z': 'zzz'}

        def iter_elements_func(elem, **attrib_kwargs):
            """ Test function for iter_elements test """
            set_element_attributes(clear_element(elem), **attrib_kwargs)

        for data in self.elem_data_inputs:
            test_elem = iter_elements(iter_elements_func, data, **base_elem.attrib)
            self.assert_elements_are_equal(test_elem.find(self.elem_xpath), base_elem)

    def test_iterparse_elements(self):

        self.assertIsNone(iterparse_elements(None, None), 'None check failed for iter_elements')
        self.assertIsNone(iterparse_elements('', ''), 'Empty check failed for iter_elements')

        base_attribs = {'x': 'xxx', 'y': 'yyy', 'z': 'zzz'}
        base_elem = fromstring('<a />')

        def iterparse_func(elem, **attrib_kwargs):
            """
            Test function for iterparse_elements test. This function is run once for every element
            in the file being parsed. The original file is not changed, but a local variable can be.
            """
            if elem.tag == self.elem_xpath:
                elem.attrib = base_attribs
                self.assert_elements_are_equal(
                    elem, copy_element(elem, insert_element(base_elem, 0, self.elem_xpath))
                )

        iterparse_elements(iterparse_func, self.elem_data_file_path, **base_attribs)

        existing_elem = fromstring(self.elem_data_str).find(self.elem_xpath)
        existing_elem.attrib = base_attribs

        self.assert_elements_are_equal(base_elem.find(self.elem_xpath), existing_elem)

    def test_strip_namespaces(self):
        """ Tests namespace stripping by comparing equivalent XML from different data sources """

        stripped = fromstring(strip_namespaces(self.namespace_file))

        for data in self.elem_data_inputs:
            self.assert_elements_are_equal(get_element(data), stripped)

    def test_write_element_to_path(self):
        """ Tests writing an element to a file path, reading it in, and testing the content for equality """

        for data in self.elem_data_inputs:

            if os.path.exists(self.test_file_path):
                os.remove(self.test_file_path)

            write_element(data, self.test_file_path)

            with open(self.test_file_path) as test:
                self.assert_elements_are_equal(get_element(test), fromstring(self.elem_data_str))

    def test_write_element_to_file(self):
        """ Tests writing an element to a file object, reading it in, and testing the content for equality """

        for data in self.elem_data_inputs:

            if os.path.exists(self.test_file_path):
                os.remove(self.test_file_path)

            with open(self.test_file_path, 'w') as test:
                write_element(data, test)

            with open(self.test_file_path) as test:
                self.assert_elements_are_equal(get_element(test), fromstring(self.elem_data_str))


class ElementUtilPropertyTests(ElementUtilTestCase):

    def assert_element_values_equal(self, prop, value1, value2):
        """ Ensures the two trimmed values are equal, and fails with an informative message """

        val1, val2 = self._reduce_property(value1), self._reduce_property(value2)

        self.assertEqual(val1, val2,
            'Element {0} properties are not equal: "{1}" ({2}) != "{3}" ({4})'.format(
                prop, val1, type(val1).__name__, val2, type(val2).__name__
            )
        )

    def assert_element_property_getter(self, prop, elem_func, elem_xpath=None, default_target=None, **elem_kwargs):
        """ Ensures the properties returned by the function are as expected for all data sources """

        self.assert_element_values_equal(prop, elem_func(None, **elem_kwargs), default_target)
        self.assert_element_values_equal(
            prop, elem_func('<a/>', **elem_kwargs), 'a' if prop == ELEM_NAME else default_target
        )

        base_elem = fromstring(self.elem_data_str)
        if elem_xpath:
            base_elem = base_elem.find(elem_xpath)

        base_prop = getattr(base_elem, prop) or default_target

        for data in self.elem_data_inputs:
            self.assert_element_values_equal(prop, elem_func(data, **elem_kwargs), base_prop)

    def test_get_element_attribute(self):
        """
        Tests get_element_attribute for null, empty, and non-existent attributes; also
        tests that an attribute returned from different data sources matches the expected
        """
        default_val = 'x'

        self.assertEqual(
            default_val, get_element_attribute(None, None, default_val),
            'Value check for get null element attribute failed.'
        )
        self.assertEqual(
            default_val, get_element_attribute('<a/>', None, default_val),
            'Value check for get empty element attribute failed.'
        )
        self.assertEqual(
            default_val, get_element_attribute('<a/>', 'a', default_val),
            'Value check for get non-existent element attribute failed.'
        )

        base_elem = fromstring(self.elem_data_str)
        base_key = base_elem.attrib.keys()[0]
        base_val = base_elem.attrib[base_key]

        for data in self.elem_data_inputs:
            self.assert_element_values_equal(
                'attributes.{0}'.format(base_key), get_element_attribute(data, base_key), base_val
            )

    def test_get_element_attributes(self):
        """
        Tests get_element_attributes for null and empty attributes; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_ATTRIBS, get_element_attributes, default_target={})

    def test_get_element_attributes_xpath(self):
        """
        Tests get_element_attributes with an XPATH for null and empty attributes; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(
            ELEM_ATTRIBS, get_element_attributes, self.elem_xpath, element_path=self.elem_xpath, default_target={}
        )

    def test_add_element_attributes(self):
        """
        Tests set_element_attributes for null, empty, and new attributes; also
        tests that attributes are added to elements parsed from different data sources
        """
        new_attrs = {'x': 'xxx', 'y': 'yyy', 'z': 'zzz'}

        self.assertIsNone(set_element_attributes(None), 'None check for adding element attributes failed.')
        self.assertEqual(
            {}, set_element_attributes('<a/>'),
            'Value check for adding empty element attributes failed.'
        )
        self.assertEqual(
            new_attrs, set_element_attributes('<a/>', x='xxx', y='yyy', z='zzz'),
            'Value check for adding all new element attributes failed.'
        )

        base_elem = fromstring(self.elem_data_str)
        base_attrs = base_elem.attrib
        base_attrs.update(new_attrs)

        for data in self.elem_data_inputs:
            self.assert_element_values_equal(
                'attributes', set_element_attributes(data, **new_attrs), base_attrs
            )

        set_element_attributes(base_elem, **new_attrs)

        self.assert_element_values_equal('attributes', base_elem.attrib, base_attrs)

    def test_remove_element_attributes(self):
        """
        Tests remove_element_attributes for null, empty, and non-existent attributes; also
        tests that attributes are removed successfully from elements parsed from different data sources
        """
        self.assertIsNone(
            remove_element_attributes(None),
            'None check for removing element attributes failed.'
        )
        self.assertEqual(
            {}, remove_element_attributes('<a/>'),
            'Value check for removing empty element attributes failed.'
        )
        self.assertEqual(
            {}, remove_element_attributes('<a/>', 'x', 'y', 'z'),
            'Value check for removing non-existent element attributes failed.'
        )

        base_elem = fromstring(self.elem_data_str)
        base_attrs = base_elem.attrib
        base_keys = base_attrs.keys()

        for data in self.elem_data_inputs:
            self.assert_element_values_equal(
                'attributes', remove_element_attributes(data, *base_keys), base_attrs
            )

        remove_element_attributes(base_elem, *base_keys)

        self.assert_element_values_equal('attributes', base_elem.attrib, {})

    def test_get_element_name(self):
        """
        Tests get_element_name with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_NAME, get_element_name)

    def test_get_element_tail(self):
        """
        Tests test_get_element_tail with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_TAIL, get_element_tail, default_target='x', default_value='x')

    def test_get_element_tail_xpath(self):
        """
        Tests test_get_element_tail with an XPATH with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(
            ELEM_TAIL, get_element_tail,
            self.elem_xpath, default_target='x', default_value='x', element_path=self.elem_xpath
        )

    def test_get_element_text(self):
        """
        Tests get_element_text with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_TEXT, get_element_text, default_target='x', default_value='x')

    def test_get_element_text_xpath(self):
        """
        Tests get_element_text with an XPATH with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(
            ELEM_TEXT, get_element_text,
            self.elem_xpath, default_target='x', default_value='x', element_path=self.elem_xpath
        )

    def test_get_elements_text(self):
        """
        Tests get_elements_text with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_TEXT, get_elements_text, default_target=[])

    def test_get_elements_text_xpath(self):
        """
        Tests get_elements_text with an XPATH with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(
            ELEM_TEXT, get_elements_text,
            self.elem_xpath, default_target=[], element_path=self.elem_xpath
        )

    def test_get_elements_tail(self):
        """
        Tests get_elements_tail with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(ELEM_TAIL, get_elements_tail, default_target=[])

    def test_get_elements_tail_xpath(self):
        """
        Tests get_elements_tail with an XPATH with null and empty elements; also
        tests that attributes returned from different data sources match those expected
        """
        self.assert_element_property_getter(
            ELEM_TAIL, get_elements_tail,
            self.elem_xpath, default_target=[], element_path=self.elem_xpath
        )

    def assert_element_property_setter(self, prop, elem_func, elem_xpath=None, default=None, target=[], **elem_kwargs):
        """ Ensures the properties returned by the function are as expected for all data sources """

        self.assert_element_values_equal(prop, elem_func(None, **elem_kwargs), default)

        target = self._wrap_property(target)

        self.elem_data_inputs += ('<a/>',)  # Test with empty element too

        for data in self.elem_data_inputs:
            elems = self._wrap_property(elem_func(data, **elem_kwargs))

            for idx, val in enumerate((getattr(elem, prop) for elem in elems)):
                self.assert_element_values_equal(prop, val, target[idx])

    def test_set_element_tail(self):
        """ Tests set_element_tail with null and empty values, and with data from different sources """
        self.assert_element_property_setter(ELEM_TAIL, set_element_tail, target='x', element_tail='x')

    def test_set_element_tail_xpath(self):
        """ Tests set_element_tail with an XPATH with null and empty values, and data from different sources """

        self.assert_element_property_setter(
            ELEM_TAIL, set_element_tail,
            self.elem_xpath, target='x', element_path=self.elem_xpath, element_tail='x'
        )

    def test_set_element_text(self):
        """ Tests set_element_text with null and empty values, and with data from different sources """
        self.assert_element_property_setter(ELEM_TEXT, set_element_text, target='x', element_text='x')

    def test_set_element_text_xpath(self):
        """ Tests set_element_text with an XPATH with null and empty values, and data from different sources """

        self.assert_element_property_setter(
            ELEM_TEXT, set_element_text,
            self.elem_xpath, target='x', element_path=self.elem_xpath, element_text='x'
        )

    def test_set_elements_text(self):
        """ Tests set_elements_text with null and empty values, and with data from different sources """
        self.assert_element_property_setter(ELEM_TEXT, set_elements_text, default=[], target=['x'], text_values=['x'])

    def test_set_elements_texts(self):
        """ Tests set_elements_text with null, empty and multiple valid values, with data from different sources """

        target = ['x', 'y', 'z']
        self.assert_element_property_setter(ELEM_TEXT,
            set_elements_text, default=[], target=target[0], text_values=target
        )

    def test_set_elements_text_xpath(self):
        """ Tests set_elements_text with an XPATH with null and empty values, and with data from different sources """

        elem_xpath = self.elem_xpath
        self.assert_element_property_setter(
            ELEM_TEXT, set_elements_text,
            elem_xpath, default=[], target=['x'], element_path=elem_xpath, text_values=['x']
        )

    def test_set_elements_texts_xpath(self):
        """
        Tests set_elements_text with an XPATH with null, empty and multiple valid values,
        and with data from different sources
        """
        target = ['x', 'y', 'z']
        elem_xpath = self.elem_xpath

        self.assert_element_property_setter(
            ELEM_TEXT, set_elements_text,
            elem_xpath, default=[], target=target, element_path=elem_xpath, text_values=target
        )

    def test_set_elements_tail(self):
        """ Tests set_elements_tail with null and empty values, and with data from different sources """
        self.assert_element_property_setter(ELEM_TAIL,
            set_elements_tail, default=[], target=['x'], tail_values=['x']
        )

    def test_set_elements_tails(self):
        """ Tests set_elements_tail with null, empty and multiple valid values, with data from different sources """

        target = ['x', 'y', 'z']
        self.assert_element_property_setter(ELEM_TAIL,
            set_elements_tail, default=[], target=target[0], tail_values=target
        )

    def test_set_elements_tail_xpath(self):
        """ Tests set_elements_tail with an XPATH with null and empty values, and with data from different sources """

        elem_xpath = self.elem_xpath
        self.assert_element_property_setter(
            ELEM_TAIL, set_elements_tail,
            elem_xpath, default=[], target=['x'], element_path=elem_xpath, tail_values=['x']
        )

    def test_set_elements_tails_xpath(self):
        """
        Tests set_elements_tail with an XPATH with null, empty and multiple valid values,
        and with data from different sources
        """
        target = ['x', 'y', 'z']
        elem_xpath = self.elem_xpath

        self.assert_element_property_setter(
            ELEM_TAIL, set_elements_tail,
            elem_xpath, default=[], target=target, element_path=elem_xpath, tail_values=target
        )


class ElementUtilCheckTests(ElementUtilTestCase):

    def test_element_exists(self):
        """ Tests element_exists with different params including None """

        self.assertFalse(element_exists(None), 'None check failed for element_exists')

        for data in self.elem_data_inputs:
            self.assertTrue(element_exists(data), 'element_exists returned False for {0}'.format(type(data).__name__))

    def test_element_exists_xpath(self):
        """ Tests element_exists at an XPATH location with different element data """

        self.assertFalse(
            element_exists(None, self.elem_xpath),
            'None check failed for element_exists at XPATH "{0}"'.format(self.elem_xpath)
        )
        for data in self.elem_data_inputs:
            self.assertTrue(
                element_exists(data, self.elem_xpath),
                'element_exists returned False for {0} at XPATH "{1}"'.format(type(data).__name__, self.elem_xpath)
            )

    def assert_elements_exist(self, test_func, elem_xpaths=[], all_exist=False, target=True):
        """ Ensures element existence agrees with target for each data source """

        self.assertFalse(elements_exist(None, elem_xpaths, all_exist), 'None check failed for {0}'.format(test_func))

        for data in self.elem_data_inputs:
            exists = elements_exist(data, elem_xpaths, all_exist)

            self.assertEqual(
                exists, target,
                '{0}: elements_exist returned {1} for {2}'.format(test_func, exists, type(data).__name__)
            )

    def assert_element_is_empty(self, test_func, elem_xpath=None, target=True):
        """ Ensures element emptiness agrees with target for each data source """

        for data in self.elem_data_inputs:
            is_empty = element_is_empty(data, elem_xpath)

            self.assertEqual(
                is_empty, target,
                '{0}: element_is_empty returned {1} for {2}'.format(test_func, is_empty, type(data).__name__)
            )

    def test_elements_exist(self):
        """ Tests elements_exist with defaults with different element data """
        self.assert_elements_exist('test_elements_exist')

    def test_elements_exist_all_xpaths(self):
        """ Tests elements_exist at all specified XPATH locations with different element data """
        self.assert_elements_exist('test_elements_exist_all_xpaths', ('b', 'c'), True)

    def test_elements_exist_any_xpaths(self):
        """ Tests elements_exist at any of several XPATH locations with different element data """
        self.assert_elements_exist('test_elements_exist_any_xpaths', ('a', 'b', 'c'))

    def test_elements_exist_no_xpaths(self):
        """ Tests elements_exist at none of several XPATH locations with different element data """
        self.assert_elements_exist('test_elements_exist_no_xpaths', ('x', 'y', 'z'), target=False)

    def test_elements_exist_not_all_xpaths(self):
        """ Tests elements_exist at only some of several XPATH locations with different element data """
        self.assert_elements_exist('test_elements_exist_not_all_xpaths', ('a', 'b', 'c'), True, False)

    def test_element_is_empty(self):
        """ Tests element_is_empty with empty and non-empty values, and different data sources """

        for empty in (None, '<a />', '<a></a>'):
            self.assertTrue(element_is_empty(empty), 'Empty check failed for {0}: False'.format(str(empty)))

        for not_empty in ('<a>aaa</a>', '<a x="xxx"></a>', '<a><b /></a>', '<a><b></b></a>'):
            self.assertFalse(element_is_empty(not_empty), 'Empty check failed for {0}: True'.format(str(not_empty)))

        self.assert_element_is_empty('test_element_is_empty', target=False)

    def test_element_is_empty_xpath(self):
        """ Tests element_is_empty at an XPATH location with different non-empty element data sources """

        empties = ('<a />', '<a></a>', '<a><b /></a>', '<a><b></b></a>')
        for empty in empties:
            self.assertTrue(element_is_empty(empty, 'b'), 'Empty check failed for {0}: False'.format(str(empty)))

        not_empties = (
            '<a><b>bbb</b></a>', '<a><b></b>bbb</a>', '<a><b x="xxx"></b></a>',
            '<a><b><c /></b></a>', '<a><b><c></c></b></a>'
        )
        for not_empty in not_empties:
            self.assertFalse(
                element_is_empty(not_empty, 'b'), 'Empty check failed for {0}: True'.format(str(not_empty))
            )

        self.assert_element_is_empty('test_element_is_empty_xpath', self.elem_xpath, False)

    def test_element_is_not_empty_xpath(self):
        """ Tests element_is_empty at an XPATH location with different empty element data sources """
        self.assert_element_is_empty('test_element_is_not_empty_xpath', 'c/f')


class ElementUtilInsertRemoveTests(ElementUtilTestCase):

    def assert_element_inserted(self, **elem_kwargs):
        """ Ensures element inserts are done correctly at various indexes and for each data source  """

        insert_kwargs = {'elem_path': elem_kwargs[ELEM_NAME]}
        insert_kwargs.update(elem_kwargs[ELEM_ATTRIBS])

        # Test that an element has been inserted at different indices

        base_elem = fromstring(self.elem_data_str)

        inserted = insert_element(base_elem, 0, elem_txt='middle', **insert_kwargs)
        self.assert_elements_are_equal(base_elem.find(insert_kwargs['elem_path']), inserted)

        inserted = insert_element(base_elem, 0, elem_txt='first', **insert_kwargs)
        self.assert_elements_are_equal(base_elem.findall(insert_kwargs['elem_path'])[0], inserted)

        inserted = insert_element(base_elem, 2, elem_txt='last', **insert_kwargs)
        self.assert_elements_are_equal(base_elem.findall(insert_kwargs['elem_path'])[2], inserted)

        # Test that elements inserted into different data sources are valid

        insert_kwargs['elem_txt'] = elem_kwargs[ELEM_TEXT]

        for data in self.elem_data_inputs:
            inserted = insert_element(data, 0, **insert_kwargs)
            self.assertIsNotNone(inserted, 'Insert failed for {0}'.format(type(data).__name__))

            # All of the original values should be accessible through inserted
            for key, val in elem_kwargs.iteritems():
                elem_val = getattr(inserted, key)

                if '/' in val:
                    val = val.split('/')[-1]

                self.assertEqual(val, elem_val, '{0} was not inserted correctly for {1}: {2} != {3}'.format(
                    key, type(data).__name__, elem_val, val
                ))

    def assert_elements_removed(self, test_func, elem_xpaths, clear_empty=False):
        """ Ensures elements for all elem_xpaths in different data sources have been removed and cleared """

        self.assertIsNone(
            remove_elements(None, elem_xpaths, clear_empty), 'None check failed for {0}'.format(test_func)
        )
        self.assertEqual(
            remove_elements(self.elem_data_str, [], clear_empty), [],
            'Empty XPATH check failed for {0}'.format(test_func)
        )

        base_elem = fromstring(self.elem_data_str)
        is_xpath = isinstance(elem_xpaths, basestring)

        for data in self.elem_data_inputs:

            data = get_element(data) if clear_empty else data
            removed = remove_elements(data, elem_xpaths, clear_empty)

            if is_xpath:
                self.assert_element_removed(test_func, data, elem_xpaths, removed, base_elem, clear_empty)
            else:
                for xpath in elem_xpaths:
                    filtered = [rem for rem in removed if rem.tag in xpath]
                    self.assert_element_removed(test_func, data, xpath, filtered, base_elem, clear_empty)

    def assert_element_removed(self, test_func, data, elem_xpath, removed_elems, base_elem, clear_empty):
        """ Ensures removed_elems have been removed and cleared """

        if clear_empty:
            self.assert_removed_element_cleared(test_func, elem_xpath, data, removed_elems, base_elem)
        else:
            found = base_elem.findall(elem_xpath)

            ecount, rcount = len(found), len(removed_elems)
            self.assertEqual(
                ecount, rcount,
                'Only {0} of {1} elements were cleared for {2}'.format(rcount, ecount, test_func)
            )

            for idx, elem in enumerate(removed_elems):
                self.assert_elements_are_equal(found[idx], elem, elem_xpath)

    def assert_removed_element_cleared(self, test_func, elem_xpath, cleared_elem, removed_elems, base_elem):
        """ Ensures removed_elems are removed from cleared_elem, and present in the return value """

        elem_xroot = elem_xpath.split('/')[0]
        elem_xtags = elem_xpath.split('/')[1:]

        removed_tags = [rem.tag for rem in removed_elems]

        xpath = elem_xroot

        for xtag in elem_xtags:

            xpath += '/' + xtag
            ecount = len(base_elem.findall(xpath))
            rcount = removed_tags.count(xtag)

            self.assertEqual(
                ecount, rcount,
                'Only {0} of {1} elements were cleared for {2}'.format(rcount, ecount, test_func)
            )
            self.assertFalse(
                iselement(cleared_elem.find(xpath)),
                'Element {0} was not cleared for {1}'.format(cleared_elem.tag, test_func)
            )

    def test_insert_element(self):
        """ Tests insert_element with valid/invalid values, and with different data sources at various indices """

        self.assertIsNone(insert_element(None, None, None), 'Insert with all None check failed for insert_element')
        self.assertIsNone(
            insert_element(self.elem_data_str, None, None), 'Insert with empty path check failed for insert_element'
        )
        self.assertIsNone(
            insert_element(None, None, 'none'), 'Insert with empty data check failed for insert_element'
        )
        self.assert_element_inserted(tag='p', text='ppp', attrib={'q': 'qqq', 'r': 'rrr', 's': 'sss'})

    def test_insert_element_xpath(self):
        """ Tests insert_element at an XPATH location with different valid/invalid data sources at various indices """
        self.assert_element_inserted(tag='t/u/v', text='www', attrib={'x': 'xxx', 'y': 'yyy', 'z': 'zzz'})

    def test_remove_element(self):
        """ Tests remove_element with None, and for equality given different data sources """
        self.assert_element_function(remove_element, self.elem_xpath, element_path=self.elem_xpath)

    def test_remove_element_clear(self):
        """ Tests remove_element with clearing of empty elements from different data sources  """

        elem_xpath = 'c/g/h/i'
        base_elem = fromstring(self.elem_data_str)

        for data in self.elem_data_inputs:
            element = get_element(data)
            removed = remove_element(element, elem_xpath, True)

            self.assert_removed_element_cleared('test_remove_element_clear', elem_xpath, element, removed, base_elem)

    def test_remove_elements_single(self):
        """ Tests remove_elements with a single XPATH but different data sources """
        self.assert_elements_removed('test_remove_elements_single', self.elem_xpath)

    def test_remove_elements_single_clear(self):
        """ Tests remove_elements with a single XPATH, clearing empty elements from different data sources """
        self.assert_elements_removed('test_remove_elements_single_clear', 'c/g/h/i', clear_empty=True)

    def test_remove_elements_multiple(self):
        """ Tests remove_elements with multiple XPATHs and different data sources """
        self.assert_elements_removed('test_remove_elements_multiple', ('c/d', 'c/e', 'c/f', 'c/g/h/i'))

    def test_remove_elements_multiple_clear(self):
        """ Tests remove_elements with multiple XPATHs, clearing empty elements from different data sources """

        elem_xpaths = ('c/d', 'c/e', 'c/f', 'c/g/h/i')
        self.assert_elements_removed('test_remove_elements_multiple_clear', elem_xpaths, clear_empty=True)

    def test_remove_empty_element(self):
        parent_to_parse = '<a/>'
        element_path = ''
        target_element = ''
        remove_empty_element(parent_to_parse, element_path, target_element)


if __name__ == '__main__':
    unittest.main()
