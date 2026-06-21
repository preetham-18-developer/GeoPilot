import pytest
from app.crawler.spider import WebsiteSpider

def test_domain_locking_strictness():
    # Setup spider with thelibrarycompany.com
    spider = WebsiteSpider(project_id="test-proj-id", website_url="https://thelibrarycompany.com")
    
    # Internal URLs
    assert spider.is_internal_url("https://thelibrarycompany.com") is True
    assert spider.is_internal_url("https://thelibrarycompany.com/about") is True
    assert spider.is_internal_url("https://www.thelibrarycompany.com/contact") is True
    assert spider.is_internal_url("/collections") is True
    
    # External URLs (even similarly named)
    assert spider.is_internal_url("https://librarycompany.org") is False
    assert spider.is_internal_url("https://librarycompany.org/about") is False
    assert spider.is_internal_url("https://google.com") is False
    assert spider.is_internal_url("https://thelibrarycompany.com.external.com") is False

def test_clean_url_strips_garbage():
    spider = WebsiteSpider(project_id="test-proj-id", website_url="https://thelibrarycompany.com")
    
    assert spider.clean_url("https://thelibrarycompany.com/about?ref=search#section") == "https://thelibrarycompany.com/about"
    assert spider.clean_url("https://thelibrarycompany.com/collections?page=2") == "https://thelibrarycompany.com/collections"
