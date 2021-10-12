""" A module to contain utility ISO-19115 metadata parsing helpers """

from _collections import OrderedDict
from copy import deepcopy
from frozendict import frozendict as FrozenOrderedDict

from parserutils.collections import filter_empty, reduce_value, wrap_value
from parserutils.elements import get_element_name, get_element_text, get_elements_text
from parserutils.elements import get_elements, get_remote_element, insert_element, remove_element
from parserutils.elements import XPATH_DELIM

from gis_metadata.exceptions import InvalidContent
from gis_metadata.metadata_parser import MetadataParser
from gis_metadata.utils import DATE_TYPE, DATE_TYPE_SINGLE, DATE_TYPE_MULTIPLE
from gis_metadata.utils import DATE_TYPE_RANGE, DATE_TYPE_RANGE_BEGIN, DATE_TYPE_RANGE_END
from gis_metadata.utils import ATTRIBUTES
from gis_metadata.utils import CONTACTS
from gis_metadata.utils import BOUNDING_BOX
from gis_metadata.utils import DATES
from gis_metadata.utils import DIGITAL_FORMS
from gis_metadata.utils import KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME
from gis_metadata.utils import LARGER_WORKS
from gis_metadata.utils import PROCESS_STEPS
from gis_metadata.utils import RASTER_DIMS, RASTER_INFO
from gis_metadata.utils import COMPLEX_DEFINITIONS, ParserProperty
from gis_metadata.utils import format_xpaths, get_default_for_complex, get_default_for_complex_sub
from gis_metadata.utils import parse_complex_list, parse_property, update_complex_list, update_property


ISO_ROOTS = ('MD_Metadata', 'MI_Metadata')

KEYWORD_PROPS = (KEYWORDS_PLACE, KEYWORDS_STRATUM, KEYWORDS_TEMPORAL, KEYWORDS_THEME)
KEYWORD_TYPES = FrozenOrderedDict({
    KEYWORDS_PLACE: 'place',
    KEYWORDS_STRATUM: 'stratum',
    KEYWORDS_TEMPORAL: 'temporal',
    KEYWORDS_THEME: 'theme'
})

# For appending digital form content to ISO distribution format specs
ISO_DIGITAL_FORMS_DELIM = '@------------------------------@'

# Define backup locations for attribute sub-properties and dimension type property
ISO_DEFINITIONS = dict({k: dict(v) for k, v in dict(COMPLEX_DEFINITIONS).items()})
ISO_DEFINITIONS[ATTRIBUTES].update({
    '_definition_source': '{_definition_src}',
    '__definition_source': '{__definition_src}',
    '___definition_source': '{___definition_src}'
})
ISO_DEFINITIONS[RASTER_DIMS]['_type'] = '{_type}'
ISO_DEFINITIONS = FrozenOrderedDict({k: FrozenOrderedDict(v) for k, v in ISO_DEFINITIONS.items()})

