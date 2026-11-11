import uuid
import logging
from pathlib import Path

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from dotenv import dotenv_values
from google import genai

from .catalog import CATEGORIES, PRODUCTS, build_products
from .models import SavedRecipe
from .recipe_format import RecipeFormatError, parse_recipe_json, recipe_to_text


logger = logging.getLogger(__name__)


def log_gemini_failure(error, api_key=""):
    """Store a short, redacted local diagnostic for the development server."""
    message = str(error).replace(api_key, "<redacted>").replace("\n", " ")[:500]
    line = f"{type(error).__name__}: {message}\n"
    logger.error("Gemini request failed: %s", line.strip())
    try:
        with (Path(settings.BASE_DIR) / "smartchef_debug.log").open("a", encoding="utf-8") as log_file:
            log_file.write(line)
    except OSError:
        pass


TEXT = {
    "kk": {
        "invalid_minutes": "Дайындау уақытын дұрыс таңдаңыз.",
        "missing_key": ".env файлын GEMINI_API_KEY мәнімен толтырыңыз.",
        "api_error": "Рецептті алу мүмкін болмады. Кейінірек қайталап көріңіз.",
        "api_timeout": "Gemini API 15 секунд ішінде жауап бермеді. Интернетті немесе кейінірек қайталап көріңіз.",
        "empty_recipe": "Gemini рецепт қайтармады. Кейінірек қайталап көріңіз.",
        "invalid_format": "Gemini рецепт пішімін дұрыс қайтармады. Кейінірек қайталап көріңіз.",
        "vegetarian_yes": "иә",
        "vegetarian_no": "жоқ",
    },
    "ru": {
        "invalid_minutes": "Выберите корректное время приготовления.",
        "missing_key": "Заполните GEMINI_API_KEY в файле .env.",
        "api_error": "Не удалось получить рецепт. Попробуйте позже.",
        "api_timeout": "Gemini API не ответил за 15 секунд. Проверьте интернет или попробуйте позже.",
        "empty_recipe": "Gemini не вернул рецепт. Попробуйте позже.",
        "invalid_format": "Gemini вернул рецепт в неверном формате. Попробуйте позже.",
        "vegetarian_yes": "да",
        "vegetarian_no": "нет",
    },
}


def index(request):
    language = request.GET.get("language", "kk")
    language = language if language in TEXT else "kk"
    products = ""
    minutes = "30"
    vegetarian = False
    recipe = ""
    error = ""
    can_save = False
    selected_products = []

    if request.method == "POST":
        language = request.POST.get("language", "kk")
        language = language if language in TEXT else "kk"
        products = request.POST.get("products", "")
        minutes = request.POST.get("minutes", "30")
        vegetarian = request.POST.get("vegetarian") == "1"
        raw_ids = request.POST.getlist("selected_products")
        selected_products = list(dict.fromkeys(raw_ids))
        action = request.POST.get("action", "")

        if action == "language":
            request.session.pop("smartchef_draft", None)
            request.session.pop("smartchef_cooking_draft", None)
            try:
                selected_products, _ = build_products(selected_products, products, language)
            except ValueError:
                selected_products = [item for item in selected_products if item in {p["id"] for p in PRODUCTS}]
        elif action == "generate":
            request.session.pop("smartchef_draft", None)
            request.session.pop("smartchef_cooking_draft", None)
            if minutes not in {"15", "30", "60"}:
                error = TEXT[language]["invalid_minutes"]
            else:
                try:
                    selected_products, combined = build_products(selected_products, products, language)
                except ValueError as exc:
                    error = str(exc)
                else:
                    config = dotenv_values(settings.BASE_DIR / ".env")
                    api_key = (config.get("GEMINI_API_KEY") or "").strip()
                    model = (config.get("GEMINI_MODEL") or "").strip() or "gemini-3.8-flash"
                    if not api_key or api_key == "PASTE_YOUR_KEY_HERE":
                        error = TEXT[language]["missing_key"]
                    else:
                        language_name = "қазақ тілі" if language == "kk" else "русский язык"
                        vegetarian_text = TEXT[language]["vegetarian_yes"] if vegetarian else TEXT[language]["vegetarian_no"]
                        prompt = (
                            f"Жауапты тек {language_name} тілінде бер. Бір ғана рецепт жаса.\n"
                            f"Өнімдер: {combined}\nДайындау уақыты: {minutes} минут\n"
                            f"Вегетариандық шектеу: {vegetarian_text}\n\n"
                            "Return only JSON with exactly title, ingredients and steps. Title: 1-120 characters; "
                            "ingredients: 1-24 nonempty strings; steps: 1-12 nonempty strings. No markdown."
                        )
                        try:
                            client = genai.Client(api_key=api_key)
                            interaction = client.interactions.create(model=model, input=prompt, timeout=15)
                            raw_recipe = (interaction.output_text or "").strip()
                            if not raw_recipe:
                                error = TEXT[language]["empty_recipe"]
                            else:
                                structured_recipe = parse_recipe_json(raw_recipe)
                                recipe = recipe_to_text(structured_recipe)
                                request.session["smartchef_draft"] = {
                                    "token": str(uuid.uuid4()), "products": combined, "recipe": recipe,
                                    "language": language, "minutes": int(minutes), "vegetarian": vegetarian,
                                }
                                request.session["smartchef_cooking_draft"] = structured_recipe
                                return redirect(f"{reverse('recipes:cooking')}?language={language}")
                        except RecipeFormatError as exc:
                            logger.info("Gemini response format rejected: %s", exc)
                            log_gemini_failure(exc)
                            error = TEXT[language]["invalid_format"]
                        except Exception as exc:
                            log_gemini_failure(exc, api_key)
                            error = TEXT[language]["api_timeout"] if "timed out" in str(exc).lower() else TEXT[language]["api_error"]

    return render(request, "recipes/index.html", {
        "language": language, "products": products, "minutes": minutes,
        "vegetarian": vegetarian, "recipe": recipe, "error": error, "can_save": can_save,
        "categories": CATEGORIES, "catalog_products": PRODUCTS, "selected_products": selected_products,
        "catalog_data": {"categories": CATEGORIES, "products": PRODUCTS, "language": language},
    })


@require_POST
def save_recipe(request):
    draft = request.session.get("smartchef_draft")
    if not draft:
        return redirect("recipes:index")
    SavedRecipe.objects.get_or_create(token=draft["token"], defaults={
        "products": draft["products"], "recipe": draft["recipe"], "language": draft["language"],
        "minutes": draft["minutes"], "vegetarian": draft["vegetarian"],
    })
    language = draft["language"] if draft["language"] in TEXT else "kk"
    return redirect(f"{reverse('recipes:saved_recipes')}?language={language}")


def saved_recipes(request):
    language = request.GET.get("language", "kk")
    language = language if language in TEXT else "kk"
    return render(request, "recipes/saved.html", {"saved_recipes": SavedRecipe.objects.all(), "language": language})


def cooking(request):
    language = request.GET.get("language", "kk")
    language = language if language in TEXT else "kk"
    recipe = request.session.get("smartchef_cooking_draft")
    if not recipe:
        return redirect(f"{reverse('recipes:index')}?language={language}")
    return render(request, "recipes/cooking.html", {"language": language, "recipe": recipe})
