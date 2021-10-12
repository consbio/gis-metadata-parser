import io
import mock
import unittest

from os.path import os

from parserutils.collections import wrap_value
from parserutils.elements import element_exists, element_to_dict, element_to_string
from parserutils.elements import clear_element, get_element, get_element_text, get_elements, get_remote_element
from parserutils.elements import insert_element, remove_element, remove_element_attributes, set_element_attributes

from gis_metadata.arcgis_metadata_parser import ArcGISParser, ARCGIS_NODES, ARCGIS_ROOTS
from gis_metadata.fgdc_metadata_parser import FgdcParser, FGDC_ROOT
from gis_metadata.iso_metadata_parser import IsoParser, ISO_ROOTS, ISO_TAG_FORMATS
from gis_metadata.metadata_parser import MetadataParser, get_metadata_parser, get_parsed_content

from gis_metadata.exceptions import ConfigurationError, InvalidContent, NoContent, ValidationError
from gis_metadata.utils import DATE_TYPE, DATE_VALUES
from gis_metadata.utils import DATE_TYPE_SINGLE, DATE_TYPE_RANGE, DATE_TYPE_MISSING, DATE_TYPE_MULTIPLE
from gis_metadata.utils import ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS
from gis_metadata.utils import BOUNDING_BOX, DATES, LARGER_WORKS, RASTER_INFO
from gis_metadata.utils import KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME
from gis_metadata.utils import COMPLEX_DEFINITIONS, SUPPORTED_PROPS, ParserProperty
from gis_metadata.utils import format_xpaths, get_default_for_complex, parse_property, update_property
from gis_metadata.utils import validate_complex, validate_complex_list, validate_dates


KEYWORD_PROPS = (KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME)

