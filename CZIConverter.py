import numpy as np
import tifffile
import glob
import re
from czifile import CziFile
import xml.etree.ElementTree as ET
from pathlib import Path
from SeriesConverter import SeriesConverter

## Converter of newer .lif images
class CziConverter(SeriesConverter):
    ## Constructor
    # @param filename: Name of the file
    def __init__(self,filename,setgrayscale):
        self.filename = filename
        i = [m.start() for m in re.finditer("/",  self.filename)]
        last_div = i[-1]
        self.projectname = self.filename[last_div + 1:][:-4]
        self.folder = self.filename[:last_div + 1]
        self.filenames = self._GetAllFilesInFolder()
        self.n_series = len(self.filenames)
        self.setgrayscale = setgrayscale
        #LUT's
        self.GREEN = np.array([[0,i,0] for i in range(256)]).T
        self.GRAY = np.array([[i,i,i] for i in range(256)],dtype=np.uint8).T

    def _GetAllFilesInFolder(self):
        return [str(p) for p in Path(self.folder).glob("*.czi")]

    def GetNImages(self):
        return self.n_series
        
          
    def _GetSteps(self, metadata):
        def _get_distance_value(id_):
            for dist in metadata.findall('.//Distance'):
                if dist.get('Id') == id_:
                    val = dist.find('Value')
                    if val is not None and val.text:
                        return float(val.text)
            return None

        dx_m = _get_distance_value('X')

        node = metadata.find('.//LineTime')
        is_linescan = node is not None

        if is_linescan:
            line_time = float(node.text)
        else:
            line_time = _get_distance_value('Y')

        return dx_m, line_time, is_linescan
            
    # Function for the conversion
    # @param[in] idx: index of the image in series
    # @param[in] folder: path where the TIFF image will be written
    def ConvertImage(self,idx,folder):
        #find the name and resolution of image
        with CziFile(self.filenames[idx]) as czi:
            name = Path(self.filenames[idx]).stem
            arr = czi.asarray()
            img = np.moveaxis(arr[0,:,:,0,0,:,0], 0, 1)
            mdata = ET.fromstring(czi.metadata())
            channels = 2
            dx, dy, is_linescan = self._GetSteps(mdata)
            print(dx, dy, is_linescan)
            yunit = 's' if is_linescan else 'nm'
            metadata = {}
            metadata["axes"] = "YX"
            metadata["PhysicalSizeX"] = dx
            metadata["PhysicalSizeXUnit"] = "nm"
            if yunit != 's' or self.setgrayscale:
                metadata["PhysicalSizeY"] = dy
                metadata["PhysicalSizeYUnit"] = 'nm'
                if yunit == "s":
                    metadata["PhysicalSizeY"] *= 1e3
                else:
                    metadata["PhysicalSizeY"] *= 1e9
            else:
                metadata["TimeIncrement"] = dy
                metadata["TimeIncrementUnit"] = yunit
            #find number of images in SERIES
            pages = []
            LUTs = []
            #write sequencially one by one
            for j in range(channels):
                pages.append(img[j,:])
                if j == 0:
                    LUTs.append(self.GREEN)
                else:
                    LUTs.append(self.GRAY)
            with tifffile.TiffWriter(f'{folder}/{name}.ome.tif',ome=True) as tif:
                if self.setgrayscale:
                    metadata["axes"] = "CYX"
                    pages = np.array(pages)
                    tif.write(pages,photometric='minisblack', metadata = metadata)
                else:
                    for j in range(channels):
                        tif.write(pages[j], colormap = LUTs[j], metadata = metadata)