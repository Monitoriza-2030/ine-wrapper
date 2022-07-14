import logging
import requests
from sys import argv
from pymongo import MongoClient
from pymongo.operations import IndexModel

from config import config


logging.basicConfig(level=logging.DEBUG)

BASE_URL = 'https://www.ine.pt/ine/json_indicador'

class Index:
  def __init__(self, code: str) -> None:
    data = requests.get(BASE_URL + '/pindicaMeta.jsp?lang=PT&varcd=' + code).json()[0]

    self._id = data['IndicadorCod']
    self._name = data['IndicadorNome']
    self._unit_description = data['UnidadeMedida']
    self._filters = [ Filter(dim['abrv'], [ Option(option[0]['categ_cod'], option[0]['categ_dsg']) for key, option in data['Dimensoes']['Categoria_Dim'][0].items() if "_Num{}_".format(dim['dim_num']) in key ]) for dim in data['Dimensoes']['Descricao_Dim'] ]

  def _format_filters(self, filters: dict = None):
    if filters is None: filters = {}

    for key, value in filters.items():
      filters[key] = value.split(',')
    
    # Hardcode full search for years
    if 'Dim1' not in filters.keys():
      filters['Dim1'] = [ option['id'] for option in self._filters[0].to_dict()['options'] ]

    return filters

  def get_values(self, **filters):
    return self._get_values(**self._format_filters(filters))

  def _get_values(self, **filters):
    if filters == {}: filters = self._format_filters()

    data = []

    for year in filters['Dim1']:
      ine_data = requests.get(BASE_URL + '/pindica.jsp?op=2&lang=PT&varcd=' + self._id + '&Dim1=' + year).json()[0]
      ine_data = [ { 
        'Dim1': { 'id': year, 'label': year_label }, 
        'Dim2': { 'id': line['geocod'], 'label': line['geodsg'] },
        **{ 'Dim' + str(i) : { 'id': line['dim_{}'.format(i)], 'label': line['dim_{}_t'.format(i)] } for i in range(3, len([key for key in line.keys() if key.startswith('dim_') and key.endswith('_t')])+3) },
        'Value': line['valor'] if 'valor' in line.keys() else None
      } for year_label, content in ine_data['Dados'].items() for line in content ]

      data.extend(list(filter(lambda entry: len([ key for key, values in filters.items() if entry[key]['id'] not in values ]) == 0, ine_data)))

    return data

  def to_dict(self) -> dict:
    return { 'id': self._id, 'name': self._name, 'unit': self._unit_description, 'filters': [ f.to_dict() for f in self._filters ] }

  def __str__(self) -> str:
    return '{} - {}\n{}'.format(self._id, self._name, '\n'.join([str(f) for f in self._filters])) 


class CachedIndex(Index):

  def __init__(self, code: str, cache: bool = True) -> None:
    client = MongoClient('mongodb://%s:%s@%s' % (config.MONGO_USERNAME, config.MONGO_PASSWORD, config.MONGO_HOST))
    db = client['ine']
    collection = db['headers']

    result = None
    mongo_filter = { 'id': code }

    if cache: 
      result = collection.find_one(mongo_filter)

    if result is None:
      super().__init__(code)

      collection.delete_one(mongo_filter)
      collection.insert_one(super().to_dict()) 
      collection.create_indexes([IndexModel("id")])
    else:
      self._id = result['id']
      self._name = result['name']
      self._unit_description = result['unit']
      self._filters = [ Filter(f['description'], [ Option(option['id'], option['description']) for option in f['options'] ]) for f in result['filters'] ]

  def _get_values(self, cache: bool = True, **filters):
    results = []

    client = MongoClient('mongodb://%s:%s@%s' % (config.MONGO_USERNAME, config.MONGO_PASSWORD, config.MONGO_HOST))
    db = client['ine']
    collection = db['values']

    if cache:
      results = collection.find({ 'index_code': self._id, **{ key + '.id': { '$in': value } for key, value in filters.items() }})
      results = [ item for item in results ]

    if len(results) == 0 and len([ item for item in collection.find({ 'index_code': self._id }) ]) == 0:
      results = super()._get_values()
      results = [ { 'index_code': self._id, **value } for value in results ]

      collection.delete_many({ 'index_code': self._id })
      collection.insert_many(results) 
      collection.create_indexes([IndexModel("index_code"), IndexModel("Dim1"), IndexModel("Dim2")])

      results = list(filter(lambda entry: len([ key for key, values in filters.items() if entry[key]['id'] not in values ]) == 0, results))
    
    results = [ { key: value for key, value in item.items() if key not in ['_id', 'index_code'] } for item in results ]

    return results


class Filter:
  def __init__(self, description: str, options: list = None) -> None:
    self._description = description
    self._options = options if options is not None else []
      
  def to_dict(self) -> dict:
    return { 'description': self._description, 'options': [option.to_dict() for option in self._options] }
      
  def __str__(self) -> str:
    return '{} [{}]'.format(self._description, ', '.join([ str(option) for option in self._options ]))


class Option:
  def __init__(self, code: str, description: str) -> None:
    self._id = code
    self._description = description

  def to_dict(self) -> dict:
    return { 'id': self._id, 'description': self._description }

  def __str__(self) -> str:
    return '{}={}'.format(self._id, self._description)


def main():
  OPERATION = argv[1] if len(argv) > 1 else ''
  INDEX_ID = argv[2] if len(argv) > 2 else '0002010'

  if OPERATION not in ['see', 'get']: OPERATION = 'see'

  index = Index(INDEX_ID)

  if OPERATION == 'see': print(index)
  elif OPERATION == 'get': print(index.get_values(**{f[0]:f[1] for f in [arg.split('=') for arg in argv[3:]]}))


if __name__ == '__main__':
  main()
