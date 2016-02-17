import unittest

from os.path import os

from gis_metadata.metadata.fgdc_metadata_parser import FgdcParser, FGDC_ROOT
from gis_metadata.metadata.iso_metadata_parser import IsoParser, ISO_ROOTS
from gis_metadata.metadata.metadata_parser import get_metadata_parser

from gis_metadata.metadata.parser_utils import get_complex_definitions, get_required_keys, get_xml_constants
from gis_metadata.metadata.parser_utils import reduce_value, wrap_value
from gis_metadata.metadata.parser_utils import DATE_TYPE, DATE_VALUES
from gis_metadata.metadata.parser_utils import DATE_TYPE_SINGLE, DATE_TYPE_RANGE, DATE_TYPE_MULTIPLE
from gis_metadata.metadata.parser_utils import ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS
from gis_metadata.metadata.parser_utils import BOUNDING_BOX, DATES, LARGER_WORKS
from gis_metadata.metadata.parser_utils import KEYWORDS_PLACE, KEYWORDS_THEME
from gis_metadata.metadata.parser_utils import ParserException

from gis_metadata.xml.element_utils import element_to_dict


class MetadataParserTestCase(unittest.TestCase):

    valid_complex_values = ('one', ['before', 'after'], ['first', 'next', 'last'])

    def setUp(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')

        # Initialize metadata files

        self.fgdc_metadata = open('/'.join((self.data_dir, 'fgdc_metadata.xml')))
        self.iso_metadata = open('/'.join((self.data_dir, 'iso_metadata.xml')))

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

    def assert_reparsed_complex_for(self, parser, prop, value, target, exclude=(), sub_prop=None):

        setattr(parser, prop, value)

        parser_type = type(parser)
        reparsed = getattr(parser_type(parser.serialize()), prop)
        sub_prop = sub_prop or prop

        if not isinstance(reparsed, (dict, list)):
            self.assert_equal_for(parser_type.__name__, sub_prop, reparsed, target)
        elif isinstance(reparsed, list):
            for idx, val in enumerate(reparsed):
                self.assert_reparsed_complex_for(
                    parser, prop, val, target[idx], exclude, sub_prop='{0}[{1}]'.format(prop, idx)
                )
        else:
            target = target or {}
            for key, val in reparsed.iteritems():
                if key not in exclude:
                    self.assert_equal_for(
                        parser_type.__name__, '{0}.{1}'.format(sub_prop, key), val, target.get(key, '')
                    )

    def assert_reparsed_simple_for(self, parser, props, value, target, exclude=()):

        for prop in props:
            setattr(parser, prop, value)

        parser_type = type(parser)
        reparsed = parser_type(parser.serialize())

        for prop in props:
            self.assert_equal_for(parser_type.__name__, prop, getattr(reparsed, prop), target)

    def assert_parser_conversion(self, content_parser, target_parser, comparison_type=''):
        converted = content_parser.convert_to(target_parser)

        self.assertFalse(
            converted is target_parser,
            '{0} conversion is returning the original {0} instance'.format(type(converted).__name__)
        )

        for prop in get_required_keys():
            self.assertEqual(
                getattr(content_parser, prop), getattr(converted, prop),
                '{0} {1}conversion does not equal original {2} content for {3}'.format(
                    type(converted).__name__, comparison_type, type(content_parser).__name__, prop
                )
            )

    def assert_parsers_are_equal(self, parser_1, parser_2):
        parser_type = type(parser_1).__name__

        for prop in get_required_keys():
            self.assert_equal_for(parser_type, prop, getattr(parser_1, prop), getattr(parser_2, prop))

    def assert_template_after_write(self, parser_type, out_file_path):

        parser = parser_type(out_file_or_path=out_file_path)

        if os.path.exists(out_file_path):
            os.remove(out_file_path)

        # Reverse each value and read the file in again
        for prop, val in get_xml_constants().iteritems():
            setattr(parser, prop, val[::-1])

        parser.write()

        with open(out_file_path) as out_file:
            self.assert_parsers_are_equal(parser, parser_type(out_file))

    def assert_parser_after_write(self, parser_type, in_file, out_file_path, use_template=False):

        parser = parser_type(in_file, out_file_path)

        if os.path.exists(out_file_path):
            os.remove(out_file_path)

        complex_defs = get_complex_definitions()

        # Update each value and read the file in again
        for prop in get_required_keys():

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

    def assert_validates_for(self, parser, prop, invalid):

        valid = getattr(parser, prop)
        setattr(parser, prop, invalid)

        try:
            parser.validate()
        except Exception as e:
            # Not using self.assertRaises to customize the failure message
            self.assertEqual(type(e), ParserException, (
                'Property "{0}.{1}" does not raise ParserException for value: "{2}" ({3})'.format(
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

    def setUp(self):
        super(MetadataParserTemplateTests, self).setUp()

    def assert_valid_template(self, parser, exclude=()):

        parser_type = type(parser.validate()).__name__

        for prop, val in get_xml_constants().iteritems():
            if prop not in exclude:
                parsed_val = getattr(parser, prop)

                self.assertEqual(parsed_val, val, (
                    '{0} property {1}, "{2}", does not equal "{3}"'.format(
                        parser_type, prop, parsed_val, val
                    )
                ))

    def test_fgdc_template_values(self):
        self.assert_valid_template(FgdcParser())

    def test_iso_template_values(self):
        self.assert_valid_template(IsoParser(), exclude=('dist_address_type'))

    def test_template_conversion(self):
        fgdc_template = FgdcParser()
        iso_template = IsoParser()

        self.assert_parser_conversion(fgdc_template, iso_template, 'template')
        self.assert_parser_conversion(iso_template, fgdc_template, 'template')

    def test_template_conversion_from_dict(self):

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser({'name': FGDC_ROOT}), 'dict-based template'
        )

        fgdc_template = FgdcParser()
        fgdc_template.dist_address_type = ''  # Address type not supported for ISO

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                fgdc_template, get_metadata_parser({'name': iso_root}), 'dict-based template'
            )

    def test_template_conversion_from_str(self):

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(FGDC_ROOT.join(('<', '></', '>'))), 'str-based template'
        )

        fgdc_template = FgdcParser()
        fgdc_template.dist_address_type = ''  # Address type not supported for ISO

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                fgdc_template, get_metadata_parser(iso_root.join(('<', '></', '>'))), 'str-based template'
            )

    def test_write_template(self):

        self.assert_template_after_write(FgdcParser, self.test_fgdc_file_path)
        self.assert_template_after_write(IsoParser, self.test_iso_file_path)

    def tearDown(self):
        super(MetadataParserTemplateTests, self).tearDown()


