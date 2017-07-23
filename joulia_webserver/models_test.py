"""Tests for joulia_webserver.models module."""

import unittest

from joulia_webserver.models import Recipe
from joulia_webserver.models import RecipeInstance


class TestRecipe(unittest.TestCase):
    """Tests Recipe model."""

    def test_constructor(self):
        pk = 3
        strike_temperature = 170.0
        mashout_temperature = 172.0
        mashout_time = 15 * 60
        boil_time = 60 * 60
        cool_temperature = 70.0
        mash_temperature_profile = []
        recipe = Recipe(
            pk, strike_temperature, mashout_temperature, mashout_time,
            boil_time, cool_temperature, mash_temperature_profile)
        self.assertEquals(recipe.pk, pk)
        self.assertEquals(recipe.strike_temperature, strike_temperature)
        self.assertEquals(recipe.mashout_temperature, mashout_temperature)
        self.assertEquals(recipe.boil_time, boil_time)
        self.assertEquals(recipe.cool_temperature, cool_temperature)
        self.assertEquals(recipe.mash_temperature_profile,
                          mash_temperature_profile)


class TestRecipeInstance(unittest.TestCase):
    """Tests RecipeInstance model."""

    def test_constructor(self):
        pk = 10
        recipe_pk = 3
        recipe_instance = RecipeInstance(pk, recipe_pk)
        self.assertEquals(recipe_instance.pk, pk)
        self.assertEquals(recipe_instance.recipe_pk, recipe_pk)
