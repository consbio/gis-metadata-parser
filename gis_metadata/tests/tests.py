import unittest

from os.path import os
from six import iteritems

from parserutils.collections import reduce_value, wrap_value
from parserutils.elements import element_exists, element_to_dict, element_to_string
from parserutils.elements import get_element_text, get_elements, get_remote_element
from parserutils.elements import clear_element, remove_element_attributes, set_element_attributes

from gis_metadata.fgdc_metadata_parser import FgdcParser, FGDC_ROOT
from gis_metadata.iso_metadata_parser import IsoParser, ISO_ROOTS, _iso_tag_formats
from gis_metadata.metadata_parser import MetadataParser, get_metadata_parser, get_parsed_content

from gis_metadata.exceptions import ParserError
from gis_metadata.utils import get_complex_definitions, get_supported_props
from gis_metadata.utils import DATE_TYPE, DATE_VALUES
from gis_metadata.utils import DATE_TYPE_SINGLE, DATE_TYPE_RANGE, DATE_TYPE_MISSING, DATE_TYPE_MULTIPLE
from gis_metadata.utils import ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS
from gis_metadata.utils import BOUNDING_BOX, DATES, LARGER_WORKS
from gis_metadata.utils import KEYWORDS_PLACE, KEYWORDS_THEME
from gis_metadata.utils import ParserProperty


TEST_TEMPLATE_CONSTANTS = {
    'dist_contact_org': 'ORG',
    'dist_contact_person': 'PERSON',
    'dist_address_type': 'PHYSICAL ADDRESS',
    'dist_address': 'ADDRESS LOCATION',
    'dist_city': 'CITY',
    'dist_state': 'STATE',
    'dist_postal': '12345',
    'dist_country': 'USA',
    'dist_phone': '123-456-7890',
    'dist_email': 'EMAIL@DOMAIN.COM',
}


