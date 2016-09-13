""" Data structures and functionality used by all Metadata Parsers """

from copy import deepcopy
from six import iteritems, string_types

from parserutils.collections import filter_empty, reduce_value, wrap_value
from parserutils.elements import get_element, get_elements, get_elements_text
from parserutils.elements import element_exists, insert_element, remove_element, remove_elements
from parserutils.elements import XPATH_DELIM


# Generic identifying property name constants

KEYWORDS_PLACE = 'place_keywords'
KEYWORDS_THEME = 'thematic_keywords'

# Identifying property name constants for all complex definitions

ATTRIBUTES = 'attributes'
BOUNDING_BOX = 'bounding_box'
CONTACTS = 'contacts'
DATES = 'dates'
DIGITAL_FORMS = 'digital_forms'
LARGER_WORKS = 'larger_works'
PROCESS_STEPS = 'process_steps'

# A set of identifying property names that must be supported by all parsers

_required_keys = {
    'title', 'abstract', 'purpose', 'supplementary_info',
    'online_linkages', 'originators', 'publish_date', 'data_credits',
    'dist_contact_org', 'dist_contact_person', 'dist_email', 'dist_phone',
    'dist_address', 'dist_city', 'dist_state', 'dist_postal', 'dist_country',
    'dist_liability', 'processing_fees', 'processing_instrs', 'resource_desc', 'tech_prerequisites',
    ATTRIBUTES, 'attribute_accuracy', BOUNDING_BOX, CONTACTS, 'dataset_completeness',
    LARGER_WORKS, PROCESS_STEPS, 'use_constraints',
    DATES, KEYWORDS_PLACE, KEYWORDS_THEME
}

# Date specific constants for the DATES complex structure

DATE_TYPE_MISSING = ''
DATE_TYPE_MULTIPLE = 'multiple'
DATE_TYPE_RANGE = 'range'
DATE_TYPE_RANGE_BEGIN = 'range_begin'
DATE_TYPE_RANGE_END = 'range_end'
DATE_TYPE_SINGLE = 'single'

DATE_TYPES = (
    DATE_TYPE_MISSING, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE, DATE_TYPE_RANGE
)

DATE_TYPE = 'type'
DATE_VALUES = 'values'


# To add a new complex definition field:
#    1. Create a new constant representing the property name for the field
#    2. Create a new item in _complex_definitions that represents the structure of the field
#    3. If required by all metadata parsers, add the constant to _required_keys
#    4. Update the target metadata parsers with a parse and update method for the new field
#    5. Update the target metadata parsers' _init_data_map method to instantiate a ParserProperty
#    6. Create a new validation method for the type if validate_complex or validate_complex_list won't suffice
#    7. Update validate_any to recognize the constant and call the intended validation method

_complex_definitions = {
    ATTRIBUTES: {
        'label': '{label}',                       # Text
        'aliases': '{aliases}',                   # Text
        'definition': '{definition}',             # Text
        'definition_source': '{definition_src}'   # Text
    },
    BOUNDING_BOX: {
        'east': '{east}',                         # Text
        'south': '{south}',                       # Text
        'west': '{west}',                         # Text
        'north': '{north}'                        # Text
    },
    CONTACTS: {
        'name': '{name}',                         # Text
        'email': '{email}',                       # Text
        'organization': '{organization}',         # Text
        'position': '{position}'                  # Text
    },
    DATES: {
        DATE_TYPE: '{type}',                      # Text
        DATE_VALUES: '{values}'                   # Text []
    },
    DIGITAL_FORMS: {
        'name': '{name}',                         # Text
        'content': '{content}',                   # Text
        'decompression': '{decompression}',       # Text
        'version': '{version}',                   # Text
        'specification': '{specification}',       # Text
        'access_desc': '{access_desc}',           # Text
        'access_instrs': '{access_instrs}',       # Text
        'network_resource': '{network_resource}'  # Text []
    },
    LARGER_WORKS: {
        'title': '{title}',                       # Text
        'edition': '{edition}',                   # Text
        'origin': '{origin}',                     # Text []
        'online_linkage': '{online_linkage}',     # Text
        'other_citation': '{other_citation}',     # Text
        'publish_date': '{date}',                 # Text
        'publish_place': '{place}',               # Text
        'publish_info': '{info}'                  # Text
    },
    PROCESS_STEPS: {
        'description': '{description}',           # Text
        'date': '{date}',                         # Text
        'sources': '{sources}'                    # Text []
    }
}


