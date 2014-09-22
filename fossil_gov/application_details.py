import re
from datetime import datetime

import requests
from BeautifulSoup import BeautifulSoup

from fossil_gov import ROOT_URL


# TODO: How should DOE communicate with the Company?
# TODO: Multiple "Any/all Order and/or Docket numbers"
# TODO: Test comments against an application with actual comments
# TODO: Order Effective Date
# TODO: Current Order Number

# TODO: URLs that don't link to full applications


def combined_volume(text):
    return remove_extraneous_whitespace(text.split(':')[1]).strip()


def date_received(text):
    return datetime.strptime(text, '%B %d, %Y').date()


def had_or_have_order(text):
    return text.split('?')[1].strip()


def noop(text):
    return text


def split_on_colon(text):
    return text.split(':', 1)[1].strip()


def remove_extraneous_whitespace(string):
    return re.sub(r'\s+', ' ', string)


def requested_authorities(text):
    raw_authorities = text.strip('- ').split('- ')
    return [remove_extraneous_whitespace(authority)
            for authority in raw_authorities]


PERSON_MAPPING = {
    "First Name:": "first_name",
    "Last Name:": "last_name",
    "Middle Initial:": "middle_initial",
    "Position/Title:": "position_or_title",
    "Country:": "country",
    "Street:": "street",
    "City:": "city",
    "State/Province:": "state_or_province",
    "Zip/Postal Code:": "zip_or_postal_code",
    "Phone Number:": "phone_number",
    "Fax:": "fax_number",
    "Email:": "email",
}


class DetailParser(object):

    sections = {
        'Basic Company Information': ('basic_company_information', {
            'Name of the Applicant:': 'applicant_name',
            'Country in which company is located:':
                'country_in_which_company_is_located',
            'Type of Business Entity:': 'type_of_business_entity',
            'State/Province of Incorporation:':
                'state_or_province_of_incorporation',
            'Parent Company Name (if applicable):': 'parent_company_name',
        }),
        'Headquarters Contact Information': (
            'headquarters_contact_information', {
                "Street:": "street",
                "City:": "city",
                "State/Province:": "state_or_province",
                "Zip/Postal Code:": "zip_or_postal_code",
                "Phone Number:": "phone_number",
                "Fax Number:": "fax_number",
            }),
        'Principal Place of Business': ('principal_place_of_business', {
            "City:": "city",
            "State/Province:": "state_or_province",
            "Zip/Postal Code:": "zip_or_postal_code",
            "Country:": "country",
        }),
        'Applicant Contact (Application/Order/Service List) Information:': (
            'applicant_contact', PERSON_MAPPING),
        'Attorney Contact Information:': ('attorney_contact_information',
                                          PERSON_MAPPING),
        'Report Contact (Monthly Reports) Information:': (
            'report_contact_information', PERSON_MAPPING),
        'Application Comments & Other Info.': ('comments_and_other_info', {
            'Application Submitted By:': ('application_submitted_by',
                                          split_on_colon),
            'Comments:': ('comments', split_on_colon),
            'Application Tracking Number:': ('application_tracking_number',
                                             split_on_colon),
        }),

    }
    simple_translations = {
        'Date Received': ('date_received', date_received),
        'Docket:': ('docket', noop),
        'Requested Authorities:': ('requested_authorities',
                                   requested_authorities),
    }
    single_cell_translations = {
        'Combined Volume for all selected authorities:': (
            'combined_volume_for_all_selected_authorities', combined_volume),
        'Have you ever had or do you currently have an Order?': (
            'have_ever_had_or_currently_have_order', had_or_have_order),
        'Any/all Order and/or Docket numbers:': (
            'all_existing_order_or_docket_numbers', split_on_colon),
    }

    def __init__(self, rows):
        self.rows = rows
        self.current_section = None
        self.data = {}
        self.section_data = {}
        self.multi_line_key = None

    def _complete_section(self):
        if self.current_section:
            key, _ = self.current_section
            self.data[key] = self.section_data
            self.multi_line_key = None
        self.section_data = {}

    def _handle_one_column(self, row):
        text = row.find('td').text
        if text in self.sections:
            self._complete_section()
            self.current_section = self.sections[text]
            return
        for prefix in self.single_cell_translations:
            if text.startswith(prefix):
                key, transform = self.single_cell_translations[prefix]
                self.data[key] = transform(text)
        if self.current_section:
            for prefix in self.current_section[1]:
                if text.startswith(prefix):
                    key, transform = self.current_section[1][prefix]
                    self.section_data[key] = transform(text)

    def _handle_two_columns(self, row):
        left, right = row.findAll('td')
        left_text = left.text.strip()
        right_text = right.text.strip()
        if left_text in self.simple_translations:
            self.multi_line_key = None
            key, transform = self.simple_translations[left_text]
            self.data[key] = transform(right_text)
        elif left_text in self.current_section[1]:
            self.multi_line_key = None
            key = self.current_section[1][left_text]
            self.section_data[key] = right_text or None
            if key == 'street':
                self.multi_line_key = key
        elif left_text == '' and right_text != '' and self.multi_line_key:
            self.section_data[self.multi_line_key] += '\n{}'.format(right_text)

    def parse(self):
        for row in self.rows:
            if len(row.findAll('td')) == 1:
                self._handle_one_column(row)
            elif len(row.findAll('td')) == 2:
                self._handle_two_columns(row)
        self._complete_section()
        return self.data


def extract_application_detail_from_body(detail_body):
    detail_soup = BeautifulSoup(detail_body,
                                convertEntities=BeautifulSoup.HTML_ENTITIES)
    parser = DetailParser(detail_soup.findAll('tr'))
    return parser.parse()


def extract_application_detail(row):
    detail_url_soup = BeautifulSoup(row.xpath('.//a').extract()[0])
    detail_relative_url = detail_url_soup.find('a')['href']
    detail_url = extract_application_detail_from_body(
        '{}{}'.format(ROOT_URL, detail_relative_url))
    detail_response = requests.get(detail_url, verify=False)
    return extract_application_detail_from_body(detail_response.content)
