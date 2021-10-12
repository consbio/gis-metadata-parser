""" Data structures and functionality used by all Metadata Parsers """

from frozendict import frozendict

from parserutils.collections import filter_empty, flatten_items, reduce_value, wrap_value
from parserutils.elements import get_element, get_elements, get_elements_attributes, get_elements_text
from parserutils.elements import insert_element, remove_element
from parserutils.elements import remove_element_attributes, set_element_attributes
from parserutils.elements import XPATH_DELIM

from gis_metadata.exceptions import ConfigurationError, ValidationError


# Generic identifying property name constants

KEYWORDS_PLACE = 'place_keywords'
KEYWORDS_STRATUM = 'stratum_keywords'
KEYWORDS_TEMPORAL = 'temporal_keywords'
KEYWORDS_THEME = 'thematic_keywords'


# Identifying property name constants for all complex definitions

ATTRIBUTES = 'attributes'
BOUNDING_BOX = 'bounding_box'
CONTACTS = 'contacts'
DATES = 'dates'
DIGITAL_FORMS = 'digital_forms'
LARGER_WORKS = 'larger_works'
PROCESS_STEPS = 'process_steps'
RASTER_INFO = 'raster_info'
RASTER_DIMS = '_raster_dims'


# Grouping property name constants for complex definitions

_COMPLEX_DELIM = '\n'
_COMPLEX_LISTS = frozenset({
    ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS,
    KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME,
})
_COMPLEX_STRUCTS = frozenset({BOUNDING_BOX, DATES, LARGER_WORKS, RASTER_INFO})
_COMPLEX_WITH_MULTI = frozendict({
    DATES: {'values'},
    LARGER_WORKS: {'origin'},
    PROCESS_STEPS: {'sources'}
})


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
#    2. Create a new item in COMPLEX_DEFINITIONS that represents the structure of the field
#    3. If required by all metadata parsers, add the constant to SUPPORTED_PROPS
#    4. Update the target metadata parsers with a parse and update method for the new field
#    5. Update the target metadata parsers' _init_data_map method to instantiate a ParserProperty
#    6. Create a new validation method for the type if validate_complex or validate_complex_list won't suffice
#    7. Update validate_any to recognize the constant and call the intended validation method

COMPLEX_DEFINITIONS = frozendict({
    ATTRIBUTES: frozendict({
        'label': '{label}',                       # Text
        'aliases': '{aliases}',                   # Text
        'definition': '{definition}',             # Text
        'definition_source': '{definition_src}'   # Text
    }),
    BOUNDING_BOX: frozendict({
        'east': '{east}',                         # Text
        'south': '{south}',                       # Text
        'west': '{west}',                         # Text
        'north': '{north}'                        # Text
    }),
    CONTACTS: frozendict({
        'name': '{name}',                         # Text
        'email': '{email}',                       # Text
        'organization': '{organization}',         # Text
        'position': '{position}'                  # Text
    }),
    DATES: frozendict({
        DATE_TYPE: '{type}',                      # Text
        DATE_VALUES: '{values}'                   # Text []
    }),
    DIGITAL_FORMS: frozendict({
        'name': '{name}',                         # Text
        'content': '{content}',                   # Text
        'decompression': '{decompression}',       # Text
        'version': '{version}',                   # Text
        'specification': '{specification}',       # Text
        'access_desc': '{access_desc}',           # Text
        'access_instrs': '{access_instrs}',       # Text
        'network_resource': '{network_resource}'  # Text
    }),
    LARGER_WORKS: frozendict({
        'title': '{title}',                       # Text
        'edition': '{edition}',                   # Text
        'origin': '{origin}',                     # Text []
        'online_linkage': '{online_linkage}',     # Text
        'other_citation': '{other_citation}',     # Text
        'publish_date': '{date}',                 # Text
        'publish_place': '{place}',               # Text
        'publish_info': '{info}'                  # Text
    }),
    PROCESS_STEPS: frozendict({
        'description': '{description}',           # Text
        'date': '{date}',                         # Text
        'sources': '{sources}'                    # Text []
    }),
    RASTER_INFO: frozendict({
        'dimensions': '{dimensions}',             # Text
        'row_count': '{row_count}',               # Text
        'column_count': '{column_count}',         # Text
        'vertical_count': '{vertical_count}',     # Text
        'x_resolution': '{x_resolution}',         # Text
        'y_resolution': '{y_resolution}',         # Text
    }),
    RASTER_DIMS: frozendict({
        # Captures dimension data for raster_info
        'type': '{type}',                         # Text
        'size': '{size}',                         # Text
        'value': '{value}',                       # Text
        'units': '{units}'                        # Text
    })
})

