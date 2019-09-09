import os
from pymongo import MongoClient
from pymongoext import Model


class BaseModel(Model):
    @classmethod
    def db(cls):
        return MongoClient()[f'{os.getenv("DB_NAME")}']



