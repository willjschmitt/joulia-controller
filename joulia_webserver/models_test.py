"""Tests for joulia_webserver.models module."""

import unittest

from joulia_webserver import models
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
        volume = 5.0
        pre_boil_volume_gallons = 6.0
        post_boil_volume_gallons = 5.1
        recipe = Recipe(
            pk, strike_temperature, mashout_temperature, mashout_time,
            boil_time, cool_temperature, mash_temperature_profile, volume,
            pre_boil_volume_gallons, post_boil_volume_gallons)
        self.assertEquals(recipe.pk, pk)
        self.assertEquals(recipe.strike_temperature, strike_temperature)
        self.assertEquals(recipe.mashout_temperature, mashout_temperature)
        self.assertEquals(recipe.boil_time, boil_time)
        self.assertEquals(recipe.cool_temperature, cool_temperature)
        self.assertEquals(
            recipe.mash_temperature_profile, mash_temperature_profile)
        self.assertEquals(recipe.volume, volume)
        self.assertEquals(
            recipe.pre_boil_volume_gallons, pre_boil_volume_gallons)
        self.assertEquals(
            recipe.post_boil_volume_gallons, post_boil_volume_gallons)


class TestRecipeInstance(unittest.TestCase):
    """Tests RecipeInstance model."""

    def test_constructor(self):
        pk = 10
        recipe_pk = 3
        recipe_instance = RecipeInstance(pk, recipe_pk)
        self.assertEquals(recipe_instance.pk, pk)
        self.assertEquals(recipe_instance.recipe_pk, recipe_pk)


class TestMashStep(unittest.TestCase):
    """Tests MashStep."""

    def test_eq(self):
        duration = 60.0
        temperature = 155.0
        a = models.MashStep(duration, temperature)
        b = models.MashStep(duration, temperature)
        self.assertEqual(a, b)

    def test_not_eq(self):
        duration1 = 60.0
        duration2 = 180.0
        temperature = 155.0
        a = models.MashStep(duration1, temperature)
        b = models.MashStep(duration2, temperature)
        self.assertNotEqual(a, b)

    def test_str(self):
        got = str(models.MashStep(60.0, 155.0))
        want = "Duration: 60.0sec, Temperature: 155.0degF"
        self.assertEqual(got, want)


class TestMashPoint(unittest.TestCase):
    """Tests MashPoint."""

    def test_eq(self):
        time = 60.0
        temperature = 155.0
        a = models.MashPoint(time, temperature)
        b = models.MashPoint(time, temperature)
        self.assertEqual(a, b)

    def test_not_eq(self):
        time1 = 60.0
        time2 = 180.0
        temperature = 155.0
        a = models.MashPoint(time1, temperature)
        b = models.MashPoint(time2, temperature)
        self.assertNotEqual(a, b)

    def test_str(self):
        got = str(models.MashPoint(0.0, 155.0))
        want = "Time: 0.0sec, Temperature: 155.0degF"
        self.assertEqual(got, want)

    def test_absolute_temperature_profile(self):
        mash_step_1 = models.MashStep(15.0, 150.0)
        mash_step_2 = models.MashStep(45.0, 155.0)
        mash_steps = (mash_step_1, mash_step_2)
        got = models.MashPoint.absolute_temperature_profile(mash_steps)
        want = [
            models.MashPoint(0.0, 150.0),
            models.MashPoint(15.0, 150.0),
            models.MashPoint(15.0, 155.0),
            models.MashPoint(60.0, 155.0),
        ]
        self.assertEqual(got, want)
