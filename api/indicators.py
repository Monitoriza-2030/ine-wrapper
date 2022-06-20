import logging
import requests
from sys import argv
from pymongo import MongoClient
from pymongo.operations import IndexModel

from config import config


BASE_URL = 'https://www.ine.pt/ine/json_indicador'

class Index:
  def __init__(self, code: str) -> None:
    data = requests.get(BASE_URL + '/pindicaMeta.jsp?lang=PT&varcd=' + code).json()[0]

    self._id = data['IndicadorCod']
    self._name = data['IndicadorNome']
    self._unit_description = data['UnidadeMedida']
    self._filters = [ Filter(dim['abrv'], [ Option(option[0]['cat_id'], option[0]['categ_dsg']) for key, option in data['Dimensoes']['Categoria_Dim'][0].items() if "_Num{}_".format(dim['dim_num']) in key ]) for dim in data['Dimensoes']['Descricao_Dim'] ]

  def normalize_filters(self, filters: dict) -> dict:
    for key, value in filters.items():
      filters[key] = value.split(',')
    
    # Hardcode full search for years
    if 'Dim1' not in filters.keys():
      filters['Dim1'] = [ option['id'] for option in self._filters[0].to_dict()['options'] ]

    return filters

  def get_values(self, cache: bool = True, **filters):
    filters = self.normalize_filters(filters)
    data = []

    if cache:
      client = MongoClient('mongodb://%s:%s@%s' % (config.MONGO_USERNAME, config.MONGO_PASSWORD, config.MONGO_HOST))
      db = client['ine']
      collection = db['values']
      data = collection.find({ 'index_code': self._id, **{ key + '.id': { '$in': value } for key, value in filters.items() }})
      data = [ { key: value for key, value in item.items() if key != '_id' } for item in data ]

      logging.info("{} items loaded from cache".format(len(data)))
      return list(data)

    for year in filters['Dim1']:
      ine_data = requests.get(BASE_URL + '/pindica.jsp?op=2&lang=PT&varcd=' + self._id + '&Dim1=' + year).json()[0]
      ine_data = [ { 
        'Dim1': { 'id': 'S7A' + str(year), 'label': year }, 
        'Dim2': { 'id': line['geocod'], 'label': line['geodsg'] },
        **{ 'Dim' + str(i) : { 'id': line['dim_{}'.format(i)], 'label': line['dim_{}_t'.format(i)] } for i in range(3, len([key for key in line.keys() if key.startswith('dim_') and key.endswith('_t')])+3) },
        'Value': line['valor'] if 'valor' in line.keys() else None
      } for year, content in ine_data['Dados'].items() for line in content ]

      data.extend(list(filter(lambda entry: len([ key for key, values in filters.items() if entry[key]['id'] not in values ]) == 0, ine_data)))

    client = MongoClient('mongodb://%s:%s@%s' % (config.MONGO_USERNAME, config.MONGO_PASSWORD, config.MONGO_HOST))
    db = client['ine']
    collection = db['values']
    collection.delete_many({ 'index_code': self._id, **{ key: { '$in': value } for key, value in filters.items() }})
    collection.insert_many([ { 'index_code': self._id, **value } for value in data ]) 
    collection.create_indexes([IndexModel("index_code"), IndexModel("Dim1"), IndexModel("Dim2")])
    
    logging.info("{} items loaded from ine".format(len(data)))
    return data

  def to_dict(self) -> dict:
    return { 'id': self._id, 'name': self._name, 'unit': self._unit_description, 'filters': [ f.to_dict() for f in self._filters ] }

  def __str__(self) -> str:
    return '{} - {}\n{}'.format(self._id, self._name, '\n'.join([str(f) for f in self._filters])) 


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