class MetadataParserTestCase(unittest.TestCase):

    valid_complex_values = ('one', ['before', 'after'], ['first', 'next', 'last'])

    def setUp(self):
        sep = os.path.sep
        dir_name = os.path.dirname(os.path.abspath(__file__))

        self.data_dir = sep.join((dir_name, 'data'))
        self.fgdc_file = sep.join((self.data_dir, 'fgdc_metadata.xml'))
        self.iso_file = sep.join((self.data_dir, 'iso_metadata.xml'))

        # Initialize metadata files

        self.fgdc_metadata = open(self.fgdc_file)
        self.iso_metadata = open(self.iso_file)

        self.metadata_files = (self.fgdc_metadata, self.iso_metadata)

        # Define test file paths

        self.test_fgdc_file_path = '/'.join((self.data_dir, 'test_fgdc.xml'))
        self.test_iso_file_path = '/'.join((self.data_dir, 'test_iso.xml'))

        self.test_file_paths = (self.test_fgdc_file_path, self.test_iso_file_path)

    def assert_equal_for(self, parser_type, prop, value, target):
        self.assertEqual(
            value, target,
            'Parser property "{0}.{1}" does not equal target:{2}'.format(
                parser_type, prop, '\n\tparsed: "{0}" ({1})\n\texpected: "{2}" ({3})'.format(
                    value, type(value).__name__, target, type(target).__name__
                )
            )
        )

    def assert_reparsed_complex_for(self, parser, prop, value, target):

        setattr(parser, prop, value)

        parser_type = type(parser)
        parser_name = parser_type.__name__
        reparsed = getattr(parser_type(parser.serialize()), prop)

        if not isinstance(reparsed, (dict, list)):
            # Reparsed should not be a collection: do a single value comparison
            self.assert_equal_for(parser_name, prop, reparsed, target)

        elif isinstance(reparsed, type(target)) and len(target) != len(reparsed):
            # Reparsed and target equal in type, but lengths differ: do a single value comparison
            self.assert_equal_for(parser_name, prop, reparsed, target)

        elif isinstance(reparsed, dict):
            # Reparsed is a dict: compare each value with corresponding in target
            for key, val in iteritems(reparsed):
                self.assert_equal_for(
                    parser_name, '{0}.{1}'.format(prop, key), val, target.get(key, u'')
                )

        elif len(reparsed) <= 1:
            # Reparsed is empty or a single-item list: do a single value comparison
            self.assert_equal_for(parser_name, prop, reparsed, target)

        else:
            # Reparsed is a multiple-item list: compare each value with corresponding in target
            for idx, value in enumerate(reparsed):
                if not isinstance(value, dict):
                    self.assert_equal_for(parser_name, '{0}[{1}]'.format(prop, idx), value, target[idx])
                else:
                    for key, val in iteritems(value):
                        self.assert_equal_for(
                            parser_name, '{0}.{1}'.format(prop, key), val, target[idx].get(key, u'')
                        )


    def assert_reparsed_simple_for(self, parser, props, value, target):

        for prop in props:
            setattr(parser, prop, value)

        parser_type = type(parser)
        parser_name = parser_type.__name__
        reparsed = parser_type(parser.serialize())

        for prop in props:
            self.assert_equal_for(parser_name, prop, getattr(reparsed, prop), target)

    def assert_parser_conversion(self, content_parser, target_parser, comparison_type=''):
        converted = content_parser.convert_to(target_parser)

        self.assert_valid_parser(content_parser)
        self.assert_valid_parser(target_parser)

        self.assertFalse(
            converted is target_parser,
            '{0} conversion is returning the original {0} instance'.format(type(converted).__name__)
        )

        for prop in get_supported_props():
            self.assertEqual(
                getattr(content_parser, prop), getattr(converted, prop),
                '{0} {1}conversion does not equal original {2} content for {3}'.format(
                    type(converted).__name__, comparison_type, type(content_parser).__name__, prop
                )
            )

    def assert_parsers_are_equal(self, parser_1, parser_2):
        parser_type = type(parser_1).__name__

        self.assert_valid_parser(parser_1)
        self.assert_valid_parser(parser_2)

        for prop in get_supported_props():
            self.assert_equal_for(parser_type, prop, getattr(parser_1, prop), getattr(parser_2, prop))

    def assert_parser_after_write(self, parser_type, in_file, out_file_path, use_template=False):

        parser = parser_type(in_file, out_file_path)

        complex_defs = get_complex_definitions()

        # Update each value and read the file in again
        for prop in get_supported_props():

            if isinstance(parser, IsoParser) and prop == ATTRIBUTES:
                val = []  # The ISO standard stores attributes in an external file
            elif prop in (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS):
                val = [
                    {}.fromkeys(complex_defs[prop], 'test'),
                    {}.fromkeys(complex_defs[prop], prop)
                ]
            elif prop in (BOUNDING_BOX, LARGER_WORKS):
                val = {}.fromkeys(complex_defs[prop], 'test ' + prop)
            elif prop == DATES:
                val = {DATE_TYPE: DATE_TYPE_RANGE, DATE_VALUES: ['test', prop]}
            elif prop in (KEYWORDS_PLACE, KEYWORDS_THEME):
                val = ['test', prop]
            else:
                val = 'test ' + prop

            setattr(parser, prop, val)

        parser.write(use_template=use_template)

        with open(out_file_path) as out_file:
            self.assert_parsers_are_equal(parser, parser_type(out_file))

    def assert_valid_parser(self, parser, root=None):

        parser_type = type(parser.validate()).__name__

        self.assertIsNotNone(parser._xml_root, '{0} root not set'.format(parser_type))

        if root is not None:
            self.assertEqual(parser._xml_root, root)

        self.assertIsNotNone(parser._xml_tree)
        self.assertEqual(parser._xml_tree.getroot().tag, parser._xml_root)

    def assert_validates_for(self, parser, prop, invalid):

        valid = getattr(parser, prop)
        setattr(parser, prop, invalid)

        try:
            parser.validate()
        except Exception as e:
            # Not using self.assertRaises to customize the failure message
            self.assertEqual(type(e), ParserError, (
                'Property "{0}.{1}" does not raise ParserError for value: "{2}" ({3})'.format(
                    type(parser).__name__, prop, invalid, type(invalid).__name__
                )
            ))
        finally:
            setattr(parser, prop, valid)  # Reset value for next test

    def tearDown(self):

        for metadata_file in self.metadata_files:
            metadata_file.close()

        for test_file_path in self.test_file_paths:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)