# A set of identifying property names that must be supported by all parsers

SUPPORTED_PROPS = frozenset({
    'title', 'abstract', 'purpose', 'other_citation_info', 'supplementary_info',
    'online_linkages', 'originators', 'publish_date', 'data_credits', 'digital_forms',
    'dist_contact_org', 'dist_contact_person', 'dist_email', 'dist_phone',
    'dist_address', 'dist_address_type', 'dist_city', 'dist_state', 'dist_postal', 'dist_country',
    'dist_liability', 'processing_fees', 'processing_instrs', 'resource_desc', 'tech_prerequisites',
    ATTRIBUTES, 'attribute_accuracy', BOUNDING_BOX, CONTACTS, 'dataset_completeness',
    LARGER_WORKS, PROCESS_STEPS, RASTER_INFO, 'use_constraints',
    DATES, KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME
})


def format_xpaths(xpath_map, *args, **kwargs):
    """ :return: a copy of xpath_map, but with XPATHs formatted with ordered or keyword values """

    formatted = {}.fromkeys(xpath_map)

    for key, xpath in xpath_map.items():
        formatted[key] = xpath.format(*args, **kwargs)

    return formatted


def get_xpath_root(xpath):
    """ :return: the base of an XPATH: the part preceding any format keys or attribute references """

    if xpath:
        if xpath.startswith('@'):
            xpath = ''
        else:
            index = xpath.find('/@' if '@' in xpath else '/{')
            xpath = xpath[:index] if index >= 0 else xpath

    return xpath


def get_xpath_branch(xroot, xpath):
    """ :return: the relative part of an XPATH: that which extends past the root provided """

    if xroot and xpath and xpath.startswith(xroot):
        xpath = xpath[len(xroot):]
        xpath = xpath.lstrip(XPATH_DELIM)

    return xpath


def get_xpath_tuple(xpath):
    """ :return: a tuple with the base of an XPATH followed by any format key or attribute reference """

    xroot = get_xpath_root(xpath)
    xattr = None

    if xroot != xpath:
        xattr = get_xpath_branch(xroot, xpath).strip('@')

    return (xroot, xattr)


def get_default_for(prop, value):
    """ Ensures complex property types have the correct default values """

    prop = prop.strip('_')     # Handle alternate props (leading underscores)
    val = reduce_value(value)  # Filtering of value happens here

    if prop in _COMPLEX_LISTS:
        return wrap_value(val)
    elif prop in _COMPLEX_STRUCTS:
        return val or {}
    else:
        return u'' if val is None else val


def get_default_for_complex(prop, value, xpath=''):

    # Ensure sub-props of complex structs and complex lists that take multiple values are wrapped as lists
    val = [
        {k: get_default_for_complex_sub(prop, k, v, xpath) for k, v in val.items()}
        for val in wrap_value(value)
    ]

    return val if prop in _COMPLEX_LISTS else reduce_value(val, {})


def get_default_for_complex_sub(prop, subprop, value, xpath):

    # Handle alternate props (leading underscores)
    prop = prop.strip('_')
    subprop = subprop.strip('_')

    value = wrap_value(value)
    if subprop in _COMPLEX_WITH_MULTI.get(prop, ''):
        return value  # Leave sub properties allowing lists wrapped

    # Join on comma for element attribute values; newline for element text values
    return ','.join(value) if '@' in xpath else _COMPLEX_DELIM.join(value)


