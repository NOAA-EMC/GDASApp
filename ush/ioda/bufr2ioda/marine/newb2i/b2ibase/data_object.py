from abc import ABC, abstractmethod


class DataObject(ABC):
    @abstractmethod
    def add_query(self, q): 
        pass

    @abstractmethod
    def set_from_query_result(self, r): 
        pass

    @abstractmethod
    def filter(self, mask):
        pass

    @abstractmethod
    def create_ioda_objects(self, obsspace):
        pass

    def log(self, logger):
        pass

    @abstractmethod
    def get_filter(self):
        pass

    @abstractmethod
    def get_data_size():
        pass
