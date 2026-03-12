from django.urls import path, include

urlpatterns = [
    path('chaining/', include('smart_selects.urls')),
    # ... outras urls
]