class MetadataParserTests(MetadataParserTestCase):

    def setUp(self):
        super(MetadataParserTests, self).setUp()

    def test_parser_conversion(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        self.assert_parser_conversion(fgdc_parser, iso_parser, 'file')
        self.assert_parser_conversion(iso_parser, fgdc_parser, 'file')

    def test_conversion_from_dict(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        fgdc_parser.dist_address_type = ''  # Address type not supported for ISO

        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(element_to_dict(fgdc_parser._xml_tree, True)), 'dict-based'
        )

        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(element_to_dict(iso_parser._xml_tree, True)), 'dict-based'
        )

    def test_conversion_from_str(self):
        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        fgdc_parser.dist_address_type = ''  # Address type not supported for ISO

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
                for empty in (None, [], [{}], [{}.fromkeys(complex_defs[prop], '')]):
                    self.assert_reparsed_complex_for(parser, prop, empty, [])

            # Test reparsed valid complex lists (strings and lists for each property in each struct)
            for prop in complex_lists:
                complex_list = []

                for val in self.valid_complex_values:
                    complex_list.append({}.fromkeys(complex_defs[prop], val))

                    # The ISO standard stores attributes in an external file
                    if isinstance(parser, IsoParser) and prop == ATTRIBUTES:
                        target_list = []
                    else:
                        target_list = reduce_value(complex_list)

                    self.assert_reparsed_complex_for(parser, prop, complex_list, target_list)

    def test_reparse_complex_structs(self):
        complex_defs = get_complex_definitions()
        complex_structs = (BOUNDING_BOX, LARGER_WORKS)

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty complex structures
            for prop in complex_structs:
                for empty in (None, {}, {}.fromkeys(complex_defs[prop], '')):
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
            for empty in (None, {}, {DATE_TYPE: '', DATE_VALUES: []}):
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
            for keywords in ('', []):
                self.assert_reparsed_complex_for(parser, KEYWORDS_PLACE, keywords, [])
                self.assert_reparsed_complex_for(parser, KEYWORDS_THEME, keywords, [])

            # Test reparsed valid keywords
            for keywords in ('keyword', ['keyword', 'list']):
                self.assert_reparsed_complex_for(parser, KEYWORDS_PLACE, keywords, keywords)
                self.assert_reparsed_complex_for(parser, KEYWORDS_THEME, keywords, keywords)

    def test_reparse_process_steps(self):
        proc_step_def = get_complex_definitions()[PROCESS_STEPS]

        for parser in (FgdcParser(self.fgdc_metadata), IsoParser(self.iso_metadata)):

            # Test reparsed empty process steps
            for empty in (None, [], [{}], [{}.fromkeys(proc_step_def, '')]):
                self.assert_reparsed_complex_for(parser, PROCESS_STEPS, empty, [])

            complex_list = []

            # Test reparsed valid process steps
            for val in self.valid_complex_values:
                complex_struct = {}.fromkeys(proc_step_def, val)

                # Process steps must have a single string value for all but sources
                complex_struct.update({
                    k: ', '.join(wrap_value(v)) for k, v in complex_struct.iteritems() if k != 'sources'
                })

                complex_list.append(complex_struct)

                self.assert_reparsed_complex_for(
                    parser, PROCESS_STEPS, complex_list, reduce_value(complex_list)
                )

    def test_reparse_simple_values(self):

        complex_props = set(get_complex_definitions().keys())
        required_props = set(get_required_keys())

        simple_props = required_props.difference(complex_props)
        simple_props = simple_props.difference({KEYWORDS_PLACE, KEYWORDS_THEME})

        fgdc_parser = FgdcParser(self.fgdc_metadata)
        iso_parser = IsoParser(self.iso_metadata)

        simple_empty_vals = ('', [])
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

        invalid_values = ('', {'x': 'xxx'}, [{'x': 'xxx'}], set(), tuple())

        for parser in (FgdcParser().validate(), IsoParser().validate()):
            for prop in complex_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_validate_complex_structs(self):
        complex_props = (BOUNDING_BOX, DATES, LARGER_WORKS)

        invalid_values = ('', {'x': 'xxx'}, list(), set(), tuple())

        for parser in (FgdcParser().validate(), IsoParser().validate()):
            for prop in complex_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_validate_simple_values(self):
        complex_props = set(get_complex_definitions().keys())
        simple_props = set(get_required_keys()).difference(complex_props)

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

    def tearDown(self):
        super(MetadataParserTests, self).tearDown()


if __name__ == '__main__':
    unittest.main()
