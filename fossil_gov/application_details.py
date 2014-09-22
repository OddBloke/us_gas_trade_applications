from datetime import datetime

import requests
from BeautifulSoup import BeautifulSoup

from fossil_gov import ROOT_URL


# TODO: Requested Authorities
# TODO: Combined Volume for all selected authorities
# TODO: How should DOE communicate with the Company?
# TODO: Have you ever had or do you currently have an Order?
# TODO: Any/all Order and/or Docket numbers
# TODO: Application Submitted By
# TODO: Comments
# TODO: Application Tracking Number

# TODO: URLs that don't link to full applications


def noop(text):
    return text


def date_received(text):
    return datetime.strptime(text, '%B %d, %Y').date()


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
    }
    simple_translations = {
        'Date Received': ('date_received', date_received),
        'Docket:': ('docket', noop),
    }

    def __init__(self, rows):
        self.rows = rows
        self.current_section = None
        self.data = {}
        self.section_data = {}
        self.multi_line_key = None

    def _handle_one_column(self, row):
        text = row.find('td').text
        if text in self.sections:
            if self.current_section:
                key, _ = self.current_section
                self.data[key] = self.section_data
                self.multi_line_key = None
            self.section_data = {}
            self.current_section = self.sections[text]

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
            print self.section_data
            print right_text
            self.section_data[self.multi_line_key] += '\n{}'.format(right_text)

    def parse(self):
        for row in self.rows:
            if len(row.findAll('td')) == 1:
                self._handle_one_column(row)
            elif len(row.findAll('td')) == 2:
                self._handle_two_columns(row)
        return self.data


def extract_application_detail(row):
    detail_url_soup = BeautifulSoup(row.xpath('.//a').extract()[0])
    detail_relative_url = detail_url_soup.find('a')['href']
    detail_url = '{}{}'.format(ROOT_URL, detail_relative_url)
    detail_response = requests.get(detail_url, verify=False)
    detail_soup = BeautifulSoup(detail_response.content,
                                convertEntities=BeautifulSoup.HTML_ENTITIES)
    parser = DetailParser(detail_soup.findAll('tr'))
    return parser.parse()
