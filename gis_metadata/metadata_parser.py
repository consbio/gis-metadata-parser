""" A module to contain utility metadata parsing helpers """

from copy import deepcopy

from parserutils.elements import create_element_tree, element_exists, element_to_string
from parserutils.elements import get_element_name, get_element_tree, remove_element, write_element
from parserutils.strings import DEFAULT_ENCODING

from gis_metadata.exceptions import InvalidContent, NoContent
from gis_metadata.utils import DATES, DATE_TYPE, DATE_VALUES
from gis_metadata.utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.utils import SUPPORTED_PROPS
from gis_metadata.utils import parse_complex, parse_complex_list, parse_dates, parse_property
from gis_metadata.utils import update_complex, update_complex_list, update_property, validate_any, validate_properties


# Place holders for lazy, one-time FGDC & ISO imports

ArcGISParser, ARCGIS_ROOTS, ARCGIS_NODES = None, None, None
FgdcParser, FGDC_ROOT = None, None
IsoParser, ISO_ROOTS = None, None
VALID_ROOTS = None


def convert_parser_to(parser, parser_or_type, metadata_props=None):
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

    for prop in (metadata_props or SUPPORTED_PROPS):
        setattr(new_parser, prop, deepcopy(getattr(old_parser, prop, u'')))

    new_parser.update()

    return new_parser


