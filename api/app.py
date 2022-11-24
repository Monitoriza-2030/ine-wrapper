from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from config import config

from indicators import CachedIndex, CachedIndexSearch


app = Flask(__name__)
CORS(app)
app.config['JSON_AS_ASCII'] = False

@app.get('/index')
def get_indexes_info():
  try:
    return jsonify(CachedIndexSearch().get_all(**request.args.to_dict()))
  except Exception as e: 
    return jsonify(e)

@app.get('/index/<code>')
def get_index_info(code: str):
  try:
    return CachedIndex(code).to_dict()
  except Exception as e: 
    return jsonify(e)

@app.get('/index/<code>/data')
def get_index_data(code: str):
  try:
    return jsonify(CachedIndex(code).get_values(**request.args.to_dict()))
  except Exception as e: 
    return jsonify(e)

@app.get('/mongo/status')
def mongo_status():
  client = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
  return jsonify(client.server_info())

app.run(host='0.0.0.0', debug=True)