def has_property(elem_to_parse, xpath):
    """
    Parse xpath for any attribute reference "path/@attr" and check for root and presence of attribute.
    :return: True if xpath is present in the element along with any attribute referenced, otherwise False
    """

    xroot, attr = get_xpath_tuple(xpath)

    if not xroot and not attr:
        return False
    elif not attr:
        return bool(get_elements_text(elem_to_parse, xroot))
    else:
        return bool(get_elements_attributes(elem_to_parse, xroot, attr))


def parse_complex(tree_to_parse, xpath_root, xpath_map, complex_key):
    """
    Creates and returns a Dictionary data structure parsed from the metadata.
    :param tree_to_parse: the XML tree compatible with element_utils to be parsed
    :param xpath_root: the XPATH location of the structure inside the parent element
    :param xpath_map: a dict of XPATHs corresponding to a complex definition
    :param complex_key: indicates which complex definition describes the structure
    """

    complex_struct = {}

    for prop in COMPLEX_DEFINITIONS.get(complex_key, xpath_map):
        # Normalize complex values: treat values with newlines like values from separate elements
        parsed = parse_property(tree_to_parse, xpath_root, xpath_map, prop)
        parsed = reduce_value(flatten_items(v.split(_COMPLEX_DELIM) for v in wrap_value(parsed)))

        complex_struct[prop] = get_default_for_complex_sub(complex_key, prop, parsed, xpath_map[prop])

    return complex_struct if any(complex_struct.values()) else {}


def parse_complex_list(tree_to_parse, xpath_root, xpath_map, complex_key):
    """
    Creates and returns a list of Dictionary data structures parsed from the metadata.
    :param tree_to_parse: the XML tree compatible with element_utils to be parsed
    :param xpath_root: the XPATH location of each structure inside the parent element
    :param xpath_map: a dict of XPATHs corresponding to a complex definition
    :param complex_key: indicates which complex definition describes each structure
    """

    complex_list = []

    for element in get_elements(tree_to_parse, xpath_root):
        complex_struct = parse_complex(element, xpath_root, xpath_map, complex_key)
        if complex_struct:
            complex_list.append(complex_struct)

    return complex_list


def parse_dates(tree_to_parse, xpath_map):
    """
    Creates and returns a Dates Dictionary data structure given the parameters provided
    :param tree_to_parse: the XML tree from which to construct the Dates data structure
    :param xpath_map: a map containing the following type-specific XPATHs:
        multiple, range, range_begin, range_end, and single
    """

    # Determine dates to query based on metadata elements

    values = wrap_value(parse_property(tree_to_parse, None, xpath_map, DATE_TYPE_SINGLE))
    if len(values) == 1:
        return {DATE_TYPE: DATE_TYPE_SINGLE, DATE_VALUES: values}
    elif len(values) > 1:
        return {DATE_TYPE: DATE_TYPE_MULTIPLE, DATE_VALUES: values}

    values = wrap_value(parse_property(tree_to_parse, None, xpath_map, DATE_TYPE_MULTIPLE))
    if len(values) == 1:
        return {DATE_TYPE: DATE_TYPE_SINGLE, DATE_VALUES: values}
    elif len(values) > 1:
        return {DATE_TYPE: DATE_TYPE_MULTIPLE, DATE_VALUES: values}

    values = flatten_items(
        d for x in (DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END)
        for d in wrap_value(parse_property(tree_to_parse, None, xpath_map, x))
    )
    if len(values) == 1:
        return {DATE_TYPE: DATE_TYPE_SINGLE, DATE_VALUES: values}
    elif len(values) == 2:
        return {DATE_TYPE: DATE_TYPE_RANGE, DATE_VALUES: values}
    elif len(values) > 2:
        return {DATE_TYPE: DATE_TYPE_MULTIPLE, DATE_VALUES: values}

    return {}


