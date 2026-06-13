import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "engine.settings")
django.setup()

from authenticator.models import CustomUser
from authenticator.schemas import UserMeSchema

user = CustomUser.objects.first()
if user:
    try:
        schema = UserMeSchema.from_orm(user)
        print("Success:", schema.dict())
    except Exception as e:
        print("Error:", e)
else:
    print("No users found")
