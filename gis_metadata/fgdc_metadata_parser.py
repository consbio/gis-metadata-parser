""" A module to contain utility FGDC metadata parsing helpers """

import six

from parserutils.elements import get_element_name

from gis_metadata.exceptions import InvalidContent
from gis_metadata.metadata_parser import MetadataParser

from gis_metadata.utils import remove_element
from gis_metadata.utils import DATE_TYPE, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE
from gis_metadata.utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.utils import ATTRIBUTES
from gis_metadata.utils import BOUNDING_BOX
from gis_metadata.utils import CONTACTS
from gis_metadata.utils import DATES
from gis_metadata.utils import DIGITAL_FORMS
from gis_metadata.utils import KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME
from gis_metadata.utils import LARGER_WORKS
from gis_metadata.utils import PROCESS_STEPS
from gis_metadata.utils import RASTER_INFO
from gis_metadata.utils import ParserProperty

from gis_metadata.utils import format_xpaths, get_complex_definitions, update_complex


iteritems = getattr(six, 'iteritems')


FGDC_ROOT = 'metadata'

_fgdc_definitions = get_complex_definitions()

# Define backup locations for contact sub-properties
_fgdc_definitions[CONTACTS].update({
    '_name': '{_name}',
    '_organization': '{_organization}'
})

# Define backup locations for raster_info sub-properties
_fgdc_definitions[RASTER_INFO].update({
    '_x_resolution': '{_x_resolution}',
    '_y_resolution': '{_y_resolution}'
})

_fgdc_tag_formats = {
    '_attributes_root': 'eainfo/detailed/attr',
    '_bounding_box_root': 'idinfo/spdom/bounding',
    '_contacts_root': 'idinfo/ptcontac',
    '_dates_root': 'idinfo/timeperd/timeinfo',
    '_digital_forms_root': 'distinfo/stdorder/digform',
    '_larger_works_root': 'idinfo/citation/citeinfo/lworkcit/citeinfo',
    '_process_steps_root': 'dataqual/lineage/procstep',

    '_raster_info_root': 'spdoinfo/rastinfo',
    '__raster_res_root': 'spref/horizsys',

    '_raster_resolution': 'spref/horizsys/planar/planci/coordrep',
    '__raster_resolution': 'spref/horizsys/geograph',

    'title': 'idinfo/citation/citeinfo/title',
    'abstract': 'idinfo/descript/abstract',
    'purpose': 'idinfo/descript/purpose',
    'supplementary_info': 'idinfo/descript/supplinf',
    'online_linkages': 'idinfo/citation/citeinfo/onlink',
    'originators': 'idinfo/citation/citeinfo/origin',
    'publish_date': 'idinfo/citation/citeinfo/pubdate',
    'data_credits': 'idinfo/datacred',
    CONTACTS: 'idinfo/ptcontac/cntinfo/{ct_path}',
    'dist_contact_org': 'distinfo/distrib/cntinfo/cntperp/cntorg',
    '_dist_contact_org': 'distinfo/distrib/cntinfo/cntorgp/cntorg',  # If not in cntperp
    'dist_contact_person': 'distinfo/distrib/cntinfo/cntperp/cntper',
    '_dist_contact_person': 'distinfo/distrib/cntinfo/cntorgp/cntper',  # If not in cntperp
    'dist_address_type': 'distinfo/distrib/cntinfo/cntaddr/addrtype',
    'dist_address': 'distinfo/distrib/cntinfo/cntaddr/address',
    'dist_city': 'distinfo/distrib/cntinfo/cntaddr/city',
    'dist_state': 'distinfo/distrib/cntinfo/cntaddr/state',
    'dist_postal': 'distinfo/distrib/cntinfo/cntaddr/postal',
    'dist_country': 'distinfo/distrib/cntinfo/cntaddr/country',
    'dist_phone': 'distinfo/distrib/cntinfo/cntvoice',
    'dist_email': 'distinfo/distrib/cntinfo/cntemail',
    'dist_liability': 'distinfo/distliab',
    'processing_fees': 'distinfo/stdorder/fees',
    'processing_instrs': 'distinfo/stdorder/ordering',
    'resource_desc': 'distinfo/resdesc',
    'tech_prerequisites': 'distinfo/techpreq',
    ATTRIBUTES: 'eainfo/detailed/attr/{ad_path}',
    'attribute_accuracy': 'dataqual/attracc/attraccr',
    BOUNDING_BOX: 'idinfo/spdom/bounding/{bbox_path}',
    'dataset_completeness': 'dataqual/complete',
    DIGITAL_FORMS: 'distinfo/stdorder/digform/{df_path}',
    PROCESS_STEPS: 'dataqual/lineage/procstep/{ps_path}',
    LARGER_WORKS: 'idinfo/citation/citeinfo/lworkcit/citeinfo/{lw_path}',
    RASTER_INFO: 'spdoinfo/rastinfo/{ri_path}',
    'other_citation_info': 'idinfo/citation/citeinfo/othercit',
    'use_constraints': 'idinfo/useconst',
    DATES: 'idinfo/timeperd/timeinfo/{type_path}',
    KEYWORDS_PLACE: 'idinfo/keywords/place/placekey',
    KEYWORDS_STRATUM: 'idinfo/keywords/stratum/stratkey',
    KEYWORDS_TEMPORAL: 'idinfo/keywords/temporal/tempkey',
    KEYWORDS_THEME: 'idinfo/keywords/theme/themekey'
}