def parse_property(tree_to_parse, xpath_root, xpath_map, prop):
    """
    Defines the default parsing behavior for metadata values.
    :param tree_to_parse: the XML tree compatible with element_utils to be parsed
    :param xpath_root: used to determine the relative XPATH location within the parent element
    :param xpath_map: a dict of XPATHs that may contain alternate locations for a property
    :param prop: the property to parse: corresponds to a key in xpath_map
    """

    xpath = xpath_map[prop]

    if isinstance(xpath, ParserProperty):
        if xpath.xpath is None:
            return xpath.get_prop(prop)

        xpath = xpath.xpath

    if xpath_root:
        xpath = get_xpath_branch(xpath_root, xpath)

    parsed = None

    if not has_property(tree_to_parse, xpath):
        # Element has no text: try next alternate location

        alternate = '_' + prop
        if alternate in xpath_map:
            return parse_property(tree_to_parse, xpath_root, xpath_map, alternate)

    elif '@' not in xpath:
        parsed = get_elements_text(tree_to_parse, xpath)
    else:
        xroot, xattr = get_xpath_tuple(xpath)
        parsed = get_elements_attributes(tree_to_parse, xroot, xattr)

    return get_default_for(prop, parsed)


def update_property(tree_to_update, xpath_root, xpaths, prop, values, supported=None):
    """
    Either update the tree the default way, or call the custom updater

    Default Way: Existing values in the tree are overwritten. If xpaths contains a single path,
    then each value is written to the tree at that path. If xpaths contains a list of xpaths,
    then the values corresponding to each xpath index are written to their respective locations.
    In either case, empty values are ignored.

    :param tree_to_update: the XML tree compatible with element_utils to be updated
    :param xpath_root: the XPATH location shared by all the xpaths passed in
    :param xpaths: a string or a list of strings representing the XPATH location(s) to which to write values
    :param prop: the name of the property of the parser containing the value(s) with which to update the tree
    :param values: a single value, or a list of values to write to the specified XPATHs

    :see: ParserProperty for more on custom updaters

    :return: a list of all elements updated by this operation
    """

    if supported and prop.startswith('_') and prop.strip('_') in supported:
        values = u''  # Remove alternate elements: write values only to primary location
    else:
        values = get_default_for(prop, values)  # Enforce defaults as required per property

    if not xpaths:
        return []
    elif not isinstance(xpaths, ParserProperty):
        return _update_property(tree_to_update, xpath_root, xpaths, values)
    else:
        # Call ParserProperty.set_prop without xpath_root (managed internally)
        return xpaths.set_prop(tree_to_update=tree_to_update, prop=prop, values=values)