ISO_TAG_ROOTS = OrderedDict((
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

    ('_srinfo_grid_rep', 'spatialRepresentationInfo/MD_GridSpatialRepresentation'),
    ('_srinfo_grid_dim', '{_srinfo_grid_rep}/axisDimensionProperties/MD_Dimension'),

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
ISO_TAG_ROOTS.update(format_xpaths(ISO_TAG_ROOTS, **ISO_TAG_ROOTS))
ISO_TAG_ROOTS.update(format_xpaths(ISO_TAG_ROOTS, **ISO_TAG_ROOTS))
ISO_TAG_ROOTS = FrozenOrderedDict(ISO_TAG_ROOTS)

ISO_TAG_FORMATS = {
    # Property-specific xpath roots: the base from which each element repeats
    '_attribute_accuracy_root': '{_dataqual_report}',
    '_attributes_root': 'featureType/FC_FeatureType/carrierOfCharacteristics',
    '_bounding_box_root': '{_idinfo_extent}/geographicElement',
    '_contacts_root': '{_idinfo}/pointOfContact',
    '_dataset_completeness_root': '{_dataqual_report}',
    '_dates_root': '{_idinfo_extent}/temporalElement',
    '_digital_forms_root': '{_distinfo}/distributionFormat',
    '_dist_liability_root': '{_idinfo}/resourceConstraints',
    '_transfer_options_root': '{_distinfo}/transferOptions/MD_DigitalTransferOptions/onLine',
    '_keywords_root': '{_idinfo}/descriptiveKeywords',
    '_larger_works_root': '{_idinfo_aggregate_citation}',
    '_process_steps_root': '{_dataqual_lineage}/processStep',
    '_raster_info_root': '{_srinfo_grid_rep}/axisDimensionProperties',
    '_use_constraints_root': '{_idinfo}/resourceConstraints',

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
    'resource_desc': '{_idinfo}/resourceSpecificUsage/MD_Usage/specificUsage/CharacterString',
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
    '_lw_collective': '{_idinfo_aggregate_citation}/collectiveTitle/CharacterString',
    '_lw_contact': '{_idinfo_aggregate_contact}/contactInfo/CI_Contact/{{lw_path}}',
    '_lw_linkage': '{_idinfo_aggregate_contact}/contactInfo/CI_Contact/onlineResource/CI_OnlineResource/{{lw_path}}',
    RASTER_INFO: '{_srinfo_grid_dim}/{{ri_path}}',
    '_ri_num_dims': '{_srinfo_grid_rep}/numberOfDimensions/Integer',
    'other_citation_info': '{_idinfo_citation}/otherCitationDetails/CharacterString',
    'use_constraints': '{_idinfo}/resourceConstraints/MD_Constraints/useLimitation/CharacterString',
    DATES: '{_idinfo_extent}/temporalElement/EX_TemporalExtent/extent/{{type_path}}',
    KEYWORDS_PLACE: '{_idinfo_keywords}/keyword/CharacterString',
    KEYWORDS_STRATUM: '{_idinfo_keywords}/keyword/CharacterString',
    KEYWORDS_TEMPORAL: '{_idinfo_keywords}/keyword/CharacterString',
    KEYWORDS_THEME: '{_idinfo_keywords}/keyword/CharacterString'
}

# Apply XPATH root formats to the basic data map formats
ISO_TAG_FORMATS.update(ISO_TAG_ROOTS)
ISO_TAG_FORMATS.update(format_xpaths(ISO_TAG_FORMATS, **ISO_TAG_ROOTS))
ISO_TAG_FORMATS = FrozenOrderedDict(ISO_TAG_FORMATS)

ISO_TAG_PRIMITIVES = frozenset({
    'Binary', 'Boolean', 'CharacterString',
    'Date', 'DateTime', 'timePosition',
    'Decimal', 'Integer', 'Real', 'RecordType',
    'CI_DateTypeCode', 'MD_KeywordTypeCode', 'URL'
})


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
            raise InvalidContent('Invalid XML root for ISO-19115 standard: {root}', root=iso_root)

        iso_data_map = {'_root': iso_root}
        iso_data_map.update(ISO_TAG_ROOTS)
        iso_data_map.update(ISO_TAG_FORMATS)

        iso_data_structures = {}

        # Capture and format complex XPATHs

        ad_format = iso_data_map[ATTRIBUTES]
        ft_source = iso_data_map['_attr_src'].replace('/carrierOfCharacteristics/FC_FeatureAttribute', '')

        iso_data_structures[ATTRIBUTES] = format_xpaths(
            ISO_DEFINITIONS[ATTRIBUTES],

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
            ISO_DEFINITIONS[BOUNDING_BOX],
            east=bb_format.format(bbox_path='eastBoundLongitude/Decimal'),
            south=bb_format.format(bbox_path='southBoundLatitude/Decimal'),
            west=bb_format.format(bbox_path='westBoundLongitude/Decimal'),
            north=bb_format.format(bbox_path='northBoundLatitude/Decimal')
        )

        ct_format = iso_data_map[CONTACTS]
        iso_data_structures[CONTACTS] = format_xpaths(
            ISO_DEFINITIONS[CONTACTS],
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
        iso_data_structures[DATES][DATE_TYPE_RANGE] = [
            iso_data_structures[DATES][DATE_TYPE_RANGE_BEGIN],
            iso_data_structures[DATES][DATE_TYPE_RANGE_END]
        ]

        df_format = iso_data_map[DIGITAL_FORMS]
        iso_data_structures[DIGITAL_FORMS] = format_xpaths(
            ISO_DEFINITIONS[DIGITAL_FORMS],
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
        for keyword_prop in KEYWORD_PROPS:
            iso_data_structures[keyword_prop] = deepcopy(keywords_structure)

        lw_format = iso_data_map[LARGER_WORKS]
        iso_data_structures[LARGER_WORKS] = format_xpaths(
            ISO_DEFINITIONS[LARGER_WORKS],
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
            ISO_DEFINITIONS[PROCESS_STEPS],
            description=ps_format.format(ps_path='description/CharacterString'),
            date=ps_format.format(ps_path='dateTime/DateTime'),
            sources=ps_format.format(
                ps_path='source/LI_Source/sourceCitation/CI_Citation/alternateTitle/CharacterString'
            )
        )

        ri_format = iso_data_map[RASTER_INFO]
        iso_data_structures[RASTER_INFO] = format_xpaths(
            ISO_DEFINITIONS[RASTER_DIMS],
            type=ri_format.format(ri_path='dimensionName/MD_DimensionNameTypeCode'),
            _type=ri_format.format(ri_path='dimensionName/MD_DimensionNameTypeCode/@codeListValue'),
            size=ri_format.format(ri_path='dimensionSize/Integer'),
            value=ri_format.format(ri_path='resolution/Measure'),
            units=ri_format.format(ri_path='resolution/Measure/@uom')
        )

        # Assign XPATHS and gis_metadata.utils.ParserProperties to data map

        for prop, xpath in dict(iso_data_map).items():
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

            elif prop in KEYWORD_PROPS:
                iso_data_map[prop] = ParserProperty(self._parse_keywords, self._update_keywords)

            elif prop == RASTER_INFO:
                iso_data_map[prop] = ParserProperty(self._parse_raster_info, self._update_raster_info)

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

        return get_default_for_complex(prop, parsed_attributes)

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
            self._attr_details_file_url = None
            return None

        try:
            tree_to_parse = get_remote_element(self._attr_details_file_url)
        except Exception:
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

        content_delim = ISO_DIGITAL_FORMS_DELIM

        for digital_form in digital_forms:
            specs = reduce_value(digital_form['specification'])
            specs = specs.splitlines() if isinstance(specs, str) else specs

            specifications = wrap_value(s.strip() for s in specs)

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

        for idx in range(0, max(df_len, to_len)):
            digital_form = {}.fromkeys(ISO_DEFINITIONS[prop], u'')

            if idx < df_len:
                digital_form.update(i for i in digital_forms[idx].items() if i[1])
            if idx < to_len:
                digital_form.update(i for i in transfer_opts[idx].items() if i[1])

            if any(digital_form.values()):
                parsed_forms.append(digital_form)

        return get_default_for_complex(prop, parsed_forms)

    def _parse_keywords(self, prop):
        """ Parse type-specific keywords from the metadata: Theme or Place """

        keywords = []

        if prop in KEYWORD_PROPS:
            xpath_root = self._data_map['_keywords_root']
            xpath_map = self._data_structures[prop]

            xtype = xpath_map['keyword_type']
            xpath = xpath_map['keyword']
            ktype = KEYWORD_TYPES[prop]

            for element in get_elements(self._xml_tree, xpath_root):
                if get_element_text(element, xtype).lower() == ktype.lower():
                    keywords.extend(get_elements_text(element, xpath))

        return keywords

    def _parse_raster_info(self, prop=RASTER_INFO):
        """ Collapses multiple dimensions into a single raster_info complex struct """

        raster_info = {}.fromkeys(ISO_DEFINITIONS[prop], u'')

        # Ensure conversion of lists to newlines is in place
        raster_info['dimensions'] = get_default_for_complex_sub(
            prop=prop,
            subprop='dimensions',
            value=parse_property(self._xml_tree, None, self._data_map, '_ri_num_dims'),
            xpath=self._data_map['_ri_num_dims']
        )

        xpath_root = self._get_xroot_for(prop)
        xpath_map = self._data_structures[prop]

        for dimension in parse_complex_list(self._xml_tree, xpath_root, xpath_map, RASTER_DIMS):
            dimension_type = dimension['type'].lower()

            if dimension_type == 'vertical':
                raster_info['vertical_count'] = dimension['size']

            elif dimension_type == 'column':
                raster_info['column_count'] = dimension['size']
                raster_info['x_resolution'] = u' '.join(dimension[k] for k in ['value', 'units']).strip()

            elif dimension_type == 'row':
                raster_info['row_count'] = dimension['size']
                raster_info['y_resolution'] = u' '.join(dimension[k] for k in ['value', 'units']).strip()

        return raster_info if any(raster_info[k] for k in raster_info) else {}

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
        :see: gis_metadata.utils.COMPLEX_DEFINITIONS[DATES]
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
        :see: gis_metadata.utils.COMPLEX_DEFINITIONS[DIGITAL_FORMS]
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
                dist_spec.append(ISO_DIGITAL_FORMS_DELIM)
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

        if prop in KEYWORD_PROPS:
            xpath_root = self._data_map['_keywords_root']
            xpath_map = self._data_structures[prop]

            xtype = xpath_map['keyword_type']
            xroot = xpath_map['keyword_root']
            xpath = xpath_map['keyword']
            ktype = KEYWORD_TYPES[prop]

            # Remove descriptiveKeyword nodes according to type
            for element in get_elements(tree_to_update, xpath_root):
                if get_element_text(element, xtype).lower() == ktype.lower():
                    remove_element(tree_to_update, xpath_root)

            element = insert_element(tree_to_update, 0, xpath_root)
            insert_element(element, 0, xtype, ktype)  # Add the type node

            keywords.extend(update_property(element, xroot, xpath, prop, values))

        return keywords

    def _update_raster_info(self, **update_props):
        """ Derives multiple dimensions from a single raster_info complex struct """

        tree_to_update = update_props['tree_to_update']
        prop = update_props['prop']
        values = update_props.pop('values')

        # Update number of dimensions at raster_info root (applies to all dimensions below)

        xroot, xpath = None, self._data_map['_ri_num_dims']
        raster_info = [update_property(tree_to_update, xroot, xpath, prop, values.get('dimensions', u''))]

        # Derive vertical, longitude, and latitude dimensions from raster_info

        xpath_root = self._get_xroot_for(prop)
        xpath_map = self._data_structures[prop]

        v_dimension = {}
        if values.get('vertical_count'):
            v_dimension = v_dimension.fromkeys(xpath_map, u'')
            v_dimension['type'] = 'vertical'
            v_dimension['size'] = values.get('vertical_count', u'')

        x_dimension = {}
        if values.get('column_count') or values.get('x_resolution'):
            x_dimension = x_dimension.fromkeys(xpath_map, u'')
            x_dimension['type'] = 'column'
            x_dimension['size'] = values.get('column_count', u'')
            x_dimension['value'] = values.get('x_resolution', u'')

        y_dimension = {}
        if values.get('row_count') or values.get('y_resolution'):
            y_dimension = y_dimension.fromkeys(xpath_map, u'')
            y_dimension['type'] = 'row'
            y_dimension['size'] = values.get('row_count', u'')
            y_dimension['value'] = values.get('y_resolution', u'')

        # Update derived dimensions as complex list, and append affected elements for return

        update_props['prop'] = RASTER_DIMS
        update_props['values'] = [v_dimension, x_dimension, y_dimension]

        raster_info += update_complex_list(xpath_root=xpath_root, xpath_map=xpath_map, **update_props)

        return raster_info

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

        for prop, xpath in self._data_map.items():
            if not prop.startswith('_') or prop.strip('_') in supported_props:
                # Send only public or alternate properties
                xroot = self._trim_xpath(xpath, prop)
                values = getattr(self, prop, u'')
                update_property(tree_to_update, xroot, xpath, prop, values, supported_props)

        return tree_to_update

    def _trim_xpath(self, xpath, prop):
        """ Removes primitive type tags from an XPATH """

        xroot = self._get_xroot_for(prop)

        if xroot is None and isinstance(xpath, str):
            xtags = xpath.split(XPATH_DELIM)

            if xtags[-1] in ISO_TAG_PRIMITIVES:
                xroot = XPATH_DELIM.join(xtags[:-1])

        return xroot
