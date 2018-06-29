"""
TU RP1210 is a 32-bit Python 3 program that uses the RP1210 API from the 
American Trucking Association's Technology and Maintenance Council (TMC). This 
framework provides an introduction sample source code with RP1210 capabilities.
To get the full utility from this program, the user should have an RP1210 compliant
device installed. To make use of the device, you should also have access to a vehicle
network with either J1939 or J1708.

The program is release under one of two licenses.  See LICENSE.TXT for details. The 
default license is as follows:

    Copyright (C) 2018  Jeremy Daily, The University of Tulsa

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QTreeView,
                             QMessageBox,
                             QFileDialog,
                             QLabel,
                             QSlider,
                             QCheckBox,
                             QLineEdit,
                             QVBoxLayout,
                             QApplication,
                             QPushButton,
                             QTableWidget,
                             QTableView,
                             QTableWidgetItem,
                             QScrollArea,
                             QAbstractScrollArea,
                             QAbstractItemView,
                             QSizePolicy,
                             QGridLayout,
                             QGroupBox,
                             QComboBox,
                             QAction,
                             QDockWidget,
                             QDialog,
                             QFrame,
                             QDialogButtonBox,
                             QInputDialog,
                             QProgressDialog,
                             QTabWidget)
from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel, QCoreApplication, QSize
from PyQt5.QtGui import QIcon
import queue
import time
import os
import sys
import serial
import serial.tools.list_ports
import threading

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
#import matplotlib.pyplot as plt
import matplotlib.figure as mpl
import matplotlib.dates as md
import datetime as dt
import csv
import traceback

import logging
logger = logging.getLogger(__name__)

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) #Depends on matplotlib from graphing
markers = [ "D", "o", "v", "*", "^", "<", ">", "1", "2", "3", "4", "8", "s", "p", "P", "h", "H", "+", "x", "X", "d", "|"]


import logging
import logging.config

logging_dictionary = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "csv_format": {
            "class": "logging.Formatter",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "format": "{\"%(asctime)s,%(message)s\"},"
        },
        "simple": {
            "format": "%(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "file_handler": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "csv_format",
            "filename": "LoadStar_Log.json",
            "mode": "w",
            "encoding": "utf8"
        }
    },
    "loggers": {
        "": {
            "handlers": [
                "console",
                "file_handler"
            ],
            "level": "DEBUG",
            "propagate": True
        }
    }
}
logging.config.dictConfig(logging_dictionary)
logger = logging.getLogger(__name__)

class LoadStarLogger(QMainWindow):
    def __init__(self):
        super(LoadStarLogger,self).__init__()
        
        self.logfile = logging_dictionary["handlers"]["file_handler"]["filename"]
        logger.info("Session log file is {}".format(self.logfile))

        self.title = "LoadStar Logger"
        self.setWindowTitle("LoadStar Sensor Logger at TU")

        logger.info("Initializing a New Document")
        self.create_new(False)
        
        self.init_ui()

        logger.info("Setting up the Load cell  Serial System")
        self.loadcell = SerialDialog()
        if self.loadcell.connect_load_cell:
            self.setup_loadcell(dialog = False)
        
        #progress_label.setText("Loading the PDF Report Generator")
        #self.pdf_engine = FLAReportTemplate(self)

        read_timer = QTimer(self)
        read_timer.timeout.connect(self.update_plot)
        read_timer.start(250) #milliseconds
        self.voltage_graph.show()

    def init_ui(self):
        # Builds GUI
        # Start with a status bar
        self.statusBar().showMessage("Welcome!")

        self.grid_layout = QGridLayout()
        
        # Build common menu options
        menubar = self.menuBar()

        # File Menu Items
        file_menu = menubar.addMenu('&File')
        new_file = QAction(QIcon(r'icons/icons8_New_Ticket_48px.png'), '&New', self)
        new_file.setShortcut('Ctrl+N')
        new_file.setStatusTip('Create a new record.')
        new_file.triggered.connect(self.new_file)
        file_menu.addAction(new_file)

        open_file = QAction(QIcon(r'icons/icons8_Open_48px_1.png'), '&Open', self)
        open_file.setShortcut('Ctrl+O')
        open_file.setStatusTip('Open an existing data file.')
        open_file.triggered.connect(self.open_file)
        file_menu.addAction(open_file)

        save_file = QAction(QIcon(r'icons/icons8_Save_48px.png'), '&Save', self)
        save_file.setShortcut('Ctrl+S')
        save_file.setStatusTip('Save the current data file.')
        save_file.triggered.connect(self.save_file)
        file_menu.addAction(save_file)

        save_file_as = QAction(QIcon(r'icons/icons8_Save_as_48px.png'), 'Save &As...', self)
        save_file_as.setShortcut('Ctrl+Shift+S')
        save_file.setStatusTip('Save current data file with a new name.')
        save_file_as.triggered.connect(self.save_file_as)
        file_menu.addAction(save_file_as)


        exit_action = QAction(QIcon(r'icons/icons8_Close_Window_48px.png'), '&Quit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit the program.')
        exit_action.triggered.connect(self.confirm_quit)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        #build the entries in the dockable tool bar
        file_toolbar = self.addToolBar("File")
        file_toolbar.addAction(new_file)
        file_toolbar.addAction(open_file)
        file_toolbar.addAction(save_file)
        file_toolbar.addAction(save_file_as)
        file_toolbar.addSeparator()
        file_toolbar.addAction(exit_action)
        
       
        # loadcell
        # Create the container widget
        loadcell_box_area = QScrollArea()
        loadcell_box_area.setWidgetResizable(True)
        loadcell_box_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        loadcell_box = QFrame(loadcell_box_area)
        loadcell_box_area.setMinimumWidth(145)
        #loadcell_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        loadcell_box_area.setWidget(loadcell_box)
        loadcell_box_area.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        
        # create a layout strategy for the container 
        loadcell_layout = QVBoxLayout()
        #set the layout so labels are at the top
        loadcell_layout.setAlignment(Qt.AlignTop)
        #assign the layout strategy to the container
        loadcell_box.setLayout(loadcell_layout)
        
        #Add some labels and content
        self.loadcell_icon = QLabel("<html><img src='/icons/icons8_loadcell_Disconnected_48px.png'><br>Disconnected</html>")
        self.loadcell_icon.setAlignment(Qt.AlignCenter)
        
        self.loadcell_time_label = QLabel("loadcell Time:\nSearching...")
        self.loadcell_time_label.setAlignment(Qt.AlignCenter)
        
        #self.message_duration = 0
        self.loadcell_value_label = QLabel("Value:\nSearching...")
        self.loadcell_value_label.setAlignment(Qt.AlignCenter)
          
        loadcell_layout.addWidget(QLabel("<html><h3>loadcell Status</h3></html>"))
        loadcell_layout.addWidget(self.loadcell_icon)
        loadcell_layout.addWidget(self.loadcell_time_label)
        loadcell_layout.addWidget(self.loadcell_value_label)
        #loadcell_layout.addWidget(loadcell_setup_button)

        
        self.voltage_graph = GraphDialog(self, title="Load Cell Output")
        #self.voltage_graph.set_yrange(9, 15)
        self.voltage_graph.set_xlabel("Time")
        self.voltage_graph.set_ylabel("Load (lb)")
        self.voltage_graph.set_title("Loadstar Loadcell Time History")
        
        self.grid_layout.addWidget(loadcell_box_area,0,0,1,1)
        
        main_widget = QWidget()
        main_widget.setLayout(self.grid_layout)
        self.setCentralWidget(main_widget)
        
        self.show()
    
    # def get_plot_bytes(self, fig):
    #     img = BytesIO()
    #     fig.figsize=(7.5, 10)
    #     fig.savefig(img, format='PDF',)
    #     return img


    def create_new(self, new_file=True):

        self.load_history = []

        try:
            self.export_path = os.path.join(os.path.expanduser('~'),"Documents","{}".format(self.title))
            if not os.path.exists(self.export_path):
                os.makedirs(self.export_path)
        except FileNotFoundError:
            logger.debug(traceback.format_exc())
            self.export_path = os.path.expanduser('~')

        self.filename = os.path.join(self.export_path,
            "{} {}.log".format(self.title, time.strftime("%Y-%m-%d %H%M%S", time.localtime())))
        if new_file:
            fname = QFileDialog.getSaveFileName(self,
                                             "Create New {} Data File".format(self.title),
                                             os.path.join(self.export_path, self.filename),
                                             "",
                                             "")
            if not fname[0]:
                #the user pressed cancel
                return
        else: 
            fname=[False]
        
        if fname[0]:
            self.export_path, self.filename = os.path.split(fname[0])
        logger.info("Current Data Directory is set to {}".format(self.export_path))
        logger.info("Current Data Package file is set to {}".format(self.filename))

        
        

    def show_graphs(self):
        self.voltage_graph.show()

    def new_file(self):
        logger.debug("New File Selected.")
        self.create_new(True)

    def open_file(self):  
        """

        Returns: a tuple as (filename, data_dictionary)
                or 
                None if something went wrong.
        """  
        filters = "{} Data Files (*.csv);;All Files (*.*)".format(self.title)
        selected_filter = "{} Data Files (*.cpt)".format(self.title)
        fname = QFileDialog.getOpenFileName(self, 
                                            'Open File',
                                            self.export_path,
                                            filters,
                                            selected_filter)
        if fname[0]:
            try:
                pgp_file_contents = pgpy.PGPMessage.from_file(fname[0])
                logger.info("User opened signed file {}".format(fname[0]))
            except:
                err_msg = "File {} was not a properly formatted {} file.".format(self.filename, self.title)
                QMessageBox.warning(self, "File Format Error", err_msg)
                logger.info(err_msg)
                logger.debug(traceback.format_exc())
                return

            try:
                new_data_package = json.loads(pgp_file_contents.message)
                logger.info("Loaded data package from pgp file contents.")
            except KeyError:
                err_msg = "File {} was missing critical information.".format(fname[0])
                QMessageBox.warning(self, "File Format Error", err_msg)
                logger.debug(traceback.format_exc())
                logger.info(err_msg)
                return
            except:
                err_msg = "Failed to load data_package."
                QMessageBox.warning(self, "File Loading Error", err_msg)
                logger.debug(traceback.format_exc())
                logger.info(err_msg)
                return

            try:
                if pgp_file_contents.is_signed:
                    logger.debug("File is signed.")
                    verification = self.verify_stream(pgp_file_contents, self.user_data.private_key)
                else:
                    verification = False
                    logger.debug("File is not signed.")
            except:
                logger.debug(traceback.format_exc())
                verification = False

            if verification:
                logger.info("The file was verified with a PGP signature")
            else:
                new_data_package["Warnings"].append("File signature not verified.")
                err_msg = "File {} was not verified. It may have been altered or the verification key is invalid.".format(fname[0])
                warn = QMessageBox.warning(self, "File Format Error",
                                           err_msg + "\nWould you like to proceed anyways?",
                                           QMessageBox.Yes | QMessageBox.No,
                                           QMessageBox.No)
                logger.info(err_msg)
                if warn == QMessageBox.No:
                    return
            #if reload:    
            self.data_package = new_data_package
            self.export_path, self.filename = os.path.split(fname[0])
            self.setWindowTitle('{} {}.{} - {}'.format(self.title,
                                                       TU_RP1210_version["major"],
                                                       TU_RP1210_version["minor"],
                                                       self.filename))
            self.data_package["File Name"] = self.filename 
            self.reload_data()
            logger.info("Opened File: {}".format(self.filename))
            logger.info("Export Path: {}".format(self.export_path))
            return (fname[0], new_data_package)   
        
    
    def save_file(self, backup=False):
        """
        Save the file as a CPT (short for TruckCRYPT) file to the
        current path. 
        """

        if backup:
            temp_name = os.path.basename(self.filename)
            temp_name.strip("Backup_")
            backup_name = "Backup_{}".format(temp_name)
            filename = os.path.normpath(os.path.join(self.export_path, backup_name))
        else:
            filename = os.path.normpath(os.path.join(self.export_path, self.filename))
            self.data_package["File Name"] = self.filename

        progress_label = QLabel("Saving and signing {} file to {}".format(self.title,filename))
        progress.setLabel(progress_label)

        saved_pgp_message = self.user_data.make_pgp_message(self.data_package)
        with open(filename,'w') as file_out:
            file_out.write(str(saved_pgp_message))

        if not backup:
            with open(filename[:-3] + 'json', 'w') as outfile:
                outfile.write(saved_pgp_message.message)
            msg = "Saved signed file to {}".format(filename)
            logger.info(msg)
            self.filename = os.path.basename(self.filename)
            self.setWindowTitle('{} {}.{} - {}'.format(self.title,
                                                       TU_RP1210_version["major"],
                                                       TU_RP1210_version["minor"],
                                                       self.filename))
            self.statusBar().showMessage(msg)
        progress.setValue(1)
        
        #CAN Logs
        progress_label.setText("Saving and signing CAN logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["can_handler"]["filename"],
                                             " CAN Log", 
                                             "CAN Log File")
        progress.setValue(2)
        
        progress_label.setText("Saving and signing J1708 logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["j1708_handler"]["filename"],
                                             " J1708 Log", 
                                             "J1708 Log File")
        progress.setValue(3)
        
        
        # Session Logs
        progress_label.setText("Saving and signing session debug logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["file_handler"]["filename"],
                                         " Session Log", 
                                         "Session Log File")
        progress.setValue(4)
        progress_label.setText("Done with saving and signing all the user files.")
        QCoreApplication.processEvents()
        
        self.Components.rebuild_trees()
        return saved_pgp_message
    
    
    def save_file_as(self):
        filters = "{} Data Files (*.cpt);;All Files (*.*)".format(self.title)
        selected_filter = "{} Data Files (*.cpt)".format(self.title)
        fname = QFileDialog.getSaveFileName(self, 
                                            'Save File As',
                                            os.path.join(self.export_path,self.filename),
                                            filters,
                                            selected_filter)
        if fname[0]:
            if fname[0][-4:] ==".cpt":
                self.filename = fname[0]
            else:
                self.filename = fname[0]+".cpt"
            self.export_path, self.filename = os.path.split(fname[0])
            return self.save_file()
    
    
    def confirm_quit(self):
        self.close()
    
    def closeEvent(self, event):
        result = QMessageBox.question(self, "Confirm Exit",
            "Are you sure you want to quit the program?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes)
        if result == QMessageBox.Yes:
            logger.debug("Quitting.")
            event.accept()
        else:
            event.ignore()
   
    def setup_loadcell(self, dialog=True):
        
        logger.debug("Setup loadcell with file.")
        success = self.loadcell.try_loadcell()
        if not success:
            logger.debug("Setup loadcell with dialog box.")
            self.loadcell.run()
        
        if self.loadcell.connected:


            self.loadcell_icon.setText("<html><img src='/icons/icons8_loadcell_Signal_48px.png'><br>Connected on {}</html>".format(self.loadcell.ser.port))
             
            self.loadcell_queue = queue.Queue()
            self.loadcell_thread = loadcellThread(self.loadcell_queue,self.loadcell.ser)
            self.loadcell_thread.setDaemon(True) #needed to close the thread when the application closes.
            self.loadcell_thread.start()
            logger.debug("Started loadcell Thread.")

        else:
            logger.debug("Setup loadcell Failed.")
            self.loadcell_icon.setText("<html><img src='/icons/icons8_loadcell_Disconnected_48px.png'><br>Disconnected</html>")

        
    def update_plot(self):
        while self.loadcell_queue.qsize() > 0:
            self.load_history.append(self.loadcell_queue.get())
        
        self.voltage_graph.add_data(self.load_history, 
                    marker = '.', 
                    label = "Load")
        self.voltage_graph.plot()  

class loadcellThread(threading.Thread):
    '''This thread is designed to receive messages from a load_cell,
       using the MicroPyload_cell https://github.com/inmcm/micropyload_cell
    '''

    def __init__(self, rx_queue, serial_port):
        threading.Thread.__init__(self)
        self.rx_queue = rx_queue
        self.ser = serial_port
        self.runSignal = True
        self.message = None
        
        logger.debug("Started load_cellThread on {}".format(self.ser.port))

    def run(self):
        while self.runSignal:
            time.sleep(0.001)
            try:
                new_load = float(self.ser.readline()[1:].decode('ascii','ignore').strip())/1000
                #logger.debug(new_load)
                self.rx_queue.put((time.time(),new_load))
            except ValueError:
                pass
            except:
                logger.debug("Error within load_cell Read Thread.")
                logger.debug(traceback.format_exc())
                break
            
        logger.debug("load_cell Receive Thread is finished.")


class SerialDialog(QDialog):
    def __init__(self):
        super(SerialDialog,self).__init__()
        #self.root = parent
        self.baudrate = 4800
        self.comport = "COM1"
        self.setup_dialog()
        self.setWindowTitle("Select Load Cell COM Port")
        self.setWindowModality(Qt.ApplicationModal)
        self.connected = False
        self.ser = None
        self.load_cell_settings_file = "load_cell_setting.txt"


    def setup_dialog(self):

        load_cell_port_label = QLabel("load_cell Communications Port")
        self.load_cell_port_combo_box = QComboBox()
        self.load_cell_port_combo_box.setInsertPolicy(QComboBox.NoInsert)
        for device in sorted(serial.tools.list_ports.comports(), reverse = True):
            self.load_cell_port_combo_box.addItem("{} - {}".format(device.device, device.description))
        self.load_cell_port_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        baud_list = ["{}".format(b) for b in [4800, 9600, 115200, 1200, 1800, 2400, 19200, 38400, 57600, 115200, 
                     230400, 460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 
                     2000000, 2500000, 3000000, 3500000, 4000000]]

        baud_label = QLabel("load_cell Baud Rate")
        self.baud_combo_box = QComboBox()
        self.baud_combo_box.setInsertPolicy(QComboBox.NoInsert)
        self.baud_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.baud_combo_box.addItems(baud_list)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.set_load_cell)
        #self.rejected.connect(self.reject_load_cell)

        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(load_cell_port_label)
        self.v_layout.addWidget(self.load_cell_port_combo_box)
        self.v_layout.addWidget(baud_label)
        self.v_layout.addWidget(self.baud_combo_box)
        self.v_layout.addWidget(self.buttons)

        self.setLayout(self.v_layout)
    
    def run(self):
        self.load_cell_port_combo_box.clear()
        for device in sorted(serial.tools.list_ports.comports(), reverse = True):
            self.load_cell_port_combo_box.addItem("{} - {}".format(device.device, device.description))
        self.load_cell_port_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.exec_()

    def set_load_cell(self): 
        self.comport = self.load_cell_port_combo_box.currentText().split('-')[0].strip()
        self.baud = int(self.baud_combo_box.currentText())
        return self.connect_load_cell()

    def connect_load_cell(self): 
        logger.debug("Trying to connect load_cell.")
        try:
            self.ser.close()
            del self.ser
        except AttributeError:
            pass

        try:
            self.ser = serial.Serial(self.comport, baudrate=self.baud, timeout=2)
        except serial.serialutil.SerialException:
            logger.debug(traceback.format_exc())
            if "PermissionError" in repr(traceback.format_exc()):
                QMessageBox.information(self,"load_cell Status","The port {} is already in use. Please unplug and replug the load cell unit.".format(self.comport))
            else:
                self.connected = False
                return False
        try:
            self.ser.write("CT0\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
            self.ser.readline()
            time.sleep(.1)
            self.ser.write("SS1\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
            test_sentence = self.ser.readline().decode('ascii','ignore').strip()
            logger.info("Connected to {}".format(test_sentence))
            

            if len(test_sentence) > 0:
                logger.info("Successful load cell connection on {}".format(self.comport))
                with open(self.load_cell_settings_file,"w") as out_file:
                    out_file.write("{},{}\n".format(self.comport, self.baud))
                self.connected = True
                #self.ser.write("CPS 32\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
                #self.ser.readline()
                self.ser.write("CSS 5\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
                self.ser.readline()
                self.ser.write("CLA 1\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
                self.ser.readline()
                self.ser.write("O0W0\r".encode('ascii')) # see http://www.loadstarsensors.com/assets/manuals/html/iload_commmand_set.html
        
                return True
            else:
                logger.debug("Could not find load cell connection on {}".format(self.comport))
                QMessageBox.information(self,"No Connection","Could not find load_cell connection on {}".format(self.comport))
                self.connected = False
                return False
        except:
            logger.debug(traceback.format_exc())
            return False

    def try_loadcell(self):
        try:
            with open(self.load_cell_settings_file, "r") as in_file:
                lines = in_file.readlines()
            line_list = lines[0].split(",")
            self.comport = line_list[0]
            self.baud = line_list[1]
            self.connected = self.connect_load_cell()

        except FileNotFoundError:
            self.connected = False
        return self.connected 


def get_plot_bytes(self, fig):
    """
    A helper function to produce a bytestream from a matplotlib figure
    """
    img = BytesIO()
    fig.figsize=(7.5, 8.5) #inches
    fig.savefig(img, format='PDF',)
    return img
 
class GraphDialog(QDialog):
    def __init__(self, parent, title="Graph"):
        super(GraphDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.figure = mpl.Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.data = {}
        self.root = parent
        self.ax = self.figure.add_subplot(111)
        self.ymin = None
        self.ymax = None
        self.x_label = ""
        self.y_label = ""
        self.title = ""

        self.update_button = QCheckBox("Dynamically Update Table")
        self.update_button.setChecked(True)

        self.clear_button = QPushButton("Clear Data")
        self.clear_button.clicked.connect(self.clear_data)
        
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.update_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.toolbar)
        self.setLayout(layout)
        #self.show()
    
    def clear_data(self):
        self.data = {}
        self.root.load_history=[]
        self.plot()
        logger.debug("Cleared Graph")

    def export_data(self):
        csv_string = ''
        for key, value in self.data.items():
            csv_string += "Time,{}\n".format(key)
            for x,y in zip(value["X"],value["Y"]):
                csv_string += "{},{}\n".format(x,y)
            csv_string += "\n\n"
        
        filters = "{} Data Files (*.csv);;All Files (*.*)".format(self.root.title)
        selected_filter = "{} Data Files (*.csv)".format(self.root.title)
        fname = QFileDialog.getSaveFileName(self, 
                                            'Save File As',
                                            '',
                                            filters,
                                            selected_filter)
        if fname[0]:
            if fname[0][-4:] ==".csv":
                self.filename = fname[0]
            else:
                self.filename = fname[0]+".csv"
            self.export_path, self.filename = os.path.split(fname[0])
            with open(fname[0],'w') as f:
                f.write(csv_string)

    def plot(self):
        ''' plot data '''
        self.ax.cla()
        #self.ax.hold(False)
        for key, value in self.data.items():
            self.ax.plot(value["X"],value["Y"],value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
        self.ax.xaxis.set_major_formatter(xfmt)
        self.figure.autofmt_xdate()
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()
    
    def plot_xy(self):
        self.ax.cla()
        #self.ax.hold(False)
        for key, value in self.data.items():
            self.ax.plot(value["X"], value["Y"], value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()
    
    def add_data(self, data, marker='*-', label=""):
        x, y = zip(*data) #unpacks a list of tuples
        dates = [dt.datetime.fromtimestamp(ts) for ts in x]
        self.data[label] = {"X": dates, "Y": y, "Marker": marker}
    
    def add_xy_data(self, data, marker='*-', label=""):
        x, y = zip(*data) #unpacks a list of tuples
        # logger.debug("X data:")
        # logger.debug(x)
        # logger.debug("Y data:")
        # logger.debug(y)

        self.data[label] = {"X": [float(val) for val in x], 
                            "Y": [float(val) for val in y], 
                            "Marker": marker}
        

    def set_yrange(self,min_y, max_y):
        self.ymax = max_y
        self.ymin = min_y
            
    
    def set_xlabel(self,label):
        self.x_label = label
    
    def set_ylabel(self,label):
        self.y_label = label
    
    def set_title(self,label):
        self.title = label
    
class GraphTab(QWidget):
    def __init__(self, parent=None, tabs=None, tab_name="Graph Tab"):
        super(GraphTab, self).__init__(parent)
        logger.debug("Setting up Graph Tab.")
        self.root = parent
        self.tabs = tabs
        self.tab_name = tab_name
        self.data_list=[]
        self.init_ui()
    
    def init_ui(self):
        self.graph_tab = QWidget()
        self.tabs.addTab(self.graph_tab, self.tab_name)
        logger.debug("Making Attribution Box")
        attribution_box = QGroupBox("Event Attribution Data")
        tab_layout = QGridLayout()
        self.graph_tab.setLayout(tab_layout)

        self.event_name_label = QLabel("Name of Event: ")
        self.ecm_rtc_label = QLabel("ECM Real Time Clock at Event: ")
        self.actual_rtc_label = QLabel("Actual Real Time Clock at Event: ")
        self.engine_hours_label = QLabel("Engine Hours at Event: ")
        self.odometer_label = QLabel("Distance Reading at Event: ")

        attribution_layout = QVBoxLayout()
        attribution_layout.addWidget(self.event_name_label)
        attribution_layout.addWidget(self.ecm_rtc_label)
        attribution_layout.addWidget(self.actual_rtc_label)
        attribution_layout.addWidget(self.engine_hours_label)
        attribution_layout.addWidget(self.odometer_label)
        attribution_box.setLayout(attribution_layout)
        logger.debug("Finished Setting Attribution Layout")
        
        self.data_table = QTableWidget()
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectColumns)
        logger.debug("Finished with Data Table")
        
        self.csv_button = QPushButton("Export CSV")
        self.csv_button.clicked.connect(self.export_csv)
        logger.debug("Finished with CSV")

        self.figure = mpl.Figure(figsize=(7,9))
        self.canvas = FigureCanvas(self.figure)
        self.top_axis = self.figure.add_subplot(3,1,1)
        self.top_axis.set_ylabel("Road Speed (mph)")
        self.middle_axis = self.figure.add_subplot(3,1,2)
        self.middle_axis.set_ylabel("Throttle Position (%)")
        self.bottom_axis = self.figure.add_subplot(3,1,3)
        self.bottom_axis.set_ylabel("Brake Switch Status")
        self.bottom_axis.set_xlabel("Event Time (sec)")
        self.canvas.draw()

        self.toolbar = NavigationToolbar(self.canvas, self.graph_tab)
        logger.debug("Finished with toolbar")

        # set the layout
        
        tab_layout.addWidget(attribution_box,0,0,1,1)
        tab_layout.addWidget(self.data_table,1,0,1,1)
        tab_layout.addWidget(self.csv_button,2,0,1,1)
        tab_layout.addWidget(self.canvas,0,1,2,1)
        tab_layout.addWidget(self.toolbar,2,1,1,1) 
        
        logger.debug("Finished with UI for Tab {}".format(self.tab_name))

    def export_csv(self):
        logger.debug("Export CSV")
        filters = "Comma Separated Values (*.csv);;All Files (*.*)"
        selected_filter = "Comma Separated Values (*.csv)"
        fname = QFileDialog.getSaveFileName(self, 
                                            'Export CSV',
                                            self.tab_name + ".csv",
                                            filters,
                                            selected_filter)
        if fname[0]:
            if fname[0][-4:] ==".csv":
                filename = fname[0]
            else:
                filename = fname[0]+".csv"
            try:
                with open(filename,'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["The University of Tulsa"])

                    writer.writerow(["Date of Creation:", "{}".format(get_local_time_string(time.time()))])
                    
                    
                    writer.writerows(['',["Vehicle Component Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["Component Information"]))

                    writer.writerows(['',["Vehicle Distance Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["Distance Information"]))

                    writer.writerows(['',["Vehicle Time Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["ECU Time Information"]))


                    writer.writerows(['',["Event Attribution Data"]])
                    writer.writerow([''] + self.event_name_label.text().split(": "))
                    writer.writerow([''] + self.ecm_rtc_label.text().split(": "))
                    writer.writerow([''] + self.actual_rtc_label.text().split(": "))
                    writer.writerow([''] + self.engine_hours_label.text().split(": "))
                    writer.writerow([''] + self.odometer_label.text().split(": "))
                    writer.writerows(['',["Event Table Data"]])
                    writer.writerows(self.data_list)

                    writer.writerows(['',["User Data"]])
                    writer.writerows(self.root.user_data.get_user_data_list())
                self.root.sign_file(filename)
                base_name = os.path.basename(filename)
                QMessageBox.information(self,"Export Success","The comma separated values file\n{}\nwas successfully exported. A verification signature was also saved as\n{}.".format(base_name,base_name+".signature"))
            
            except PermissionError:
                logger.info("Permission Error - Please close the file and try again.")
                QMessageBox.warning(self,"Permission Error","Permission Error\nThe file may be open in another application.\nPlease close the file and try again.")
            
    

    def update_plot_xy(self):
        for key, value in self.data.items():
            self.ax.plot(value["X"], value["Y"], value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    execute = LoadStarLogger()
    sys.exit(app.exec_())