TEST_TEMPLATE_VALUES = {
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

TEST_METADATA_VALUES = {
    'abstract': 'Test Abstract',
    'attribute_accuracy': 'Test Attribute Accuracy',
    'attributes': [{
        'definition': 'Attributes Definition 1',
        'label': 'Attributes Label 1',
        'aliases': 'Attributes Alias 1',
        'definition_source': 'Attributes Definition Source 1'
    }, {
        'definition': 'Attributes Definition 2',
        'label': 'Attributes Label 2',
        'aliases': 'Attributes Alias 2',
        'definition_source': 'Attributes Definition Source 2'
    }, {
        'definition': 'Attributes Definition 3',
        'label': 'Attributes Label 3',
        'aliases': 'Attributes Alias 3',
        'definition_source': 'Attributes Definition Source 3'
    }],
    'bounding_box': {
        'east': '179.99999999998656',
        'north': '87.81211601444309',
        'west': '-179.99999999998656',
        'south': '-86.78249642712764'
    },
    'contacts': [{
        'name': 'Contact Name 1', 'email': 'Contact Email 1',
        'position': 'Contact Position 1', 'organization': 'Contact Organization 1'
    }, {
        'name': 'Contact Name 2', 'email': 'Contact Email 2',
        'position': 'Contact Position 2', 'organization': 'Contact Organization 2'
    }],
    'dataset_completeness': 'Test Dataset Completeness',
    'data_credits': 'Test Data Credits',
    'dates': {'type': 'multiple', 'values': ['Multiple Date 1', 'Multiple Date 2', 'Multiple Date 3']},
    'digital_forms': [{
        'access_desc': 'Digital Form Access Description 1',
        'version': 'Digital Form Version 1',
        'specification': 'Digital Form Specification 1',
        'access_instrs': 'Digital Form Access Instructions 1',
        'name': 'Digital Form Name 1',
        'network_resource': 'Digital Form Resource 1',
        'content': 'Digital Form Content 1',
        'decompression': 'Digital Form Decompression 1'
    }, {
        'access_desc': 'Digital Form Access Description 2',
        'version': 'Digital Form Version 2',
        'specification': 'Digital Form Specification 2',
        'access_instrs': 'Digital Form Access Instructions 2',
        'name': 'Digital Form Name 2',
        'network_resource': 'Digital Form Resource 2',
        'content': 'Digital Form Content 2',
        'decompression': 'Digital Form Decompression 2'
    }],
    'dist_address': 'Test Distribution Address',
    'dist_address_type': 'Test Distribution Address Type',
    'dist_city': 'Test Distribution City',
    'dist_contact_org': 'Test Distribution Org',
    'dist_contact_person': 'Test Distribution Person',
    'dist_country': 'US',
    'dist_email': 'Test Distribution Email',
    'dist_liability': 'Test Distribution Liability',
    'dist_phone': 'Test Distribution Phone',
    'dist_postal': '12345',
    'dist_state': 'OR',
    'larger_works': {
        'publish_place': 'Larger Works Place',
        'publish_info': 'Larger Works Info',
        'other_citation': 'Larger Works Other Citation',
        'online_linkage': 'http://test.largerworks.online.linkage.com',
        'publish_date': 'Larger Works Date',
        'title': 'Larger Works Title',
        'edition': 'Larger Works Edition',
        'origin': ['Larger Works Originator']
    },
    'raster_info': {
        'dimensions': 'Test # Dimensions',
        'row_count': 'Test Row Count',
        'column_count': 'Test Column Count',
        'vertical_count': 'Test Vertical Count',
        'x_resolution': 'Test X Resolution',
        'y_resolution': 'Test Y Resolution',
    },
    'online_linkages': 'http://test.onlinelinkages.org',
    'originators': 'Test Originators',
    'other_citation_info': 'Test Other Citation Info',
    'place_keywords': ['Oregon', 'Washington'],
    'process_steps': [{
        'sources': ['Process Step Sources 1.1', 'Process Step Sources 1.2'],
        'description': 'Process Step Description 1',
        'date': 'Process Step Date 1'
    }, {
        'sources': [],
        'description': 'Process Step Description 2',
        'date': ''
    }, {
        'sources': [], 'description': '', 'date': 'Process Step Date 3'
    }, {
        'sources': ['Process Step Sources 4.1', 'Process Step Sources 4.2'],
        'description': 'Process Step Description 4',
        'date': ''
    }],
    'processing_fees': 'Test Processing Fees',
    'processing_instrs': 'Test Processing Instructions',
    'purpose': 'Test Purpose',
    'publish_date': 'Test Publish Date',
    'resource_desc': 'Test Resource Description',
    'stratum_keywords': ['Layer One', 'Layer Two'],
    'supplementary_info': 'Test Supplementary Info',
    'tech_prerequisites': 'Test Technical Prerequisites',
    'temporal_keywords': ['Now', 'Later'],
    'thematic_keywords': ['Ecoregion', 'Risk', 'Threat', 'Habitat'],
    'title': 'Test Title',
    'use_constraints': 'Test Use Constraints'
}
TEST_REMOTE_ISO_ATTRIBUTES = {
    'href': [{
        'definition': 'HREF Attributes Definition 1',
        'label': 'HREF Attributes Label 1',
        'aliases': 'HREF Attributes Alias 1',
        'definition_source': 'HREF Attributes Definition Source 1'
    }, {
        'definition': 'HREF Attributes Definition 2',
        'label': 'HREF Attributes Label 2',
        'aliases': 'HREF Attributes Alias 2',
        'definition_source': 'HREF Attributes Definition Source 2'
    }, {
        'definition': 'HREF Attributes Definition 3',
        'label': 'HREF Attributes Label 3',
        'aliases': 'HREF Attributes Alias 3',
        'definition_source': 'HREF Attributes Definition Source 3'
    }],
    'linkage': [{
        'definition': 'LINKAGE Attributes Definition 1',
        'label': 'LINKAGE Attributes Label 1',
        'aliases': 'LINKAGE Attributes Alias 1',
        'definition_source': 'LINKAGE Attributes Definition Source 1'
    }, {
        'definition': 'LINKAGE Attributes Definition 2',
        'label': 'LINKAGE Attributes Label 2',
        'aliases': 'LINKAGE Attributes Alias 2',
        'definition_source': 'LINKAGE Attributes Definition Source 2'
    }, {
        'definition': 'LINKAGE Attributes Definition 3',
        'label': 'LINKAGE Attributes Label 3',
        'aliases': 'LINKAGE Attributes Alias 3',
        'definition_source': 'LINKAGE Attributes Definition Source 3'
    }]
}


class MetadataParserTestCase(unittest.TestCase):

    valid_complex_values = ('one', ['before', 'after'], ['first', 'next', 'last'])

    def setUp(self):
        sep = os.path.sep
        dir_name = os.path.dirname(os.path.abspath(__file__))

        # Define input file paths

        self.data_dir = sep.join((dir_name, 'data'))
        self.arcgis_file = sep.join((self.data_dir, 'arcgis_metadata.xml'))
        self.fgdc_file = sep.join((self.data_dir, 'fgdc_metadata.xml'))
        self.iso_file = sep.join((self.data_dir, 'iso_metadata.xml'))
        self.iso_href_file = sep.join((self.data_dir, 'iso_citation_href.xml'))
        self.iso_linkage_file = sep.join((self.data_dir, 'iso_citation_linkage.xml'))

        # Define test output file paths

        self.test_arcgis_file_path = '/'.join((self.data_dir, 'test_arcgis.xml'))
        self.test_fgdc_file_path = '/'.join((self.data_dir, 'test_fgdc.xml'))
        self.test_iso_file_path = '/'.join((self.data_dir, 'test_iso.xml'))

        self.test_file_paths = (self.test_arcgis_file_path, self.test_fgdc_file_path, self.test_iso_file_path)

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

        if prop in COMPLEX_DEFINITIONS:
            target = get_default_for_complex(prop, target)

        if isinstance(reparsed, dict):
            # Reparsed is a dict: compare each value with corresponding in target
            for key, val in reparsed.items():
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
                    for key, val in value.items():
                        self.assert_equal_for(
                            parser_name, '{0}.{1}'.format(prop, key), val, target[idx].get(key, u'')
                        )

    def assert_reparsed_simple_for(self, parser, props, value=None, target=None):

        use_props = isinstance(props, dict)

        for prop in props:
            if use_props:
                value = props[prop]
            setattr(parser, prop, value)

        parser_type = type(parser)
        parser_name = parser_type.__name__
        reparsed = parser_type(parser.serialize())

        for prop in props:
            if use_props:
                target = props[prop]
            self.assert_equal_for(parser_name, prop, getattr(reparsed, prop), target)

    def assert_parser_conversion(self, content_parser, target_parser, comparison_type=''):
        converted = content_parser.convert_to(target_parser)

        self.assert_valid_parser(content_parser)
        self.assert_valid_parser(target_parser)

        self.assertFalse(
            converted is target_parser,
            '{0} conversion is returning the original {0} instance'.format(type(converted).__name__)
        )

        for prop in SUPPORTED_PROPS:
            self.assertEqual(
                getattr(content_parser, prop), getattr(converted, prop),
                '{0} {1}conversion does not equal original {2} content for {3}'.format(
                    type(converted).__name__, comparison_type, type(content_parser).__name__, prop
                )
            )

    def assert_parsers_are_equal(self, parser_tgt, parser_val):
        parser_type = type(parser_tgt).__name__

        self.assert_valid_parser(parser_tgt)
        self.assert_valid_parser(parser_val)

        for prop in SUPPORTED_PROPS:
            self.assert_equal_for(parser_type, prop, getattr(parser_val, prop), getattr(parser_tgt, prop))

    def assert_parser_after_write(self, parser_type, in_file_path, out_file_path, use_template=False):

        with open(in_file_path) as in_file:
            parser = parser_type(in_file, out_file_path)

        # Update each value and read the file in again
        for prop in SUPPORTED_PROPS:

            if prop in (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS):
                value = [
                    {}.fromkeys(COMPLEX_DEFINITIONS[prop], 'test'),
                    {}.fromkeys(COMPLEX_DEFINITIONS[prop], prop)
                ]
            elif prop in (BOUNDING_BOX, LARGER_WORKS, RASTER_INFO):
                value = {}.fromkeys(COMPLEX_DEFINITIONS[prop], 'test ' + prop)
            elif prop == DATES:
                value = {DATE_TYPE: DATE_TYPE_RANGE, DATE_VALUES: ['test', prop]}
            elif prop in KEYWORD_PROPS:
                value = ['test', prop]
            else:
                value = 'test ' + prop

            if prop in COMPLEX_DEFINITIONS:
                value = get_default_for_complex(prop, value)

            setattr(parser, prop, value)

        parser.write(use_template=use_template)

        with open(out_file_path) as out_file:
            self.assert_parsers_are_equal(parser, parser_type(out_file))

    def assert_valid_parser(self, parser):

        parser_type = type(parser.validate()).__name__

        self.assertIsNotNone(parser._xml_root, '{0} root not set'.format(parser_type))

        self.assertIsNotNone(parser._xml_tree)
        self.assertEqual(parser._xml_tree.getroot().tag, parser._xml_root)

    def assert_validates_for(self, parser, prop, invalid):

        valid = getattr(parser, prop)
        setattr(parser, prop, invalid)

        try:
            parser.validate()
        except Exception as e:
            # Not using self.assertRaises to customize the failure message
            self.assertEqual(type(e), ValidationError, (
                'Property "{0}.{1}" does not raise ParserError for value: "{2}" ({3})'.format(
                    type(parser).__name__, prop, invalid, type(invalid).__name__
                )
            ))
        finally:
            setattr(parser, prop, valid)  # Reset value for next test

    def tearDown(self):

        for test_file_path in self.test_file_paths:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)