def format_xpath(xpath, *args, **kwargs):
    """ :return: an XPATH formatted with the ordered or keyword values """
    return xpath.format(*args, **kwargs)


def format_xpaths(xpath_map, *args, **kwargs):
    """ :return: a copy of xpath_map, but with XPATHs formatted with ordered or keyword values """

    formatted = {}.fromkeys(xpath_map)

    for key, xpath in iteritems(xpath_map):
        formatted[key] = format_xpath(xpath, *args, **kwargs)

    return formatted


def get_complex_definitions():
    """
    Get a deep copy of the complex data structures definition, which contains
    a map with all of the supported data structure definitions by field name
    """

    return deepcopy(_complex_definitions)


def get_required_keys():
    """
    Get a deep copy of the set of required keys, which contains the set of
    identifying property names that must be supported by all parsers
    """

    return deepcopy(_required_keys)


def get_xpath_root(xpath):
    """ :return: the base of an XPATH: the part preceding any formattable segments """

    if xpath:
        format_idx = xpath.find('/{')
        xpath = xpath[:format_idx] if format_idx >= 0 else xpath

    return xpath


def get_xpath_branch(xroot, xpath):
    """ :return: the relative part of an XPATH: that which extends past the root provided """

    if xroot and xpath and xpath.startswith(xroot):
        xpath = xpath.replace(xroot, '')
        xpath = xpath.lstrip(XPATH_DELIM)

    return xpath


def filter_property(prop, value):
    """ Ensures complex property types have the correct default values """

    val = reduce_value(value)  # Filtering of value happens here

    if prop in (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, KEYWORDS_PLACE, KEYWORDS_THEME, PROCESS_STEPS):
        return val or []
    elif prop in (BOUNDING_BOX, DATES, LARGER_WORKS):
        return val or {}
    else:
        return val


def parse_complex(tree_to_parse, xpath_root, xpath_map, complex_key):
    """
    Creates and returns a Dictionary data structure parsed from the metadata.
    :param tree_to_update: the XML tree compatible with element_utils to be parsed
    :param props: a set or list of sub-properties to be stored in the structure
    :param xpath_map: a Dictionary of XPATHs corresponding to the props provided
    """

    complex_struct = {}

    for prop in _complex_definitions[complex_key].keys():
        xpath = xpath_map[prop]
        complex_struct[prop] = reduce_value(get_elements_text(tree_to_parse, xpath))

    return complex_struct if any(complex_struct.values()) else {}


def parse_complex_list(tree_to_parse, xpath_root, xpath_map, complex_key):
    """
    Creates and returns a list of Dictionary data structures parsed from the metadata.
    :param tree_to_update: the XML tree compatible with element_utils to be parsed
    :param props: a set or list of sub-properties to be stored in each structure
    :param xpath_root: the XPATH location of the parent element of all the structures
    :param xpath_map: a Dictionary of XPATHs corresponding to the props provided
    """

    complex_list = []

    for element in get_elements(tree_to_parse, xpath_root):
        complex_struct = {}

        for prop in _complex_definitions[complex_key].keys():
            xpath = get_xpath_branch(xpath_root, xpath_map[prop])
            complex_struct[prop] = reduce_value(get_elements_text(element, xpath))

        if any(complex_struct.values()):
            complex_list.append(complex_struct)

    return complex_list


