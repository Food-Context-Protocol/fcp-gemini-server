import asyncio
import json
import os
from fcp.tools.recipe_crud import list_recipes
from fcp.auth.local import DEMO_USER_ID

async def main():
    try:
        # Use the tool function directly
        recipes = await list_recipes(DEMO_USER_ID)
        print(json.dumps(recipes))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
