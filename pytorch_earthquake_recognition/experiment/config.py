import os
from enum import Enum
import json

RGB_MEAN = [0.0009950225259743484, 0.000795141388388241, 0.0018111652018977147]
RGB_STD = [0.0001881388618665583, 0.0006368028766968671, 0.00028853512862149407]

GRAY_MEAN = [0.0009636541207631429, 0.0009636541207631429, 0.0009636541207631429]
GRAY_STD = [0.0003674938398249009, 0.0003674938398249009, 0.0003674938398249009]

BORDER_COLOR_GRAY = 30

DIVIDE_TEST = .2   # % test

VISUALIZE_PATH = os.path.join(os.path.join(os.getcwd(), 'visualize/'))

class Folders(Enum):
    Amatrice = 'AmatriceQuakes'
    Alaska = 'AlaskaQuakes'
    California = 'CaliforniaQuakes'
    Costa = 'CostaQuakes'
    Oklahoma = 'OklahomaQuakes'
    Puerto = 'PuertoQuakes'
    SouthAmerica = 'SouthAmericaQuakes'
    Utah = 'UtahQuakes'

    @classmethod
    def values(cls):
        return [folder.value for folder in cls]




# Settings
ignore = Folders.values()
ignore.remove(Folders.Oklahoma.value)

options = dict(
    oklahoma={
        'train': {
            'path': 'new-spectrograms-oklahoma',
            'divide_test': 0.2,
        },
        'test': {
            'path': 'new-spectrograms-oklahoma',
            'divide_test': 0.2
        },
        'image': {
          'height': 258,
          'width': 293,
        }
    },
    my_data={
        'train': {
            'path': 'spectrograms',
            'divide_test': 0.2,
            'ignore': ignore
        },
        'test': {
            'path': 'spectrograms',
            'divide_test': 0.2,
            'ignore': ignore
        },
        'image': {
          'height': 217,
          'width': 296,
        }
    }
)

configuration = os.environ.get('configuration')

if configuration:
    options['loaded'] = json.loads(configuration)