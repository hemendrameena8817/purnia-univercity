"""
Reusable pagination classes for PG app
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with 50 items per page.
    Can be customized via query parameters.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for large datasets with 100 items per page.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for small datasets with 20 items per page.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
