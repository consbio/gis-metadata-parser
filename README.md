# gis_metadata_parser
Parser for GIS metadata standards including ArcGIS, FGDC and ISO-19115.

[![Build Status](https://travis-ci.org/consbio/gis-metadata-parser.png?branch=master)](https://travis-ci.org/consbio/gis-metadata-parser) [![Coverage Status](https://coveralls.io/repos/github/consbio/gis-metadata-parser/badge.svg?branch=master)](https://coveralls.io/github/consbio/gis-metadata-parser?branch=master)

#Installation#
Install with `pip install gis-metadata-parser`.

#Usage#

Parsers can be instantiated from files, XML strings or URLs. They can be converted from one standard to another as well.
```python
from gis_metadata.arcgis_metadata_parser import ArcGISParser
from gis_metadata.fgdc_metadata_parser import FgdcParser
from gis_metadata.iso_metadata_parser import IsoParser
from gis_metadata.metadata_parser import get_metadata_parser

# From file objects
with open(r'/path/to/metadata.xml') as metadata:
    fgdc_from_file = FgdcParser(metadata)

with open(r'/path/to/metadata.xml') as metadata:
    iso_from_file = IsoParser(metadata)

# Detect standard based on root element, metadata
fgdc_from_string = get_metadata_parser(
    """
    <?xml version='1.0' encoding='UTF-8'?>
    <metadata>
        <idinfo>
        </idinfo>
    </metadata>
    """
)

# Detect ArcGIS standard based on root element and its nodes
iso_from_string = get_metadata_parser(
    """
    <?xml version='1.0' encoding='UTF-8'?>
    <metadata>
        <dataIdInfo/></dataIdInfo>
        <distInfo/></distInfo>
        <dqInfo/></dqInfo>
    </metadata>
    """
)

# Detect ISO standard based on root element, MD_Metadata or MI_Metadata
iso_from_string = get_metadata_parser(
    """
    <?xml version='1.0' encoding='UTF-8'?>
    <MD_Metadata>
        <identificationInfo>
        </identificationInfo>
    </MD_Metadata>
    """
)

# Convert from one standard to another
fgdc_converted = iso_from_file.convert_to(FgdcParser)
iso_converted = fgdc_from_file.convert_to(IsoParser)
arcgis_converted = iso_converted.convert_to(ArcGISParser)
```

Finally, the properties of the parser can be updated, validated, applied and output:
```python
with open(r'/path/to/metadata.xml') as metadata:
    fgdc_from_file = FgdcParser(metadata)

# Example simple properties
fgdc_from_file.title
fgdc_from_file.abstract
fgdc_from_file.place_keywords
fgdc_from_file.thematic_keywords

# :see: gis_metadata.utils.get_supported_props for list of all supported properties

# Complex properties
fgdc_from_file.attributes
fgdc_from_file.bounding_box
fgdc_from_file.dates
fgdc_from_file.digital_forms
fgdc_from_file.larger_works
fgdc_from_file.process_steps

# :see: gis_metadata.utils.get_complex_definitions for structure of all complex properties

# Update properties
fgdc_from_file.title = 'New Title'
fgdc_from_file.dates = {'type': 'single' 'values': '1/1/2016'}

# Apply updates
fgdc_from_file.validate()                                      # Ensure updated properties are valid
fgdc_from_file.serialize()                                     # Output updated XML as a string
fgdc_from_file.write()                                         # Output updated XML to existing file
fgdc_from_file.write(out_file_or_path='/path/to/updated.xml')  # Output updated XML to new file
```

#Extending and Customizing#

Any of the supported parsers can be extended to include more of a standard's supported data.
```python
from gis_metadata.iso_metadata_parser import IsoParser
from gis_metadata.utils import CONTACTS, format_xpaths, get_complex_definitions, ParserProperty


class CustomIsoParser(IsoParser):

    def _init_data_map(self):
        super(CustomIsoParser, self)._init_data_map()

        # Basic property: text or list (with default location)
        lang_prop = 'metadata_language'
        self._data_map[lang_prop] = 'language/CharacterString'
        self._data_map['_' + lang_prop] = 'language/LanguageCode/@codeListValue'

        # Complex structure (reuse of contacts structure plus phone)
        ct_prop = 'metadata_contacts'
        ct_format = 'contact/CI_ResponsibleParty/{ct_path}'
        ct_defintion = get_complex_definitions()[CONTACTS]
        ct_defintion['phone'] = '{phone}'

        # Reusing CONTACT structure definition to specify locations per prop
        self._data_structures[ct_prop] = format_xpaths(
            ct_defintion,
            name=ct_format.format(ct_path='individualName/CharacterString'),
            organization=ct_format.format(ct_path='organisationName/CharacterString'),
            position=ct_format.format(ct_path='positionName/CharacterString'),
            phone=ct_format.format(
                ct_path='contactInfo/CI_Contact/phone/CI_Telephone/voice/CharacterString'
            ),
            email=ct_format.format(
                ct_path='contactInfo/CI_Contact/address/CI_Address/electronicMailAddress/CharacterString'
            )
        )

        # Set the root: elements will be inserted at "contact" level
        # By default we would get multiple "CI_ResponsibleParty" elements
        # This way we get multiple "contact" elements, each with a "CI_ResponsibleParty"
        self._data_map['_{prop}_root'.format(prop=ct_prop)] = 'contact'

        # Use the built-in support for parsing complex properties (or customize a parser/updater)
        self._data_map[ct_prop] = ParserProperty(self._parse_complex_list, self._update_complex_list)
        self._metadata_props.add(lang_prop)

        # Ensure the parent logic knows about the two custom properties
        self._metadata_props.add(lang_prop)
        self._metadata_props.add(ct_prop)


with open(r'C:\Users\Daniel\Docs\Desktop\iso_test_contacts.xml') as metadata:
    iso_from_file = CustomIsoParser(metadata)

iso_from_file.metadata_language
iso_from_file.metadata_contacts
```
