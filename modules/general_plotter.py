# Code Highlighter
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont
from PyQt5.QtCore import QRegExp, Qt

# Window
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QComboBox, QWidget, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QPlainTextEdit, QPushButton, QSpinBox, QMessageBox

# Plots
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Data 
import yaml
import sys
import numpy as np
import pandas as pd


# Later to be possible for multiple i guess

def general_plotter(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    app = QApplication(sys.argv)
    window = PlotWindow(config_dict)
    window.show()
    sys.exit(app.exec_())
    

    
    
class PlotWindow(QMainWindow):
    def __init__(self, config_dict):
        # get info from config
        directory_prefix = config_dict['directory_prefix']
        filename = config_dict['filename']
        codefile = config_dict['codefile'] if 'codefile' in config_dict else {"empty": ""}
        title = config_dict['title'] if 'title' in config_dict else 'General Plotter'
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
        
        self.canvas.setSizePolicy(1, 1)
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

        # Add a dropdown menu with example codes
        self.code_dropdown = QComboBox()
        self.code_dropdown.addItems(self.code_keys)
        layout.addWidget(self.code_dropdown)
        self.code_dropdown.textActivated.connect(self.update_code)
        
        
        # Add a text field for user code input
        self.code_input = QPlainTextEdit()
        self.code_input.setPlainText(self.code)
        self.code_input.setMinimumHeight(200)
        layout.addWidget(self.code_input)

        # Add syntax highlighting to the code input
        self.highlighter = CodeHighlighter(self.code_input.document())

        # Add a button to submit the code
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.submit_code)
        layout.addWidget(self.submit_button)
        
        # Add a label with the available variables
        self.variables_label = QLabel("Available variables: np, ax")
        layout.addWidget(self.variables_label)
        
        
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
            # Maybe a try must be added here in case the file does not yet exist
            data = pd.read_csv(self.datafile, sep='\t')
            self.keys = list(data.columns)
            self.variables = {key: data[key] for key in self.keys}
            self.variables['ax'] = self.ax
            self.variables['np'] = np
            self.variables_label.setText(f"Available variables: {', '.join(self.variables.keys())}")
            self.read_first_data = True
        
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
    def __init__(self, parent=None):
        super(CodeHighlighter, self).__init__(parent)
        self._highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(Qt.blue)
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ["def", "class", "import", "from", "for", "while", "if", "else", "elif", "return", "self"]
        self._highlighting_rules += [(QRegExp(r'\b' + keyword + r'\b'), keyword_format) for keyword in keywords]

        string_format = QTextCharFormat()
        string_format.setForeground(Qt.darkGreen)
        self._highlighting_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self._highlighting_rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(Qt.darkGray)
        self._highlighting_rules.append((QRegExp(r'#.*'), comment_format))
        

    def highlightBlock(self, text):
        for pattern, format in self._highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)