def _update_property(tree_to_update, xpath_root, xpaths, values):
    """
    Default update operation for a single parser property. If xpaths contains one xpath,
    then one element per value will be inserted at that location in the tree_to_update;
    otherwise, the number of values must match the number of xpaths.
    """

    # Inner function to update a specific XPATH with the values provided

    def update_element(elem, idx, root, path, vals):
        """ Internal helper function to encapsulate single item update """

        has_root = bool(root and len(path) > len(root) and path.startswith(root))
        path, attr = get_xpath_tuple(path)  # 'path/@attr' to ('path', 'attr')

        if attr:
            removed = [get_element(elem, path)]
            remove_element_attributes(removed[0], attr)
        elif not has_root:
            removed = wrap_value(remove_element(elem, path))
        else:
            path = get_xpath_branch(root, path)
            removed = [] if idx != 0 else [remove_element(e, path, True) for e in get_elements(elem, root)]

        if not vals:
            return removed

        items = []

        for i, val in enumerate(wrap_value(vals)):
            elem_to_update = elem

            if has_root:
                elem_to_update = insert_element(elem, (i + idx), root)

            val = val.decode('utf-8') if not isinstance(val, str) else val
            if not attr:
                items.append(insert_element(elem_to_update, i, path, val))
            elif path:
                items.append(insert_element(elem_to_update, i, path, **{attr: val}))
            else:
                set_element_attributes(elem_to_update, **{attr: val})
                items.append(elem_to_update)

        return items

    # Code to update each of the XPATHs with each of the values

    xpaths = reduce_value(xpaths)
    values = filter_empty(values)

    if isinstance(xpaths, str):
        return update_element(tree_to_update, 0, xpath_root, xpaths, values)
    else:
        each = []

        for index, xpath in enumerate(xpaths):
            value = values[index] if values else None
            each.extend(update_element(tree_to_update, index, xpath_root, xpath, value))

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
        # Returns the elements corresponding to property removed from the tree
        updated = update_property(tree_to_update, xpath_root, xpath_root, prop, values)
    else:
        for subprop, value in values.items():
            xpath = xpath_map[subprop]
            value = get_default_for_complex_sub(prop, subprop, value, xpath)
            update_property(tree_to_update, None, xpath, subprop, value)
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

    if not values:
        # Returns the elements corresponding to property removed from the tree
        complex_list.append(update_property(tree_to_update, xpath_root, xpath_root, prop, values))
    else:
        for idx, complex_struct in enumerate(wrap_value(values)):

            # Insert a new complex element root for each dict in the list
            complex_element = insert_element(tree_to_update, idx, xpath_root)

            for subprop, value in complex_struct.items():
                xpath = get_xpath_branch(xpath_root, xpath_map[subprop])
                value = get_default_for_complex_sub(prop, subprop, value, xpath)
                complex_list.append(update_property(complex_element, None, xpath, subprop, value))

    return complex_list


def validate_any(prop, value, xpath_map=None):
    """ Validates any metadata property, complex or simple (string or array) """

    if value is not None:
        if prop in (ATTRIBUTES, CONTACTS, DIGITAL_FORMS):
            validate_complex_list(prop, value, xpath_map)

        elif prop in (BOUNDING_BOX, LARGER_WORKS, RASTER_INFO):
            validate_complex(prop, value, xpath_map)

        elif prop == DATES:
            validate_dates(prop, value, xpath_map)

        elif prop == PROCESS_STEPS:
            validate_process_steps(prop, value)

        elif prop not in SUPPORTED_PROPS and xpath_map is not None:
            # Validate custom data structures as complex lists by default
            validate_complex_list(prop, value, xpath_map)

        else:
            for val in wrap_value(value, include_empty=True):
                validate_type(prop, val, (str, list))


def validate_complex(prop, value, xpath_map=None):
    """ Default validation for single complex data structure """

    if value is not None:
        validate_type(prop, value, dict)

        if prop in COMPLEX_DEFINITIONS:
            complex_keys = COMPLEX_DEFINITIONS[prop]
        else:
            complex_keys = {} if xpath_map is None else xpath_map

        for complex_prop, complex_val in value.items():
            complex_key = '.'.join((prop, complex_prop))

            if complex_prop not in complex_keys:
                _validation_error(prop, None, value, ('keys: {0}'.format(','.join(complex_keys))))

            validate_type(complex_key, complex_val, (str, list))


def validate_complex_list(prop, value, xpath_map=None):
    """ Default validation for Attribute Details data structure """

    if value is not None:
        validate_type(prop, value, (dict, list))

        if prop in COMPLEX_DEFINITIONS:
            complex_keys = COMPLEX_DEFINITIONS[prop]
        else:
            complex_keys = {} if xpath_map is None else xpath_map

        for idx, complex_struct in enumerate(wrap_value(value)):
            cs_idx = prop + '[' + str(idx) + ']'
            validate_type(cs_idx, complex_struct, dict)

            for cs_prop, cs_val in complex_struct.items():
                cs_key = '.'.join((cs_idx, cs_prop))

                if cs_prop not in complex_keys:
                    _validation_error(prop, None, value, ('keys: {0}'.format(','.join(complex_keys))))

                if not isinstance(cs_val, list):
                    validate_type(cs_key, cs_val, (str, list))
                else:
                    for list_idx, list_val in enumerate(cs_val):
                        list_prop = cs_key + '[' + str(list_idx) + ']'
                        validate_type(list_prop, list_val, str)


