"""Client side representations of the joulia-webserver database models."""


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
        cool_temperature: Temperature to cool the boiled wort down to after the
            boil is complete. Units: degrees Fahrenheit.
        mash_temperature_profile: Mash points as an array of (duration,
            temperature) pairs.
    """

    def __init__(self, pk, strike_temperature, mashout_temperature,
                 mashout_time, boil_time, cool_temperature,
                 mash_temperature_profile):
        self.pk = pk
        self.strike_temperature = strike_temperature
        self.mashout_temperature = mashout_temperature
        self.mashout_time = mashout_time
        self.boil_time = boil_time
        self.cool_temperature = cool_temperature
        self.mash_temperature_profile = mash_temperature_profile

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
        return cls(pk, strike_temperature, mashout_temperature, mashout_time,
                   boil_time, cool_temperature, mash_temperature_profile)