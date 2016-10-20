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

