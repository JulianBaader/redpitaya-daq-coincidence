# Code Highlighter
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt5.QtCore import QRegExp, Qt

# Window
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QComboBox, QWidget, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QPlainTextEdit, QPushButton, QSpinBox, QMessageBox, QSizePolicy, QSizeGrip

# Plots
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Data 
import yaml
import sys
import numpy as np
import pandas as pd

def general_plotter(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    """
    General Plotter module. This module is used to plot data from a txt file in real time.
    It is to be called as a mimocorb function. The function will create a window with a plot and a text field for code input.
    """
    app = QApplication(sys.argv)
    window = PlotWindow(config_dict)
    window.show()
    sys.exit(app.exec_())
    
class PlotWindow(QMainWindow):
    def __init__(self, config_dict):
        # get info from config
        directory_prefix = config_dict['directory_prefix']
        filename = config_dict['filename']
        codefile = config_dict['codefile'] if 'codefile' in config_dict else {"help": "Here you can write your own code.\nThe variables listed below are already accesible.\nThe code will be executed in every frame of the animation after you hit submit."}
        title = config_dict['title'] if 'title' in config_dict else 'General Plotter'
        self.set_variables = config_dict['set_variables'] if 'set_variables' in config_dict else {}
        self.datafile = directory_prefix + filename + '.txt'
        with open(codefile) as f:
            self.code_dict = yaml.safe_load(f)
        
        self.code_keys = list(self.code_dict.keys())
        self.code = self.code_dict[self.code_keys[0]]
        self.error_in_code = False
        self.read_first_data = False
        
        # interval between plot updates in ms
        self.minimal_interval = 200
        self.maximal_interval = 10000
        self.current_interval = 500 # starting value

        super().__init__()
        
        self.setWindowTitle(title)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        #crete figure and init UI and start animation
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        
        self.initUI()
        
        self.ani = animation.FuncAnimation(self.figure, self.update_plot, interval=self.current_interval,cache_frame_data=False)
        
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas)
        
        # Add a number box to set the interval of FuncAnimation
        interval_layout = QHBoxLayout()
        interval_label = QLabel(f"Animation Interval ({self.minimal_interval} - {self.maximal_interval} ms):")
        self.interval_spinbox = QSpinBox()

        self.interval_spinbox.setRange(self.minimal_interval, self.maximal_interval)
        self.interval_spinbox.setValue(self.current_interval)
        
        self.interval_spinbox.valueChanged.connect(self.update_interval)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spinbox)
        layout.addLayout(interval_layout)
        
        # Add Code controll
        # Add a dropdown menu with example codes
        self.code_dropdown = QComboBox()
        self.code_dropdown.addItems(self.code_keys)
        layout.addWidget(self.code_dropdown)
        self.code_dropdown.textActivated.connect(self.update_code)
        # Add a button to hide the code
        self.hide_button = QPushButton("Hide Code")
        self.hide_button.clicked.connect(self.hide_code)
        # Layout
        code_control_layout = QHBoxLayout()
        code_control_layout.addWidget(self.code_dropdown)
        code_control_layout.addWidget(self.hide_button)
        layout.addLayout(code_control_layout)
        
        # Add a text field for user code input
        self.code_input = QPlainTextEdit()
        self.code_input.setPlainText(self.code)
        self.code_input.setMinimumHeight(200)
        layout.addWidget(self.code_input)

        # Add a button to submit the code
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_code)
        layout.addWidget(self.submit_button)
        
        
        # Add a label with the available variables
        self.variables_label = QLabel("Available variables: np, ax")
        layout.addWidget(self.variables_label)
        
        # Add QSizeGrip to the bottom-right corner
        size_grip = QSizeGrip(self)
        layout.addWidget(size_grip, 0, Qt.AlignBottom | Qt.AlignRight)
        
        self.hide_code()
        
    def hide_code(self):
        is_hidden = self.code_input.isHidden()
        self.code_input.setHidden(not is_hidden)
        self.variables_label.setHidden(not is_hidden)
        self.submit_button.setHidden(not is_hidden)
        if self.code_input.isHidden():
            self.hide_button.setText("Show Code")
        else:
            self.hide_button.setText("Hide Code")

    def submit_code(self):
        self.code = self.code_input.toPlainText()
        self.error_in_code = False

    def update_code(self, key):
        self.code_input.setPlainText(self.code_dict[key])
        self.code = self.code_dict[key]
        self.error_in_code = False
    
    def update_interval(self, value):
        self.current_interval = value
        self.ani.event_source.interval = self.current_interval  
    
    def update_plot(self, frame):
        if not self.read_first_data:
            data = pd.read_csv(self.datafile, sep='\t') # Maybe a try must be added here in case the file does not yet exist
            self.keys = list(data.columns)
            self.variables = {key: data[key] for key in self.keys}
            self.variables['ax'] = self.ax
            self.variables['np'] = np
            for key, value in self.set_variables.items():
                self.variables[key] = value
            variable_names = self.variables.keys()
            self.variables_label.setText(f"Available variables: {', '.join(variable_names)}")
            self.read_first_data = True
            
            # Add syntax highlighting to the code input
            self.highlighter = CodeHighlighter(self.code_input.document(), list(variable_names))
        
        # update variables
        data = pd.read_csv(self.datafile, sep='\t')
        for key in self.keys:
            self.variables[key] = data[key]
        self.ax.clear()
        if not self.error_in_code:
            try:
                exec(self.code, self.variables)
            except Exception as e:
                self.error_in_code = True
                QMessageBox.critical(self, "Code Error", str(e))

        self.canvas.draw()
        
        
        
        
class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, variable_names=None):
        super(CodeHighlighter, self).__init__(parent)
        self._highlighting_rules = []

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.blue)
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def','del',
            'elif', 'else', 'except', 'exec', 'finally','for', 'from', 
            'global', 'if', 'import', 'in','is', 'lambda', 'not', 'or', 
            'pass', 'print','raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False']
        self._highlighting_rules += [(QRegExp(r'\b' + keyword + r'\b'), keyword_format) for keyword in keywords]

        # Operators
        operator_format = QTextCharFormat()
        operator_format.setForeground(Qt.darkYellow)
        operators = ['=','==', '!=', '<', '<=', '>', '>=','\+', '-', 
                     '\*', '/', '//', '\%', '\*\*', '\+=', '-=', '\*=', 
                     '/=', '\%=',  '\^', '\|', '\&', '\~', '>>', '<<']
        self._highlighting_rules += [(QRegExp(r'\b' + operator + r'\b'), operator_format) for operator in operators]
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(Qt.darkGreen)
        self._highlighting_rules.append((QRegExp(r'\b[+-]?[0-9]+[lL]?\b'), number_format))
        self._highlighting_rules.append((QRegExp(r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b'), number_format))
        self._highlighting_rules.append((QRegExp(r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b'), number_format))
        
        # String
        string_format = QTextCharFormat()
        string_format.setForeground(Qt.red)
        self._highlighting_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self._highlighting_rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # Imported variables
        if variable_names is not None:
            variable_format = QTextCharFormat()
            variable_format.setForeground(Qt.blue)
            self._highlighting_rules += [(QRegExp(r'\b' + variable + r'\b'), variable_format) for variable in variable_names]

        # Comment
        comment_format = QTextCharFormat()
        comment_format.setForeground(Qt.green)
        self._highlighting_rules.append((QRegExp(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self._highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)