""" A module to contain utility metadata parsing helpers """

from copy import deepcopy
from six import iteritems

from parserutils.elements import create_element_tree, element_exists, element_to_string, strip_namespaces
from parserutils.elements import get_element_name, get_element_tree, get_elements_text
from parserutils.elements import insert_element, remove_element, write_element
from parserutils.strings import DEFAULT_ENCODING

from gis_metadata.parser_utils import DATE_TYPE, DATE_VALUES
from gis_metadata.parser_utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.parser_utils import filter_property, get_required_keys
from gis_metadata.parser_utils import update_property, validate_any, validate_keyset
from gis_metadata.parser_utils import ParserException


# Place holders for lazy, one-time FGDC & ISO imports

FgdcParser, FGDC_ROOT = None, None
IsoParser, ISO_ROOTS = None, None
VALID_ROOTS = None


def convert_parser_to(parser, parser_or_type):
    """
    :return: a parser of type parser_or_type, initialized with the properties of parser. If parser_or_type
    is a type, an instance of it must contain a update method. The update method must also process
    the set of properties supported by MetadataParser for the conversion to have any affect.
    :param parser: the parser (or content or parser type) to convert to new_type
    :param parser_or_type: a parser (or content) or type of parser to return
    :see: get_metadata_parser(metadata_container) for more on how parser_or_type is treated
    """

    old_parser = parser if isinstance(parser, MetadataParser) else get_metadata_parser(parser)
    new_parser = get_metadata_parser(parser_or_type)

    for prop in get_required_keys():
        setattr(new_parser, prop, deepcopy(getattr(old_parser, prop, '')))

    new_parser.update()

    return new_parser


def get_metadata_parser(metadata_container, **metadata_defaults):
    """
    :return: an appropriate instance of MetadataParser depending on what is passed in. If metadata_container
    is a type, an instance of it must contain an update method that returns parsable content.
    :param metadata_container: a parser, parser type, or parsable content
    :throws ParserException: if the content does not correspond to a supported metadata standard
    :see: get_parsed_content(metdata_content) for more on types of content that can be parsed
    """

    if isinstance(metadata_container, type):
        metadata_container = metadata_container().update(**metadata_defaults)

    xml_root, xml_tree = get_parsed_content(metadata_container)

    # The get_parsed_content method ensures only these roots will be returned

    if xml_root == FGDC_ROOT:
        return FgdcParser(xml_tree, **metadata_defaults)
    elif xml_root in ISO_ROOTS:
        return IsoParser(xml_tree, **metadata_defaults)


def get_parsed_content(metadata_content):
    """
    Parses any of the following types of content:
    1. XML string or file object: parses XML content
    2. MetadataParser instance: deep copies xml_tree
    3. Dictionary with nested objects containing:
        - name (required): the name of the element tag
        - text: the text contained by element
        - tail: text immediately following the element
        - attributes: a Dictionary containing element attributes
        - children: a List of converted child elements

    :throws ParserException: If the content passed in is null or otherwise invalid
    :return: the XML root along with an XML Tree parsed by and compatible with element_utils
    """

    _import_parsers()  # Prevents circular dependencies between modules

    xml_tree = None

    if metadata_content is not None:
        if isinstance(metadata_content, MetadataParser):
            xml_tree = deepcopy(metadata_content._xml_tree)
        elif isinstance(metadata_content, dict):
            xml_tree = get_element_tree(metadata_content)
        else:
            try:
                # Strip name spaces from file or XML content
                xml_tree = get_element_tree(strip_namespaces(metadata_content))
            except:
                xml_tree = None  # Several exceptions possible, outcome is the same

    if xml_tree is None:
        raise ParserException(
            'Cannot instantiate a {parser_type} parser with invalid content to parse',
            parser_type=type(metadata_content)
        )

    xml_root = get_element_name(xml_tree)
    if xml_root in VALID_ROOTS:
        return xml_root, xml_tree

    raise ParserException('Invalid root element for MetadataParser: {xml_root}', xml_root=xml_root)


