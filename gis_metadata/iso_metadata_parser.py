""" A module to contain utility ISO-19115 metadata parsing helpers """

import six

from collections import OrderedDict
from six import iteritems, string_types

from parserutils.collections import filter_empty, reduce_value, wrap_value
from parserutils.elements import get_element_name, get_element_text, get_elements_text
from parserutils.elements import get_elements, get_remote_element, insert_element, remove_element
from parserutils.elements import XPATH_DELIM

from gis_metadata.metadata_parser import MetadataParser
from gis_metadata.exceptions import ParserError

from gis_metadata.utils import DATE_TYPE, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE
from gis_metadata.utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.utils import ATTRIBUTES
from gis_metadata.utils import CONTACTS
from gis_metadata.utils import BOUNDING_BOX
from gis_metadata.utils import DATES
from gis_metadata.utils import DIGITAL_FORMS
from gis_metadata.utils import KEYWORDS_PLACE, KEYWORDS_THEME
from gis_metadata.utils import LARGER_WORKS
from gis_metadata.utils import PROCESS_STEPS
from gis_metadata.utils import ParserProperty

from gis_metadata.utils import format_xpaths, get_complex_definitions
from gis_metadata.utils import parse_complex_list, parse_property, update_complex_list, update_property


xrange = getattr(six.moves, 'xrange')


ISO_ROOTS = ('MD_Metadata', 'MI_Metadata')

KEYWORD_TYPE_PLACE = 'place'
KEYWORD_TYPE_THEME = 'theme'

_DIGITAL_FORMS_CONTENT_DELIM = '@------------------------------@'


_iso_definitions = get_complex_definitions()
_iso_definitions[ATTRIBUTES].update({
    '_definition_source': '{_definition_src}',
    '__definition_source': '{__definition_src}',
    '___definition_source': '{___definition_src}',
})

_iso_tag_roots = OrderedDict((
    # First process private dependency tags (order enforced by key sorting)
    ('_content_coverage', 'contentInfo/MD_CoverageDescription'),
    ('_dataqual', 'dataQualityInfo/DQ_DataQuality'),
    ('_dataqual_lineage', '{_dataqual}/lineage/LI_Lineage'),
    ('_dataqual_report', '{_dataqual}/report'),
    ('_distinfo', 'distributionInfo/MD_Distribution'),
    ('_distinfo_dist', '{_distinfo}/distributor/MD_Distributor'),
    ('_distinfo_proc', '{_distinfo_dist}/distributionOrderProcess/MD_StandardOrderProcess'),
    ('_distinfo_resp', '{_distinfo_dist}/distributorContact/CI_ResponsibleParty'),
    ('_distinfo_resp_contact', '{_distinfo_resp}/contactInfo/CI_Contact'),
    ('_distinfo_rsrc', '{_distinfo}/transferOptions/MD_DigitalTransferOptions/onLine/CI_OnlineResource'),
    ('_idinfo', 'identificationInfo/MD_DataIdentification'),
    ('_idinfo_aggregate', '{_idinfo}/aggregationInfo/MD_AggregateInformation'),
    ('_idinfo_aggregate_citation', '{_idinfo_aggregate}/aggregateDataSetName/CI_Citation'),
    ('_idinfo_aggregate_contact', '{_idinfo_aggregate_citation}/citedResponsibleParty/CI_ResponsibleParty'),
    ('_idinfo_citation', '{_idinfo}/citation/CI_Citation'),
    ('_idinfo_citresp', '{_idinfo_citation}/citedResponsibleParty/CI_ResponsibleParty'),
    ('_idinfo_extent', '{_idinfo}/extent/EX_Extent'),
    ('_idinfo_keywords', '{_idinfo}/descriptiveKeywords/MD_Keywords'),
    ('_idinfo_resp', '{_idinfo}/pointOfContact/CI_ResponsibleParty'),
    ('_idinfo_resp_contact', '{_idinfo_resp}/contactInfo/CI_Contact'),

    # Supported in separate file ISO-19110: FC_FeatureCatalog
    ('_attr_root', 'FC_FeatureCatalogue'),
    ('_attr_base', 'featureType/FC_FeatureType/carrierOfCharacteristics/FC_FeatureAttribute'),
    ('_attr_def', '{_attr_base}/definitionReference/FC_DefinitionReference/definitionSource/FC_DefinitionSource'),
    ('_attr_src', '{_attr_def}/source/CI_Citation/citedResponsibleParty/CI_ResponsibleParty'),

    # References to separate file ISO-19110 from: MD_Metadata
    ('_attr_citation', 'contentInfo/MD_FeatureCatalogueDescription/featureCatalogueCitation'),
    ('_attr_contact', '{_attr_citation}/CI_Citation/citedResponsibleParty/CI_ResponsibleParty/contactInfo/CI_Contact'),
    ('_attr_contact_url', '{_attr_contact}/onlineResource/CI_OnlineResource/linkage/URL')
))


