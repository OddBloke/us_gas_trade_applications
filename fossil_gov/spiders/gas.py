from collections import namedtuple
from datetime import datetime

import scrapy

from fossil_gov.items import FossilGovItem


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


Order = namedtuple('Order', ('number', 'status'))


def extract_order_number(row):
    number = int(extract_cell(3)(row)) or None
    status = extract_cell(5)(row)
    return Order(number, status)


PARSERS = {
    'applicant': extract_cell(6),
    'docket_number': extract_cell(2),
    'filed_date': extract_date_from_cell(10),
    'issue_date': extract_date_from_cell(11),
    'order_number': extract_order_number,
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