def _import_parsers():
    """ Lazy imports to prevent circular dependencies between this module and parser_utils """

    global FGDC_ROOT
    global FgdcParser

    global ISO_ROOTS
    global IsoParser

    global VALID_ROOTS

    if FGDC_ROOT is None or FgdcParser is None:
        from gis_metadata.fgdc_metadata_parser import FGDC_ROOT
        from gis_metadata.fgdc_metadata_parser import FgdcParser

    if ISO_ROOTS is None or IsoParser is None:
        from gis_metadata.iso_metadata_parser import ISO_ROOTS
        from gis_metadata.iso_metadata_parser import IsoParser

    if VALID_ROOTS is None:
        VALID_ROOTS = {FGDC_ROOT}.union(ISO_ROOTS)


class MetadataParser(object):
    """
    A class to parent all XML metadata parsing classes. To add more fields for parsing and updating:

    I. If the new field contains a String or a List of Strings, do the following and skip to step III

        Update the dictionary of formatted tags in each child parser that needs to read in the value.
        Nothing more is needed, because the _init_data_map methods should be written to put all XPATHs
        into the data map as they are, overriding the values for only complex XML content. If an XPATH
        is in the data map, it will be read and written at parsing time and updating time respectively.

    II. If the new field contains complex XML content:

        A. Add the new complex definition to parser_utils
            :see: parser_utils._complex_definitions for examples of complex XML content

        B. Define the necessary property parsing and updating methods in the child parsers

            By default, XPATH values in a data map Dictionary handle Strings or Lists of Strings.
            If the new property requires conversion to-and-from a Dictionary, then:

                1. A parse and update method will need to be defined in the child parser
                    - Parse methods should take zero arguments and return the value in the desired format
                    - Update methods take a **kwargs parameter and return the updated element
                2. A ParserProperties must be instantiated with them and put in data map

        C. Update _init_data_map() to instantiate a ParserProperty for the new field

            The result of _init_data_map is that _data_map is defined for use in _init_metadata.
            The _data_map dictionary will contain identifying property names as keys, and either
            XPATHs or ParserProperties as values.

    III. If the new content is required across standards, update parser_utils._required_keys as needed

        Requiring new content does not mean a value is required from the incoming metadata. Rather,
        it means all MetadataParser children must provide an XPATH for parsing the value, even if
        the XPATH provided is blank. This ensures an initialized parser will have a property named
        after the identifying property name, even if its value is an empty String.

    """

    def __init__(self, metadata_to_parse=None, out_file_or_path=None, **metadata_defaults):
        """
        Initialize new parser with valid content as defined by get_parsed_content
        :see: get_parsed_content(metdata_content) for more on what constitutes valid content
        """

        self.has_data = False
        self.out_file_or_path = out_file_or_path

        self._data_map = None
        self._xml_tree = None

        if metadata_to_parse is None:
            self._xml_tree = self._get_template(**metadata_defaults)
            self._xml_root = self._data_map['root']
        else:
            self._xml_root, self._xml_tree = get_parsed_content(metadata_to_parse)

        self._init_metadata()

    def _init_metadata(self):
        """
        Dynamically sets attributes from a Dictionary passed in by children.
        The Dictionary will contain the name of each attribute as keys, and
        either an XPATH mapping to a text value in _xml_tree, or a function
        that takes no parameters and returns the intended value.
        """

        if self._data_map is None:
            self._init_data_map()

        validate_keyset(self._data_map.keys())

        # Parse attribute values and assign them: key = parse(val)

        for prop, xpath in iteritems(self._data_map):
            if not xpath:
                parsed = ''
            elif hasattr(xpath, '__call__'):
                parsed = xpath(prop)
            else:
                parsed = get_elements_text(self._xml_tree, xpath)

            setattr(self, prop, filter_property(prop, parsed))

            if not self.has_data:
                self.has_data = bool(parsed)

    def _init_data_map(self):
        """ Default data map initialization: MUST be overridden in children """

        if self._data_map is None:
            self._data_map = {'root': None}
            self._data_map.update({}.fromkeys(get_required_keys()))

    def _get_template(self, root=None, **metadata_defaults):
        """ Iterate over items retrieved from _get_template_paths to populate template """

        if root is None:
            if self._data_map is None:
                self._init_data_map()

            root = self._data_map['root']

        template = create_element_tree(root)

        for path, val in iteritems(self._get_template_paths(**metadata_defaults)):
            if path and val:
                insert_element(template, 0, path, val)

        return template

    def _get_template_paths(self, **metadata_defaults):
        """
        Default template XPATHs: MAY be overridden in children.
        :return: a dict containing at least the distribution contact info: {xpath: value}
        """

        if not hasattr(self, '_template_paths'):
            self._template_paths = {
                self._data_map[key]: val for key, val in iteritems(metadata_defaults)
            }

        return self._template_paths

    def _get_elements_text(self, xpath):
        """ :return: all the text associated with the specified XPATH as a string array """

        return [] if not xpath else get_elements_text(self._xml_tree, xpath)

    def _has_element(self, xpath):
        """ :return: true if the specified XPATH identifies a metadata element, false otherwise """

        return False if not xpath else element_exists(self._xml_tree, xpath)

    def _parse_property(self, prop):
        """ :return: the value for the XPATH corresponding to prop """

        xpath = self._data_map[prop]

        return filter_property(prop, self._get_elements_text(getattr(xpath, 'xpath', xpath)))

    def _update_dates_property(self, xpath_root, xpaths, **update_props):
        """
        Default update operation for Dates metadata
        :see: parser_utils._complex_definitions[DATES]
        """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = filter_property(prop, update_props['values']).get(DATE_VALUES, '')

        if not self.dates:
            date_xpaths = xpath_root
        elif self.dates[DATE_TYPE] != DATE_TYPE_RANGE:
            date_xpaths = xpaths.get(self.dates[DATE_TYPE], '')
        else:
            date_xpaths = [
                xpaths[DATE_TYPE_RANGE_BEGIN],
                xpaths[DATE_TYPE_RANGE_END]
            ]

        if xpath_root:
            remove_element(tree_to_update, xpath_root)

        return update_property(tree_to_update, xpath_root, date_xpaths, prop, values)

    def convert_to(self, new_parser_or_type):
        """
        :return: a parser initialized with this parser's data. If new_parser_or_type is to be treated
        as a parser, it must have
        :param new_parser_or_type: a new parser to initialize, or parser type to instantiate
        """
        return convert_parser_to(self, new_parser_or_type)

    def serialize(self, use_template=False):
        """
        Validates instance properties, writes them to an XML tree, and returns the content as a string.
        :param use_template: if True, updates a new template XML tree; otherwise the original XML tree
        """
        return element_to_string(self.update(use_template))

    def write(self, use_template=False, out_file_or_path=None, encoding=DEFAULT_ENCODING):
        """
        Validates instance properties, updates an XML tree with them, and writes the content to a file.
        :param use_template: if True, updates a new template XML tree; otherwise the original XML tree
        :param out_file_or_path: optionally override self.out_file_or_path with a custom file path
        :param encoding: optionally use another encoding instead of UTF-8
        """

        if not out_file_or_path:
            out_file_or_path = self.out_file_or_path

        if not out_file_or_path:
            raise ParserException('Output file path has not been provided')

        write_element(self.update(use_template), out_file_or_path, encoding)

    def update(self, use_template=False, **metadata_defaults):
        """
        Validates instance properties and updates either a template or the original XML tree with them.
        :param use_template: if True, updates a new template XML tree; otherwise the original XML tree
        """

        self.validate()

        tree_to_update = self._xml_tree if not use_template else self._get_template(**metadata_defaults)

        for prop, xpath in iteritems(self._data_map):
            if not prop.startswith('_'):  # Update only non-private properties
                update_property(tree_to_update, None, xpath, prop, getattr(self, prop, ''))

        return tree_to_update

    def validate(self):
        """ Default validation for updated properties: MAY be overridden in children """

        validate_keyset(self._data_map.keys())

        for prop in self._data_map:
            validate_any(prop, getattr(self, prop))

        return self