# Two passes required because of self references within roots dict
_iso_tag_roots.update(format_xpaths(_iso_tag_roots, **_iso_tag_roots))
_iso_tag_roots.update(format_xpaths(_iso_tag_roots, **_iso_tag_roots))

_iso_tag_formats = {
    # Property-specific xpath roots: the base from which each element repeats
    '_attribute_accuracy_root': '{_dataqual_report}',
    '_attributes_root': 'featureType/FC_FeatureType/carrierOfCharacteristics',
    '_bounding_box_root': '{_idinfo_extent}/geographicElement',
    '_contacts_root': '{_idinfo_resp}',
    '_dataset_completeness_root': '{_dataqual_report}',
    '_dates_root': '{_idinfo_extent}/temporalElement',
    '_digital_forms_root': '{_distinfo}/distributionFormat',
    '_transfer_options_root': '{_distinfo}/transferOptions',
    '_keywords_root': '{_idinfo}/descriptiveKeywords',
    '_larger_works_root': '{_idinfo_aggregate_citation}',
    '_process_steps_root': '{_dataqual_lineage}/processStep',

    # Then process public dependent tags
    'title': '{_idinfo_citation}/title/CharacterString',
    'abstract': '{_idinfo}/abstract/CharacterString',
    'purpose': '{_idinfo}/purpose/CharacterString',
    'supplementary_info': '{_idinfo}/supplementalInformation/CharacterString',
    'online_linkages': '{_idinfo_citresp}/contactInfo/CI_Contact/onlineResource/CI_OnlineResource/linkage/URL',
    'originators': '{_idinfo_citresp}/organisationName/CharacterString',
    'publish_date': '{_idinfo_citation}/date/CI_Date/date/Date',
    'publish_date_type': '{_idinfo_citation}/date/CI_Date/dateType/CI_DateTypeCode',
    'data_credits': '{_idinfo}/credit/CharacterString',
    CONTACTS: '{_idinfo_resp}/{{ct_path}}',
    'dist_contact_org': '{_distinfo_resp}/organisationName/CharacterString',
    'dist_contact_person': '{_distinfo_resp}/individualName/CharacterString',
    'dist_address_type': '{_distinfo_resp_contact}/address/@type',
    'dist_address': '{_distinfo_resp_contact}/address/CI_Address/deliveryPoint/CharacterString',
    'dist_city': '{_distinfo_resp_contact}/address/CI_Address/city/CharacterString',
    'dist_state': '{_distinfo_resp_contact}/address/CI_Address/administrativeArea/CharacterString',
    'dist_postal': '{_distinfo_resp_contact}/address/CI_Address/postalCode/CharacterString',
    'dist_country': '{_distinfo_resp_contact}/address/CI_Address/country/CharacterString',
    '_dist_country': '{_distinfo_resp_contact}/address/CI_Address/country/Country',  # If not in CharacterString
    'dist_phone': '{_distinfo_resp_contact}/phone/CI_Telephone/voice/CharacterString',
    'dist_email': '{_distinfo_resp_contact}/address/CI_Address/electronicMailAddress/CharacterString',
    'dist_liability': '{_idinfo}/resourceConstraints/MD_LegalConstraints/otherConstraints/CharacterString',
    'processing_fees': '{_distinfo_proc}/fees/CharacterString',
    'processing_instrs': '{_distinfo_proc}/orderingInstructions/CharacterString',
    'resource_desc': '{_idinfo_citation}/identifier/MD_Identifier/code/CharacterString',
    'tech_prerequisites': '{_idinfo}/environmentDescription/CharacterString',
    ATTRIBUTES: '{_attr_base}/{{ad_path}}',
    '_attributes_file': '{_attr_citation}/@href',
    '__attributes_file': '{_attr_contact_url}',  # If not in above: "_attr_citation/@href"
    'attribute_accuracy': '{_dataqual_report}/DQ_QuantitativeAttributeAccuracy/measureDescription/CharacterString',
    BOUNDING_BOX: '{_idinfo_extent}/geographicElement/EX_GeographicBoundingBox/{{bbox_path}}',
    'dataset_completeness': '{_dataqual_report}/DQ_CompletenessOmission/measureDescription/CharacterString',
    DIGITAL_FORMS: '{_distinfo}/distributionFormat/MD_Format/{{df_path}}',
    '_access_desc': '{_distinfo_rsrc}/description/CharacterString',
    '_access_instrs': '{_distinfo_rsrc}/protocol/CharacterString',
    '_network_resource': '{_distinfo_rsrc}/linkage/URL',
    PROCESS_STEPS: '{_dataqual_lineage}/processStep/LI_ProcessStep/{{ps_path}}',
    LARGER_WORKS: '{_idinfo_aggregate_citation}/{{lw_path}}',
    '_lw_citation': '{_idinfo_aggregate_contact}/{{lw_path}}',
    '_lw_collective': '{_idinfo_citation}/collectiveTitle/CharacterString',
    '_lw_contact': '{_idinfo_aggregate_contact}/contactInfo/CI_Contact/{{lw_path}}',
    '_lw_linkage': '{_idinfo_aggregate_contact}/contactInfo/CI_Contact/onlineResource/CI_OnlineResource/{{lw_path}}',
    'other_citation_info': '{_idinfo_citation}/otherCitationDetails/CharacterString',
    'use_constraints': '{_idinfo}/resourceConstraints/MD_Constraints/useLimitation/CharacterString',
    DATES: '{_idinfo_extent}/temporalElement/EX_TemporalExtent/extent/{{type_path}}',
    KEYWORDS_PLACE: '{_idinfo_keywords}/keyword/CharacterString',
    KEYWORDS_THEME: '{_idinfo_keywords}/keyword/CharacterString'
}

