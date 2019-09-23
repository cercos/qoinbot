from pymongo import IndexModel
from pymongoext import Model, DictField, StringField, ListField, NumberField, DateTimeField
from pymongoext.manipulators import Manipulator
from toolz import curried

from models import BaseModel
from datetime import datetime, timedelta
from utils import default, number, coins

config = default.get("config.json")


class User(BaseModel):
    __schema__ = DictField(dict(
        user_id=StringField(required=True),
        name=StringField(required=True),
        discriminator=StringField(required=True),
        quote_to=StringField(default='USD'),
        price_list=DictField(dict(
            coins=ListField(default=[])
        )),
        item_list=ListField(default=[]),
        game=DictField(dict(
            money=NumberField(default=config.economy.start_money),
            in_pocket=NumberField(default=0),
            portfolio=DictField(dict(
                transactions=ListField(default=[]),
                coins=ListField(default=[])
            )),
            wage=NumberField(default=config.economy.start_wage),
            total_wages=NumberField(default=0),
            last_wage=DateTimeField(default=None),
            created_at=DateTimeField(default=datetime.now())
        ))
    ))

    __indexes__ = [IndexModel('user_id', unique=True)]

    class InventoryAggregateManipulator(Manipulator):
        def transform_outgoing(self, doc, model):
            cur = User.aggregate([
                {"$lookup": {
                    "from": "item",
                    "let": {
                        "items": "$item_list"
                    },
                    "pipeline": [
                        {"$match": {"$expr": {"$in": ["$_id", "$$items.id"]}}},
                        {"$project": {"name": "$name", 'rate': "$rate", "payout": "$payout"}},
                        # {"$addFields": {"last_run": "$$list_item.created_at"}}
                    ],
                    "as": "inventory"
                }},
                {"$match": {"_id": doc['_id']}}
            ])
            for doc in cur:
                return doc

        def transform_incoming(self, doc, model, action):
            if 'inventory' in doc:
                del doc['inventory']
            return doc

    class RoundGameBalanceManipulator(Manipulator):
        def transform_outgoing(self, doc, model):
            if 'game' in doc:
                if 'money' in doc['game']:
                    doc['game']['money'] = float('{0:.6f}'.format(doc['game']['money']))
                if 'in_pocket' in doc['game']:
                    doc['game']['in_pocket'] = float('{0:.6f}'.format(doc['game']['in_pocket']))
            return doc

        # def transform_incoming(self, doc, model, action):
        #     return doc
