from rest_framework.pagination import PageNumberPagination

class CalendarPagination(PageNumberPagination):
    page_size = 5  # ile elementów na stronę
    page_size_query_param = "page_size"
    max_page_size = 50

class ImagesPagination(PageNumberPagination):
    page_size = 20  # ile elementów na stronę
    page_size_query_param = "page_size"
    max_page_size = 50