class MetadataParserTemplateTests(MetadataParserTestCase):

    def assert_template_after_write(self, parser_type, out_file_path):

        parser = parser_type(out_file_or_path=out_file_path)

        # Reverse each value and read the file in again
        for prop, val in iteritems(TEST_TEMPLATE_CONSTANTS):
            setattr(parser, prop, val[::-1])

        parser.write()

        with open(out_file_path) as out_file:
            self.assert_parsers_are_equal(parser, parser_type(out_file))

    def assert_valid_template(self, parser, root):

        parser_type = type(parser.validate()).__name__

        self.assertIsNotNone(parser._xml_root, '{0} root not set'.format(parser_type))
        self.assertEqual(parser._xml_root, root)
        self.assertIsNotNone(parser._xml_tree)
        self.assertEqual(parser._xml_tree.getroot().tag, parser._xml_root)

        for prop, val in iteritems(TEST_TEMPLATE_CONSTANTS):
            parsed_val = getattr(parser, prop)
            self.assertEqual(parsed_val, val, (
                '{0} property {1}, "{2}", does not equal "{3}"'.format(parser_type, prop, parsed_val, val)
            ))

    def test_fgdc_template_values(self):
        self.assert_valid_template(FgdcParser(**TEST_TEMPLATE_CONSTANTS), root='metadata')

    def test_iso_template_values(self):
        self.assert_valid_template(IsoParser(**TEST_TEMPLATE_CONSTANTS), root='MD_Metadata')

    def test_template_conversion(self):
        fgdc_template = FgdcParser()
        iso_template = IsoParser()

        self.assert_parser_conversion(fgdc_template, iso_template, 'template')
        self.assert_parser_conversion(iso_template, fgdc_template, 'template')

    def test_template_conversion_bad_roots(self):

        for bad_root in (None, '', '<badRoot/>', '<badRoot>invalid</badRoot>'):
            with self.assertRaises(ParserError):
                get_parsed_content(bad_root)
            with self.assertRaises(ParserError):
                get_metadata_parser(bad_root)

            if bad_root is not None:
                with self.assertRaises(ParserError):
                    IsoParser(bad_root)
                with self.assertRaises(ParserError):
                    FgdcParser(bad_root)

        with self.assertRaises(ParserError):
            IsoParser(FGDC_ROOT.join(('<', '></', '>')))

        for iso_root in ISO_ROOTS:
            with self.assertRaises(ParserError):
                FgdcParser(iso_root.join(('<', '></', '>')))

    def test_template_conversion_from_dict(self):

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser({'name': FGDC_ROOT}), 'dict-based template'
        )

        fgdc_template = FgdcParser()
        fgdc_template.dist_address_type = u''  # Address type not supported for ISO

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                fgdc_template, get_metadata_parser({'name': iso_root}), 'dict-based template'
            )

    def test_template_conversion_from_str(self):

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(FGDC_ROOT.join(('<', '></', '>'))), 'str-based template'
        )

        fgdc_template = FgdcParser()
        fgdc_template.dist_address_type = u''  # Address type not supported for ISO

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                fgdc_template, get_metadata_parser(iso_root.join(('<', '></', '>'))), 'str-based template'
            )

    def test_template_conversion_from_type(self):

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(FgdcParser), 'type-based template'
        )

        fgdc_template = FgdcParser()
        fgdc_template.dist_address_type = u''  # Address type not supported for ISO

        self.assert_parser_conversion(
            fgdc_template, get_metadata_parser(IsoParser), 'type-based template'
        )

    def test_write_template(self):

        self.assert_template_after_write(FgdcParser, self.test_fgdc_file_path)
        self.assert_template_after_write(IsoParser, self.test_iso_file_path)