# Apply XPATH root formats to the basic data map formats
_iso_tag_formats.update(_iso_tag_roots)
_iso_tag_formats.update(format_xpaths(_iso_tag_formats, **_iso_tag_roots))

_iso_tag_primitives = {
    'Binary', 'Boolean', 'CharacterString',
    'Date', 'DateTime', 'timePosition',
    'Decimal', 'Integer', 'Real', 'RecordType',
    'CI_DateTypeCode', 'MD_KeywordTypeCode', 'URL'
}


class IsoParser(MetadataParser):
    """ A class to parse metadata files conforming to the ISO-19115 standard """

    def _init_data_map(self):
        """ OVERRIDDEN: Initialize required ISO-19115 data map with XPATHS and specialized functions """

        if self._data_map is not None:
            return  # Initiation happens once

        # Parse and validate the ISO metadata root

        if self._xml_tree is None:
            iso_root = ISO_ROOTS[0]
        else:
            iso_root = get_element_name(self._xml_tree)

        if iso_root not in ISO_ROOTS:
            raise ParserError('Invalid XML root for ISO-19115 standard: {root}', root=iso_root)

        iso_data_map = {'_root': iso_root}
        iso_data_map.update(_iso_tag_roots)
        iso_data_map.update(_iso_tag_formats)

        iso_data_structures = {}

        # Capture and format complex XPATHs

        ad_format = iso_data_map[ATTRIBUTES]
        ft_source = iso_data_map['_attr_src'].replace('/carrierOfCharacteristics/FC_FeatureAttribute', '')

        iso_data_structures[ATTRIBUTES] = format_xpaths(
            _iso_definitions[ATTRIBUTES],
            label=ad_format.format(ad_path='memberName/LocalName'),
            aliases=ad_format.format(ad_path='aliases/LocalName'),  # Not in spec
            definition=ad_format.format(ad_path='definition/CharacterString'),

            # First try to populate attribute definition source from FC_FeatureAttribute
            definition_src=iso_data_map['_attr_src'] + '/organisationName/CharacterString',
            _definition_src=iso_data_map['_attr_src'] + '/individualName/CharacterString',

            # Then assume feature type source is the same as attribute: populate from FC_FeatureType
            __definition_src=ft_source + '/organisationName/CharacterString',
            ___definition_src=ft_source + '/individualName/CharacterString'
        )

        bb_format = iso_data_map[BOUNDING_BOX]
        iso_data_structures[BOUNDING_BOX] = format_xpaths(
            _iso_definitions[BOUNDING_BOX],
            east=bb_format.format(bbox_path='eastBoundLongitude/Decimal'),
            south=bb_format.format(bbox_path='southBoundLatitude/Decimal'),
            west=bb_format.format(bbox_path='westBoundLongitude/Decimal'),
            north=bb_format.format(bbox_path='northBoundLatitude/Decimal')
        )

        ct_format = iso_data_map[CONTACTS]
        iso_data_structures[CONTACTS] = format_xpaths(
            _iso_definitions[CONTACTS],
            name=ct_format.format(ct_path='individualName/CharacterString'),
            organization=ct_format.format(ct_path='organisationName/CharacterString'),
            position=ct_format.format(ct_path='positionName/CharacterString'),
            email=ct_format.format(
                ct_path='contactInfo/CI_Contact/address/CI_Address/electronicMailAddress/CharacterString'
            )
        )

        dt_format = iso_data_map[DATES]
        iso_data_structures[DATES] = {
            DATE_TYPE_MULTIPLE: dt_format.format(type_path='TimeInstant/timePosition'),
            DATE_TYPE_RANGE_BEGIN: dt_format.format(type_path='TimePeriod/begin/TimeInstant/timePosition'),
            DATE_TYPE_RANGE_END: dt_format.format(type_path='TimePeriod/end/TimeInstant/timePosition'),
            DATE_TYPE_SINGLE: dt_format.format(type_path='TimeInstant/timePosition')  # Same as multiple
        }

        df_format = iso_data_map[DIGITAL_FORMS]
        iso_data_structures[DIGITAL_FORMS] = format_xpaths(
            _iso_definitions[DIGITAL_FORMS],
            name=df_format.format(df_path='name/CharacterString'),
            content='',  # Not supported in ISO-19115 (appending to spec)
            decompression=df_format.format(df_path='fileDecompressionTechnique/CharacterString'),
            version=df_format.format(df_path='version/CharacterString'),
            specification=df_format.format(df_path='specification/CharacterString'),
            access_desc=iso_data_map['_access_desc'],
            access_instrs=iso_data_map['_access_instrs'],
            network_resource=iso_data_map['_network_resource']
        )

        keywords_structure = {
            'keyword_root': 'MD_Keywords/keyword',
            'keyword_type': 'MD_Keywords/type/MD_KeywordTypeCode',
            'keyword': 'MD_Keywords/keyword/CharacterString'
        }
        iso_data_structures[KEYWORDS_PLACE] = keywords_structure
        iso_data_structures[KEYWORDS_THEME] = keywords_structure

        lw_format = iso_data_map[LARGER_WORKS]
        iso_data_structures[LARGER_WORKS] = format_xpaths(
            _iso_definitions[LARGER_WORKS],
            title=lw_format.format(lw_path='title/CharacterString'),
            edition=lw_format.format(lw_path='edition/CharacterString'),
            origin=iso_data_map['_lw_citation'].format(lw_path='individualName/CharacterString'),
            online_linkage=iso_data_map['_lw_linkage'].format(lw_path='linkage/URL'),
            other_citation=lw_format.format(lw_path='otherCitationDetails/CharacterString'),
            date=lw_format.format(lw_path='editionDate/Date'),
            place=iso_data_map['_lw_contact'].format(lw_path='address/CI_Address/city/CharacterString'),
            info=iso_data_map['_lw_citation'].format(lw_path='organisationName/CharacterString')
        )

        ps_format = iso_data_map[PROCESS_STEPS]
        iso_data_structures[PROCESS_STEPS] = format_xpaths(
            _iso_definitions[PROCESS_STEPS],
            description=ps_format.format(ps_path='description/CharacterString'),
            date=ps_format.format(ps_path='dateTime/DateTime'),
            sources=ps_format.format(
                ps_path='source/LI_Source/sourceCitation/CI_Citation/alternateTitle/CharacterString'
            )
        )

        # Assign XPATHS and gis_metadata.utils.ParserProperties to data map

        for prop, xpath in iteritems(dict(iso_data_map)):
            if prop == ATTRIBUTES:
                iso_data_map[prop] = ParserProperty(self._parse_attribute_details, self._update_attribute_details)

            elif prop in (CONTACTS, PROCESS_STEPS):
                iso_data_map[prop] = ParserProperty(self._parse_complex_list, self._update_complex_list)

            elif prop in (BOUNDING_BOX, LARGER_WORKS):
                iso_data_map[prop] = ParserProperty(self._parse_complex, self._update_complex)

            elif prop == DATES:
                iso_data_map[prop] = ParserProperty(self._parse_dates, self._update_dates)

            elif prop == DIGITAL_FORMS:
                iso_data_map[prop] = ParserProperty(self._parse_digital_forms, self._update_digital_forms)

            elif prop in [KEYWORDS_PLACE, KEYWORDS_THEME]:
                iso_data_map[prop] = ParserProperty(self._parse_keywords, self._update_keywords)

            else:
                iso_data_map[prop] = xpath

        self._data_map = iso_data_map
        self._data_structures = iso_data_structures

    def _parse_attribute_details(self, prop=ATTRIBUTES):
        """ Concatenates a list of Attribute Details data structures parsed from a remote file """

        parsed_attributes = self._parse_attribute_details_file(prop)
        if parsed_attributes is None:
            # If not in the (official) remote location, try the tree itself
            parsed_attributes = self._parse_complex_list(prop)

        for attribute in (a for a in parsed_attributes if not a['aliases']):
            # Aliases are not in ISO standard: default to label
            attribute['aliases'] = attribute['label']

        return parsed_attributes

    def _parse_attribute_details_file(self, prop=ATTRIBUTES):
        """ Concatenates a list of Attribute Details data structures parsed from a remote file """

        # Parse content from remote file URL, which may be stored in one of two places:
        #    Starting at: contentInfo/MD_FeatureCatalogueDescription/featureCatalogueCitation
        #    ATTRIBUTE: href
        #    ELEMENT TEXT: CI_Citation/.../CI_Contact/onlineResource/CI_OnlineResource/linkage

        self._attr_details_file_url = parse_property(
            self._xml_tree, None, self._data_map, '_attributes_file'
        )
        if not self._attr_details_file_url:
            return None

        try:
            tree_to_parse = get_remote_element(self._attr_details_file_url)
        except:
            self._attr_details_file_url = None
            return None

        xpath_map = self._data_structures[ATTRIBUTES]
        xpath_root = self._get_xroot_for(prop)

        return parse_complex_list(tree_to_parse, xpath_root, xpath_map, prop)

    def _parse_digital_forms(self, prop=DIGITAL_FORMS):
        """ Concatenates a list of Digital Form data structures parsed from the metadata """

        xpath_map = self._data_structures[prop]

        # Parse base digital form fields: 'name', 'content', 'decompression', 'version', 'specification'
        xpath_root = self._data_map['_digital_forms_root']
        digital_forms = parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

        # Parse digital form transfer option fields: 'access_desc', 'access_instrs', 'network_resource'
        xpath_root = self._data_map['_transfer_options_root']
        transfer_opts = parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)

        # Split out digital form content that has been appended to specifications

        content_delim = _DIGITAL_FORMS_CONTENT_DELIM

        for digital_form in digital_forms:
            specifications = wrap_value(s.strip() for s in digital_form['specification'])

            digital_form['content'] = []
            digital_form['specification'] = []
            has_content = False

            # For each specification, insert delim before appending content
            for spec in specifications:
                has_content = has_content or spec == content_delim

                if not has_content:
                    digital_form['specification'].append(spec)
                elif spec != content_delim:
                    digital_form['content'].append(spec)

            # Reduce spec and content to single string values if possible
            for form_prop in ('content', 'specification'):
                digital_form[form_prop] = reduce_value(filter_empty(digital_form[form_prop], u''))

        # Combine digital forms and transfer options into a single complex struct

        df_len = len(digital_forms)
        to_len = len(transfer_opts)
        parsed_forms = []

        for idx in xrange(0, max(df_len, to_len)):
            digital_form = {}.fromkeys(_iso_definitions[prop], u'')

            if idx < df_len:
                digital_form.update(i for i in digital_forms[idx].items() if i[1])
            if idx < to_len:
                digital_form.update(i for i in transfer_opts[idx].items() if i[1])

            if any(digital_form.values()):
                parsed_forms.append(digital_form)

        return parsed_forms

    def _parse_keywords(self, prop):
        """ Parse type-specific keywords from the metadata: Theme or Place """

        keywords = []

        if prop in [KEYWORDS_PLACE, KEYWORDS_THEME]:
            xpath_root = self._data_map['_keywords_root']
            xpath_map = self._data_structures[prop]

            xtype = xpath_map['keyword_type']
            xpath = xpath_map['keyword']

            if prop == KEYWORDS_PLACE:
                ktype = KEYWORD_TYPE_PLACE
            elif prop == KEYWORDS_THEME:
                ktype = KEYWORD_TYPE_THEME

            for element in get_elements(self._xml_tree, xpath_root):
                if get_element_text(element, xtype).lower() == ktype.lower():
                    keywords.extend(get_elements_text(element, xpath))

        return keywords

    def _update_attribute_details(self, **update_props):
        """ Update operation for ISO Attribute Details metadata: write to "MD_Metadata/featureType" """

        tree_to_update = update_props['tree_to_update']
        xpath = self._data_map['_attr_citation']

        # Cannot write to remote file: remove the featureCatalogueCitation element

        self._attr_details_file_url = None
        remove_element(tree_to_update, xpath, True)

        return self._update_complex_list(**update_props)

    def _update_dates(self, **update_props):
        """
        Update operation for ISO Dates metadata
        :see: gis_metadata.utils._complex_definitions[DATES]
        """

        tree_to_update = update_props['tree_to_update']
        xpath_root = self._data_map['_dates_root']

        if self.dates:
            date_type = self.dates[DATE_TYPE]

            # First remove all date info from common root
            remove_element(tree_to_update, xpath_root)

            if date_type == DATE_TYPE_MULTIPLE:
                xpath_root += '/TimeInstant'
            elif date_type == DATE_TYPE_RANGE:
                xpath_root += '/TimePeriod'

        return super(IsoParser, self)._update_dates(xpath_root, **update_props)

    def _update_digital_forms(self, **update_props):
        """
        Update operation for ISO Digital Forms metadata
        :see: gis_metadata.utils._complex_definitions[DIGITAL_FORMS]
        """

        digital_forms = wrap_value(update_props['values'])

        # Update all Digital Form properties: distributionFormat*

        xpath_map = self._data_structures[update_props['prop']]

        dist_format_props = ('name', 'decompression', 'version', 'specification')
        dist_format_xroot = self._data_map['_digital_forms_root']
        dist_format_xmap = {prop: xpath_map[prop] for prop in dist_format_props}
        dist_formats = []

        for digital_form in digital_forms:
            dist_format = {prop: digital_form[prop] for prop in dist_format_props}

            if digital_form.get('content'):
                dist_spec = wrap_value(digital_form.get('specification'))
                dist_spec.append(_DIGITAL_FORMS_CONTENT_DELIM)
                dist_spec.extend(wrap_value(digital_form['content']))
                dist_format['specification'] = dist_spec

            dist_formats.append(dist_format)

        update_props['values'] = dist_formats
        dist_formats = update_complex_list(
            xpath_root=dist_format_xroot, xpath_map=dist_format_xmap, **update_props
        )

        # Update all Network Resources: transferOptions+

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

    def _update_keywords(self, **update_props):
        """ Update operation for ISO type-specific Keywords metadata: Theme or Place """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = update_props['values']

        keywords = []

        if prop in [KEYWORDS_PLACE, KEYWORDS_THEME]:
            xpath_root = self._data_map['_keywords_root']
            xpath_map = self._data_structures[update_props['prop']]

            xtype = xpath_map['keyword_type']
            xroot = xpath_map['keyword_root']
            xpath = xpath_map['keyword']

            if prop == KEYWORDS_PLACE:
                ktype = KEYWORD_TYPE_PLACE
            elif prop == KEYWORDS_THEME:
                ktype = KEYWORD_TYPE_THEME

            # Remove descriptiveKeyword nodes according to type
            for element in get_elements(tree_to_update, xpath_root):
                if get_element_text(element, xtype).lower() == ktype.lower():
                    remove_element(tree_to_update, xpath_root)

            element = insert_element(tree_to_update, 0, xpath_root)
            insert_element(element, 0, xtype, ktype)  # Add the type node

            keywords.extend(update_property(element, xroot, xpath, prop, values))

        return keywords

    def update(self, use_template=False, **metadata_defaults):
        """ OVERRIDDEN: Prevents writing multiple CharacterStrings per XPATH property """

        self.validate()

        tree_to_update = self._xml_tree if not use_template else self._get_template(**metadata_defaults)
        supported_props = self._metadata_props

        # Iterate over keys, and extract non-primitive root for all XPATHs
        #    xroot = identificationInfo/MD_DataIdentification/abstract/
        #    xpath = identificationInfo/MD_DataIdentification/abstract/CharacterString
        #
        # This prevents multiple primitive tags from being inserted under an element

        for prop, xpath in iteritems(self._data_map):
            if not prop.startswith('_') or prop.strip('_') in supported_props:
                # Send only public or alternate properties
                xroot = self._trim_xpath(xpath, prop)
                values = getattr(self, prop, u'')
                update_property(tree_to_update, xroot, xpath, prop, values, supported_props)

        return tree_to_update

    def _trim_xpath(self, xpath, prop):
        """ Removes primitive type tags from an XPATH """

        xroot = self._get_xroot_for(prop)

        if xroot is None and isinstance(xpath, string_types):
            xtags = xpath.split(XPATH_DELIM)

            if xtags[-1] in _iso_tag_primitives:
                xroot = XPATH_DELIM.join(xtags[:-1])

        return xroot
