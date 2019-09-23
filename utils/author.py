from utils import default
from models import User
from prodict import Prodict


async def get(author, create=True):
    user = User.find_one({"user_id": str(author.id)})
    if not user:
        if create is False:
            return False
        user_template = {
            'user_id': author.id,
            'name': author.name,
            'discriminator': author.discriminator
        }
        user_id = User.insert_one(user_template).inserted_id
        user = User.find_one({"_id": user_id})

    return Prodict.from_dict(user)