def parse_dates(tree_to_parse, date_xpath_map, date_type=None, date_xpaths=None, date_values=None):
    """
    Creates and returns a Dates Dictionary data structure given the parameters provided
    :param tree_to_parse: the XML tree from which to construct the Dates data structure
    :param date_xpath_map: a map containing the following type-specific XPATHs:
        multiple, range_begin, range_end, and single
    :param date_type: if type is known, use it to determine which XPATHs to parse values
    :param date_xpaths: if an array of XPATHs is provided, use them to parse values from tree_to_parse
    :param date_values: if values are already parsed, use them to construct a Dates data structure
    """

    if date_type is None or date_xpaths is None:
        # Pull the intended XPATHs out of the map

        dt_multiple_xpath = date_xpath_map[DATE_TYPE_MULTIPLE]
        dt_range_beg_xpath = date_xpath_map[DATE_TYPE_RANGE_BEGIN]
        dt_range_end_xpath = date_xpath_map[DATE_TYPE_RANGE_END]
        dt_single_xpath = date_xpath_map[DATE_TYPE_SINGLE]

    if date_type is None:
        # Determine dates type based on metadata elements

        if element_exists(tree_to_parse, dt_multiple_xpath):
            date_type = DATE_TYPE_MULTIPLE
        elif (element_exists(tree_to_parse, dt_range_beg_xpath) and
              element_exists(tree_to_parse, dt_range_end_xpath)):
            date_type = DATE_TYPE_RANGE
        elif element_exists(tree_to_parse, dt_single_xpath):
            date_type = DATE_TYPE_SINGLE
        else:
            return {}

    if date_xpaths is None:
        # Determine XPATHs from dates type

        if date_type == DATE_TYPE_MULTIPLE:
            date_xpaths = [dt_multiple_xpath]
        elif date_type == DATE_TYPE_RANGE:
            date_xpaths = [dt_range_beg_xpath, dt_range_end_xpath]
        elif date_type == DATE_TYPE_SINGLE:
            date_xpaths = [dt_single_xpath]

        date_xpaths = filter_empty(date_xpaths, [])

    if date_values is None:
        date_values = [text for xpath in date_xpaths for text in get_elements_text(tree_to_parse, xpath)]

    if len(date_values) == 1:
        date_type = DATE_TYPE_SINGLE

    return {DATE_TYPE: date_type, DATE_VALUES: date_values}


def update_property(tree_to_update, xpath_root, xpaths, prop, values):
    """
    Either update the tree the default way, or call the custom updater

    Default Way: Existing values in the tree are overwritten. If xpaths contains a single path,
    then each value is written to the tree at that path. If xpaths contains a list of xpaths,
    then the values corresponding to each xpath index are written to their respective locations.
    In either case, empty values are ignored.

    :param tree_to_update: the XML tree compatible with element_utils to be updated
    :param xpath_root: the XPATH location shared by all the xpaths passed in
    :param xpaths: a string or a list of strings representing the XPATH location(s) of the values to update
    :param prop: the name of the property of the parser containing the value(s) with which to update the tree
    :param values: a single value, or a list of values to write to the specified XPATHs

    :see: ParserProperty for more on custom updaters

    :return: a list of all elements updated by this operation
    """

    if not xpaths:
        return []
    elif not isinstance(xpaths, ParserProperty):
        return _update_property(tree_to_update, xpath_root, xpaths, prop, values)

    custom_update = xpaths.set_prop

    # Do not send xpath_root: this is generally parsed in the custom update method
    return custom_update(tree_to_update=tree_to_update, prop=prop, values=values)


def _update_property(tree_to_update, xpath_root, xpaths, prop, values):
    """
    Default update operation for a single parser property. If xpaths contains one xpath,
    then one element per value will be inserted at that location in the tree_to_update;
    otherwise, the number of values must match the number of xpaths.
    """

    # Inner function to update a specific XPATH with the values provided

    def update_element(elem, idx, root, path, vals):
        """ Internal helper function to encapsulate single item update """

        has_root = (root and len(path) > len(root) and path.startswith(root))

        if not has_root:
            remove_element(elem, path)
        else:
            path = get_xpath_branch(root, path)

            if idx == 0:
                for e in get_elements(elem, root):
                    remove_element(e, path, True)

        items = []

        for i, val in enumerate(wrap_value(vals)):
            if len(val):
                elem_to_update = elem

                if has_root:
                    elem_to_update = insert_element(elem, (i + idx), root)

                val = val.decode('utf-8') if not isinstance(val, string_types) else val
                items.append(insert_element(elem_to_update, i, path, val))

        return items

    # Code to update each of the XPATHs with each of the values

    xpaths = reduce_value(xpaths)

    if not values:
        return remove_elements(tree_to_update, xpaths)
    elif isinstance(xpaths, string_types):
        # Insert an element for each value
        return update_element(tree_to_update, 0, xpath_root, xpaths, values)
    else:
        # Insert elements for each XPATH provided (values must correspond)
        each = []

        for index, xpath in enumerate(xpaths):
            each.extend(update_element(tree_to_update, index, xpath_root, xpath, values[index]))

        return each


