from django.urls import path
from core import views  # ✅ Importing from core.views

urlpatterns = [
    path('theater-zone/', views.theater_zone, name='theater-zone'),
    path('box-office/', views.box_office, name='box-office'),
    path('lobby/', views.theater_lobby, name='theater-lobby'),
    path('entrance/', views.theater_entrance, name='theater-entrance'),
    path('stream/', views.theater_stream, name='theater-stream'),
    path('buy-ticket/<int:movie_id>/', views.buy_ticket, name='buy-ticket'),
    path('coming-soon/', views.coming_soon, name='coming-soon'),
    path('trailer/', views.trailer_view, name='trailer-view'),  # ✅ NEW route for trailer
]