def get_metadata_parser(metadata_container, **metadata_defaults):
    """
    Takes a metadata_container, which may be a type or instance of a parser, a dict, string, or file.
    :return: a new instance of a parser corresponding to the standard represented by metadata_container
    :see: get_parsed_content(metdata_content) for more on types of content that can be parsed
    """

    parser_type = None

    if isinstance(metadata_container, MetadataParser):
        parser_type = type(metadata_container)

    elif isinstance(metadata_container, type):
        parser_type = metadata_container
        metadata_container = metadata_container().update(**metadata_defaults)

    xml_root, xml_tree = get_parsed_content(metadata_container)

    # The get_parsed_content method ensures only these roots will be returned

    parser = None

    if parser_type is not None:
        parser = parser_type(xml_tree, **metadata_defaults)
    elif xml_root in ISO_ROOTS:
        parser = IsoParser(xml_tree, **metadata_defaults)
    else:
        has_arcgis_data = any(element_exists(xml_tree, e) for e in ARCGIS_NODES)

        if xml_root == FGDC_ROOT and not has_arcgis_data:
            parser = FgdcParser(xml_tree, **metadata_defaults)
        elif xml_root in ARCGIS_ROOTS:
            parser = ArcGISParser(xml_tree, **metadata_defaults)

    return parser


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

    :raises InvalidContent: if the XML is invalid or does not conform to a supported metadata standard
    :raises NoContent: If the content passed in is null or otherwise empty

    :return: the XML root along with an XML Tree parsed by and compatible with element_utils
    """

    _import_parsers()  # Prevents circular dependencies between modules

    xml_tree = None

    if metadata_content is None:
        raise NoContent('Metadata has no data')
    else:
        if isinstance(metadata_content, MetadataParser):
            xml_tree = deepcopy(metadata_content._xml_tree)
        elif isinstance(metadata_content, dict):
            xml_tree = get_element_tree(metadata_content)
        else:
            try:
                # Strip name spaces from file or XML content
                xml_tree = get_element_tree(metadata_content)
            except Exception:
                xml_tree = None  # Several exceptions possible, outcome is the same

    if xml_tree is None:
        raise InvalidContent(
            'Cannot instantiate a {parser_type} parser with invalid content to parse',
            parser_type=type(metadata_content).__name__
        )

    xml_root = get_element_name(xml_tree)

    if xml_root is None:
        raise NoContent('Metadata contains no data')
    elif xml_root not in VALID_ROOTS:
        content = type(metadata_content).__name__
        raise InvalidContent('Invalid root element for {content}: {xml_root}', content=content, xml_root=xml_root)

    return xml_root, xml_tree


def _import_parsers():
    """ Lazy imports to prevent circular dependencies between this module and utils """

    global ARCGIS_NODES
    global ARCGIS_ROOTS
    global ArcGISParser

    global FGDC_ROOT
    global FgdcParser

    global ISO_ROOTS
    global IsoParser

    global VALID_ROOTS

    if ARCGIS_NODES is None or ARCGIS_ROOTS is None or ArcGISParser is None:
        from gis_metadata.arcgis_metadata_parser import ARCGIS_NODES
        from gis_metadata.arcgis_metadata_parser import ARCGIS_ROOTS
        from gis_metadata.arcgis_metadata_parser import ArcGISParser

    if FGDC_ROOT is None or FgdcParser is None:
        from gis_metadata.fgdc_metadata_parser import FGDC_ROOT
        from gis_metadata.fgdc_metadata_parser import FgdcParser

    if ISO_ROOTS is None or IsoParser is None:
        from gis_metadata.iso_metadata_parser import ISO_ROOTS
        from gis_metadata.iso_metadata_parser import IsoParser

    if VALID_ROOTS is None:
        VALID_ROOTS = {FGDC_ROOT}.union(ARCGIS_ROOTS + ISO_ROOTS)


class MetadataParser(object):
    """
    A class to parent all XML metadata parsing classes. To add more fields for parsing and updating:

    I. If the new field contains a String or a List of Strings, do the following and skip to step III

        Update the dictionary of formatted tags in each child parser that needs to read in the value.
        Nothing more is needed, because the _init_data_map methods should be written to put all XPATHs
        into the data map as they are, overriding the values for only complex XML content. If an XPATH
        is in the data map, it will be read and written at parsing time and updating time respectively.

    II. If the new field contains complex XML content:

        A. Add the new complex definition to utils
            :see: gis_metadata.utils.COMPLEX_DEFINITIONS for examples of complex XML content

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

    III. If the new content is required across standards, update utils.SUPPORTED_PROPS as needed

        Requiring new content does not mean a value is required from the incoming metadata. Rather,
        it means all MetadataParser children must provide an XPATH for parsing the value, even if
        the XPATH provided is blank. This ensures an initialized parser will have a property named
        after the identifying property name, even if its value is an empty String.

    """

    def __init__(self, metadata_to_parse=None, out_file_or_path=None, metadata_props=None, **metadata_defaults):
        """
        Initialize new parser with valid content as defined by get_parsed_content
        :see: get_parsed_content(metdata_content) for more on what constitutes valid content
        """

        self.has_data = False
        self.out_file_or_path = out_file_or_path

        self._xml_tree = None
        self._data_map = None
        self._data_structures = None
        self._metadata_props = set(metadata_props or SUPPORTED_PROPS)

        if metadata_to_parse is not None:
            self._xml_root, self._xml_tree = get_parsed_content(metadata_to_parse)
        else:
            self._xml_tree = self._get_template(**metadata_defaults)
            self._xml_root = self._data_map['_root']

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

        validate_properties(self._data_map, self._metadata_props)

        # Parse attribute values and assign them: key = parse(val)

        for prop in self._data_map:
            setattr(self, prop, parse_property(self._xml_tree, None, self._data_map, prop))

        self.has_data = any(getattr(self, prop) for prop in self._data_map)

    def _init_data_map(self):
        """ Default data map initialization: MUST be overridden in children """

        if self._data_map is None:
            self._data_map = {'_root': None}
            self._data_map.update({}.fromkeys(self._metadata_props))

    def _get_template(self, root=None, **metadata_defaults):
        """ Iterate over items metadata_defaults {prop: val, ...} to populate template """

        if root is None:
            if self._data_map is None:
                self._init_data_map()

            root = self._xml_root = self._data_map['_root']

        template_tree = self._xml_tree = create_element_tree(root)

        for prop, val in metadata_defaults.items():
            path = self._data_map.get(prop)
            if path and val:
                setattr(self, prop, val)
                update_property(template_tree, None, path, prop, val)

        return template_tree

    def _get_xpath_for(self, prop):
        """ :return: the configured xpath for a given property """

        xpath = self._data_map.get(prop)
        return getattr(xpath, 'xpath', xpath)  # May be a ParserProperty

    def _get_xroot_for(self, prop):
        """ :return: the configured root for a given property based on the property name """

        return self._get_xpath_for(f'_{prop}_root')

    def _parse_complex(self, prop):
        """ Default parsing operation for a complex struct """

        xpath_root = None
        xpath_map = self._data_structures[prop]

        return parse_complex(self._xml_tree, xpath_root, xpath_map, prop)

    def _parse_complex_list(self, prop):
        """ Default parsing operation for lists of complex structs """

        xpath_root = self._get_xroot_for(prop)
        xpath_map = self._data_structures[prop]

        return parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

    def _parse_dates(self, prop=DATES):
        """ Creates and returns a Date Types data structure parsed from the metadata """

        return parse_dates(self._xml_tree, self._data_structures[prop])

    def _update_complex(self, **update_props):
        """ Default update operation for a complex struct """

        prop = update_props['prop']
        xpath_root = self._get_xroot_for(prop)
        xpath_map = self._data_structures[prop]

        return update_complex(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_complex_list(self, **update_props):
        """ Default update operation for lists of complex structs """

        prop = update_props['prop']
        xpath_root = self._get_xroot_for(prop)
        xpath_map = self._data_structures[prop]

        return update_complex_list(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_dates(self, xpath_root=None, **update_props):
        """
        Default update operation for Dates metadata
        :see: gis_metadata.utils.COMPLEX_DEFINITIONS[DATES]
        """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = (update_props['values'] or {}).get(DATE_VALUES) or u''
        xpaths = self._data_structures[prop]

        if not self.dates:
            date_xpaths = xpath_root
        elif self.dates[DATE_TYPE] != DATE_TYPE_RANGE:
            date_xpaths = xpaths.get(self.dates[DATE_TYPE], u'')
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

        try:
            to_dict = issubclass(new_parser_or_type, dict)
        except TypeError:
            to_dict = isinstance(new_parser_or_type, dict)

        if to_dict:
            return {p: getattr(self, p) for p in self._metadata_props if p[0] != '_'}
        else:
            return convert_parser_to(self, new_parser_or_type, self._metadata_props)

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
            raise IOError('Output file path has not been provided')

        write_element(self.update(use_template), out_file_or_path, encoding)

    def update(self, use_template=False, **metadata_defaults):
        """
        Validates instance properties and updates either a template or the original XML tree with them.
        :param use_template: if True, updates a new template XML tree; otherwise the original XML tree
        """

        self.validate()

        tree_to_update = self._xml_tree if not use_template else self._get_template(**metadata_defaults)
        supported_props = self._metadata_props

        for prop, xpath in self._data_map.items():
            if not prop.startswith('_') or prop.strip('_') in supported_props:
                # Send only public or alternate properties
                update_property(
                    tree_to_update, self._get_xroot_for(prop), xpath, prop, getattr(self, prop, u''), supported_props
                )

        return tree_to_update

    def validate(self):
        """ Default validation for updated properties: MAY be overridden in children """

        validate_properties(self._data_map, self._metadata_props)

        for prop in self._data_map:
            validate_any(prop, getattr(self, prop), self._data_structures.get(prop))

        return self
