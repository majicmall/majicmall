from django.urls import path
from core import views as core_views
from . import views as theater_views

urlpatterns = [
    path("theater-zone/", core_views.theater_zone, name="theater-zone"),
    path("box-office/", core_views.box_office, name="box-office"),
    path("lobby/", core_views.theater_lobby, name="theater-lobby"),
    path("entrance/", core_views.theater_entrance, name="theater-entrance"),
    path("stream/", core_views.theater_stream, name="theater-stream"),
    path("buy-ticket/<int:movie_id>/", core_views.buy_ticket, name="buy-ticket"),
    path("ticket-success/<int:movie_id>/", core_views.ticket_success, name="ticket-success"),
    path("coming-soon/", core_views.coming_soon, name="coming-soon"),
    path("trailer/", core_views.trailer_view, name="trailer-view"),

    # New movie experience routes
    path("movies/", theater_views.movie_list, name="movie-list"),
    path("movies/<int:movie_id>/", theater_views.movie_detail, name="movie-detail"),
    path("movies/<int:movie_id>/watch/", theater_views.watch_movie, name="watch-movie"),
]