def update_complex(tree_to_update, xpath_root, xpath_map, prop, values):
    """
    Updates and returns the updated complex Element parsed from tree_to_update.
    :param tree_to_update: the XML tree compatible with element_utils to be updated
    :param xpath_root: the XPATH location of the root of the complex Element
    :param xpath_map: a Dictionary of XPATHs corresponding to the complex structure definition
    :param prop: the property identifying the complex structure to be serialized
    :param values: a Dictionary representing the complex structure to be updated
    """

    remove_element(tree_to_update, xpath_root, True)

    values = reduce_value(values, {})

    if not values:
        updated = update_property(tree_to_update, xpath_root, xpath_root, prop, values)
    else:
        for subprop, val in iteritems(values):
            update_property(tree_to_update, None, xpath_map[subprop], subprop, val)
        updated = get_element(tree_to_update, xpath_root)

    return updated


def update_complex_list(tree_to_update, xpath_root, xpath_map, prop, values):
    """
    Updates and returns the list of updated complex Elements parsed from tree_to_update.
    :param tree_to_update: the XML tree compatible with element_utils to be updated
    :param xpath_root: the XPATH location of each complex Element
    :param xpath_map: a Dictionary of XPATHs corresponding to the complex structure definition
    :param prop: the property identifying the complex structure to be serialized
    :param values: a List containing the updated complex structures as Dictionaries
    """

    complex_list = []

    remove_element(tree_to_update, xpath_root, True)

    for idx, complex_struct in enumerate(wrap_value(values)):

        # Insert a new complex element root for each dict in the list
        complex_element = insert_element(tree_to_update, idx, xpath_root)

        for subprop, value in iteritems(complex_struct):
            xpath = get_xpath_branch(xpath_root, xpath_map[subprop])
            complex_list.append(update_property(complex_element, None, xpath, subprop, value))

    return complex_list


def validate_any(prop, value):
    """ Validates any metadata property, complex or simple (string or array) """

    if value is not None:
        if prop in [ATTRIBUTES, CONTACTS, DIGITAL_FORMS]:
            validate_complex_list(prop, value)

        elif prop in [BOUNDING_BOX, LARGER_WORKS]:
            validate_complex(prop, value)

        elif prop == DATES:
            validate_dates(prop, value)

        elif prop == PROCESS_STEPS:
            validate_process_steps(prop, value)

        else:
            for val in wrap_value(value):
                validate_type(prop, val, string_types)


def validate_complex(prop, value):
    """ Default validation for single complex data structure """

    if value is not None:
        validate_type(prop, value, dict)

        complex_keys = _complex_definitions[prop].keys()

        for complex_prop, complex_val in iteritems(value):
            complex_key = '.'.join((prop, complex_prop))

            if complex_prop not in complex_keys:
                _validation_error(prop, None, value, ('keys: {0}'.format(complex_keys)))

            validate_type(complex_key, complex_val, (string_types, list))


def validate_complex_list(prop, value):
    """ Default validation for Attribute Details data structure """

    if value is not None:
        validate_type(prop, value, (dict, list))

        complex_keys = _complex_definitions[prop].keys()

        for idx, complex_struct in enumerate(wrap_value(value)):
            cs_idx = prop + '[' + str(idx) + ']'
            validate_type(cs_idx, complex_struct, dict)

            for cs_prop, cs_val in iteritems(complex_struct):
                cs_key = '.'.join((cs_idx, cs_prop))

                if cs_prop not in complex_keys:
                    _validation_error(prop, None, value, ('keys: {0}'.format(complex_keys)))

                if not isinstance(cs_val, list):
                    validate_type(cs_key, cs_val, (string_types, list))
                else:
                    for list_idx, list_val in enumerate(cs_val):
                        list_prop = cs_key + '[' + str(list_idx) + ']'
                        validate_type(list_prop, list_val, string_types)


def validate_dates(prop, value):
    """ Default validation for Date Types data structure """

    if value is not None:
        validate_type(prop, value, dict)

        date_keys = value.keys()

        if date_keys:
            if DATE_TYPE not in date_keys or DATE_VALUES not in date_keys:
                _validation_error(prop, None, value, ('keys: {0}'.format(_complex_definitions[prop].keys())))

            date_type = value[DATE_TYPE]

            if date_type not in DATE_TYPES:
                _validation_error('dates.type', None, date_type, DATE_TYPES)

            date_vals = value[DATE_VALUES]

            validate_type('dates.values', date_vals, list)

            dates_len = len(date_vals)

            if date_type == DATE_TYPE_MISSING and dates_len != 0:
                _validation_error('len(dates.values)', None, dates_len, 0)

            if date_type == DATE_TYPE_SINGLE and dates_len != 1:
                _validation_error('len(dates.values)', None, dates_len, 1)

            if date_type == DATE_TYPE_RANGE and dates_len != 2:
                _validation_error('len(dates.values)', None, dates_len, 2)

            if date_type == DATE_TYPE_MULTIPLE and dates_len < 2:
                _validation_error('len(dates.values)', None, dates_len, 'at least two')

            for idx, date in enumerate(date_vals):
                date_key = 'dates.value[' + str(idx) + ']'
                validate_type(date_key, date, string_types)


