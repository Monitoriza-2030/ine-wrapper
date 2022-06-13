from flask import Flask, request, jsonify

from indicators import Index


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

@app.get('/index/<code>')
def get_index_info(code: str):
  return Index(code).to_dict()

@app.get('/index/<code>/data')
def get_index_data(code: str):
  return jsonify(Index(code).get_values(**request.args.to_dict()))

app.run(debug=True)
