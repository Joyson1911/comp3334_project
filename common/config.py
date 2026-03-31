import configparser
from os.path import exists, isfile
from os import getcwd

class Config():
    _config = configparser.ConfigParser()
    
    @staticmethod
    def add_conf(path: str = 'config.ini'):
        if not exists(path):
                raise FileNotFoundError(f'{path} does not exist in {getcwd()}')
        if not isfile(path):
            raise IsADirectoryError(f'{path} is not a file.')
  
        Config._config.read(path)
    
    @staticmethod
    def get() -> configparser.ConfigParser:
        if len(Config._config.keys()) <= 0:
            Config.add_conf()
        return Config._config