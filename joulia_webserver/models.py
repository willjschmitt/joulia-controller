"""Client side representations of the joulia-webserver database models."""

import logging

import numpy as np


LOGGER = logging.getLogger(__name__)


class RecipeInstance(object):
    """A client side representation of a brewery.RecipeInstance database model.

    Attributes:
        pk: Primary key/id for the RecipeInstance.
        recipe_pk: Foreign key for the id of the Recipe this RecipeInstance
            implements.
    """

    def __init__(self, pk, recipe_pk):
        self.pk = pk
        self.recipe_pk = recipe_pk

    @classmethod
    def from_joulia_webserver_response(cls, response):
        """Converts a json serialized RecipeInstance instance into a local
        Python RecipeInstance instance.

        Args:
            response: The data received from Joulia webserver containing
                RecipeInstance instance attributes.
        """
        pk = response['id']
        recipe_pk = response['recipe']
        return cls(pk, recipe_pk)


class Recipe(object):
    """A client side representation of the brewery.Recipe database model.

    Attributes:
        pk: Primary key/id for the recipe instance.
        strike_temperature: Temperature to heat the Hot Liquor Tun to prior to
            mash strike. Units: degrees Fahrenheit.
        mashout_temperature: Temperature to raise the wort to after the mash.
            Units: degrees Fahrenheit.
        mashout_time: Time to hold the wort at the ``mashout_temperature``.
            Units: seconds.
        boil_time: Time to hold the temperature at a boil. Units: seconds.
        boil_temperature: Temperature to consider as boiling.
        cool_temperature: Temperature to cool the boiled wort down to after the
            boil is complete. Units: degrees Fahrenheit.
        mash_temperature_profile: Mash points as an array of (duration,
            temperature) pairs.
        volume: Amount of beer to be brewed. Units: gallons.
        pre_boil_volume_gallons: Amount of wort expected to enter into the boil
            kettle.
        post_boil_volume_gallons: Amount of wort expected to exit the boil
            kettle and enter fermenter. This - `pre_boil_volume_gallons`
            influences the boil off power during boil.
    """

    def __init__(self, pk, strike_temperature, mashout_temperature,
                 mashout_time, boil_time, cool_temperature,
                 mash_temperature_profile, volume, pre_boil_volume_gallons,
                 post_boil_volume_gallons):
        self.pk = pk
        self.strike_temperature = strike_temperature
        self.mashout_temperature = mashout_temperature
        self.mashout_time = mashout_time
        self.boil_time = boil_time
        self.boil_temperature = 217.0
        self.cool_temperature = cool_temperature
        self.mash_temperature_profile = mash_temperature_profile

        self.volume = volume
        self.pre_boil_volume_gallons = pre_boil_volume_gallons
        self.post_boil_volume_gallons = post_boil_volume_gallons

    @classmethod
    def from_joulia_webserver(cls, recipe_response, mash_temperature_profile):
        """Converts a json serialized Recipe instance into a local python
        Recipe instance.

        Args:
            recipe_response: The data received from Joulia webserver
                containing Recipe instance attributes.
            mash_temperature_profile: The mash profile associated with the
                recipe.
        """
        pk = recipe_response["id"]
        strike_temperature = recipe_response["strike_temperature"]
        mashout_temperature = recipe_response["mashout_temperature"]
        mashout_time = recipe_response["mashout_time"]
        boil_time = recipe_response["boil_time"]
        cool_temperature = recipe_response["cool_temperature"]

        volume = recipe_response["volume"]
        pre_boil_volume_gallons = recipe_response["pre_boil_volume_gallons"]
        post_boil_volume_gallons = recipe_response["post_boil_volume_gallons"]
        return cls(pk, strike_temperature, mashout_temperature, mashout_time,
                   boil_time, cool_temperature, mash_temperature_profile,
                   volume, pre_boil_volume_gallons, post_boil_volume_gallons)


class MashProfile(object):
    """A set of mash points in a mash temperature profile.

    Contains the individual mash points as duration, temperature pairs as well
    as conveniences for accessing the temperatures as times along a profile.

    Attributes:
        _mash_steps: The underlying duration, temperature MashSteps.
        _mash_points: The time, temperature MashPoints calculated from
            _mash_steps.
    """

    def __init__(self, mash_steps):
        self._mash_steps = mash_steps
        self._mash_points = MashPoint.absolute_temperature_profile(mash_steps)

    def __getitem__(self, index):
        """Provides simple subscripting of the underlying mash steps.

        Indexes by step number.
        """
        return self._mash_steps[index]

    def __len__(self):
        return len(self._mash_steps)

    def temperature_at_time(self, time_in_profile):
        """Gets the temperature current time relative to the start.

        Converts the duration, temp to time from start, temp and retrieves the
        temperature at the time.

        Args:
            time_in_profile: The time to reference as the beginning of the
                profile.
        """
        LOGGER.info('Getting temperature at time %s.', time_in_profile)
        assert time_in_profile >= 0.0
        assert time_in_profile <= self.temperature_profile_length

        times = [point.time for point in self._mash_points]
        temps = [point.temperature for point in self._mash_points]
        return np.interp(time_in_profile, times, temps)

    @property
    def temperature_profile_length(self):
        """The total amount of time prescribed in the temperature profile."""
        if not self._mash_points:
            return 0.0
        return self._mash_points[-1].time


class MashStep(object):
    """A single mash step in a mash profile.

    Attributes:
        duration: The amount of time to hold the temperature at. Units: Seconds.
        temperature: The temperature to hold the mash at. Units: Degrees F.
    """

    def __init__(self, duration, temperature):
        self.duration = duration
        self.temperature = temperature

    def __eq__(self, other):
        return (
            self.duration == other.duration
            and self.temperature == other.temperature
        )

    def __str__(self):
        return "Duration: {}sec, Temperature: {}degF".format(
            self.duration, self.temperature)


class MashPoint(object):
    """A single mash point defining the temperature at a specific time.

    This contrasts with MashStep, which references duration. For example,
    MashSteps: (15min, 150deg), (45min, 155deg), translates to a _MashPoint
    representation of: (0min, 150deg), (15min, 150deg), (15min, 155deg),
    (60min, 155deg).

    Attributes:
        time: The time in a profile. Units: Seconds.
        temperature: The temperature to hold the mash at. Units: Degrees F.
    """

    def __init__(self, time, temperature):
        self.time = time
        self.temperature = temperature

    def __eq__(self, other):
        return (
            self.time == other.time
            and self.temperature == other.temperature
        )

    def __str__(self):
        return "Time: {}sec, Temperature: {}degF".format(
            self.time, self.temperature)

    @staticmethod
    def absolute_temperature_profile(mash_steps):
        """Creates a temperature profile of MashPoints from MashStesps.

        Creates profile, where the times are relative to start rather than the
        lengths of time for each segment. An additional segment at the end is
        added with None for the temperature, indicating the end.

        That is, `[(15.0, 150.), (15.0, 155.0)]` becomes
        `[(0.0, 150.0), (15.0, 155.0), (30.0, None)]`.
        """
        current_time = 0.0
        profile = []
        for i, step in enumerate(mash_steps):
            start_point = MashPoint(current_time, step.temperature)
            profile.append(start_point)
            current_time += step.duration
            end_point = MashPoint(current_time, step.temperature)
            profile.append(end_point)
        return profile
