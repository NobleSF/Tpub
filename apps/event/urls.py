from django.urls import path

# from apps.source.models import Source
from apps.event.views import EventPage


app_name = "event"

urlpatterns = [

    # path('table_as_view/', Table.as_view(auto__model=Source)),
    path('', EventsPage().as_view()),

]
