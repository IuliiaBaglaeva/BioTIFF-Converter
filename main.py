from LEIConverter import LeiConverter
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QCheckBox, QLabel, QPushButton, QFileDialog, QProgressBar, qApp, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool
import sys
import os
import traceback

## Class, which defines the Qt signals available from a running worker thread
class WorkerSignals(QObject):

    progress = pyqtSignal(int)
    error = pyqtSignal(tuple)
    finished = pyqtSignal()


## Worker thread used for not freezing the UI while the file is being converted
class ConversionThread(QRunnable):

    def __init__(self, filename,out_dir,setgrayscale):
        super(ConversionThread, self).__init__()
        self.filename = filename
        self.signals = WorkerSignals()
        self.out_folder = out_dir
        self.setgray = setgrayscale
        self.num_of_images = 0

    def run(self):
        
        try:
            self.converter = LeiConverter(filename=self.filename,setgrayscale = self.setgray)
            self.num_of_images = self.converter.n_series
            i = 0
            while i < self.num_of_images:
                print(i)
                new_img = self.converter.ConvertImage(i,self.out_folder)
                progress_int = int((i+1)/self.num_of_images * 100) if i < self.num_of_images - 1 else 100
                self.signals.progress.emit(progress_int)
                i += 1
            self.signals.finished.emit()
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        '''
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
            '''
            
## Class, which defines the GUI
class MainWindow(QMainWindow):
    ## The Constructor. All widgets are initialized and connected with slots here.
    def __init__(self,*args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('window.ui', self)
        #self.setWindowIcon(QIcon("BMC.png"))
        ## File name
        self.filename = ""
        self.path = ""
        ## Associative array (std::map<>, dictionary) of conversion parameters with its values
        ## QLabel reporting the state of input images
        self.label_input = self.findChild(QLabel, 'LabelInput')
        ## QLabel reporting the state of the conversion
        self.label_convertation = self.findChild(QLabel, 'LabelOutput')
        ## QPushButton for choosing the file in commercial format
        self.button_input = self.findChild(QPushButton, 'ButtonInput')
        self.button_input.clicked.connect(self.ChooseImage)
        ## QPushButton for starting the conversion into TIFFs
        self.button_input = self.findChild(QPushButton, 'ButtonOutput')
        self.button_input.clicked.connect(self.StartConversion)
        ## QProgressBar, shows the progress of the  conversion
        self.progress_bar = self.findChild(QProgressBar, 'progressBar')
        self.GrayCheckBox = self.findChild(QCheckBox,'GrayScaleCheckBox')
        
        self.threadpool = QThreadPool()
    
    ## Slot, which defines the name of the input image  
    def ChooseImage(self):
        filename = QFileDialog.getOpenFileName(self,"Open File",self.path,"Leica Microsystems (*.lif *.lei);; Zeiss (*.mdb)") [0]
        if filename != "":
            self.filename = filename
            self.path, file = os.path.split(os.path.abspath(filename))
            self.label_input.setText(f"Current image is {file}")
    
    def ShowProgress(self,score):
        self.progress_bar.setValue(score)
        
    def WorkIsFinished(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("Conversion is finished")
        msg.setWindowTitle("Message")
        msg.setStandardButtons(QMessageBox.Ok)
    # Slot, which starts the conversion
    def StartConversion(self):
        if self.filename == "":
            return
        out_directory = QFileDialog.getExistingDirectory(self,"Choose the directory for converted files",self.path)
        if out_directory == "":
            return
        print(out_directory)
        self.progress_bar.setValue(0)
        worker = ConversionThread(self.filename,out_directory,self.GrayCheckBox.isChecked())
        worker.signals.progress.connect(self.ShowProgress)
        worker.signals.finished.connect(self.WorkIsFinished)
        # Execute
        self.threadpool.start(worker) 
                
    
def main():
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()