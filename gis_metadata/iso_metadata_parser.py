""" A module to contain utility ISO-19115 metadata parsing helpers """

import six

from collections import OrderedDict
from six import iteritems, string_types

from parserutils.collections import reduce_value, wrap_value
from parserutils.elements import set_element_attributes
from parserutils.elements import clear_element, insert_element, remove_element
from parserutils.elements import get_element, get_elements, get_remote_element
from parserutils.elements import get_element_attributes, get_element_name, get_element_text, get_elements_text
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

from gis_metadata.utils import format_xpaths, get_complex_definitions, get_xpath_branch
from gis_metadata.utils import parse_complex_list, update_complex_list, update_property


xrange = getattr(six.moves, 'xrange')


ISO_ROOTS = ('MD_Metadata', 'MI_Metadata')

KEYWORD_TYPE_PLACE = 'place'
KEYWORD_TYPE_THEME = 'theme'

_iso_definitions = get_complex_definitions()

_iso_tag_roots = OrderedDict((
    # First process private dependency tags (order enforced by key sorting)
    ('_contentinfo', 'contentInfo'),
    ('_contentinfo_coverage', '{_contentinfo}/MD_CoverageDescription'),
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

    # Supported in separate file ISO-19110
    ('_attr_root', 'FC_FeatureCatalogue'),
    ('_attr_base', 'featureType/FC_FeatureType'),
    ('_attr_ref', '{_attr_base}/definitionReference/FC_DefinitionReference'),
    ('_attr_citation', '{_contentinfo}/MD_FeatureCatalogueDescription/featureCatalogueCitation'),
    ('_attr_contact', '{_attr_citation}/CI_Citation/citedResponsibleParty/CI_ResponsibleParty/contactInfo/CI_Contact')
))

# Two passes required because of self references within roots dict
_iso_tag_roots.update(format_xpaths(_iso_tag_roots, **_iso_tag_roots))
_iso_tag_roots.update(format_xpaths(_iso_tag_roots, **_iso_tag_roots))

