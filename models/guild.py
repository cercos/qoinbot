from pymongo import IndexModel
from pymongoext import DictField, StringField
from pymongoext.manipulators import Manipulator
from models import BaseModel
from utils import default

config = default.get("config.json")


class Guild(BaseModel):
    __schema__ = DictField(dict(
        name=StringField(required=True),
        guild_id=StringField(default=''),
    ))

    __indexes__ = [IndexModel('guild_id', unique=True)]

    # class InventoryAggregateManipulator(Manipulator):
    #     def transform_outgoing(self, doc, model):
    #
    #         return doc
    #
    #     def transform_incoming(self, doc, model, action):
    #
    #         return doc
