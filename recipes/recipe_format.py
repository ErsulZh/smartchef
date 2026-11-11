import json


class RecipeFormatError(ValueError):
    pass


def parse_recipe_json(raw):
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 3000:
        raise RecipeFormatError("Recipe response is empty or too long.")
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        recipe = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RecipeFormatError("Recipe is not valid JSON.") from exc
    if not isinstance(recipe, dict) or set(recipe) != {"title", "ingredients", "steps"}:
        raise RecipeFormatError("Recipe must contain only title, ingredients and steps.")
    title, ingredients, steps = recipe["title"], recipe["ingredients"], recipe["steps"]
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise RecipeFormatError("Recipe title is invalid.")
    if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 24:
        raise RecipeFormatError("Recipe ingredients are invalid.")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise RecipeFormatError("Recipe steps are invalid.")
    if any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 200 for item in ingredients):
        raise RecipeFormatError("Recipe ingredients are invalid.")
    if any(not isinstance(item, str) or not item.strip() or len(item.strip()) > 120 for item in steps):
        raise RecipeFormatError("Recipe steps are invalid.")
    return {"title": title.strip(), "ingredients": [item.strip() for item in ingredients], "steps": [item.strip() for item in steps]}


def recipe_to_text(recipe):
    ingredients = "\n".join(f"• {item}" for item in recipe["ingredients"])
    steps = "\n".join(f"{number}. {item}" for number, item in enumerate(recipe["steps"], 1))
    return f"{recipe['title']}\n\nИнгредиенты:\n{ingredients}\n\nШаги:\n{steps}"
