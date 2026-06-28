# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("DietHealthAdvisor")

# Sample Data
RECIPES = {
    "grilled salmon with asparagus": {
        "ingredients": [
            "150g Salmon fillet",
            "1 bunch Asparagus",
            "1 tbsp Olive oil",
            "1/2 Lemon",
            "Salt and black pepper to taste"
        ],
        "instructions": (
            "1. Preheat grill to medium-high heat.\n"
            "2. Brush salmon and asparagus with olive oil, then season with salt and pepper.\n"
            "3. Grill salmon for 4-5 minutes per side until cooked through.\n"
            "4. Grill asparagus for 3-5 minutes until tender-crisp.\n"
            "5. Serve with squeezed lemon juice."
        )
    },
    "quinoa salad": {
        "ingredients": [
            "1 cup Cooked quinoa",
            "1/2 Cucumber, diced",
            "1/2 cup Cherry tomatoes, halved",
            "1/4 cup Feta cheese, crumbled",
            "2 tbsp Lemon vinaigrette dressing"
        ],
        "instructions": (
            "1. Cook quinoa according to package instructions and let cool.\n"
            "2. In a large bowl, combine quinoa, diced cucumber, tomatoes, and feta.\n"
            "3. Drizzle vinaigrette and toss gently.\n"
            "4. Chill in the refrigerator for 10 minutes before serving."
        )
    },
    "avocado toast with egg": {
        "ingredients": [
            "1 slice Whole wheat bread",
            "1/2 Ripe avocado",
            "1 Large egg",
            "Pinch of red pepper flakes",
            "Salt and black pepper"
        ],
        "instructions": (
            "1. Toast the bread to desired crispness.\n"
            "2. Mash the avocado with a pinch of salt and black pepper, then spread onto the toast.\n"
            "3. Fry or poach the egg to your preference.\n"
            "4. Place the egg on top of the mashed avocado and sprinkle with red pepper flakes."
        )
    },
    "oatmeal with berries": {
        "ingredients": [
            "1/2 cup Rolled oats",
            "1 cup Almond milk (unsweetened)",
            "1/2 cup Mixed berries (blueberries, raspberries)",
            "1 tbsp Chia seeds",
            "1 tsp Honey"
        ],
        "instructions": (
            "1. In a small pot, bring almond milk to a simmer.\n"
            "2. Stir in oats and cook on medium-low heat for 5 minutes, stirring occasionally.\n"
            "3. Pour oatmeal into a bowl, top with mixed berries and chia seeds.\n"
            "4. Drizzle honey on top."
        )
    }
}

FOOD_DATABASE = {
    "banana": {"calories": 89, "protein": 1.1, "carbs": 22.8, "fat": 0.3},
    "chicken breast": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
    "egg": {"calories": 78, "protein": 6, "carbs": 0.6, "fat": 5},
    "quinoa": {"calories": 120, "protein": 4.4, "carbs": 21.3, "fat": 1.9},
    "oatmeal": {"calories": 150, "protein": 5, "carbs": 27, "fat": 2.5},
    "salmon": {"calories": 208, "protein": 20, "carbs": 0, "fat": 13},
    "avocado": {"calories": 160, "protein": 2, "carbs": 8.5, "fat": 14.7},
    "almond milk": {"calories": 30, "protein": 1, "carbs": 1, "fat": 2.5},
    "chia seeds": {"calories": 137, "protein": 4.4, "carbs": 12, "fat": 8.6},
    "apple": {"calories": 52, "protein": 0.3, "carbs": 14, "fat": 0.2},
    "sweet potato": {"calories": 86, "protein": 1.6, "carbs": 20, "fat": 0.1}
}

DIET_RULES = {
    "keto": {
        "summary": "High-fat, low-carbohydrate diet designed to induce ketosis.",
        "allowed": ["Meat", "Fish", "Eggs", "Butter/Oils", "Nuts/Seeds", "Low-carb veggies (leafy greens)"],
        "avoid": ["Sugar", "Grains/Starches (bread, pasta, rice)", "Fruit (except small portions of berries)", "Beans/Legumes"]
    },
    "vegan": {
        "summary": "Strictly plant-based diet excluding all animal products.",
        "allowed": ["Vegetables", "Fruits", "Grains", "Legumes/Beans", "Nuts/Seeds", "Plant-based alternatives"],
        "avoid": ["Meat/Poultry", "Fish/Seafood", "Dairy products (milk, cheese, butter)", "Eggs", "Honey"]
    },
    "gluten-free": {
        "summary": "Excludes gluten, a protein family found in wheat, barley, rye, and triticale.",
        "allowed": ["Fruits/Vegetables", "Plain meats/fish", "Beans/Legumes", "Rice/Quinoa", "Corn/Gluten-free oats"],
        "avoid": ["Wheat (bread, pasta, baked goods)", "Barley", "Rye", "Spelt", "Standard beer"]
    }
}


