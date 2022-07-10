"""
Tests for the tags API.
"""
from decimal import Decimal

from core.models import Recipe, Tag
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import TagSerializer
from rest_framework import status
from rest_framework.test import APIClient

TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return a tag detail url."""
    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="user@example.com", password="testpass123"):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class PublicTagsAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""
        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags."""
        for name in ["Vegan", "Dessert", "Drinks"]:
            Tag.objects.create(user=self.user, name=name)

        response = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""
        user = create_user(email="testuser@example.com")
        Tag.objects.create(user=user, name="Fruity")
        tag = Tag.objects.create(user=self.user, name="Comfort Food")

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], tag.name)
        self.assertEqual(response.data[0]["id"], tag.id)

    def test_update_tag(self):
        """Test updating a tag."""
        tag = Tag.objects.create(user=self.user, name="After Dinner")

        payload = {"name": "Dessert"}
        url = detail_url(tag.id)
        response = self.client.patch(url, payload)

        tag.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Test deleting a tag."""
        tag = Tag.objects.create(user=self.user, name="After Dinner")

        url = detail_url(tag.id)
        response = self.client.delete(url)

        tags = Tag.objects.filter(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name="Breakfast")
        tag2 = Tag.objects.create(user=self.user, name="Dinner")
        recipe = Recipe.objects.create(
            title="Green Eggs on Toast",
            time_minutes=10,
            price=Decimal("2.50"),
            user=self.user,
        )
        recipe.tag.add(tag1)

        response = self.client.get(TAGS_URL, {"assigned_only": 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, response.data)
        self.assertNotIn(s2.data, response.data)

    def test_filter_tags_unique(self):
        """Test filtered tags returns a unique list."""
        tag = Tag.objects.create(user=self.user, name="Breakfast")
        Tag.objects.create(user=self.user, name="Dinner")
        recipe1 = Recipe.objects.create(
            title="Eggs Benedict",
            time_minutes=60,
            price=Decimal("4.00"),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title="Eggs Herbs",
            time_minutes=10,
            price=Decimal("7.00"),
            user=self.user,
        )

        recipe1.tag.add(tag)
        recipe2.tag.add(tag)

        response = self.client.get(TAGS_URL, {"assigned_only": 1})

        self.assertEqual(len(response.data), 1)
