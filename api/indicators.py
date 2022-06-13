import requests
from sys import argv


BASE_URL = 'https://www.ine.pt/ine/json_indicador'

class Index:
  def __init__(self, code: str) -> None:
    data = requests.get(BASE_URL + '/pindicaMeta.jsp?lang=PT&varcd=' + code).json()[0]

    self._id = data['IndicadorCod']
    self._name = data['IndicadorNome']
    self._unit_description = data['UnidadeMedida']
    self._filters = [ Filter(dim['abrv'], [ Option(option[0]['cat_id'], option[0]['categ_dsg']) for key, option in data['Dimensoes']['Categoria_Dim'][0].items() if "_Num{}_".format(dim['dim_num']) in key ]) for dim in data['Dimensoes']['Descricao_Dim'] ]

  def get_values(self, **filters):
    data = requests.get(BASE_URL + '/pindica.jsp?op=2&lang=PT&varcd=' + self._id + ''.join('&' + key + '=' + option for key, option in filters.items())).json()[0]
    data = [ { 
      'Dim1': { 'id': 'S7A' + str(year), 'label': year }, 
      'Dim2': { 'id': line['geocod'], 'label': line['geodsg'] },
      **{ 'Dim' + str(i) : { 'id': line['dim_{}'.format(i)], 'label': line['dim_{}_t'.format(i)] } for i in range(3, len([key for key in line.keys() if key.startswith('dim_') and key.endswith('_t')])+3) },
      'Value': line['valor'] if 'valor' in line.keys() else None
    } for year, content in data['Dados'].items() for line in content ]
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