class MetadataParserTemplateTests(MetadataParserTestCase):

    def assert_template_after_write(self, parser_type, out_file_path):

        parser = parser_type(out_file_or_path=out_file_path)

        # Reverse each value and read the file in again
        for prop, val in TEST_TEMPLATE_VALUES.items():
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

        for prop, val in TEST_TEMPLATE_VALUES.items():
            parsed_val = getattr(parser, prop)
            self.assertEqual(parsed_val, val, (
                '{0} property {1}, "{2}", does not equal "{3}"'.format(parser_type, prop, parsed_val, val)
            ))

    def test_arcgis_template_values(self):
        arcgis_template = ArcGISParser(**TEST_TEMPLATE_VALUES)

        self.assert_valid_template(arcgis_template, root='metadata')
        self.assert_reparsed_simple_for(arcgis_template, TEST_TEMPLATE_VALUES)

    def test_fgdc_template_values(self):
        fgdc_template = FgdcParser(**TEST_TEMPLATE_VALUES)

        self.assert_valid_template(fgdc_template, root='metadata')
        self.assert_reparsed_simple_for(fgdc_template, TEST_TEMPLATE_VALUES)

    def test_iso_template_values(self):
        iso_template = IsoParser(**TEST_TEMPLATE_VALUES)

        self.assert_valid_template(iso_template, root='MD_Metadata')
        self.assert_reparsed_simple_for(iso_template, TEST_TEMPLATE_VALUES)

    def test_template_conversion(self):
        arcgis_template = ArcGISParser()
        fgdc_template = FgdcParser()
        iso_template = IsoParser()

        self.assert_parser_conversion(arcgis_template, fgdc_template, 'template')
        self.assert_parser_conversion(arcgis_template, iso_template, 'template')

        self.assert_parser_conversion(fgdc_template, iso_template, 'template')
        self.assert_parser_conversion(fgdc_template, arcgis_template, 'template')

        self.assert_parser_conversion(iso_template, fgdc_template, 'template')
        self.assert_parser_conversion(iso_template, arcgis_template, 'template')

    def test_template_conversion_bad_roots(self):

        bad_root_format = 'Bad root test failed for {0} with {1}'

        for bad_root in (None, u'', io.StringIO(u''), {}, '<?xml version="1.0" encoding="UTF-8"?>\n'):
            with self.assertRaises(NoContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                get_parsed_content(bad_root)
            with self.assertRaises(NoContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                get_metadata_parser(bad_root)

            if bad_root is not None:
                with self.assertRaises(NoContent, msg=bad_root_format.format('ArcGISParser', bad_root)):
                    ArcGISParser(bad_root)
                with self.assertRaises(NoContent, msg=bad_root_format.format('FgdcParser', bad_root)):
                    FgdcParser(bad_root)
                with self.assertRaises(NoContent, msg=bad_root_format.format('IsoParser', bad_root)):
                    IsoParser(bad_root)

        for bad_root in (u'NOT XML', u'<badRoot/>', u'<badRoot>invalid</badRoot>'):
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                get_parsed_content(bad_root)
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                get_metadata_parser(bad_root)
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('ArcGISParser', bad_root)):
                ArcGISParser(bad_root)
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('FgdcParser', bad_root)):
                FgdcParser(bad_root)
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('IsoParser', bad_root)):
                IsoParser(bad_root)

        with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
            IsoParser(FGDC_ROOT.join(('<', '></', '>')))

        for iso_root in ISO_ROOTS:
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                ArcGISParser(iso_root.join(('<', '></', '>')))
            with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                FgdcParser(iso_root.join(('<', '></', '>')))

        for arcgis_root in ARCGIS_ROOTS:

            with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                IsoParser(arcgis_root.join(('<', '></', '>')))

            if arcgis_root != FGDC_ROOT:
                with self.assertRaises(InvalidContent, msg=bad_root_format.format('get_parsed_content', bad_root)):
                    FgdcParser(arcgis_root.join(('<', '></', '>')))

    def test_template_conversion_from_dict(self):

        for arcgis_root in ARCGIS_ROOTS:
            for arcgis_node in ARCGIS_NODES:

                data = {'name': arcgis_root, 'children': [{'name': arcgis_node}]}
                self.assert_parser_conversion(
                    FgdcParser(), get_metadata_parser(data), 'dict-based template'
                )
                self.assert_parser_conversion(
                    IsoParser(), get_metadata_parser(data), 'dict-based template'
                )

        self.assert_parser_conversion(
            ArcGISParser(), get_metadata_parser({'name': FGDC_ROOT}), 'dict-based template'
        )
        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser({'name': FGDC_ROOT}), 'dict-based template'
        )

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                ArcGISParser(), get_metadata_parser({'name': iso_root}), 'dict-based template'
            )
            self.assert_parser_conversion(
                FgdcParser(), get_metadata_parser({'name': iso_root}), 'dict-based template'
            )

    def test_template_conversion_from_str(self):

        for arcgis_root in ARCGIS_ROOTS:
            for arcgis_node in ARCGIS_NODES:

                data = arcgis_node.join(('<', '></', '>'))
                data = arcgis_root.join(('<', '>{0}</', '>')).format(data)

                self.assert_parser_conversion(
                    FgdcParser(), get_metadata_parser(data), 'dict-based template'
                )
                self.assert_parser_conversion(
                    IsoParser(), get_metadata_parser(data), 'dict-based template'
                )

        self.assert_parser_conversion(
            ArcGISParser(), get_metadata_parser(FGDC_ROOT.join(('<', '></', '>'))), 'str-based template'
        )
        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(FGDC_ROOT.join(('<', '></', '>'))), 'str-based template'
        )

        for iso_root in ISO_ROOTS:
            self.assert_parser_conversion(
                ArcGISParser(), get_metadata_parser(iso_root.join(('<', '></', '>'))), 'str-based template'
            )
            self.assert_parser_conversion(
                FgdcParser(), get_metadata_parser(iso_root.join(('<', '></', '>'))), 'str-based template'
            )

    def test_template_conversion_from_type(self):

        self.assert_parser_conversion(
            ArcGISParser(), get_metadata_parser(FgdcParser), 'type-based template'
        )
        self.assert_parser_conversion(
            ArcGISParser(), get_metadata_parser(IsoParser), 'type-based template'
        )

        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(ArcGISParser), 'type-based template'
        )
        self.assert_parser_conversion(
            IsoParser(), get_metadata_parser(FgdcParser), 'type-based template'
        )

        self.assert_parser_conversion(
            FgdcParser(), get_metadata_parser(ArcGISParser), 'type-based template'
        )
        self.assert_parser_conversion(
            FgdcParser(), get_metadata_parser(IsoParser), 'type-based template'
        )

    def test_write_template(self):

        self.assert_template_after_write(ArcGISParser, self.test_arcgis_file_path)
        self.assert_template_after_write(FgdcParser, self.test_fgdc_file_path)
        self.assert_template_after_write(IsoParser, self.test_iso_file_path)


