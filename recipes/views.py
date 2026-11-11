import uuid

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from dotenv import dotenv_values
from google import genai

from .catalog import CATEGORIES, PRODUCTS, build_products
from .models import SavedRecipe


TEXT = {
    "kk": {
        "invalid_minutes": "Дайындау уақытын дұрыс таңдаңыз.",
        "missing_key": ".env файлын GEMINI_API_KEY мәнімен толтырыңыз.",
        "api_error": "Рецептті алу мүмкін болмады. Кейінірек қайталап көріңіз.",
        "empty_recipe": "Gemini рецепт қайтармады. Кейінірек қайталап көріңіз.",
        "vegetarian_yes": "иә",
        "vegetarian_no": "жоқ",
    },
    "ru": {
        "invalid_minutes": "Выберите корректное время приготовления.",
        "missing_key": "Заполните GEMINI_API_KEY в файле .env.",
        "api_error": "Не удалось получить рецепт. Попробуйте позже.",
        "empty_recipe": "Gemini не вернул рецепт. Попробуйте позже.",
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
            try:
                selected_products, _ = build_products(selected_products, products, language)
            except ValueError:
                selected_products = [item for item in selected_products if item in {p["id"] for p in PRODUCTS}]
        elif action == "generate":
            request.session.pop("smartchef_draft", None)
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
                            "Мына бөлімдерді бер: рецепт атауы, дайындау уақыты, ингредиенттер, "
                            "нөмірленген қадамдар және бір кеңес."
                        )
                        try:
                            client = genai.Client(api_key=api_key)
                            interaction = client.interactions.create(model=model, input=prompt, timeout=30)
                            recipe = (interaction.output_text or "").strip()
                            if not recipe:
                                error = TEXT[language]["empty_recipe"]
                            else:
                                request.session["smartchef_draft"] = {
                                    "token": str(uuid.uuid4()), "products": combined, "recipe": recipe,
                                    "language": language, "minutes": int(minutes), "vegetarian": vegetarian,
                                }
                                can_save = True
                        except Exception:
                            error = TEXT[language]["api_error"]

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
