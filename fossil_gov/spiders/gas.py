from datetime import datetime

import scrapy

from fossil_gov.application_details import extract_application_detail
from fossil_gov.items import FossilGovItem


# TODO: Print out JSON lines


def extract_cell(column_number):
    def f(row):
        return row.xpath('normalize-space(td[{}])'.format(
            column_number))[0].extract().strip()
    return f


def extract_date_from_cell(column_number):
    def f(row):
        text = extract_cell(column_number)(row)
        if text:
            return datetime.strptime(text, '%d-%b-%Y').date()
        return None
    return f


def extract_order_number(row):
    number = int(extract_cell(3)(row)) or None
    status = extract_cell(5)(row)
    return {'number': number, 'status': status}


def extract_import_export_status(row):
    statuses = {
        'I': 'import',
        'E': 'export',
        'B': 'both',
    }
    cell = extract_cell(7)(row)
    if cell in statuses:
        return statuses[cell]
    return cell


def extract_term(row):
    terms = {
        'S': 'short-term',
        'L': 'long-term',
    }
    cell = extract_cell(8)(row)
    if cell in terms:
        return terms[cell]
    return cell


PARSERS = {
    'applicant': extract_cell(6),
    'application_detail': extract_application_detail,
    'docket_number': extract_cell(2),
    'exp_date': extract_date_from_cell(13),
    'filed_date': extract_date_from_cell(10),
    'import_export_status': extract_import_export_status,
    'init_date': extract_date_from_cell(12),
    'issue_date': extract_date_from_cell(11),
    'order_number': extract_order_number,
    'status': extract_cell(9),
    'term': extract_term,
}


class FossilGovScraper(scrapy.Spider):
    name = "fossil_gov"
    allowed_domains = ["app.fossil.energy.gov"]

    def _get_request(self, year):
        return scrapy.FormRequest(
            "https://app.fossil.energy.gov/app/fergas/DocketOrderList.go",
            formdata={
                'appFiledYear': unicode(year),
                'orderBy': 'docket',
                'ascOrder': 'false',
                'fromNum': unicode(self.from_num),
            },
            callback=self.parse,
        )

    def start_requests(self):
        self.from_num = 0
        return [self._get_request(2014)]

    def parse(self, response):
        if response.xpath('//a[contains(., ">>")]'):
            self.from_num += 50
            yield self._get_request(2014)
        for row in response.css('tr.RowLowlight,tr.RowHighlight'):
            item = FossilGovItem()
            for key in PARSERS:
                item[key] = PARSERS[key](row)
            yield item