class MetadataParserTests(MetadataParserTestCase):

    def test_custom_fgdc_parser(self):
        """ Covers support for custom FGDC parser fields """

        target_prop = 'projection'
        target_values = {
            'name': 'Custom Projection',
            'standard_parallel': '7',
            'meridian_longitude': '8',
            'origin_latitude': '9',
            'false_easting': '22',
            'false_northing': '11',
        }

        with open(self.fgdc_file) as fgdc_metadata:
            custom_parser = CustomFgdcParser(fgdc_metadata)

        self.assertEqual(custom_parser.projection, target_values, 'Custom FGDC projection values were not parsed')

        complex_val = {
            'name': 'New Projection Name',
            'standard_parallel': '14',
            'meridian_longitude': '16',
            'origin_latitude': '18',
            'false_easting': '44',
            'false_northing': '22',
        }
        self.assert_reparsed_complex_for(custom_parser, target_prop, complex_val, complex_val)

        # Test conversion with custom props
        converted_parser = custom_parser.convert_to(CustomFgdcParser)

        self.assert_parsers_are_equal(custom_parser, converted_parser)
        self.assertEqual(converted_parser.projection, custom_parser.projection)

        # Test conversion that must ignore custom props
        agis_parser = custom_parser.convert_to(ArcGISParser)
        iso_parser = custom_parser.convert_to(IsoParser)
        self.assert_parsers_are_equal(agis_parser, iso_parser)

        # Test invalid projection structure value

        projection = custom_parser.projection
        custom_parser.projection = u'Nope'

        with self.assertRaises(ValidationError):
            custom_parser.validate()

        custom_parser.projection = projection
        custom_parser.validate()

    def test_custom_iso_parser(self):
        """ Covers support for custom ISO parser fields """

        target_values = {
            'metadata_contacts': [{
                'name': 'Custom Contact Name',
                'email': 'Custom Contact Email',
                'phone': 'Custom Contact Phone',
                'position': 'Custom Contact Position',
                'organization': 'Custom Contact Organization'
            }],
            'metadata_language': ['eng', 'esp']
        }

        with open(self.iso_file) as iso_metadata:
            custom_parser = CustomIsoParser(iso_metadata)

        for prop in target_values:
            self.assertEqual(
                getattr(custom_parser, prop),
                target_values[prop],
                'Custom ISO parser values were not parsed'
            )

        complex_val = {
            'name': 'Changed Contact Name',
            'email': 'Changed Contact Email',
            'phone': 'Changed Contact Phone',
            'position': 'Changed Contact Position',
            'organization': 'Changed Contact Organization'
        }
        self.assert_reparsed_complex_for(custom_parser, 'metadata_contacts', complex_val, [complex_val])
        self.assert_reparsed_simple_for(custom_parser, ['metadata_language'], ['en', 'es'], ['en', 'es'])

        # Test conversion with custom props
        converted_parser = custom_parser.convert_to(CustomIsoParser)

        self.assert_parsers_are_equal(custom_parser, converted_parser)
        self.assertEqual(converted_parser.metadata_contacts, custom_parser.metadata_contacts)
        self.assertEqual(converted_parser.metadata_language, custom_parser.metadata_language)

        # Test conversion that must ignore custom props
        agis_parser = custom_parser.convert_to(ArcGISParser)
        fgdc_parser = custom_parser.convert_to(FgdcParser)
        self.assert_parsers_are_equal(agis_parser, fgdc_parser)

        # Test invalid custom complex structure value

        metadata_contacts = custom_parser.metadata_contacts
        custom_parser.metadata_contacts = u'Nope'

        with self.assertRaises(ValidationError):
            custom_parser.validate()

        custom_parser.metadata_contacts = metadata_contacts
        custom_parser.validate()

        # Test invalid custom simple value

        metadata_language = custom_parser.metadata_language
        custom_parser.metadata_language = {}

        with self.assertRaises(ValidationError):
            custom_parser.validate()

        custom_parser.metadata_language = metadata_language
        custom_parser.validate()

    def test_generic_parser(self):
        """ Covers code that enforces certain behaviors for custom parsers """

        parser = MetadataParser()

        data_map_1 = parser._data_map
        parser._init_data_map()
        data_map_2 = parser._data_map

        self.assertIs(data_map_1, data_map_2, 'Data map was reinitialized after instantiation')

        with self.assertRaises(IOError):
            parser.write()

    def test_specific_parsers(self):
        """ Ensures code enforces certain behaviors for existing parsers """

        for parser_type in (ArcGISParser, FgdcParser, IsoParser):
            parser = parser_type()

            data_map_1 = parser._data_map
            parser._init_data_map()
            data_map_2 = parser._data_map

            self.assertIs(data_map_1, data_map_2, 'Data map was reinitialized after instantiation')

            with self.assertRaises(IOError):
                parser.write()

            with self.assertRaises(ValidationError):
                parser._data_map.clear()
                parser.validate()

    def test_arcgis_parser(self):
        """ Tests behavior unique to the ArcGIS parser """

        # Test dates structure defaults

        # Remove multiple dates to ensure range is queried
        arcgis_element = get_remote_element(self.arcgis_file)
        remove_element(arcgis_element, 'dataIdInfo/dataExt/tempEle/TempExtent/exTemp/TM_Instant', True)

        arcgis_parser = ArcGISParser(element_to_string(arcgis_element))

        # Assert that ArcGIS-specific keywords are read in correctly

        self.assertEqual(arcgis_parser.discipline_keywords, ['ArcGIS Discipline One', 'ArcGIS Discipline Two'])
        self.assertEqual(arcgis_parser.other_keywords, ['ArcGIS Other One', 'ArcGIS Other Two'])
        self.assertEqual(arcgis_parser.product_keywords, ['ArcGIS Product One', 'ArcGIS Product Two'])
        self.assertEqual(arcgis_parser.search_keywords, ['ArcGIS Search One', 'ArcGIS Search Two'])
        self.assertEqual(arcgis_parser.topic_category_keywords, ['ArcGIS Topical One', 'ArcGIS Topical Two'])

        # Assert that the backup dates are read in successfully

        self.assertEqual(arcgis_parser.dates, {'type': 'range', 'values': ['Date Range Start', 'Date Range End']})

        # Remove one of the date range values and assert that only the end date is read in as a single
        remove_element(arcgis_element, 'dataIdInfo/dataExt/tempEle/TempExtent/exTemp/TM_Period/tmBegin', True)
        arcgis_parser = ArcGISParser(element_to_string(arcgis_element))
        self.assertEqual(arcgis_parser.dates, {'type': 'single', 'values': ['Date Range End']})

        # Remove the last of the date range values and assert that no dates are read in
        remove_element(arcgis_element, 'dataIdInfo/dataExt/tempEle/TempExtent/exTemp/TM_Period', True)
        arcgis_parser = ArcGISParser(element_to_string(arcgis_element))
        self.assertEqual(arcgis_parser.dates, {})

        # Insert a single date value and assert that only it is read in

        single_path = 'dataIdInfo/dataExt/tempEle/TempExtent/exTemp/TM_Instant/tmPosition'
        single_text = 'Single Date'
        insert_element(arcgis_element, 0, single_path, single_text)

        arcgis_parser = ArcGISParser(element_to_string(arcgis_element))
        self.assertEqual(arcgis_parser.dates, {'type': 'single', 'values': [single_text]})

    def test_fgdc_parser(self):
        """ Tests behavior unique to the FGDC parser """

        # Test dates structure defaults

        # Remove multiple dates to ensure range is queried
        fgdc_element = get_remote_element(self.fgdc_file)
        remove_element(fgdc_element, 'idinfo/timeperd/timeinfo/mdattim', True)

        # Assert that the backup dates are read in successfully
        fgdc_parser = FgdcParser(element_to_string(fgdc_element))
        self.assertEqual(fgdc_parser.dates, {'type': 'range', 'values': ['Date Range Start', 'Date Range End']})

        # Test contact data structure defaults

        contacts_def = COMPLEX_DEFINITIONS[CONTACTS]

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

    @mock.patch('gis_metadata.iso_metadata_parser.get_remote_element')
    def test_iso_parser(self, mock_get):
        """ Tests behavior unique to the ISO parser """

        # Test reading in attributes from remote feature catalog citation href attribute

        with open(self.iso_href_file) as href_attributes:
            mock_get.return_value = href_attributes.read()

        iso_element = get_remote_element(self.iso_file)

        # Assert that the data from the href attribute URL was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attributes = iso_parser.attributes
        self.assertEquals(
            iso_parser._attr_details_file_url,
            'http://www.isotc211.org/2005/gfc/resources/example/G_3.xml',
            'ISO href attribute was not read in'
        )
        self.assertEqual(
            attributes, TEST_REMOTE_ISO_ATTRIBUTES['href'], 'Invalid HREF attributes: {0}'.format(attributes)
        )

        # Test reading in attributes from remote feature catalog citation linkage URL

        with open(self.iso_linkage_file) as linkage_attributes:
            mock_get.return_value = linkage_attributes.read()

        # Remove the feature catalog citation href attribute for `attribute_details`
        for citation_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_citation']):
            removed = remove_element_attributes(citation_element, 'href')
        self.assertIsNotNone(removed, 'ISO href attribute URL was not removed')

        # Assert that data from the linkage URL was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attributes = iso_parser.attributes
        self.assertEquals(
            iso_parser._attr_details_file_url,
            'ftp://ftp.ncddc.noaa.gov/pub/Metadata//ISO/87ffdfd0-775a-11e0-a1f0-0800200c9a66.xml',
            'ISO linkage URL was not read in'
        )
        self.assertEqual(
            attributes, TEST_REMOTE_ISO_ATTRIBUTES['linkage'], 'Invalid LINKAGE attributes: {0}'.format(attributes)
        )

        # Test reading in attributes from nested feature catalog data in the file

        mock_get.return_value = None

        # Remove the feature catalog citation linkage URL for `attribute_details`
        for linkage_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_contact_url']):
            removed = get_element_text(linkage_element)
            clear_element(linkage_element)
        self.assertIsNotNone(removed, 'ISO linkage URL was not removed')

        # Assert that data from the nested feature catalog citation was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attributes = iso_parser.attributes
        self.assertIsNone(iso_parser._attr_details_file_url, 'No URL should be with parser')
        self.assertEqual(
            attributes, TEST_METADATA_VALUES[ATTRIBUTES],
            msg='Invalid parsed attributes with no URL: {0}'.format(attributes)
        )

        # Test reading in attributes from nested feature catalog data when URL is invalid

        mock_get.side_effect = Exception

        # Change the href attribute so that it is invalid
        for citation_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_citation']):
            inserted = set_element_attributes(citation_element, href='neither url nor file')
        self.assertIsNotNone(inserted, 'Invalid ISO href attribute URL was not added')

        # Assert that the href attribute was ignored and the nested data was read in
        iso_parser = IsoParser(element_to_string(iso_element))
        attributes = iso_parser.attributes
        self.assertIsNone(iso_parser._attr_details_file_url, 'Invalid URL was stored with parser')
        self.assertEqual(
            attributes, TEST_METADATA_VALUES[ATTRIBUTES],
            msg='Invalid parsed attributes with invalid URL: {0}'.format(attributes)
        )

    def test_parser_values(self):
        """ Tests that parsers are populated with the expected values """

        arcgis_element = get_remote_element(self.arcgis_file)
        arcgis_parser = ArcGISParser(element_to_string(arcgis_element))
        arcgis_new = ArcGISParser(**TEST_METADATA_VALUES)

        # Test that the two ArcGIS parsers have the same data given the same input file
        self.assert_parsers_are_equal(arcgis_parser, arcgis_new)

        fgdc_element = get_remote_element(self.fgdc_file)
        fgdc_parser = FgdcParser(element_to_string(fgdc_element))
        fgdc_new = FgdcParser(**TEST_METADATA_VALUES)

        # Test that the two FGDC parsers have the same data given the same input file
        self.assert_parsers_are_equal(fgdc_parser, fgdc_new)

        iso_element = get_remote_element(self.iso_file)
        remove_element(iso_element, ISO_TAG_FORMATS['_attr_citation'], True)
        iso_parser = IsoParser(element_to_string(iso_element))
        iso_new = IsoParser(**TEST_METADATA_VALUES)

        # Test that the two ISO parsers have the same data given the same input file
        self.assert_parsers_are_equal(iso_parser, iso_new)

        # Test that all distinct parsers have the same data given equivalent input files

        self.assert_parsers_are_equal(arcgis_parser, fgdc_parser)
        self.assert_parsers_are_equal(fgdc_parser, iso_parser)
        self.assert_parsers_are_equal(iso_parser, arcgis_parser)

        # Test that each parser's values correspond to the target values
        for parser in (arcgis_parser, fgdc_parser, iso_parser):
            parser_type = type(parser)

            for prop, target in TEST_METADATA_VALUES.items():
                self.assert_equal_for(parser_type, prop, getattr(parser, prop), target)

    def test_parser_conversion(self):
        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)

        # Remove references to remote attribute details files in MD_FeatureCatalogueDescription
        iso_element = get_remote_element(self.iso_file)
        for citation_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_citation']):
            clear_element(citation_element)
        iso_parser = IsoParser(element_to_string(iso_element))

        self.assert_parser_conversion(arcgis_parser, fgdc_parser, 'file')
        self.assert_parser_conversion(arcgis_parser, iso_parser, 'file')
        self.assertEqual(arcgis_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(fgdc_parser, arcgis_parser, 'file')
        self.assert_parser_conversion(fgdc_parser, iso_parser, 'file')
        self.assertEqual(fgdc_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(iso_parser, arcgis_parser, 'file')
        self.assert_parser_conversion(iso_parser, fgdc_parser, 'file')
        self.assertEqual(iso_parser.convert_to(dict), TEST_METADATA_VALUES)

    def test_conversion_from_dict(self):
        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)

        # Remove references to remote attribute details files in MD_FeatureCatalogueDescription
        iso_element = get_remote_element(self.iso_file)
        for citation_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_citation']):
            clear_element(citation_element)
        iso_parser = IsoParser(element_to_string(iso_element))

        self.assert_parser_conversion(
            arcgis_parser, get_metadata_parser(element_to_dict(fgdc_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assert_parser_conversion(
            arcgis_parser, get_metadata_parser(element_to_dict(iso_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assertEqual(arcgis_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(element_to_dict(arcgis_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(element_to_dict(iso_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assertEqual(fgdc_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(element_to_dict(arcgis_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(element_to_dict(fgdc_parser._xml_tree, recurse=True)), 'dict-based'
        )
        self.assertEqual(iso_parser.convert_to(dict), TEST_METADATA_VALUES)

    def test_conversion_from_str(self):
        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)

        # Remove references to remote attribute details files in MD_FeatureCatalogueDescription
        iso_element = get_remote_element(self.iso_file)
        for citation_element in get_elements(iso_element, ISO_TAG_FORMATS['_attr_citation']):
            clear_element(citation_element)
        iso_parser = IsoParser(element_to_string(iso_element))

        self.assert_parser_conversion(
            arcgis_parser, get_metadata_parser(fgdc_parser.serialize()), 'str-based'
        )
        self.assert_parser_conversion(
            arcgis_parser, get_metadata_parser(iso_parser.serialize()), 'str-based'
        )
        self.assertEqual(arcgis_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(arcgis_parser.serialize()), 'str-based'
        )
        self.assert_parser_conversion(
            fgdc_parser, get_metadata_parser(iso_parser.serialize()), 'str-based'
        )
        self.assertEqual(fgdc_parser.convert_to(dict), TEST_METADATA_VALUES)

        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(arcgis_parser.serialize()), 'str-based'
        )
        self.assert_parser_conversion(
            iso_parser, get_metadata_parser(fgdc_parser.serialize()), 'str-based'
        )
        self.assertEqual(iso_parser.convert_to(dict), TEST_METADATA_VALUES)

    def test_reparse_complex_lists(self):
        complex_lists = (ATTRIBUTES, CONTACTS, DIGITAL_FORMS)

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

            # Test reparsed empty complex lists
            for prop in complex_lists:
                for empty in (None, [], [{}], [{}.fromkeys(COMPLEX_DEFINITIONS[prop], u'')]):
                    self.assert_reparsed_complex_for(parser, prop, empty, [])

            # Test reparsed valid complex lists (strings and lists for each property in each struct)
            for prop in complex_lists:
                complex_list = []

                for val in self.valid_complex_values:

                    # Test with single unwrapped value
                    next_complex = {}.fromkeys(COMPLEX_DEFINITIONS[prop], val)
                    self.assert_reparsed_complex_for(parser, prop, next_complex, wrap_value(next_complex))

                    # Test with accumulated list of values
                    complex_list.append({}.fromkeys(COMPLEX_DEFINITIONS[prop], val))
                    self.assert_reparsed_complex_for(parser, prop, complex_list, wrap_value(complex_list))

    def test_reparse_complex_structs(self):
        complex_structs = (BOUNDING_BOX, LARGER_WORKS, RASTER_INFO)

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

            # Test reparsed empty complex structures
            for prop in complex_structs:
                for empty in (None, {}, {}.fromkeys(COMPLEX_DEFINITIONS[prop], u'')):
                    self.assert_reparsed_complex_for(parser, prop, empty, {})

            # Test reparsed valid complex structures
            for prop in complex_structs:
                for val in self.valid_complex_values:
                    complex_struct = {}.fromkeys(COMPLEX_DEFINITIONS[prop], val)
                    self.assert_reparsed_complex_for(parser, prop, complex_struct, complex_struct)

    def test_reparse_dates(self):
        valid_values = (
            (DATE_TYPE_SINGLE, ['one']),
            (DATE_TYPE_RANGE, ['before', 'after']),
            (DATE_TYPE_MULTIPLE, ['first', 'next', 'last'])
        )

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

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

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

            # Test reparsed empty keywords
            for keywords in ('', u'', []):
                for keyword_prop in KEYWORD_PROPS:
                    self.assert_reparsed_complex_for(parser, keyword_prop, keywords, [])

            # Test reparsed valid keywords
            for keywords in ('keyword', ['keyword', 'list']):
                for keyword_prop in KEYWORD_PROPS:
                    self.assert_reparsed_complex_for(parser, keyword_prop, keywords, wrap_value(keywords))

    def test_reparse_process_steps(self):
        proc_step_def = COMPLEX_DEFINITIONS[PROCESS_STEPS]

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

            # Test reparsed empty process steps
            for empty in (None, [], [{}], [{}.fromkeys(proc_step_def, u'')]):
                self.assert_reparsed_complex_for(parser, PROCESS_STEPS, empty, [])

            complex_list = []

            # Test reparsed valid process steps
            for val in self.valid_complex_values:
                complex_struct = {}.fromkeys(proc_step_def, val)

                # Process steps must have a single string value for all but sources
                complex_struct.update({
                    k: ', '.join(wrap_value(v)) for k, v in complex_struct.items() if k != 'sources'
                })

                complex_list.append(complex_struct)

                self.assert_reparsed_complex_for(parser, PROCESS_STEPS, complex_list, complex_list)

    def test_reparse_simple_values(self):

        simple_props = SUPPORTED_PROPS.difference(COMPLEX_DEFINITIONS).difference(KEYWORD_PROPS)

        simple_empty_vals = ('', u'', [])
        simple_valid_vals = (u'value', [u'item', u'list'])

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):

            # Test reparsed empty values
            for val in simple_empty_vals:
                self.assert_reparsed_simple_for(parser, simple_props, val, u'')

            # Test reparsed valid values
            for val in simple_valid_vals:
                self.assert_reparsed_simple_for(parser, simple_props, val, val)

    def test_validate_complex_lists(self):
        complex_props = (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS)

        invalid_values = ('', u'', {'x': 'xxx'}, [{'x': 'xxx'}], set(), tuple())

        for parser in (ArcGISParser().validate(), FgdcParser().validate(), IsoParser().validate()):
            for prop in complex_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_validate_complex_structs(self):
        complex_props = (BOUNDING_BOX, DATES, LARGER_WORKS, RASTER_INFO)

        invalid_values = ('', u'', {'x': 'xxx'}, list(), set(), tuple())

        for parser in (ArcGISParser().validate(), FgdcParser().validate(), IsoParser().validate()):
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

        with open(self.arcgis_file) as arcgis_metadata:
            arcgis_parser = ArcGISParser(arcgis_metadata)
        with open(self.fgdc_file) as fgdc_metadata:
            fgdc_parser = FgdcParser(fgdc_metadata)
        with open(self.iso_file) as iso_metadata:
            iso_parser = IsoParser(iso_metadata)

        for parser in (arcgis_parser, fgdc_parser, iso_parser):
            for val in invalid_values:
                self.assert_validates_for(parser, DATES, {DATE_TYPE: val[0], DATE_VALUES: val[1]})

    def test_validate_simple_values(self):
        simple_props = SUPPORTED_PROPS.difference(COMPLEX_DEFINITIONS)
        invalid_values = (None, [None], dict(), [dict()], set(), [set()], tuple(), [tuple()])

        for parser in (ArcGISParser().validate(), FgdcParser().validate(), IsoParser().validate()):
            for prop in simple_props:
                for invalid in invalid_values:
                    self.assert_validates_for(parser, prop, invalid)

    def test_write_values(self):

        self.assert_parser_after_write(ArcGISParser, self.arcgis_file, self.test_arcgis_file_path)
        self.assert_parser_after_write(FgdcParser, self.fgdc_file, self.test_fgdc_file_path)
        self.assert_parser_after_write(IsoParser, self.iso_file, self.test_iso_file_path)

    def test_write_values_to_template(self):

        self.assert_parser_after_write(ArcGISParser, self.arcgis_file, self.test_arcgis_file_path, True)
        self.assert_parser_after_write(FgdcParser, self.fgdc_file, self.test_fgdc_file_path, True)
        self.assert_parser_after_write(IsoParser, self.iso_file, self.test_iso_file_path, True)


class ParserUtilityTestCase(unittest.TestCase):
    """ A test case to cover utility function edge cases not covered by test data """

    def setUp(self):
        sep = os.path.sep
        dir_name = os.path.dirname(os.path.abspath(__file__))

        self.data_dir = sep.join((dir_name, 'data'))
        self.xml_data = sep.join((self.data_dir, 'utility_metadata.xml'))

        with open(self.xml_data) as xml_data:
            self.utility_parser = UtilityFgdcParser(xml_data)

    def test_parser_property(self):
        prop_get = '{0}'.format
        prop_set = '{xpaths}'.format

        with self.assertRaises(ConfigurationError):
            # Un-callable property parser (no xpath)
            ParserProperty(None, None)

        with self.assertRaises(ConfigurationError):
            # Un-callable property parser (no xpath)
            ParserProperty(None, prop_set)

        with self.assertRaises(ConfigurationError):
            # Un-callable property updater
            ParserProperty(prop_get, None)

        parser_prop = ParserProperty(None, prop_set, 'path')
        with self.assertRaises(ConfigurationError):
            # Un-callable property parser with xpath
            parser_prop.get_prop('prop')

        parser_prop = ParserProperty(prop_get, prop_set, 'path')
        self.assertEqual(parser_prop.get_prop('prop'), 'prop')
        self.assertEqual(parser_prop.set_prop(), 'path')
        self.assertEqual(parser_prop.set_prop(xpaths='diff'), 'path')

    def test_parse_dates(self):

        prop = DATES

        # Test single date stored as multiple (mdattim) is converted to single
        multiple_to_single_date = {'Multiple Date 1'}
        self.assertEqual(set(self.utility_parser.dates['values']), multiple_to_single_date)
        validate_dates(prop, self.utility_parser.dates, self.utility_parser._data_structures[prop])

        # Remove multiple date root in order to parse multiple-range dates (rngdates)
        with open(self.xml_data) as xml_data:
            xml_tree = get_element(xml_data)
            remove_element(xml_tree, 'idinfo/timeperd/timeinfo/mdattim')
            self.utility_parser = UtilityFgdcParser(xml_tree)

        # Test multiple dates stored as range (rngdates) are converted to multiple
        range_to_multiple_dates = {'Date Range Start 1', 'Date Range Start 2', 'Date Range End 1', 'Date Range End 2'}
        self.assertEqual(set(self.utility_parser.dates['values']), range_to_multiple_dates)
        validate_dates(prop, self.utility_parser.dates, self.utility_parser._data_structures[prop])

        # Test validation with missing "type" parameter and non-standard dates prop
        self.utility_parser.dates['no_type'] = self.utility_parser.dates.pop('type')
        with self.assertRaises(ValidationError):
            validate_dates('nope', self.utility_parser.dates, self.utility_parser._data_structures[prop])

        # Test validation with missing "values" parameter and non-standard dates prop
        self.utility_parser.dates['type'] = self.utility_parser.dates.pop('no_type')
        self.utility_parser.dates['no_vals'] = self.utility_parser.dates.pop('values')
        with self.assertRaises(ValidationError):
            validate_dates('nope', self.utility_parser.dates, self.utility_parser._data_structures[prop])

    def test_parse_property(self):

        initial_vals = {}
        updated_vals = {}

        for prop in self.utility_parser._parser_props:

            # Test that each property was initialized as expected
            init_val = getattr(self.utility_parser, prop)
            test_val = self.utility_parser._data_map[prop].get_prop(prop)
            self.assertEqual(init_val, test_val, 'Unmatching utility parser values for "{0}"'.format(prop))

            initial_vals[prop] = test_val
            updated_vals[prop] = test_val[::-1]
            setattr(self.utility_parser, prop, updated_vals[prop])

        self.utility_parser.update()

        for prop in updated_vals:
            # Test that each property was updated in the XML
            old_val = initial_vals[prop]
            new_val = updated_vals[prop]
            get_val = getattr(self.utility_parser, prop)
            xml_val = self.utility_parser._data_map[prop].get_prop(prop)

            self.assertNotEqual(old_val, new_val, 'Utility parser property unchanged: "{0}"'.format(prop))
            self.assertEqual(get_val, new_val, 'Utility parser property not set: "{0}"'.format(prop))
            self.assertEqual(get_val, new_val, 'Utility parser property not applied: "{0}"'.format(prop))
            self.assertEqual(get_val, xml_val, 'Utility parser XML not updated for "{0}"'.format(prop))

    def test_validate_complex(self):
        complex_props = (BOUNDING_BOX, LARGER_WORKS, RASTER_INFO)

        for prop in complex_props:
            rprop = prop[::-1]
            value = getattr(self.utility_parser, prop)
            setattr(self.utility_parser, rprop, value)
            # Test the same valid structure under a different prop name
            validate_complex(rprop, value, self.utility_parser._data_structures[prop])

    def test_validate_complex_list(self):
        complex_props = (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS)

        for prop in complex_props:
            rprop = prop[::-1]
            value = getattr(self.utility_parser, prop)
            setattr(self.utility_parser, rprop, value)
            # Test the same valid list structure under a different prop name
            validate_complex_list(rprop, value, self.utility_parser._data_structures[prop])

    def test_validate_dates(self):

        # Test validation with missing "type" parameter and non-standard dates prop
        self.utility_parser.dates['no_type'] = self.utility_parser.dates.pop('type')
        with self.assertRaises(ValidationError):
            validate_dates('nope', self.utility_parser.dates, self.utility_parser._data_structures[DATES])

        # Test validation with missing "values" parameter and non-standard dates prop
        self.utility_parser.dates['type'] = self.utility_parser.dates.pop('no_type')
        self.utility_parser.dates['no_vals'] = self.utility_parser.dates.pop('values')
        with self.assertRaises(ValidationError):
            validate_dates('nope', self.utility_parser.dates, self.utility_parser._data_structures[DATES])


class CustomFgdcParser(FgdcParser):

    def _init_data_map(self):
        super(CustomFgdcParser, self)._init_data_map()

        # Define PROJECTION as a complex structure

        mp_definition = {
            'name': '{name}',
            'standard_parallel': '{standard_parallel}',
            'meridian_longitude': '{meridian_longitude}',
            'origin_latitude': '{origin_latitude}',
            'false_easting': '{false_easting}',
            'false_northing': '{false_northing}',
        }
        mp_prop = 'projection'
        mp_xpath = 'spref/horizsys/planar/mapproj/{mp_path}'

        # Add PROJECTION structure to data map
        self._data_structures[mp_prop] = format_xpaths(
            mp_definition,
            name=mp_xpath.format(mp_path='mapprojn'),
            standard_parallel=mp_xpath.format(mp_path='equirect/stdparll'),
            meridian_longitude=mp_xpath.format(mp_path='equirect/longcm'),
            origin_latitude=mp_xpath.format(mp_path='equirect/latprjo'),
            false_easting=mp_xpath.format(mp_path='equirect/feast'),
            false_northing=mp_xpath.format(mp_path='equirect/fnorth'),
        )

        # Set the root and add getter/setter (parser/updater) to the data map
        self._data_map['_{prop}_root'.format(prop=mp_prop)] = mp_prop
        self._data_map[mp_prop] = ParserProperty(self._parse_complex, self._update_complex)

        # Let the parent validation logic know about the two new custom properties
        self._metadata_props.add(mp_prop)


class CustomIsoParser(IsoParser):

    def _init_data_map(self):
        super(CustomIsoParser, self)._init_data_map()

        # Basic property: text or list (with backup location referencing codeListValue attribute)

        lang_prop = 'metadata_language'
        self._data_map[lang_prop] = 'language/CharacterString'                    # Parse from here if present
        self._data_map['_' + lang_prop] = 'language/LanguageCode/@codeListValue'  # Otherwise, try from here

        # Complex structure (reuse of contacts structure plus phone)

        # Define some basic variables
        ct_prop = 'metadata_contacts'
        ct_xpath = 'contact/CI_ResponsibleParty/{ct_path}'
        ct_defintion = dict(COMPLEX_DEFINITIONS[CONTACTS])
        ct_defintion['phone'] = '{phone}'

        # Reuse CONTACT structure to specify locations per prop (adapted only slightly from parent)
        self._data_structures[ct_prop] = format_xpaths(
            ct_defintion,
            name=ct_xpath.format(ct_path='individualName/CharacterString'),
            organization=ct_xpath.format(ct_path='organisationName/CharacterString'),
            position=ct_xpath.format(ct_path='positionName/CharacterString'),
            phone=ct_xpath.format(
                ct_path='contactInfo/CI_Contact/phone/CI_Telephone/voice/CharacterString'
            ),
            email=ct_xpath.format(
                ct_path='contactInfo/CI_Contact/address/CI_Address/electronicMailAddress/CharacterString'
            )
        )

        # Set the root and add getter/setter (parser/updater) to the data map
        self._data_map['_{prop}_root'.format(prop=ct_prop)] = 'contact'
        self._data_map[ct_prop] = ParserProperty(self._parse_complex_list, self._update_complex_list)

        # And finally, let the parent validation logic know about the two new custom properties

        self._metadata_props.add(lang_prop)
        self._metadata_props.add(ct_prop)


class UtilityFgdcParser(FgdcParser):

    def _init_data_map(self):
        """ Convert all string xpaths in data map to equivalent ParserProperty """

        super(UtilityFgdcParser, self)._init_data_map()

        # Replace all string paths in data map with dummy parser

        updated_data_map = {}
        for prop, xpath in self._data_map.items():
            if prop in self._metadata_props and isinstance(xpath, str):
                updated_data_map[prop] = ParserProperty(self._parse_prop, self._update_prop, xpath)

        # Ensure at least one property was updated (should be many) and add to data map

        assert len(updated_data_map) > 0

        self._parser_props = list(updated_data_map)
        self._data_map.update(updated_data_map)

    def _parse_prop(self, prop):
        """ :return: the data map property directly, same as self._data_map[prop] """
        return parse_property(self._xml_tree, None, self._data_map, prop)

    def _update_prop(self, **update_props):
        """ Update the value directly, same as utils._update_property """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = update_props['values']
        xpaths = self._data_map[prop].xpath

        return update_property(tree_to_update, None, xpaths, prop, values)
