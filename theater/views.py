from django.shortcuts import get_object_or_404, render
from .models import Movie, MovieScreen


def theater_zone(request):
    screens = MovieScreen.objects.prefetch_related("movies").all()
    featured_movies = Movie.objects.filter(is_active=True, is_featured=True)[:5]
    premieres = Movie.objects.filter(is_active=True, is_premiere=True)[:5]

    return render(
        request,
        "theater/theater_zone.html",
        {
            "screens": screens,
            "featured_movies": featured_movies,
            "premieres": premieres,
        },
    )


def movie_list(request):
    movies = Movie.objects.filter(is_active=True).select_related("screen")
    return render(request, "theater/movie_list.html", {"movies": movies})


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie.objects.select_related("screen"), id=movie_id, is_active=True)
    return render(request, "theater/movie_detail.html", {"movie": movie})


def watch_movie(request, movie_id):
    movie = get_object_or_404(Movie.objects.select_related("screen"), id=movie_id, is_active=True)
    return render(request, "theater/watch_movie.html", {"movie": movie})


def box_office(request):
    movies = Movie.objects.filter(is_active=True).select_related("screen")
    return render(request, "theater/box_office.html", {"movies": movies})