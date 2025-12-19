from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import MOVIE_URL

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie Title",
        "description": "Sample Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@mail.ts",
            password="test12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        sample_movie()
        movie_test_1 = sample_movie()
        movie_test_2 = sample_movie()
        genre_1 = Genre.objects.create(name="Horror")
        genre_2 = Genre.objects.create(name="Sci-fi")
        movie_test_1.genres.add(genre_1)
        movie_test_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filtered_movies_by_actors(self):
        movie_test = sample_movie()
        movie_test_1 = sample_movie(title="Test 1")
        movie_test_2 = sample_movie(title="Test 2")

        actor_1 = Actor.objects.create(
            first_name="Jack",
            last_name="Nicholson")
        actor_2 = Actor.objects.create(
            first_name="Leonardo",
            last_name="DiCaprio"
        )

        movie_test_1.actors.add(actor_1)
        movie_test_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"},
        )

        serializer_without_actors = MovieListSerializer(movie_test)
        serializer_1 = MovieListSerializer(movie_test_1)
        serializer_2 = MovieListSerializer(movie_test_2)

        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(
            serializer_without_actors.data, res.data)

    def test_filtered_movies_by_genres(self):
        movie_test = sample_movie()
        movie_test_1 = sample_movie(title="Test 1")
        movie_test_2 = sample_movie(title="Test 2")

        genre_1 = Genre.objects.create(name="Horror")
        genre_2 = Genre.objects.create(name="Sci-fi")

        movie_test_1.genres.add(genre_1)
        movie_test_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"},
        )

        serializer_without_genres = MovieListSerializer(movie_test)
        serializer_1 = MovieListSerializer(movie_test_1)
        serializer_2 = MovieListSerializer(movie_test_2)

        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(
            serializer_without_genres.data, res.data)


    def test_filtered_movies_by_genres(self):
        movie_test = sample_movie()
        movie_test_1 = sample_movie(title="Test 1")

        res = self.client.get(
            MOVIE_URL,
            {"title": "Test 1"},
        )

        serializer_ = MovieListSerializer(movie_test)
        serializer_1 = MovieListSerializer(movie_test_1)

        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(
            serializer_.data, res.data)

    def test_retrieve_movie_details(self):
        movie_test = sample_movie()
        movie_test.actors.add(
            Actor.objects.create(
                first_name="Leonardo",last_name="DiCaprio"))
        movie_test.genres.add(
            Genre.objects.create(name="Horror"))

        url = detail_url(movie_test.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie_test)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test 1",
            "description": "Test description",
            "duration": 123,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@mail.ts",
            password="test12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test 1",
            "description": "Test description",
            "duration": 123,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        genre = Genre.objects.create(name="Horror")
        actor_1 = Actor.objects.create(
            first_name="Jack",
            last_name="Nicholson")
        actor_2 = Actor.objects.create(
            first_name="Leonardo",
            last_name="DiCaprio"
        )
        payload = {
            "title": "Test 1",
            "description": "Test description",
            "duration": 123,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
