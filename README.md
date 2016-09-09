# gis_metadata_parser
Parser for GIS metadata standards including FGDC and ISO-19115.

[![Build Status](https://travis-ci.org/consbio/gis-metadata-parser.png?branch=master)](https://travis-ci.org/consbio/gis-metadata-parser) [![Coverage Status](https://coveralls.io/repos/github/consbio/gis-metadata-parser/badge.svg?branch=master)](https://coveralls.io/github/consbio/gis-metadata-parser?branch=master)

#Installation#
Install with `pip install gis-metadata-parser`.

#Usage#

Parsers can be instantiated from files, XML strings or URLs. They can be converted from one standard to another as well.
```
from gis_metadata.metadata.fgdc_metadata_parser import FgdcParser
from gis_metadata.metadata.iso_metadata_parser import IsoParser
from gis_metadata.metadata.metadata_parser import get_metadata_parser

# From file objects
fgdc_from_file = FgdcParser(file(r'/path/to/metadata.xml'))
iso_from_file = IsoParser(file(r'/path/to/metadata.xml'))

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

# Detect standard based on root element, MD_Metadata or MI_Metadata
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
```

Finally, the properties of the parser can be updated, validated, applied and output:
```
fgdc_from_file = FgdcParser(file(r'/path/to/metadata.xml'))

# Example simple properties
fgdc_from_file.title
fgdc_from_file.abstract
fgdc_from_file.place_keywords
fgdc_from_file.thematic_keywords

# Complex properties
fgdc_from_file.attributes
fgdc_from_file.bounding_box
fgdc_from_file.dates
fgdc_from_file.digital_forms
fgdc_from_file.larger_works
fgdc_from_file.process_steps

# :see: gis_metadata.metadata.parser_utils._required_keys for list of all properties

# Update properties
fgdc_from_file.title = 'New Title'
fgdc_from_file.dates = {'type': 'single' 'values': '1/1/2016'}

# Apply updates
fgdc_from_file.validate()                                      # Ensure updated properties are valid
fgdc_from_file.serialize()                                     # Output updated XML as a string
fgdc_from_file.write()                                         # Output updated XML to existing file
fgdc_from_file.write(out_file_or_path='/path/to/updated.xml')  # Output updated XML to new file

```

