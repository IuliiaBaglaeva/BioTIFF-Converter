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
        self.lifmetadata = self.lifmetadata.find_all("Children").find_all("Element")[::2]
        self.n_series = self.data.num_images
        self.setgrayscale = setgrayscale
        #LUT's
        self.GREEN = np.array([[0,i,0] for i in range(256)]).T

    def GetNImages(self):
        return self.n_series
        
    def GetNameAndResolution(self,idx):
        res =  float(self.lifmetadata.find("ImageDescription").find_all("ChannelDescription")[0]["Max"])
        Name = self.lifmetadata[idx]["Name"]
        return Name, res
    
    def GetNumberofChannelsandSteps(self,idx):
        scanner_found = False
        channels = 2
        x = self.lifmetadata[idx].find("ImageDescription").find_all("DimensionDescription")[0]
        xunit = "nm"
        y = self.lifmetadata[idx].find("ImageDescription").find_all("DimensionDescription")[1]
        yunit = "nm"        
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