""" A module to contain utility ArcGIS metadata parsing helpers """

import six

from six import iteritems

from gis_metadata.exceptions import InvalidContent
from gis_metadata.metadata_parser import MetadataParser

from gis_metadata.utils import DATE_TYPE, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE
from gis_metadata.utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.utils import ATTRIBUTES
from gis_metadata.utils import BOUNDING_BOX
from gis_metadata.utils import CONTACTS
from gis_metadata.utils import DATES
from gis_metadata.utils import DIGITAL_FORMS
from gis_metadata.utils import KEYWORDS_PLACE
from gis_metadata.utils import KEYWORDS_THEME
from gis_metadata.utils import LARGER_WORKS
from gis_metadata.utils import PROCESS_STEPS
from gis_metadata.utils import ParserProperty

from gis_metadata.utils import format_xpaths, get_complex_definitions, get_default_for_complex
from gis_metadata.utils import parse_complex_list, update_complex_list

from parserutils.collections import flatten_items, reduce_value, wrap_value
from parserutils.elements import get_elements, get_element_name, get_element_attributes
from parserutils.elements import clear_element, element_to_dict, insert_element, remove_element, remove_empty_element


xrange = getattr(six.moves, 'xrange')


ARCGIS_ROOTS = ('metadata', 'Metadata')
ARCGIS_NODES = ('dataIdInfo', 'distInfo', 'dqInfo', 'Esri')

_agis_definitions = get_complex_definitions()

_agis_tag_formats = {
    '_attribute_accuracy_root': 'dqInfo/report',
    '_attributes_root': 'eainfo/detailed/attr',
    '_bounding_box_root': 'dataIdInfo/dataExt/geoEle',
    '_contacts_root': 'dataIdInfo/idPoC',
    '_dataset_completeness_root': 'dqInfo/report',
    '_dates_root': 'dataIdInfo/dataExt/tempEle',
    '_digital_forms_root': 'distInfo/distFormat',
    '_dist_liability_root': 'dataIdInfo/resConst',
    '_transfer_options_root': 'distInfo/distTranOps/onLineSrc',
    '_larger_works_root': 'dataIdInfo/aggrInfo/aggrDSName',
    '_process_steps_root': 'dqInfo/dataLineage/prcStep',
    '_use_constraints_root': 'dataIdInfo/resConst',

    'title': 'dataIdInfo/idCitation/resTitle',
    'abstract': 'dataIdInfo/idAbs',
    'purpose': 'dataIdInfo/idPurp',
    'supplementary_info': 'dataIdInfo/suppInfo',
    'online_linkages': 'dataIdInfo/idCitation/citRespParty/rpCntInfo/cntOnlineRes/linkage',
    '_online_linkages': 'dataIdInfo/idCitation/citOnlineRes/linkage',  # If not in citRespParty
    'originators': 'dataIdInfo/idCitation/citRespParty/rpOrgName',
    'publish_date': 'dataIdInfo/idCitation/date/pubDate',
    'data_credits': 'dataIdInfo/idCredit',
    CONTACTS: 'dataIdInfo/idPoC/{ct_path}',
    'dist_contact_org': 'distInfo/distributor/distorCont/rpOrgName',
    'dist_contact_person': 'distInfo/distributor/distorCont/rpIndName',
    'dist_address_type': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/@addressType',
    'dist_address': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/delPoint',
    'dist_city': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/city',
    'dist_state': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/adminArea',
    'dist_postal': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/postCode',
    'dist_country': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/country',
    'dist_phone': 'distInfo/distributor/distorCont/rpCntInfo/cntPhone/voiceNum',
    '_dist_phone': 'distInfo/distributor/distorCont/rpCntInfo/voiceNum',  # If not in cntPhone
    'dist_email': 'distInfo/distributor/distorCont/rpCntInfo/cntAddress/eMailAdd',
    'dist_liability': 'dataIdInfo/resConst/LegConsts/othConsts',
    'processing_fees': 'distInfo/distributor/distorOrdPrc/resFees',
    'processing_instrs': 'distInfo/distributor/distorOrdPrc/ordInstr',
    'resource_desc': 'dataIdInfo/idSpecUse/specUsage',
    'tech_prerequisites': 'dataIdInfo/envirDesc',
    ATTRIBUTES: 'eainfo/detailed/attr/{ad_path}',  # Same as in FGDC (and for good reason)
    'attribute_accuracy': 'dqInfo/report/measDesc',
    BOUNDING_BOX: 'dataIdInfo/dataExt/geoEle/GeoBndBox/{bbox_path}',
    'dataset_completeness': 'dqInfo/report/measDesc',
    DIGITAL_FORMS: 'distInfo/distFormat/{df_path}',
    '_access_desc': 'distInfo/distTranOps/onLineSrc/orDesc',
    '_access_instrs': 'distInfo/distTranOps/onLineSrc/protocol',
    '_network_resource': 'distInfo/distTranOps/onLineSrc/linkage',
    PROCESS_STEPS: 'dqInfo/dataLineage/prcStep/{ps_path}',
    LARGER_WORKS: 'dataIdInfo/aggrInfo/aggrDSName/{lw_path}',
    'other_citation_info': 'dataIdInfo/idCitation/otherCitDet',
    'use_constraints': 'dataIdInfo/resConst/Consts/useLimit',
    DATES: 'dataIdInfo/dataExt/tempEle/TempExtent/exTemp/{type_path}',
    KEYWORDS_PLACE: 'dataIdInfo/placeKeys/keyword',
    KEYWORDS_THEME: 'dataIdInfo/themeKeys/keyword'
}


