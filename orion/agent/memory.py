from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from orion.config import settings

class Memory(object):
    def __init__(self):
        self.memory = MongoDBChatMessageHistory(
            session_id="default", 
            connection_string=settings.mongodb.uri,
            database_name=settings.mongodb.database,
            collection_name=settings.mongodb.collection
        )

    