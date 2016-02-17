# gis-metadata-parser
Parser for GIS metadata standards including FGDC and ISO-19115.


#Installation#
Install with pip install git+https://github.com/consbio/gis-metadata-parser.git.

#Usage#
Parsers can be instantiated from files, XML strings or URLs:
```
#!python
from gis_metadata.metadata.fgdc_metadata_parser import FgdcParser
from gis_metadata.metadata.iso_metadata_parser import IsoParser
from gis_metadata.metadata.metadata_parser import get_metadata_parser

iso_from_file = IsoParser(file(r'/path/to/metadata.xml'))
fgdc_from_file = FgdcParser(file(r'/path/to/metadata.xml'))

# Detect standard based on root element, metadata
fgdc_from_string = FgdcParser(
    """
    <?xml version='1.0' encoding='UTF-8'?>
    <metadata>
        <idinfo>
        </idinfo>
    </metadata>
    """
)

# Detect standard based on root element, MD_Metadata or MI_Metadata
iso_from_string = IsoParser(
    """
    <?xml version='1.0' encoding='UTF-8'?>
    <MD_Metadata>
        <identificationInfo>
        </identificationInfo>
    </MD_Metadata>
    """
)

# Then, given successful parsing of data according to the standard:

print fgdc_from_file.title
print iso_from_file.abstract
print fgdc_from_string.purpose
print fgdc_from_file.title

```