class ArcGISParser(MetadataParser):
    """ A class to parse metadata files generated by ArcGIS """

    def _init_data_map(self):
        """ OVERRIDDEN: Initialize required FGDC data map with XPATHS and specialized functions """

        if self._data_map is not None:
            return  # Initiation happens once

        # Parse and validate the ArcGIS metadata root

        if self._xml_tree is None:
            agis_root = ARCGIS_ROOTS[0]  # Default to uncapitalized
        else:
            agis_root = get_element_name(self._xml_tree)

        if agis_root not in ARCGIS_ROOTS:
            raise InvalidContent('Invalid XML root for ArcGIS metadata: {root}', root=agis_root)

        agis_data_map = {'_root': agis_root}
        agis_data_map.update(_agis_tag_formats)

        agis_data_structures = {}

        # Capture and format complex XPATHs

        ad_format = agis_data_map[ATTRIBUTES]
        agis_data_structures[ATTRIBUTES] = format_xpaths(
            _agis_definitions[ATTRIBUTES],
            label=ad_format.format(ad_path='attrlabl'),
            aliases=ad_format.format(ad_path='attalias'),
            definition=ad_format.format(ad_path='attrdef'),
            definition_src=ad_format.format(ad_path='attrdefs')
        )

        bb_format = agis_data_map[BOUNDING_BOX]
        agis_data_structures[BOUNDING_BOX] = format_xpaths(
            _agis_definitions[BOUNDING_BOX],
            east=bb_format.format(bbox_path='eastBL'),
            south=bb_format.format(bbox_path='southBL'),
            west=bb_format.format(bbox_path='westBL'),
            north=bb_format.format(bbox_path='northBL')
        )

        ct_format = agis_data_map[CONTACTS]
        agis_data_structures[CONTACTS] = format_xpaths(
            _agis_definitions[CONTACTS],
            name=ct_format.format(ct_path='rpIndName'),
            organization=ct_format.format(ct_path='rpOrgName'),
            position=ct_format.format(ct_path='rpPosName'),
            email=ct_format.format(ct_path='rpCntInfo/cntAddress/eMailAdd')
        )

        dt_format = agis_data_map[DATES]
        agis_data_structures[DATES] = {
            DATE_TYPE_MULTIPLE: dt_format.format(type_path='TM_Instant/tmPosition'),
            '_' + DATE_TYPE_MULTIPLE: dt_format.format(type_path='TM_Instant/tmPosition/@date'),
            DATE_TYPE_RANGE_BEGIN: dt_format.format(type_path='TM_Period/tmBegin'),
            '_' + DATE_TYPE_RANGE_BEGIN: dt_format.format(type_path='TM_Period/tmBegin/@date'),
            DATE_TYPE_RANGE_END: dt_format.format(type_path='TM_Period/tmEnd'),
            '_' + DATE_TYPE_RANGE_END: dt_format.format(type_path='TM_Period/tmEnd/@date'),
            # Same as multiple dates, but will contain only one
            DATE_TYPE_SINGLE: dt_format.format(type_path='TM_Instant/tmPosition'),
            '_' + DATE_TYPE_SINGLE: dt_format.format(type_path='TM_Instant/tmPosition/@date')
        }
        agis_data_structures[DATES][DATE_TYPE_RANGE] = [
            agis_data_structures[DATES][DATE_TYPE_RANGE_BEGIN],
            agis_data_structures[DATES][DATE_TYPE_RANGE_END]
        ]
        agis_data_structures[DATES]['_' + DATE_TYPE_RANGE] = [
            agis_data_structures[DATES]['_' + DATE_TYPE_RANGE_BEGIN],
            agis_data_structures[DATES]['_' + DATE_TYPE_RANGE_END]
        ]

        df_format = agis_data_map[DIGITAL_FORMS]
        agis_data_structures[DIGITAL_FORMS] = format_xpaths(
            _agis_definitions[DIGITAL_FORMS],
            name=df_format.format(df_path='formatName'),
            content=df_format.format(df_path='formatInfo'),
            decompression=df_format.format(df_path='fileDecmTech'),
            version=df_format.format(df_path='formatVer'),
            specification=df_format.format(df_path='formatSpec'),
            access_desc=agis_data_map['_access_desc'],
            access_instrs=agis_data_map['_access_instrs'],
            network_resource=agis_data_map['_network_resource']
        )

        lw_format = agis_data_map[LARGER_WORKS]
        agis_data_structures[LARGER_WORKS] = format_xpaths(
            _agis_definitions[LARGER_WORKS],
            title=lw_format.format(lw_path='resTitle'),
            edition=lw_format.format(lw_path='resEd'),
            origin=lw_format.format(lw_path='citRespParty/rpIndName'),
            online_linkage=lw_format.format(lw_path='citRespParty/rpCntInfo/cntOnlineRes/linkage'),
            other_citation=lw_format.format(lw_path='otherCitDet'),
            date=lw_format.format(lw_path='date/pubDate'),
            place=lw_format.format(lw_path='citRespParty/rpCntInfo/cntAddress/city'),
            info=lw_format.format(lw_path='citRespParty/rpOrgName')
        )

        ps_format = agis_data_map[PROCESS_STEPS]
        agis_data_structures[PROCESS_STEPS] = format_xpaths(
            _agis_definitions[PROCESS_STEPS],
            description=ps_format.format(ps_path='stepDesc'),
            date=ps_format.format(ps_path='stepDateTm'),
            sources=ps_format.format(ps_path='stepSrc/srcDesc')
        )

        # Assign XPATHS and gis_metadata.utils.ParserProperties to data map

        for prop, xpath in iteritems(dict(agis_data_map)):
            if prop in (ATTRIBUTES, CONTACTS, PROCESS_STEPS):
                agis_data_map[prop] = ParserProperty(self._parse_complex_list, self._update_complex_list)

            elif prop in (BOUNDING_BOX, LARGER_WORKS):
                agis_data_map[prop] = ParserProperty(self._parse_complex, self._update_complex)

            elif prop in ('attribute_accuracy', 'dataset_completeness'):
                agis_data_map[prop] = ParserProperty(self._parse_report_item, self._update_report_item)

            elif prop == DATES:
                agis_data_map[prop] = ParserProperty(self._parse_dates, self._update_dates)

            elif prop == DIGITAL_FORMS:
                agis_data_map[prop] = ParserProperty(self._parse_digital_forms, self._update_digital_forms)

            else:
                agis_data_map[prop] = xpath

        self._data_map = agis_data_map
        self._data_structures = agis_data_structures

    def _parse_digital_forms(self, prop=DIGITAL_FORMS):
        """ Concatenates a list of Digital Form data structures parsed from the metadata """

        xpath_map = self._data_structures[prop]

        # Parse base digital form fields: 'name', 'content', 'decompression', 'version', 'specification'
        xpath_root = self._data_map['_digital_forms_root']
        digital_forms = parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

        # Parse digital form transfer option fields: 'access_desc', 'access_instrs', 'network_resource'
        xpath_root = self._data_map['_transfer_options_root']
        transfer_opts = parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

        # Combine digital forms and transfer options into a single complex struct

        df_len = len(digital_forms)
        to_len = len(transfer_opts)
        parsed_forms = []

        for idx in xrange(0, max(df_len, to_len)):
            digital_form = {}.fromkeys(_agis_definitions[prop], u'')

            if idx < df_len:
                digital_form.update(i for i in digital_forms[idx].items() if i[1])
            if idx < to_len:
                digital_form.update(i for i in transfer_opts[idx].items() if i[1])

            if any(digital_form.values()):
                parsed_forms.append(digital_form)

        return get_default_for_complex(prop, parsed_forms)

    def _parse_report_item(self, prop):
        """ :return: the text for each element at the configured path if type attribute matches"""

        item_type = None

        if prop == 'attribute_accuracy':
            item_type = 'DQQuanAttAcc'
        elif prop == 'dataset_completeness':
            item_type = 'DQCompOm'

        xroot = self._get_xroot_for(prop)

        parsed = (element_to_dict(e) for e in get_elements(self._xml_tree, xroot))
        parsed = flatten_items(e['children'] for e in parsed if e['attributes'].get('type') == item_type)

        return reduce_value([p['text'] for p in parsed if p['name'] == 'measDesc'])

    def _update_digital_forms(self, **update_props):
        """
        Update operation for ArcGIS Digital Forms metadata
        :see: gis_metadata.utils._complex_definitions[DIGITAL_FORMS]
        """

        digital_forms = wrap_value(update_props['values'])

        # Update all Digital Form properties: distFormat*

        xpath_map = self._data_structures[update_props['prop']]

        dist_format_props = ('name', 'content', 'decompression', 'version', 'specification')
        dist_format_xroot = self._data_map['_digital_forms_root']
        dist_format_xmap = {prop: xpath_map[prop] for prop in dist_format_props}
        dist_formats = []

        for digital_form in digital_forms:
            dist_formats.append({prop: digital_form[prop] for prop in dist_format_props})

        update_props['values'] = dist_formats
        dist_formats = update_complex_list(
            xpath_root=dist_format_xroot, xpath_map=dist_format_xmap, **update_props
        )

        # Update all Network Resources: distTranOps+

        trans_option_props = ('access_desc', 'access_instrs', 'network_resource')
        trans_option_xroot = self._data_map['_transfer_options_root']
        trans_option_xmap = {prop: self._data_map['_' + prop] for prop in trans_option_props}

        trans_options = []
        for digital_form in digital_forms:
            trans_options.append({prop: digital_form[prop] for prop in trans_option_props})

        update_props['values'] = trans_options
        trans_options = update_complex_list(
            xpath_root=trans_option_xroot, xpath_map=trans_option_xmap, **update_props
        )

        return {
            'distribution_formats': dist_formats,
            'transfer_options': trans_options
        }

    def _update_dates(self, **update_props):
        """
        Update operation for ArcGIS Dates metadata
        :see: gis_metadata.utils._complex_definitions[DATES]
        """

        tree_to_update = update_props['tree_to_update']
        xpath_root = self._data_map['_dates_root']

        if self.dates:
            date_type = self.dates[DATE_TYPE]

            # First remove all date info from common root
            remove_element(tree_to_update, xpath_root)

            if date_type == DATE_TYPE_MULTIPLE:
                xpath_root += '/TempExtent/TM_Instant'
            elif date_type == DATE_TYPE_RANGE:
                xpath_root += '/TempExtent/TM_Period'

        return super(ArcGISParser, self)._update_dates(xpath_root, **update_props)

    def _update_report_item(self, **update_props):
        """ Update the text for each element at the configured path if attribute matches """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = wrap_value(update_props['values'])
        xroot = self._get_xroot_for(prop)

        attr_key = 'type'
        attr_val = u''

        if prop == 'attribute_accuracy':
            attr_val = 'DQQuanAttAcc'
        elif prop == 'dataset_completeness':
            attr_val = 'DQCompOm'

        # Clear (make empty) all elements of the appropriate type
        for elem in get_elements(tree_to_update, xroot):
            if get_element_attributes(elem).get(attr_key) == attr_val:
                clear_element(elem)

        # Remove all empty elements, including those previously cleared
        remove_empty_element(tree_to_update, xroot)

        # Insert elements with correct attributes for each new value

        attrs = {attr_key: attr_val}
        updated = []

        for idx, value in enumerate(values):
            elem = insert_element(tree_to_update, idx, xroot, **attrs)
            updated.append(insert_element(elem, idx, 'measDesc', value))

        return updated