class MetadataParserTests(MetadataParserTestCase):

    def test_generic_parser(self):
        """ Covers code that enforces certain behaviors for custom parsers """

        parser = MetadataParser()

        with self.assertRaises(ParserError):
            ParserProperty(None, None)  # Un-callable property parser

        with self.assertRaises(ParserError):
            ParserProperty(list, None)  # Un-callable property updater

        data_map_1 = parser._data_map
        parser._init_data_map()
        data_map_2 = parser._data_map

        self.assertIs(data_map_1, data_map_2, 'Data map was reinitialized after instantiation')

        with self.assertRaises(ParserError):
            parser.write()

    def test_specific_parsers(self):
        """ Ensures code enforces certain behaviors for existing parsers """

        for parser_type in (FgdcParser, IsoParser):
            parser = parser_type()

            data_map_1 = parser._data_map
            parser._init_data_map()
            data_map_2 = parser._data_map

            self.assertIs(data_map_1, data_map_2, 'Data map was reinitialized after instantiation')

            with self.assertRaises(ParserError):
                parser.write()

            with self.assertRaises(ParserError):
                parser._data_map.clear()
                parser.validate()

    def test_fgdc_parser(self):
        """ Tests behavior unique to the FGDC parser """

        contacts_def = get_complex_definitions()[CONTACTS]

        # Remove the contact organization completely
        fgdc_element = get_remote_element(self.fgdc_file)
        for contact_element in get_elements(fgdc_element, 'idinfo/ptcontac'):
            if element_exists(contact_element, 'cntinfo/cntorgp'):
                clear_element(contact_element)

        # Assert that the contact organization has been read in
        fgdc_parser = FgdcParser(element_to_string(fgdc_element))
        for key in contacts_def:
            for contact in fgdc_parser.contacts:
                self.assertIsNotNone(contact[key], 'Failed to read contact.{0}'.format(key))

        # Remove the contact person completely
        fgdc_element = get_remote_element(self.fgdc_file)
        for contact_element in get_elements(fgdc_element, 'idinfo/ptcontac'):
            if element_exists(contact_element, 'cntinfo/cntperp'):
                clear_element(contact_element)

        # Assert that the contact organization has been read in
        fgdc_parser = FgdcParser(element_to_string(fgdc_element))
        for key in contacts_def:
            for contact in fgdc_parser.contacts:
                self.assertIsNotNone(contact[key], 'Failed to read updated contact.{0}'.format(key))

    def test_iso_parser(self):
        """ Tests behavior unique to the ISO parser """

        # Remove the attribute details href attribute
        iso_element = get_remote_element(self.iso_file)
        for citation_element in get_elements(iso_element, _iso_tag_formats['_attr_citation']):
            removed = remove_element_attributes(citation_element, 'href')

        # Assert that the href attribute was removed and a different one was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attribute_href = iso_parser._attr_details_file_url

        self.assertIsNotNone(removed, 'ISO file URL was not removed')
        self.assertIsNotNone(attribute_href, 'ISO href attribute was not read in')
        self.assertNotEqual(attribute_href, removed, 'ISO href attribute is the same as the one removed')

        # Remove the attribute details linkage attribute
        iso_element = get_remote_element(self.iso_file)
        for linkage_element in get_elements(iso_element, _iso_tag_formats['_attr_url']):
            removed = get_element_text(linkage_element)
            clear_element(linkage_element)

        # Assert that the linkage URL was removed and a different one was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        linkage_url = iso_parser._attr_details_file_url

        self.assertIsNotNone(removed, 'ISO linkage URL was not removed')
        self.assertIsNotNone(linkage_url, 'ISO linkage URL was not read in')
        self.assertNotEqual(linkage_url, removed, 'ISO file URL is the same as the one removed')

        # Change the href attribute so that it is invalid
        for citation_element in get_elements(iso_element, _iso_tag_formats['_attr_citation']):
            removed = set_element_attributes(citation_element, href='neither url nor file')

        # Assert that the href attribute was removed and a different one was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attributes = iso_parser.attributes
        self.assertIsNone(iso_parser._attr_details_file_url, 'Invalid URL stored with parser')
        self.assertEqual(attributes, [], 'Invalid parsed attributes: {0}'.format(attributes))

    def test_parser_conversion(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        self.assert_parser_conversion(fgdc_parser, iso_parser, 'file')
        self.assert_parser_conversion(iso_parser, fgdc_parser, 'file')

    def test_conversion_from_dict(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        fgdc_parser.dist_address_type = u''  # Address type not supported for ISO

        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(element_to_dict(fgdc_parser._xml_tree, recurse=True)), 'dict-based'
        )

        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(element_to_dict(iso_parser._xml_tree, recurse=True)), 'dict-based'
        )

    def test_conversion_from_str(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        fgdc_parser.dist_address_type = u''  # Address type not supported for ISO

        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(fgdc_parser.serialize()), 'str-based'
        )

        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(iso_parser.serialize()), 'str-based'
        )

    def test_reparse_complex_lists(self):
        complex_defs = get_complex_definitions()
        complex_lists = (ATTRIBUTES, CONTACTS, DIGITAL_FORMS)

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty complex lists
            for prop in complex_lists:
                for empty in (None, [], [{}], [{}.fromkeys(complex_defs[prop], u'')]):
                    self.assert_reparsed_complex_for(parser, prop, empty, [])

            # Test reparsed valid complex lists (strings and lists for each property in each struct)
            for prop in complex_lists:
                complex_list = []

                for val in self.valid_complex_values:
                    # The ISO standard stores attributes in an external file
                    wont_parse = isinstance(parser, IsoParser) and prop == ATTRIBUTES

                    # Test with single unwrapped value
                    next_complex = {}.fromkeys(complex_defs[prop], val)
                    target_list = [] if wont_parse else wrap_value(next_complex)
                    self.assert_reparsed_complex_for(parser, prop, next_complex, target_list)

                    # Test with accumulated list of values
                    complex_list.append({}.fromkeys(complex_defs[prop], val))
                    target_list = [] if wont_parse else wrap_value(complex_list)

                    self.assert_reparsed_complex_for(parser, prop, complex_list, target_list)

    def test_reparse_complex_structs(self):
        complex_defs = get_complex_definitions()
        complex_structs = (BOUNDING_BOX, LARGER_WORKS)

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty complex structures
            for prop in complex_structs:
                for empty in (None, {}, {}.fromkeys(complex_defs[prop], u'')):
                    self.assert_reparsed_complex_for(parser, prop, empty, {})

            # Test reparsed valid complex structures
            for prop in complex_structs:
                for val in self.valid_complex_values:
                    complex_struct = {}.fromkeys(complex_defs[prop], val)
                    self.assert_reparsed_complex_for(parser, prop, complex_struct, complex_struct)

    def test_reparse_dates(self):
        valid_values = (
            (DATE_TYPE_SINGLE, ['one']),
            (DATE_TYPE_RANGE, ['before', 'after']),
            (DATE_TYPE_MULTIPLE, ['first', 'next', 'last'])
        )

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty dates
            for empty in (None, {}, {DATE_TYPE: u'', DATE_VALUES: []}):
                self.assert_reparsed_complex_for(parser, DATES, empty, {})

            # Test reparsed valid dates
            for val in valid_values:
                complex_struct = {DATE_TYPE: val[0], DATE_VALUES: val[1]}
                self.assert_reparsed_complex_for(
                    parser, DATES, complex_struct, complex_struct
                )

    def test_reparse_keywords(self):

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty keywords
            for keywords in ('', u'', []):
                self.assert_reparsed_complex_for(parser, KEYWORDS_PLACE, keywords, [])
                self.assert_reparsed_complex_for(parser, KEYWORDS_THEME, keywords, [])

            # Test reparsed valid keywords
            for keywords in ('keyword', ['keyword', 'list']):
                self.assert_reparsed_complex_for(parser, KEYWORDS_PLACE, keywords, wrap_value(keywords))
                self.assert_reparsed_complex_for(parser, KEYWORDS_THEME, keywords, wrap_value(keywords))

    def test_reparse_process_steps(self):
        proc_step_def = get_complex_definitions()[PROCESS_STEPS]

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty process steps
            for empty in (None, [], [{}], [{}.fromkeys(proc_step_def, u'')]):
                self.assert_reparsed_complex_for(parser, PROCESS_STEPS, empty, [])

            complex_list = []

            # Test reparsed valid process steps
            for val in self.valid_complex_values:
                complex_struct = {}.fromkeys(proc_step_def, val)

                # Process steps must have a single string value for all but sources
                complex_struct.update({
                    k: ', '.join(wrap_value(v)) for k, v in iteritems(complex_struct) if k != 'sources'
                })

                complex_list.append(complex_struct)

                self.assert_reparsed_complex_for(parser, PROCESS_STEPS, complex_list, complex_list)

    def test_reparse_simple_values(self):

        complex_props = set(get_complex_definitions().keys())
        required_props = set(get_supported_props())

        simple_props = required_props.difference(complex_props)
        simple_props = simple_props.difference({KEYWORDS_PLACE, KEYWORDS_THEME})

        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        simple_empty_vals = ('', u'', [])
        simple_valid_vals = ('value', ['item', 'list'])

        for parser in (fgdc_parser, iso_parser):

            # Test reparsed empty values
            for val in simple_empty_vals:
                self.assert_reparsed_simple_for(parser, simple_props, val, '')

            # Test reparsed valid values
            for val in simple_valid_vals:
                self.assert_reparsed_simple_for(parser, simple_props, val, val)

    def test_validate_complex_lists(self):
        complex_props = (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS)

        invalid_values = ('', u'', {'x': 'xxx'}, [{'x': 'xxx'}], set(), tuple())

        for parser in (FgdcParser().validate(), IsoParser().validate()):
            for prop in complex_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_validate_complex_structs(self):
        complex_props = (BOUNDING_BOX, DATES, LARGER_WORKS)

        invalid_values = ('', u'', {'x': 'xxx'}, list(), set(), tuple())

        for parser in (FgdcParser().validate(), IsoParser().validate()):
            for prop in complex_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_validate_dates(self):
        invalid_values = (
            (DATE_TYPE_MISSING, ['present']),
            (DATE_TYPE_MULTIPLE, ['single']),
            (DATE_TYPE_MULTIPLE, ['first', 'last']),
            (DATE_TYPE_RANGE, []),
            (DATE_TYPE_RANGE, ['just one']),
            (DATE_TYPE_SINGLE, []),
            (DATE_TYPE_SINGLE, ['one', 'two']),
            ('unknown', ['unknown'])
        )

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):
            for val in invalid_values:
                self.assert_validates_for(parser, DATES, {DATE_TYPE: val[0], DATE_VALUES: val[1]})

    def test_validate_simple_values(self):
        complex_props = set(get_complex_definitions().keys())
        simple_props = set(get_supported_props()).difference(complex_props)

        invalid_values = (None, [None], dict(), [dict()], set(), [set()], tuple(), [tuple()])

        for parser in (FgdcParser().validate(), IsoParser().validate()):
            for prop in simple_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_write_values(self):

        self.assert_parser_after_write(FgdcParser, self.fgdc_metadata, self.test_fgdc_file_path)
        self.assert_parser_after_write(IsoParser, self.iso_metadata, self.test_iso_file_path)

    def test_write_values_to_template(self):

        self.assert_parser_after_write(FgdcParser, self.fgdc_metadata, self.test_fgdc_file_path, True)
        self.assert_parser_after_write(IsoParser, self.iso_metadata, self.test_iso_file_path, True)
