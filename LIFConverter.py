import numpy as np
import tifffile
from readlif.reader import LifFile
from SeriesConverter import SeriesConverter
from readlif.reader import _check_magic, _check_mem, _read_int
from bs4 import BeautifulSoup

        
#taken from readlif package
def get_xml(filename):
    """
    Given a lif file, returns two values (xml_root, xml_header) where
    xml_root is an ElementTree root, and xml_header is the text.

    This is useful for debugging.

    Some private functions are used from readlif.reader.

    Args:
        filename (string): what file to open?
    """
    f = open(filename, "rb")
    _check_magic(f)  # read 4 byte, check for magic bytes
    f.seek(8)
    _check_mem(f)  # read 1 byte, check for memory byte

    header_len = _read_int(f)  # length of the xml header
    xml_header = f.read(header_len * 2).decode("utf-16")
    xml_root = BeautifulSoup(xml_header, 'xml')
    f.close()
    return xml_root, xml_header

## Converter of newer .lif images
class LifConverter(SeriesConverter):
    ## Constructor
    # @param filename: Name of the file
    def __init__(self,filename,setgrayscale):
        self.filename = filename
        self.data = LifFile(filename)
        self.lifmetadata, _ = get_xml(filename)
        self.lifmetadata = self.lifmetadata.find_all("Children")[0].find_all("Element")[::2]
        self.n_series = self.data.num_images
        self.setgrayscale = setgrayscale
        #LUT's
        self.GREEN = np.array([[0,i,0] for i in range(256)],dtype=np.uint8).T
        self.GRAY = np.array([[i,i,i] for i in range(256)],dtype=np.uint8).T

    def GetNImages(self):
        return self.n_series
        
    def GetNameAndResolution(self,idx):
        res =  float(self.lifmetadata[idx].find("ImageDescription").find_all("ChannelDescription")[0]["Resolution"])
        Name = self.lifmetadata[idx]["Name"]
        return Name, res
    
    def GetNumberofChannelsandSteps(self,idx):
        scanner_found = False
        channels = 2
        x = float(self.lifmetadata[idx].find("ImageDescription").find_all("DimensionDescription")[0]["Length"])
        xunit = "nm"
        y = float(self.lifmetadata[idx].find("ImageDescription").find_all("DimensionDescription")[1]["Length"])
        yunit = self.lifmetadata[idx].find("ImageDescription").find_all("DimensionDescription")[1]["Unit"]     
        return channels,x,xunit,y,yunit
          
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
        metadata["PhysicalSizeX"] = x * 1e9
        metadata["PhysicalSizeXUnit"] = xunit
        if yunit != 's' or self.setgrayscale:
            metadata["PhysicalSizeY"] = y
            metadata["PhysicalSizeYUnit"] = yunit if yunit != 's' else "nm"
            if yunit == "s":
                metadata["PhysicalSizeY"] *= 1e3
        else:
            metadata["TimeIncrement"] = y
            metadata["TimeIncrementUnit"] = yunit
        #find number of images in SERIES
        pages = []
        LUTs = []
        #write sequencially one by one
        img = self.data.get_image(idx)
        for j in range(channels):
            pages.append(np.array(img.get_plane(c = j)))
            if j == 0:
                metadata["PhysicalSizeX"] /= pages[j].shape[1]
                metadata["PhysicalSizeY"] /= pages[j].shape[0]
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