"""
Fills DynamoDB + Cognito with demo data for Green & Tasty:
3 locations, 4 tables per location, 9 dishes per location and 1 waiter per location.

Safe to run several times: records use fixed ids and are overwritten, existing users are reused.

Run from the repo root with the syndicate venv active (it already has boto3):
    python scripts/seed_demo_data.py
Optional: --waiter-password "Waiter#2026" (default below), --region us-west-2
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal

import boto3

USER_POOL_NAME = "restaurant-backend-user-pool"
WAITER_GROUP = "Waiter"

LOCATIONS = [
    {
        "id": "loc-rustaveli",
        "address": "48 Rustaveli Avenue",
        "description": "Flagship restaurant in the heart of the city with a summer terrace.",
        "image": "assets/img/locations/rustaveli-avenue-48.jpg",
        "rating": 4.8,
        "occupancy": "85%",
    },
    {
        "id": "loc-baratashvili",
        "address": "14 Baratashvili Street",
        "description": "Cozy place in the Old Town, perfect for family dinners.",
        "image": "assets/img/locations/baratashvili-street-14.jpg",
        "rating": 4.6,
        "occupancy": "70%",
    },
    {
        "id": "loc-abashidze",
        "address": "9 Abashidze Street",
        "description": "Quiet green spot in Vake with large tables for groups.",
        "image": "assets/img/locations/abashidze-street-9.jpg",
        "rating": 4.5,
        "occupancy": "60%",
    },
]

TABLE_CAPACITIES = [2, 4, 6, 8]

# (key, name, type 0=Appetizer 1=MainCourse 2=Dessert, price, weight, kcal, image)
DISHES = [
    ("spring-salad", "Spring Salad", 0, "12.50", "250 g", "210 kcal", "assets/img/dishes/spring-salad.jpg"),
    ("strawberry-mint", "Fresh Strawberry Mint Salad", 0, "11.00", "220 g", "180 kcal", "assets/img/dishes/fresh-strawberry-mint-salad.jpg"),
    ("bruschetta", "Tomato & Basil Bruschetta", 0, "8.50", "180 g", "260 kcal", "assets/img/dish.png"),
    ("lentil-salad", "Roasted Sweet Potato and Lentil Salad", 1, "16.00", "350 g", "420 kcal", "assets/img/dishes/roasted-sweet-potato-and-lentil-salad.jpg"),
    ("avocado-bowl", "Avocado Pine Nut Bowl", 1, "17.50", "380 g", "510 kcal", "assets/img/dishes/avocado-pine-nut-bowl.jpg"),
    ("mushroom-risotto", "Wild Mushroom Risotto", 1, "19.00", "320 g", "560 kcal", "assets/img/dish.png"),
    ("cheesecake", "Berry Cheesecake", 2, "9.00", "150 g", "390 kcal", "assets/img/dish.png"),
    ("chia-pudding", "Coconut Chia Pudding", 2, "7.50", "160 g", "280 kcal", "assets/img/dish.png"),
    ("apple-crumble", "Warm Apple Crumble", 2, "8.00", "170 g", "340 kcal", "assets/img/dish.png"),
]


def find_user_pool_id(cognito):
    for page in cognito.get_paginator("list_user_pools").paginate(MaxResults=50):
        for pool in page["UserPools"]:
            if pool["Name"] == USER_POOL_NAME:
                return pool["Id"]
    raise SystemExit(f"User pool '{USER_POOL_NAME}' not found. Did terraform apply succeed?")


def ensure_waiter(cognito, pool_id, email, first, last, password):
    try:
        user = cognito.admin_get_user(UserPoolId=pool_id, Username=email)
        attrs = user["UserAttributes"]
    except cognito.exceptions.UserNotFoundException:
        user = cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            MessageAction="SUPPRESS",
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "given_name", "Value": first},
                {"Name": "family_name", "Value": last},
            ],
        )["User"]
        attrs = user["Attributes"]
    cognito.admin_set_user_password(UserPoolId=pool_id, Username=email, Password=password, Permanent=True)

    try:
        cognito.create_group(GroupName=WAITER_GROUP, UserPoolId=pool_id, Description=f"Group for role {WAITER_GROUP}")
    except cognito.exceptions.GroupExistsException:
        pass
    cognito.admin_add_user_to_group(UserPoolId=pool_id, Username=email, GroupName=WAITER_GROUP)

    return next(a["Value"] for a in attrs if a["Name"] == "sub")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--waiter-password", default="Waiter#2026")
    args = parser.parse_args()

    dynamo = boto3.resource("dynamodb", region_name=args.region)
    cognito = boto3.client("cognito-idp", region_name=args.region)
    pool_id = find_user_pool_id(cognito)

    locations_t = dynamo.Table("Locations")
    tables_t = dynamo.Table("Tables")
    dishes_t = dynamo.Table("Dishes")
    waiters_t = dynamo.Table("Waiters")

    for idx, loc in enumerate(LOCATIONS, start=1):
        dish_ids = []
        for key, name, dish_type, price, weight, kcal, image in DISHES:
            dish_id = f"{loc['id']}-{key}"
            dish_ids.append(dish_id)
            dishes_t.put_item(Item={
                "id": dish_id,
                "name": name,
                "description": f"{name} prepared from fresh seasonal ingredients.",
                "dishType": dish_type,
                "price": Decimal(price),
                "weight": weight,
                "calories": kcal,
                "proteins": "12 g",
                "fats": "14 g",
                "carbohydrates": "30 g",
                "vitamins": "A, C, E",
                "imageUrl": image,
                "state": 1,  # Available
                "locationId": loc["id"],
            })

        for number, capacity in enumerate(TABLE_CAPACITIES, start=1):
            tables_t.put_item(Item={
                "id": f"{loc['id']}-table-{number}",
                "locationId": loc["id"],
                "capacity": capacity,
                "tableNumber": number,
            })

        locations_t.put_item(Item={
            "id": loc["id"],
            "address": loc["address"],
            "description": loc["description"],
            "totalCapacity": sum(TABLE_CAPACITIES),
            "averageOccupancy": loc["occupancy"],
            "imageUrl": loc["image"],
            "rating": Decimal(str(loc["rating"])),
            "specialtyDishIds": dish_ids[:4],
        })

        waiter_email = f"waiter{idx}@greenandtasty.demo"
        waiter_id = ensure_waiter(cognito, pool_id, waiter_email, "Waiter", str(idx), args.waiter_password)
        existing = waiters_t.get_item(Key={"userId": waiter_id}).get("Item")
        waiters_t.put_item(Item={
            "userId": waiter_id,
            "locationId": loc["id"],
            "createdAt": (existing or {}).get("createdAt") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "reservations": (existing or {}).get("reservations", []),
        })

        print(f"✔ {loc['address']}: {len(DISHES)} dishes, {len(TABLE_CAPACITIES)} tables, waiter {waiter_email}")

    print(f"\nDone. Waiter password: {args.waiter_password}")


if __name__ == "__main__":
    main()