def validate_dates(prop, value, xpath_map=None):
    """ Default validation for Date Types data structure """

    if value is not None:
        validate_type(prop, value, dict)

        date_keys = set(value)

        if date_keys:
            if DATE_TYPE not in date_keys or DATE_VALUES not in date_keys:
                if prop in COMPLEX_DEFINITIONS:
                    complex_keys = COMPLEX_DEFINITIONS[prop]
                else:
                    complex_keys = COMPLEX_DEFINITIONS[DATES] if xpath_map is None else xpath_map

                _validation_error(prop, None, value, ('keys: {0}'.format(','.join(complex_keys))))

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
                validate_type(date_key, date, str)


def validate_process_steps(prop, value):
    """ Default validation for Process Steps data structure """

    if value is not None:
        validate_type(prop, value, (dict, list))

        procstep_keys = COMPLEX_DEFINITIONS[prop]

        for idx, procstep in enumerate(wrap_value(value)):
            ps_idx = prop + '[' + str(idx) + ']'
            validate_type(ps_idx, procstep, dict)

            for ps_prop, ps_val in procstep.items():
                ps_key = '.'.join((ps_idx, ps_prop))

                if ps_prop not in procstep_keys:
                    _validation_error(prop, None, value, ('keys: {0}'.format(','.join(procstep_keys))))

                if ps_prop != 'sources':
                    validate_type(ps_key, ps_val, str)
                else:
                    validate_type(ps_key, ps_val, (str, list))

                    for src_idx, src_val in enumerate(wrap_value(ps_val)):
                        src_key = ps_key + '[' + str(src_idx) + ']'
                        validate_type(src_key, src_val, str)


def validate_properties(props, required):
    """
    Ensures the key set contains the base supported properties for a Parser
    :param props: a set of property names to validate against those supported
    """

    props = set(props)
    required = set(required or SUPPORTED_PROPS)

    if len(required.intersection(props)) < len(required):
        missing = required - props
        raise ValidationError(
            'Missing property names: {props}', props=','.join(missing), missing=missing
        )


def validate_type(prop, value, expected):
    """ Default validation for all types """

    # Validate on expected type(s), but ignore None: defaults handled elsewhere
    if value is not None and not isinstance(value, expected):
        _validation_error(prop, type(value).__name__, None, expected)


def _validation_error(prop, prop_type, prop_value, expected):
    """ Default validation for updated properties """

    if prop_type is None:
        attrib = 'value'
        assigned = prop_value
    else:
        attrib = 'type'
        assigned = prop_type

    raise ValidationError(
        'Invalid property {attrib} for {prop}:\n\t{attrib}: {assigned}\n\texpected: {expected}',
        attrib=attrib, prop=prop, assigned=assigned, expected=expected,
        invalid={prop: prop_value} if attrib == 'value' else {}
    )


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
        elif xpath is not None:
            self._parser = None
        else:
            raise ConfigurationError(
                'Invalid property getter:\n\tpassed in: {param}\n\texpected: {expected}',
                param=type(prop_parser), expected='<type "callable"> or provide XPATH'
            )

        if hasattr(prop_updater, '__call__'):
            self._updater = prop_updater
        else:
            raise ConfigurationError(
                'Invalid property setter:\n\tpassed in: {param}\n\texpected: {expected}',
                param=type(prop_updater), expected='<type "callable">'
            )

        self.xpath = xpath

    def get_prop(self, prop):
        """ Calls the getter with no arguments and returns its value """

        if self._parser is None:
            raise ConfigurationError('Cannot call ParserProperty."get_prop" with no parser configured')

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
