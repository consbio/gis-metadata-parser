""" A module to contain utility FGDC metadata parsing helpers """


from gis_metadata.xml.element_utils import get_element_name

from parser_utils import remove_element
from parser_utils import DATE_TYPE, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE
from parser_utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from parser_utils import ATTRIBUTES
from parser_utils import BOUNDING_BOX
from parser_utils import DATES
from parser_utils import DIGITAL_FORMS
from parser_utils import KEYWORDS_PLACE
from parser_utils import KEYWORDS_THEME
from parser_utils import LARGER_WORKS
from parser_utils import PROCESS_STEPS
from parser_utils import ParserException, ParserProperty

from parser_utils import format_xpath, format_xpaths
from parser_utils import get_complex_definitions, get_xpath_root
from parser_utils import parse_complex, parse_complex_list, parse_dates
from parser_utils import update_complex, update_complex_list

from metadata_parser import MetadataParser


FGDC_ROOT = 'metadata'

_fgdc_definitions = get_complex_definitions()

_fgdc_tag_formats = {
    'title': 'idinfo/citation/citeinfo/title',
    'abstract': 'idinfo/descript/abstract',
    'purpose': 'idinfo/descript/purpose',
    'supplementary_info': 'idinfo/descript/supplinf',
    'online_linkages': 'idinfo/citation/citeinfo/onlink',
    'originators': 'idinfo/citation/citeinfo/origin',
    'publish_date': 'idinfo/citation/citeinfo/pubdate',
    'data_credits': 'idinfo/datacred',
    'contact_emails': 'idinfo/ptcontac/cntinfo/cntemail',
    'contact_org': 'idinfo/ptcontac/cntinfo/{org}/cntorg',
    'contact_person': 'idinfo/ptcontac/cntinfo/{person}/cntper',
    'dist_contact_org': 'distinfo/distrib/cntinfo/{org}/cntorg',
    'dist_contact_person': 'distinfo/distrib/cntinfo/{person}/cntper',
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
    'other_citation_info': 'idinfo/citation/citeinfo/othercit',
    'use_constraints': 'idinfo/useconst',
    DATES: 'idinfo/timeperd/timeinfo/{type_path}',
    KEYWORDS_PLACE: 'idinfo/keywords/place/placekey',
    KEYWORDS_THEME: 'idinfo/keywords/theme/themekey'
}


