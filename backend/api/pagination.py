from rest_framework.pagination import PageNumberPagination
from  rest_framework.response import Response

class CalendarPagination(PageNumberPagination):
    page_size = 5  # ile elementów na stronę
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        next_page = self.get_next_link()
        return Response({
            'count': self.page.paginator.count,
            'next': next_page,
            'previous': self.get_previous_link(),
            'results': data,
            'has_more': bool(next_page),  # True jeśli jest kolejna strona
        })



class ImagesPagination(PageNumberPagination):
    page_size = 20  # ile elementów na stronę
    page_size_query_param = "page_size"
    max_page_size = 50

 
    def get_paginated_response(self, data):
        next_page = self.get_next_link()
        return Response({
            'count': self.page.paginator.count,
            'next': next_page,
            'previous': self.get_previous_link(),
            'results': data,
            'has_more': bool(next_page),  # True jeśli jest kolejna strona
        })