class FgdcParser(MetadataParser):
    """ A class to parse metadata files conforming to the FGDC standard """

    def _init_data_map(self):
        """ OVERRIDDEN: Initialize required FGDC data map with XPATHS and specialized functions """

        if self._data_map is not None:
            return  # Initiation happens once

        # Parse and validate the FGDC metadata root

        if self._xml_tree is None:
            fgdc_root = FGDC_ROOT
        else:
            fgdc_root = get_element_name(self._xml_tree)

        if fgdc_root != FGDC_ROOT:
            raise InvalidContent('Invalid XML root for ISO-19115 standard: {root}', root=fgdc_root)

        fgdc_data_map = {'_root': FGDC_ROOT}
        fgdc_data_structures = {}

        # Capture and format other complex XPATHs

        ad_format = _fgdc_tag_formats[ATTRIBUTES]
        fgdc_data_structures[ATTRIBUTES] = format_xpaths(
            _fgdc_definitions[ATTRIBUTES],
            label=ad_format.format(ad_path='attrlabl'),
            aliases=ad_format.format(ad_path='attalias'),
            definition=ad_format.format(ad_path='attrdef'),
            definition_src=ad_format.format(ad_path='attrdefs')
        )

        bb_format = _fgdc_tag_formats[BOUNDING_BOX]
        fgdc_data_structures[BOUNDING_BOX] = format_xpaths(
            _fgdc_definitions[BOUNDING_BOX],
            east=bb_format.format(bbox_path='eastbc'),
            south=bb_format.format(bbox_path='southbc'),
            west=bb_format.format(bbox_path='westbc'),
            north=bb_format.format(bbox_path='northbc')
        )

        ct_format = _fgdc_tag_formats[CONTACTS]
        fgdc_data_structures[CONTACTS] = format_xpaths(
            _fgdc_definitions[CONTACTS],

            name=ct_format.format(ct_path='cntperp/cntper'),
            _name=ct_format.format(ct_path='cntorgp/cntper'),  # If not in cntperp

            organization=ct_format.format(ct_path='cntperp/cntorg'),
            _organization=ct_format.format(ct_path='cntorgp/cntorg'),  # If not in cntperp

            position=ct_format.format(ct_path='cntpos'),
            email=ct_format.format(ct_path='cntemail')
        )

        dt_format = _fgdc_tag_formats[DATES]
        fgdc_data_structures[DATES] = {
            DATE_TYPE_MULTIPLE: dt_format.format(type_path='mdattim/sngdate/caldate'),
            DATE_TYPE_RANGE_BEGIN: dt_format.format(type_path='rngdates/begdate'),
            DATE_TYPE_RANGE_END: dt_format.format(type_path='rngdates/enddate'),
            DATE_TYPE_SINGLE: dt_format.format(type_path='sngdate/caldate')
        }
        fgdc_data_structures[DATES][DATE_TYPE_RANGE] = [
            fgdc_data_structures[DATES][DATE_TYPE_RANGE_BEGIN],
            fgdc_data_structures[DATES][DATE_TYPE_RANGE_END]
        ]

        df_format = _fgdc_tag_formats[DIGITAL_FORMS]
        fgdc_data_structures[DIGITAL_FORMS] = format_xpaths(
            _fgdc_definitions[DIGITAL_FORMS],
            name=df_format.format(df_path='digtinfo/formname'),
            content=df_format.format(df_path='digtinfo/formcont'),
            decompression=df_format.format(df_path='digtinfo/filedec'),
            version=df_format.format(df_path='digtinfo/formvern'),
            specification=df_format.format(df_path='digtinfo/formspec'),
            access_desc=df_format.format(df_path='digtopt/onlinopt/oncomp'),
            access_instrs=df_format.format(df_path='digtopt/onlinopt/accinstr'),
            network_resource=df_format.format(df_path='digtopt/onlinopt/computer/networka/networkr')
        )

        lw_format = _fgdc_tag_formats[LARGER_WORKS]
        fgdc_data_structures[LARGER_WORKS] = format_xpaths(
            _fgdc_definitions[LARGER_WORKS],
            title=lw_format.format(lw_path='title'),
            edition=lw_format.format(lw_path='edition'),
            origin=lw_format.format(lw_path='origin'),
            online_linkage=lw_format.format(lw_path='onlink'),
            other_citation=lw_format.format(lw_path='othercit'),
            date=lw_format.format(lw_path='pubdate'),
            place=lw_format.format(lw_path='pubinfo/pubplace'),
            info=lw_format.format(lw_path='pubinfo/publish')
        )

        ps_format = _fgdc_tag_formats[PROCESS_STEPS]
        fgdc_data_structures[PROCESS_STEPS] = format_xpaths(
            _fgdc_definitions[PROCESS_STEPS],
            description=ps_format.format(ps_path='procdesc'),
            date=ps_format.format(ps_path='procdate'),
            sources=ps_format.format(ps_path='srcused')
        )

        ri_format = _fgdc_tag_formats[RASTER_INFO]
        fgdc_data_structures[RASTER_INFO] = format_xpaths(
            _fgdc_definitions[RASTER_INFO],

            dimensions=ri_format.format(ri_path='rasttype'),
            row_count=ri_format.format(ri_path='rowcount'),
            column_count=ri_format.format(ri_path='colcount'),
            vertical_count=ri_format.format(ri_path='vrtcount'),

            x_resolution=_fgdc_tag_formats['_raster_resolution'] + '/absres',
            _x_resolution=_fgdc_tag_formats['__raster_resolution'] + '/longres',
            y_resolution=_fgdc_tag_formats['_raster_resolution'] + '/ordres',
            _y_resolution=_fgdc_tag_formats['__raster_resolution'] + '/latres',
        )

        # Assign XPATHS and gis_metadata.utils.ParserProperties to fgdc_data_map

        fgdc_data_formats = dict(_fgdc_tag_formats)

        for prop, xpath in iteritems(fgdc_data_formats):
            if prop in (ATTRIBUTES, CONTACTS, DIGITAL_FORMS, PROCESS_STEPS):
                fgdc_data_map[prop] = ParserProperty(self._parse_complex_list, self._update_complex_list)

            elif prop in (BOUNDING_BOX, LARGER_WORKS):
                fgdc_data_map[prop] = ParserProperty(self._parse_complex, self._update_complex)

            elif prop == DATES:
                fgdc_data_map[prop] = ParserProperty(self._parse_dates, self._update_dates)

            elif prop == RASTER_INFO:
                fgdc_data_map[prop] = ParserProperty(self._parse_complex, self._update_raster_info)

            else:
                fgdc_data_map[prop] = xpath

        self._data_map = fgdc_data_map
        self._data_structures = fgdc_data_structures

    def _update_dates(self, **update_props):
        """
        Update operation for FGDC Dates metadata
        :see: gis_metadata.utils._complex_definitions[DATES]
        """

        tree_to_update = update_props['tree_to_update']
        xpath_root = self._data_map['_dates_root']

        if self.dates:
            date_type = self.dates[DATE_TYPE]

            if date_type == DATE_TYPE_MULTIPLE:
                xpath_root += '/mdattim/sngdate'

            elif date_type == DATE_TYPE_RANGE:
                xpath_root = ''  # /rngdates/begdate and enddate are siblings, not cousins
                remove_element(tree_to_update, self._data_map['_dates_root'])

        return super(FgdcParser, self)._update_dates(xpath_root, **update_props)

    def _update_raster_info(self, **update_props):
        """ Ensures complete removal of raster_info given the two roots: <spdoinfo> and <spref> """

        xpath_map = self._data_structures[update_props['prop']]

        return [
            update_complex(xpath_root=self._data_map.get('_raster_info_root'), xpath_map=xpath_map, **update_props),
            update_complex(xpath_root=self._data_map.get('__raster_res_root'), xpath_map=xpath_map, **update_props)
        ]
