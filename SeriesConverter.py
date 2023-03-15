from abc import ABC, abstractmethod
 
class SeriesConverter(ABC):
 
    @abstractmethod
    def GetNImages(self):
        pass

    @abstractmethod
    def ConvertImage(self,idx,out_folder):
        pass