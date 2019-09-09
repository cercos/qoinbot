from pymongo import IndexModel
from pymongoext import DictField, StringField, IntField
from models import BaseModel
from utils import default

config = default.get("config.json")


class Item(BaseModel):
    __schema__ = DictField(dict(
        name=StringField(required=True),
        about=StringField(default=''),
        price=IntField(required=True),
        rate=IntField(default=60),
        payout=IntField(required=True)
    ))

    __indexes__ = [IndexModel('name', unique=True)]

    # class FullNameManipulator(Manipulator):
    #     def transform_outgoing(self, doc, model):
    #         return doc
    #
    #     def transform_incoming(self, doc, model, action):
    #         return doc