_iso_tag_formats = {
    # Property-specific xpath roots: the base from which each element repeats
    '_bounding_box_root': '{_idinfo_extent}/geographicElement',
    '_contacts_root': '{_idinfo_resp}',
    '_dates_root': '{_idinfo_extent}/temporalElement',
    '_digital_form_content_root': '{_contentinfo_coverage}',
    '_distribution_format_root': '{_distinfo}/distributionFormat',
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
    ATTRIBUTES: '{_attr_base}/carrierOfCharacteristics/FC_FeatureAttribute/{{ad_path}}',
    '_attr_alias': '{_attr_base}/{{ad_path}}',
    '_attr_src': '{_attr_ref}/definitionSource/FC_DefinitionSource/source/{{ad_path}}',
    '_attr_url': '{_attr_contact}/onlineResource/CI_OnlineResource/linkage/URL',
    'attribute_accuracy': '{_dataqual_report}/DQ_QuantitativeAttributeAccuracy/measureDescription/CharacterString',
    BOUNDING_BOX: '{_idinfo_extent}/geographicElement/EX_GeographicBoundingBox/{{bbox_path}}',
    'dataset_completeness': '{_dataqual_report}/DQ_CompletenessOmission/measureDescription/CharacterString',
    DIGITAL_FORMS: '{_distinfo}/distributionFormat/MD_Format/{{df_path}}',
    '_access_desc': '{_distinfo_rsrc}/description/CharacterString',
    '_access_instrs': '{_distinfo_rsrc}/protocol/CharacterString',
    '_network_resource': '{_distinfo_rsrc}/linkage/URL',
    '_digital_form_content': '{_contentinfo_coverage}/attributeDescription/RecordType',
    PROCESS_STEPS: '{_dataqual_lineage}/processStep/LI_ProcessStep',
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
        iso_data_structures[ATTRIBUTES] = format_xpaths(
            _iso_definitions[ATTRIBUTES],
            label=ad_format.format(ad_path='memberName/LocalName'),
            aliases=iso_data_map['_attr_alias'].format(ad_path='aliases/LocalName'),
            definition=ad_format.format(ad_path='definition/CharacterString'),
            definition_src=iso_data_map['_attr_src'].format(
                ad_path='CI_Citation/organisationName/CharacterString'
            )
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
            content='',  # Not supported in ISO-19115 (using coverage description)
            decompression=df_format.format(df_path='fileDecompressionTechnique/CharacterString'),
            version=df_format.format(df_path='version/CharacterString'),
            specification=df_format.format(df_path='specification/CharacterString'),
            access_desc='',  # Placeholder for later assignment
            access_instrs='',  # Placeholder for later assignment
            network_resource=''  # Placeholder for later assignment
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

        ps_format = iso_data_map[PROCESS_STEPS] + '/{ps_path}'
        iso_data_structures[PROCESS_STEPS] = format_xpaths(
            _iso_definitions[PROCESS_STEPS],
            description=ps_format.format(ps_path='description/CharacterString'),
            date=ps_format.format(ps_path='dateTime/DateTime'),
            sources=ps_format.format(
                ps_path='source/LI_Source/sourceCitation/CI_Citation/alternateTitle/CharacterString'
            )
        )

        # Assign XPATHS and gis_metadata.utils.ParserProperties to fgdc_data_map

        for prop, xpath in iteritems(dict(iso_data_map)):
            if prop == ATTRIBUTES:
                iso_data_map[prop] = ParserProperty(self._parse_attribute_details, self._update_attribute_details)

            elif prop in ('attribute_accuracy', 'dataset_completeness'):
                iso_data_map[prop] = ParserProperty(self._parse_property, self._update_report_item, xpath=xpath)

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

        # Parse content from remote file URL, which may be stored in one of two places:
        #    Starting at: contentInfo/MD_FeatureCatalogueDescription/featureCatalogueCitation
        #    ATTRIBUTE: href
        #    ELEMENT TEXT: CI_Citation/.../CI_Contact/onlineResource/CI_OnlineResource/linkage

        attrib_details = []

        file_element = get_element(self._xml_tree, self._data_map['_attr_citation'])
        file_location = None

        if file_element is not None:
            # First try the href attribute for a URL reference to ISO attributes
            file_location = get_element_attributes(file_element).get('href')

            if not file_location:
                # Then try the deeper location for the ISO attributes URL
                file_location = get_element_text(self._xml_tree, self._data_map['_attr_url'])

        if not file_location:
            self._attr_details_file_url = None
        else:
            # Definition Source location in the remote file:
            #    Starting at: FC_FeatureCatalogue/featureType/FC_FeatureType/definitionReference/FC_DefinitionReference
            #        source/CI_Citation/.../organisationName (Default)
            #        source/CI_Citation/.../individualName
            #        sourceIdentifier (if nowhere else)

            self._attr_details_file_url = file_location

            xpath_map = dict(self._data_structures[ATTRIBUTES])
            xpath_root = 'featureType'

            try:
                remote_xtree = get_remote_element(file_location)
            except:
                self._attr_details_file_url = None
                return attrib_details  # Nothing to parse

            def_src_xpath = xpath_map['definition_source']

            if not get_element_text(remote_xtree, def_src_xpath):
                def_src_xpath = def_src_xpath.replace('organisationName', 'individualName')

                if not get_element_text(remote_xtree, def_src_xpath):
                    def_src_xpath = self._data_map['_attr_ref'] + '/sourceIdentifier/CharacterString'

            xpath_map['definition_source'] = def_src_xpath

            parsed_details = parse_complex_list(remote_xtree, xpath_root, xpath_map, prop)

            # There may be more than one carrierOfCharacteristics element per featureType
            # If so, create a new attribute detail for each one with copies of the other properties

            for parsed_detail in parsed_details:
                attrib_detail = dict(parsed_detail)

                attrib_detail['label'] = u''
                attrib_detail['definition'] = u''

                parsed_defs = wrap_value(parsed_detail['definition'])
                parsed_lbls = wrap_value(parsed_detail['label'])

                len_defs = len(parsed_defs)
                len_lbls = len(parsed_lbls)
                limit = max(len_defs, len_lbls)

                if not limit:
                    attrib_details.append(dict(attrib_detail))
                else:
                    for idx in xrange(0, limit):

                        attrib_detail['label'] = parsed_lbls[idx] if idx < len_lbls else u''
                        attrib_detail['definition'] = parsed_defs[idx] if idx < len_defs else u''

                        attrib_details.append(dict(attrib_detail))

        return attrib_details

    def _parse_digital_forms(self, prop=DIGITAL_FORMS):
        """ Concatenates a list of Digital Form data structures parsed from the metadata """

        xpath_root = self._data_map['_distribution_format_root']
        xpath_map = self._data_structures[prop]

        transopt_root = self._data_map['_transfer_options_root']
        acdesc_xpath = get_xpath_branch(transopt_root, self._data_map['_access_desc'])
        acinstr_xpath = get_xpath_branch(transopt_root, self._data_map['_access_instrs'])
        netrsrc_xpath = get_xpath_branch(transopt_root, self._data_map['_network_resource'])

        digital_forms = parse_complex_list(self._xml_tree, xpath_root, xpath_map, prop)
        digital_form_content = self._parse_form_content()
        transfer_opts = get_elements(self._xml_tree, transopt_root)

        dist_format_len = len(digital_forms)
        trans_option_len = len(transfer_opts)

        combined = []

        for idx in xrange(0, max(dist_format_len, trans_option_len)):
            if idx < dist_format_len:
                digital_form = digital_forms[idx]
            else:
                digital_form = {}.fromkeys(_iso_definitions[prop], u'')

            digital_form['content'] = digital_form_content

            if idx < trans_option_len:
                transopt = transfer_opts[idx]

                digital_form['access_desc'] = reduce_value(get_elements_text(transopt, acdesc_xpath))
                digital_form['access_instrs'] = reduce_value(get_elements_text(transopt, acinstr_xpath))
                digital_form['network_resource'] = reduce_value(get_elements_text(transopt, netrsrc_xpath))

            if any(digital_form.values()):
                combined.append(digital_form)

        return combined

    def _parse_form_content(self, form_content=None):
        """ :return: the form_content filtered down to a single value (only one supported) """

        if form_content is not None:
            content_value = form_content
        elif getattr(self, '_digital_form_content', None):
            content_value = self._digital_form_content
        else:
            content_value = self._parse_property('_digital_form_content')

        return (wrap_value(content_value) or [u''])[0]

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
        """ Update operation for ISO Attribute Details metadata (standard 19110) """

        attributes = []

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        xpath = self._data_map['_attr_citation']

        if not getattr(self, prop):
            # Property cleared: remove the featureCatalogueCitation element altogether

            self._attr_details_file_url = None
            attributes = [remove_element(tree_to_update, xpath)]

        if self._attr_details_file_url:
            # Clear all the irrelevant feature attribute data, and write just the reference

            attrib_element = get_element(tree_to_update, xpath)

            if attrib_element is None:
                attrib_element = insert_element(tree_to_update, 0, xpath)
            else:
                clear_element(attrib_element)

            set_element_attributes(attrib_element, href=self._attr_details_file_url)

            attributes = [attrib_element]

        return attributes

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

        # Capture last altered form content for all digital forms

        original_form_content = self._parse_form_content()
        digital_form_content = original_form_content

        for digital_form in digital_forms:
            next_form_content = self._parse_form_content(digital_form.get('content') or u'')
            if next_form_content != original_form_content:
                digital_form_content = next_form_content

        # Update digital form content: contentInfo/MD_CoverageDescription*

        tree_to_update = update_props['tree_to_update']
        xpaths = self._data_map['_digital_form_content']
        xroot = self._data_map['_digital_form_content_root']

        coverage_desc = update_property(tree_to_update, xroot, xpaths, DIGITAL_FORMS, digital_form_content)

        # Update all Digital Form properties: distributionFormat*

        xpath_map = self._data_structures[update_props['prop']]

        dist_format_props = ('name', 'decompression', 'version', 'specification')
        dist_format_xroot = self._data_map['_distribution_format_root']
        dist_format_xmap = {prop: xpath_map[prop] for prop in dist_format_props}

        dist_formats = []
        for digital_form in digital_forms:
            dist_formats.append({prop: digital_form[prop] for prop in dist_format_props})
            digital_form['content'] = digital_form_content

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
            'coverage_desc': coverage_desc,
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

    def _update_report_item(self, **update_props):
        """ Update operation for ISO Attribute Accuracy metadata """

        return update_property(xpath_root=self._data_map['_dataqual_report'], **update_props)

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
                xroot = self._trim_xpath(xpath)
                values = getattr(self, prop, u'')
                update_property(tree_to_update, xroot, xpath, prop, values, supported_props)

        return tree_to_update

    def _trim_xpath(self, xpath, default_value=None):
        """ Removes primitive type tags from an XPATH """

        if isinstance(xpath, string_types):
            xtags = xpath.split(XPATH_DELIM)

            if xtags[-1] in _iso_tag_primitives:
                xpath = XPATH_DELIM.join(xtags[:-1])
            else:
                xpath = default_value

        return default_value
