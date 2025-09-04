from django.shortcuts import render
from .models import Movie

def movie_list(request):
    # Get all movies from the database
    movies = Movie.objects.all()
    return render(request, 'theater/movie_list.html', {'movies': movies})
from django.shortcuts import render

def theater_zone(request):
    # Add your logic or context here if needed
    return render(request, 'theater/theater_zone.html')

def box_office(request):
    return render(request, 'theater/box_office.html')