class FgdcParser(MetadataParser):
    """
    A class to parse metadata files conforming to the FGDC standard
    To add more properties for parsing and updating, see the comment
    in the MetadataParser class header.
    """

    DEFAULT_CONTACT_TAG = 'cntperp'

    def _init_data_map(self):
        """ OVERRIDDEN: Initialize required FGDC data map with XPATHS and specialized functions """

        if self._data_map is not None:
            return  # Initiation happens once

        # Parse and validate the FGDC metadata root

        if self._xml_tree is not None:
            fgdc_root = get_element_name(self._xml_tree)
        else:
            fgdc_root = FGDC_ROOT

        if fgdc_root != fgdc_root:
            raise ParserException('Invalid XML root for ISO-19115 standard: {root}', root=fgdc_root)

        fgdc_data_map = {'root': FGDC_ROOT}

        # Capture and format other complex XPATHs

        ad_format = _fgdc_tag_formats[ATTRIBUTES]
        self._attr_details_xpaths = format_xpaths(
            _fgdc_definitions[ATTRIBUTES],
            label=format_xpath(ad_format, ad_path='attrlabl'),
            aliases=format_xpath(ad_format, ad_path='attalias'),
            definition=format_xpath(ad_format, ad_path='attrdef'),
            definition_src=format_xpath(ad_format, ad_path='attrdefs')
        )
        self._attr_details_root = get_xpath_root(ad_format)

        bb_format = _fgdc_tag_formats[BOUNDING_BOX]
        self._bounding_box_xpaths = format_xpaths(
            _fgdc_definitions[BOUNDING_BOX],
            east=format_xpath(bb_format, bbox_path='eastbc'),
            south=format_xpath(bb_format, bbox_path='southbc'),
            west=format_xpath(bb_format, bbox_path='westbc'),
            north=format_xpath(bb_format, bbox_path='northbc')
        )
        self._bounding_box_root = get_xpath_root(bb_format)

        dt_format = _fgdc_tag_formats[DATES]
        self._dates_xpaths = {
            DATE_TYPE_MULTIPLE: format_xpath(dt_format, type_path='mdattim/sngdate/caldate'),
            DATE_TYPE_RANGE_BEGIN: format_xpath(dt_format, type_path='rngdates/begdate'),
            DATE_TYPE_RANGE_END: format_xpath(dt_format, type_path='rngdates/enddate'),
            DATE_TYPE_SINGLE: format_xpath(dt_format, type_path='sngdate/caldate')
        }
        self._dates_root = get_xpath_root(dt_format)

        df_format = _fgdc_tag_formats[DIGITAL_FORMS]
        self._digital_forms_xpaths = format_xpaths(
            _fgdc_definitions[DIGITAL_FORMS],
            name=format_xpath(df_format, df_path='digtinfo/formname'),
            content=format_xpath(df_format, df_path='digtinfo/formcont'),
            decompression=format_xpath(df_format, df_path='digtinfo/filedec'),
            version=format_xpath(df_format, df_path='digtinfo/formvern'),
            specification=format_xpath(df_format, df_path='digtinfo/formspec'),
            access_desc=format_xpath(df_format, df_path='digtopt/onlinopt/oncomp'),
            access_instrs=format_xpath(df_format, df_path='digtopt/onlinopt/accinstr'),
            network_resource=format_xpath(df_format, df_path='digtopt/onlineopt/computer/networka/networkr')
        )
        self._digital_forms_root = get_xpath_root(df_format)

        lw_format = _fgdc_tag_formats[LARGER_WORKS]
        self._larger_works_xpaths = format_xpaths(
            _fgdc_definitions[LARGER_WORKS],
            title=format_xpath(lw_format, lw_path='title'),
            edition=format_xpath(lw_format, lw_path='edition'),
            origin=format_xpath(lw_format, lw_path='origin'),
            online_linkage=format_xpath(lw_format, lw_path='onlink'),
            other_citation=format_xpath(lw_format, lw_path='othercit'),
            date=format_xpath(lw_format, lw_path='pubdate'),
            place=format_xpath(lw_format, lw_path='pubinfo/pubplace'),
            info=format_xpath(lw_format, lw_path='pubinfo/publish')
        )
        self._larger_works_root = get_xpath_root(lw_format)

        ps_format = _fgdc_tag_formats[PROCESS_STEPS]
        self._process_steps_xpaths = format_xpaths(
            _fgdc_definitions[PROCESS_STEPS],
            description=format_xpath(ps_format, ps_path='procdesc'),
            date=format_xpath(ps_format, ps_path='procdate'),
            sources=format_xpath(ps_format, ps_path='srcused')
        )
        self._process_steps_root = get_xpath_root(ps_format)

        # Capture contact information that may differ per document

        cntinfo = 'idinfo/ptcontac/cntinfo/{contact}'

        if self._has_element(format_xpath(cntinfo, contact='cntorgp')):
            contact = 'cntorgp'
        elif self._has_element(format_xpath(cntinfo, contact='cntperp')):
            contact = 'cntperp'
        else:
            contact = FgdcParser.DEFAULT_CONTACT_TAG

        # Assign XPATHS and parser_utils.ParserProperties to fgdc_data_map

        fgdc_data_formats = dict(_fgdc_tag_formats)

        for prop, xpath in fgdc_data_formats.iteritems():
            if prop == ATTRIBUTES:
                fgdc_data_map[prop] = ParserProperty(self._parse_attribute_details, self._update_attribute_details)

            elif prop == BOUNDING_BOX:
                fgdc_data_map[prop] = ParserProperty(self._parse_bounding_box, self._update_bounding_box)

            elif prop in ['contact_org', 'dist_contact_org']:
                fgdc_data_map[prop] = format_xpath(xpath, org=contact)

            elif prop in ['contact_person', 'dist_contact_person']:
                fgdc_data_map[prop] = format_xpath(xpath, person=contact)

            elif prop == DATES:
                fgdc_data_map[prop] = ParserProperty(self._parse_dates, self._update_dates)

            elif prop == DIGITAL_FORMS:
                fgdc_data_map[prop] = ParserProperty(self._parse_digital_forms, self._update_digital_forms)

            elif prop == LARGER_WORKS:
                fgdc_data_map[prop] = ParserProperty(self._parse_larger_works, self._update_larger_works)

            elif prop == PROCESS_STEPS:
                fgdc_data_map[prop] = ParserProperty(self._parse_process_steps, self._update_process_steps)

            else:
                fgdc_data_map[prop] = xpath

        self._data_map = fgdc_data_map

    def _parse_attribute_details(self, prop=ATTRIBUTES):
        """ Concatenates a list of Attribute Details data structures parsed from the metadata """

        xpath_root = self._attr_details_root
        xpath_map = self._attr_details_xpaths

        return parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

    def _parse_bounding_box(self, prop=BOUNDING_BOX):
        """ Creates and returns a Bounding Box data structure parsed from the metadata """

        return parse_complex(self._xml_tree, None, self._bounding_box_xpaths, prop)

    def _parse_dates(self, prop=DATES):
        """ Creates and returns a Dates data structure parsed from the metadata """

        return parse_dates(self._xml_tree, self._dates_xpaths)

    def _parse_digital_forms(self, prop=DIGITAL_FORMS):
        """ Concatenates a list of Digital Form data structures parsed from the metadata """

        xpath_root = self._digital_forms_root
        xpath_map = self._digital_forms_xpaths

        return parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

    def _parse_larger_works(self, prop=LARGER_WORKS):
        """ Creates and returns a Larger Works data structure parsed from the metadata """

        return parse_complex(self._xml_tree, None, self._larger_works_xpaths, prop)

    def _parse_process_steps(self, prop=PROCESS_STEPS):
        """ Creates and returns a list of Process Steps data structures parsed from the metadata """

        xpath_root = self._process_steps_root
        xpath_map = self._process_steps_xpaths

        return parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

    def _update_attribute_details(self, **update_props):
        """
        Update operation for FGDC Attribute Details metadata
        :see: parser_utils._complex_definitions[ATTRIBUTES]
        """

        xpath_root = self._attr_details_root
        xpath_map = self._attr_details_xpaths

        return update_complex_list(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_bounding_box(self, **update_props):
        """
        Update operation for FGDC Bounding Box metadata
        :see: parser_utils._complex_definitions[BOUNDING_BOX]
        """

        xpath_root = self._bounding_box_root
        xpath_map = self._bounding_box_xpaths

        return update_complex(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_dates(self, **update_props):
        """
        Update operation for FGDC Dates metadata
        :see: parser_utils._complex_definitions[DATES]
        """

        xpath_root = self._dates_root

        if self.dates:
            date_type = self.dates[DATE_TYPE]

            if date_type == DATE_TYPE_MULTIPLE:
                xpath_root += '/mdattim/sngdate'

            elif date_type == DATE_TYPE_RANGE:
                xpath_root = ''  # /rngdates/begdate and enddate are siblings, not cousins
                remove_element(update_props['tree_to_update'], self._dates_root)

        return self._update_dates_property(xpath_root, self._dates_xpaths, **update_props)

    def _update_digital_forms(self, **update_props):
        """
        Update operation for FGDC Digital Forms metadata
        :see: parser_utils._complex_definitions[DIGITAL_FORMS]
        """

        xpath_root = self._digital_forms_root
        xpath_map = self._digital_forms_xpaths

        return update_complex_list(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_larger_works(self, **update_props):
        """
        Update operation for FGDC Larger Works metadata
        :see: parser_utils._complex_definitions[LARGER_WORKS]
        """

        xpath_root = self._larger_works_root
        xpath_map = self._larger_works_xpaths

        return update_complex(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

    def _update_process_steps(self, **update_props):
        """
        Update operation for FGDC Process Steps metadata
        :see: parser_utils._complex_definitions[PROCESS_STEPS]
        """

        xpath_root = self._process_steps_root
        xpath_map = self._process_steps_xpaths

        return update_complex_list(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

