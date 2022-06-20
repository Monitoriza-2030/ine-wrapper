import json
from flask import Flask, request, jsonify
from pymongo import MongoClient
from config import config

from indicators import CachedIndex


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.get('/index/<code>')
def get_index_info(code: str):
  return CachedIndex(code).to_dict()

@app.get('/index/<code>/data')
def get_index_data(code: str):
  return jsonify(CachedIndex(code).get_values(**request.args.to_dict()))

@app.get('/mongo/status')
def mongo_status():
  client = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
  return jsonify(client.server_info())

app.run(host='0.0.0.0', debug=True)
