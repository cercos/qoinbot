from pymongo import IndexModel
from pymongoext import DictField, StringField, ListField
from pymongoext.manipulators import Manipulator
from models import BaseModel
from utils import default

config = default.get("config.json")


class Store(BaseModel):
    __schema__ = DictField(dict(
        name=StringField(required=True),
        about=StringField(default=''),
        item_list=ListField(default=[])
    ))

    __indexes__ = [IndexModel('name', unique=True)]

    class InventoryAggregateManipulator(Manipulator):
        def transform_outgoing(self, doc, model):
            cur = Store.aggregate([
                {"$lookup": {
                    "from": "item",
                    "foreignField": "_id",
                    "localField": "item_list",
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