def validate_process_steps(prop, value):
    """ Default validation for Process Steps data structure """

    if value is not None:
        validate_type(prop, value, (dict, list))

        procstep_keys = _complex_definitions[prop].keys()

        for idx, procstep in enumerate(wrap_value(value)):
            ps_idx = prop + '[' + str(idx) + ']'
            validate_type(ps_idx, procstep, dict)

            for ps_prop, ps_val in iteritems(procstep):
                ps_key = '.'.join((ps_idx, ps_prop))

                if ps_prop not in procstep_keys:
                    _validation_error(prop, None, value, ('keys: {0}'.format(procstep_keys)))

                if ps_prop != 'sources':
                    validate_type(ps_key, ps_val, string_types)
                else:
                    validate_type(ps_key, ps_val, (string_types, list))

                    for src_idx, src_val in enumerate(wrap_value(ps_val)):
                        src_key = ps_key + '[' + str(src_idx) + ']'
                        validate_type(src_key, src_val, string_types)


def validate_type(prop, value, expected):
    """ Default validation for all types """

    if not isinstance(value, expected):
        _validation_error(prop, type(value), None, expected)


def _validation_error(prop, prop_type, prop_value, expected):
    """ Default validation for updated properties """

    if prop_type is None:
        attrib = 'value'
        assigned = prop_value
    else:
        attrib = 'type'
        assigned = prop_type

    raise ParserException(
        'Invalid property {attrib} for {prop}:\n\t{attrib}: {assigned}\n\texpected: {expected}',
        attrib=attrib, prop=prop, assigned=assigned, expected=expected
    )


def validate_keyset(props):
    """
    Ensures the key set contains the required properties for a Parser
    :param props: a set of keys to validate against those required
    """

    props = set(props)

    if len(_required_keys.intersection(props)) < len(_required_keys):
        raise ParserException(
            'Missing property names: {props}',
            props=', '.join(_required_keys - props)
        )


class ParserException(Exception):
    """ A class to encapsulate all parsing exceptions """

    def __init__(self, msg_format, *args, **kwargs):
        """
        Call Exception with a message formatted with named arguments from
        a Dictionary with values by key, or a list of named parameters.
        """
        Exception.__init__(self, msg_format.format(*args, **kwargs))


class ParserProperty(object):
    """
    A class to manage Parser dynamic getter & setters.
    Usually an XPATH is sufficient to define reads and writes,
    but for complex data structures more processing is necessary.
    """

    def __init__(self, prop_parser, prop_updater, xpath=None):
        """ Initialize with callables for getting and setting """

        if hasattr(prop_parser, '__call__'):
            self._parser = prop_parser
        else:
            raise ParserException(
                'Invalid property getter:\n\tpassed in: {param}\n\texpected: {expected}',
                param=type(prop_parser), expected='<type "callable">'
            )

        if hasattr(prop_updater, '__call__'):
            self._updater = prop_updater
        else:
            raise ParserException(
                'Invalid property setter:\n\tpassed in: {param}\n\texpected: {expected}',
                param=type(prop_updater), expected='<type "callable">'
            )

        self.xpath = get_xpath_root(xpath)

    def __call__(self, prop=None):
        """ :return: the value of the getter by default """
        return self.get_prop(prop)

    def get_prop(self, prop):
        """ Calls the getter with no arguments and returns its value """
        return self._parser(prop) if prop else self._parser()

    def set_prop(self, **setter_args):
        """
        Calls the setter with the specified keyword arguments for flexibility.
        :param setter_args: must contain tree_to_update, prop, values
        :return: None, or the value updated for complex values
        """

        if self.xpath:
            setter_args['xpaths'] = self.xpath

        return self._updater(**setter_args)