@mcp.tool()
def get_recipe_details(recipe_name: str) -> str:
    """
    Get detailed ingredients list and step-by-step instructions for a specific healthy recipe.

    Args:
        recipe_name: The name of the recipe (e.g., 'quinoa salad', 'grilled salmon with asparagus').
    """
    name_clean = recipe_name.lower().strip()
    if name_clean in RECIPES:
        recipe = RECIPES[name_clean]
        ingredients = "\n".join([f"- {ing}" for ing in recipe["ingredients"]])
        return (
            f"### Recipe: {recipe_name.title()}\n\n"
            f"**Ingredients:**\n{ingredients}\n\n"
            f"**Instructions:**\n{recipe['instructions']}"
        )
    
    # Try fuzzy match
    for k, recipe in RECIPES.items():
        if k in name_clean or name_clean in k:
            ingredients = "\n".join([f"- {ing}" for ing in recipe["ingredients"]])
            return (
                f"### Recipe: {k.title()}\n\n"
                f"**Ingredients:**\n{ingredients}\n\n"
                f"**Instructions:**\n{recipe['instructions']}"
            )
            
    available = ", ".join([f"'{k}'" for k in RECIPES.keys()])
    return f"Recipe '{recipe_name}' not found. Available healthy recipes: {available}."


@mcp.tool()
def search_food_calories(food_item: str) -> str:
    """
    Search the calorie and macronutrient breakdown (protein, carbs, fats) for a food item per 100g.

    Args:
        food_item: The name of the food item (e.g., 'banana', 'chicken breast', 'egg').
    """
    item_clean = food_item.lower().strip()
    if item_clean in FOOD_DATABASE:
        nutrients = FOOD_DATABASE[item_clean]
        return (
            f"### Nutritional Info: {food_item.title()} (per 100g)\n"
            f"- **Calories:** {nutrients['calories']} kcal\n"
            f"- **Protein:** {nutrients['protein']}g\n"
            f"- **Carbohydrates:** {nutrients['carbs']}g\n"
            f"- **Fats:** {nutrients['fat']}g"
        )
    
    # Try fuzzy match
    for k, nutrients in FOOD_DATABASE.items():
        if k in item_clean or item_clean in k:
            return (
                f"### Nutritional Info: {k.title()} (per 100g)\n"
                f"- **Calories:** {nutrients['calories']} kcal\n"
                f"- **Protein:** {nutrients['protein']}g\n"
                f"- **Carbohydrates:** {nutrients['carbs']}g\n"
                f"- **Fats:** {nutrients['fat']}g"
            )

    return (
        f"Food item '{food_item}' not found in the local database. "
        "Estimated average: ~100 kcal, 2g protein, 15g carbs, 1g fat per 100g."
    )


@mcp.tool()
def get_diet_rules(diet_type: str) -> str:
    """
    Get the guidelines, allowed foods, and foods to avoid for a specific diet type.

    Args:
        diet_type: The type of diet (e.g., 'keto', 'vegan', 'gluten-free').
    """
    type_clean = diet_type.lower().strip()
    if type_clean in DIET_RULES:
        rules = DIET_RULES[type_clean]
        allowed = ", ".join(rules["allowed"])
        avoid = ", ".join(rules["avoid"])
        return (
            f"### Diet Guidelines: {diet_type.title()}\n"
            f"**Summary:** {rules['summary']}\n\n"
            f"**Allowed Foods:** {allowed}\n\n"
            f"**Foods to Avoid:** {avoid}"
        )
    
    available = ", ".join([f"'{k}'" for k in DIET_RULES.keys()])
    return f"Diet rules for '{diet_type}' not found. Available diet types: {available}."


if __name__ == "__main__":
    mcp.run()
