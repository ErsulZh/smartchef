import json

from django.test import SimpleTestCase

from .recipe_format import RecipeFormatError, parse_recipe_json, recipe_to_text


class RecipeFormatTests(SimpleTestCase):
    def test_valid_recipe_is_accepted(self):
        recipe = parse_recipe_json(json.dumps({"title": "Омлет", "ingredients": ["Яйца"], "steps": ["Взбейте яйца."]}))
        self.assertEqual(recipe["title"], "Омлет")
        self.assertIn("Ингредиенты", recipe_to_text(recipe))

    def test_extra_key_is_rejected(self):
        with self.assertRaises(RecipeFormatError):
            parse_recipe_json('{"title":"x","ingredients":["a"],"steps":["b"],"extra":true}')
