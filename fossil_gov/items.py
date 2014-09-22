# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class FossilGovItem(scrapy.Item):
    applicant = scrapy.Field()
    application_detail = scrapy.Field()
    docket_number = scrapy.Field()
    exp_date = scrapy.Field()
    filed_date = scrapy.Field()
    import_export_status = scrapy.Field()
    init_date = scrapy.Field()
    issue_date = scrapy.Field()
    order_number = scrapy.Field()
    status = scrapy.Field()
    term = scrapy.Field()
