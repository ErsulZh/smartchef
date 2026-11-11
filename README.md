# SmartChef

Local Django learning project for selecting products, generating a Gemini recipe, saving it in SQLite, and following a validated recipe step by step.

## Branches

- `main` — verified SmartChef baseline.
- `feature/cooking-mode` — structured JSON recipe and cooking-mode work.

## T1–T8 checks

- T1: a valid generated recipe opens `/cooking/` and can be saved.
- T2: malformed JSON, an empty response, and missing draft are handled without saving a fake recipe.
- T3: the cooking page reads the current session draft only.
- T4–T5: previous and next buttons stay within the recipe steps.
- T6: saving uses the existing session draft and SQLite model.
- T7: Kazakh/Russian interface and responsive layout remain usable.
- T8: catalog, search, saving and Git tracking do not expose `.env`, SQLite or virtual environments.
