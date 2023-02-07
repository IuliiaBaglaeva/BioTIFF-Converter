import numpy as np
import re
import tifffile
from SeriesConverter import SeriesConverter

 
## Converter of old .lei images
class LeiConverter(SeriesConverter):
    ## Constructor
    # @param filename: Name of the file
    def __init__(self,filename,setgrayscale):
        self.filename = filename
        i = [m.start() for m in re.finditer("/",  self.filename)]
        last_div = i[-1]
        self.projectname = self.filename[last_div + 1:][:-4]
        self.folder = self.filename[:last_div + 1]
        self.logname = filename[:-3] + "txt"
        self.domxml = None
        self.n_series = self.FindNumberofSeries()
        self.setgrayscale = setgrayscale
        #LUT's
        self.GREEN = np.array([[0,i,0] for i in range(256)]).T


    def GetNImages(self):
        return self.n_series

    def FindNumberofSeries(self):
        with open(self.logname) as f:
            for line in f:
                num_exp = re.search('(?<=Number of Images: )\d+', line)
                if num_exp is not None:
                    return int(num_exp[0])

    def GetNameAndResolution(self,idx):
        scanner_found = False
        res = 0
        Name = ""
        with open(self.logname) as f:
            for line in f:
                num_exp = re.search('(?<=DIMENSION DESCRIPTION #)\d+', line)
                if num_exp is not None and int(num_exp[0]) == idx:
                    scanner_found = True
                    continue
                if scanner_found:
                    res = re.search('(?<=Resolution in Bit:   	)\d+', line)
                    if res is not None:
                        res = int(res[0])
                    Name = re.search('(?<=Series Name:	)\S+', line)
                    if Name is not None:
                        return Name[0].replace('\x00', ''), res
    
    def GetNumberofChannelsandSteps(self,idx):
        scanner_found = False
        channels = 0
        x = 0
        xunit = "nm"
        y = 0
        yunit = "s"
        is_xt = False
        with open(self.logname) as f:
            for line in f:
                num_exp = re.search('(?<=SCANNER INFORMATION #)\d+', line)
                if num_exp is not None and int(num_exp[0]) == idx:
                    scanner_found = True
                    continue
                if scanner_found:
                    line_list = line.split()
                    if line_list[0] == "ScanMode" and line_list[1] == "xt":
                        is_xt = True
                        continue
                    if line_list[0] == "Size-Width":
                        x = float(line_list[2].replace('\x00', ''))
                    if line_list[0] == "Size-Height":
                        y = float(line_list[2].replace('\x00', '')) # https://stackoverflow.com/questions/44536431/extract-decimal-number-from-string-in-c-sharp
                        if not is_xt:
                            yunit = "nm"
                    channels = re.search('(?<=Channels		)\d+', line)
                    if channels is not None:
                        channels = int(channels[0])
                        return channels,x,xunit,y,yunit
   
    def GetNumberofImages(self,idx):
        n_images = 0
        scanner_found = False
        with open(self.logname) as f:
            for line in f:
                num_exp = re.search('(?<=IMAGES INFORMATION #)\d+', line)
                if num_exp is not None and int(num_exp[0]) == idx:
                    scanner_found = True
                    continue
                if scanner_found:
                    n_images = re.search('(?<=Number of Images: 	)\d+', line)
                    if n_images is not None:
                        return int(n_images[0])
        
    # Function for the conversion
    # @param[in] idx: index of the image in series
    # @param[in] folder: path where the TIFF image will be written
    def ConvertImage(self,idx,folder):
        #find the name and resolution of image
        metadata = {}
        name, res = self.GetNameAndResolution(idx)
        #find number of channels, dx,dy
        channels,x,xunit,y,yunit = self.GetNumberofChannelsandSteps(idx)
        metadata["axes"] = "YX"
        metadata["PhysicalSizeX"] = x
        metadata["PhysicalSizeXUnit"] = xunit
        if yunit != 's' or self.setgrayscale:
            metadata["PhysicalSizeY"] = y
            metadata["PhysicalSizeYUnit"] = yunit if yunit != 's' else "nm"
        else:
            metadata["TimeIncrement"] = y
            metadata["TimeIncrementUnit"] = yunit
        #find number of images in SERIES
        number_of_images = self.GetNumberofImages(idx)
        number_of_images //= channels
        pages = []
        LUTs = []
        #write sequencially one by one
        for i in range(number_of_images):
            for j in range(channels):
                imgname = f'{self.folder+self.projectname}_{name}_Nt{i:03d}_ch{j:02d}.tif' if number_of_images > 1 else f'{self.folder+self.projectname}_{name}_ch{j:02d}.tif'
                with tifffile.TiffFile(imgname) as tif:
                    if i == 0:
                        img = tif.pages[0].asarray()
                        pages.append(img)
                        LUTs.append(tif.pages[0].colormap)
                        if j == 0:
                            metadata["PhysicalSizeX"] /= img.shape[1]/1e3 #um to nm
                            if yunit != 's' or self.setgrayscale:
                                metadata["PhysicalSizeY"] /= img.shape[0]/1e3 #um to nm
                            else:
                                metadata["TimeIncrement"] /= img.shape[0]
                    else:
                        pages[j] = np.vstack((pages[j],tif.pages[0].asarray()))
        with tifffile.TiffWriter(f'{folder}/{name}.ome.tif',ome=True) as tif:
            if self.setgrayscale:
                metadata["axes"] = "CYX"
                pages = np.array(pages)
                tif.save(pages,photometric='minisblack', metadata = metadata)
            else:
                for j in range(channels):
                    tif.save(pages[j], colormap = LUTs[j], metadata = metadata)
        
        
        