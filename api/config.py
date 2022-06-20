from pydantic import BaseModel


class Config(BaseModel):

  MONGO_HOST: str = "mongodb"
  MONGO_PORT: int = 27017

  MONGO_USERNAME: str = "admin"
  MONGO_PASSWORD: str = "admin"

config = Config()
