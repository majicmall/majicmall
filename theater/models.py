from django.db import models

# Movie Screen Model
class MovieScreen(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    sponsor = models.CharField(max_length=100, null=True, blank=True)
    screen_type = models.CharField(
        max_length=50,
        choices=[
            ('Majic', 'Majic'),
            ('Nostalgia', 'Nostalgia'),
            ('Fantasy', 'Fantasy'),
            ('Indie', 'Indie'),
            ('Experience', 'Experience')
        ]
    )
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# Movie Model
class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    release_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in minutes")
    image = models.ImageField(upload_to='movies/', null=True, blank=True)
    screen = models.ForeignKey(MovieScreen, on_delete=models.CASCADE)
    is_premiere = models.BooleanField(default=False)

    def __str__(self):
        return self.title
