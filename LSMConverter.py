import numpy as np
import tifffile
import glob
import os
import re
from SeriesConverter import SeriesConverter

## Converter of newer .lif images
class LsmConverter(SeriesConverter):
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
        return glob.glob(f"{self.folder}\*.lsm")

    def GetNImages(self):
        return self.n_series
        
          
    # Function for the conversion
    # @param[in] idx: index of the image in series
    # @param[in] folder: path where the TIFF image will be written
    def ConvertImage(self,idx,folder):
        #find the name and resolution of image
        lsm = tifffile.TiffFile(self.filenames[idx])
        channels = 2
        i = [m.start() for m in re.finditer("/",  self.filename)]
        last_div = i[-1]
        name = self.filenames[idx][last_div + 1:][:-4]
        metadata = lsm.lsm_metadata
        dx = metadata["VoxelSizeX"] * 1e9
        if metadata["DimensionY"] > 1:
            dy = metadata["VoxelSizeY"]
            yunit = "nm"
        else:
            dy = metadata["TimeIntervall"]
            yunit = "s"
        #find number of channels, dx,dy
        metadata["axes"] = "YX"
        metadata["PhysicalSizeX"] = dx
        metadata["PhysicalSizeXUnit"] = "nm"
        if yunit != 's' or self.setgrayscale:
            metadata["PhysicalSizeY"] = dy
            metadata["PhysicalSizeYUnit"] = yunit if yunit != 's' else "nm"
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
        img = lsm.pages[0]
        for j in range(channels):
            pages.append(img.asarray()[j,:])
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