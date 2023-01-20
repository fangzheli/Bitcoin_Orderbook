from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('orderbook/api/', include('Orderbook.urls')),
    path('orderbook/', TemplateView.as_view(template_name='order_book.html')),
    path('admin/', admin.site.urls),
]
