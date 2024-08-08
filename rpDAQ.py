import numpy as np
import struct
import sys
import time
import socket
import matplotlib.pyplot as plt

command_dictionary = {
    0: "reset histogram",
    1: "reset timer",
    2: "reset oscilloscope", 
    3: "reset generator",
    4: "set sample rate",
    5: "set negator mode (0 for disabled, 1 for enabled)",
    6: "set pha delay",
    7: "set pha threshold min",
    8: "set pha threshold max",
    9: "set timer",
    10: "set timer mode (0 for stop, 1 for running)",
    11: "read status", 
    12: "read histogram",
    13: "set trigger source (0 for channel 1, 1 for channel 2)", 
    14: "set trigger slope (0 for rising, 1 for falling)",
    15: "set trigger mode (0 for normal, 1 for auto)",
    16: "set trigger level",
    17: "set number of samples before trigger",
    18: "set total number of samples",
    19: "start oscilloscope",
    20: "read oscilloscope data",
    21: "set fall time",
    22: "set rise time",
    23: "set lower limit",
    24: "set upper limit",
    25: "set rate",
    26: "set probability distribution",
    27: "reset spectrum",
    28: "set spectrum bin",
    29: "start generator",
    30: "stop generator",
    31: "start daq",
    32: "drain daq"
}

SAMPLE_RATES = [1, 4, 8, 16, 32, 64, 128, 256]
TRIGGER_SOURCES = {1: 0, 2: 1}
TRIGGER_SLOPES = {"rising": 0, "falling": 1}
TRIGGER_MODES = {"normal": 0, "auto": 1}
MAXIMUM_SAMPLES = 8388607 #TODO überprüfen
ADC_RANGE = 4095 #TODO prob -4095 bis 4096 oder so ach keine Ahnung
GENERATOR_BINS = 4096
DISTRIBUTIONS = {'uniform': 0, 'poisson': 1}

np.set_printoptions(threshold=1000)

generator_array = np.zeros(GENERATOR_BINS, np.uint32)
for i in range(16):  # initialize with delta-functions
    generator_array[(i + 1) * 256 - 1] = 1

        
class rpCommunication:
    def __init__(self ,config_dict = {}):
        self.load_config_from_dict(config_dict)
        self.check_config()
        

        # oscilloscope buffer
        self.osc_buffer = np.zeros(2 * self.total_samples, np.int16)
        self.osc_buffer_view = self.osc_buffer.view(np.uint8)
        self.SIZE = self.osc_buffer_view.size
        
        # daq
        self.daq_counter = 0
        self.total_daq = 0
        self.min_daq_counter = 100
        self.daq_count_step = 1000
        
        # socket
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(5)
        
        
        self.setup_general()
        self.setup_oscilloscope()
        self.setup_generator() #TODO test if überhaupt gewünscht
        
        #self.start_first_osc()

        
        self.main()
        
        
    def command(self, code, number, value):
        self.socket.sendall(struct.pack("<Q", code << 56 | number << 52 | (int(value) & 0xFFFFFFFFFFFFF)))
        
            

    
    def main(self):
        self.command(2, 0, 0)
        self.command(19, 0, 0)

        time.sleep(5)
        self.command(20, 0, 0)
        data = self.socket.recv(self.SIZE)
        view = np.frombuffer(data, np.uint8)
        real = view.view(np.int16)
        print(real)
        
        
        

                

            
            
    # -> Functions for setting up the RedPitaya
            
    def setup_general(self):
        self.command(4, 0, self.sample_rate)
        self.command(5, 0, int(self.ch1_negated))
        self.command(5, 1, int(self.ch2_negated))
            
    def setup_oscilloscope(self):
        self.command(13, 0, TRIGGER_SOURCES[self.trigger_source])
        self.command(14, 0, TRIGGER_SLOPES[self.trigger_slope])
        self.command(15, 0, TRIGGER_MODES[self.trigger_mode])
        self.command(16, 0, self.trigger_level)
        self.command(17, 0, self.pretrigger_samples)
        self.command(18, 0, self.total_samples)
            
    def setup_generator(self):
        self.command(30, 0, 0) # stop generator
        self.command(3, 0, 0) # reset generator
        for value in np.arange(GENERATOR_BINS, dtype=np.uint64) << 32 | self.spectrum:
            self.command(28, 0, value)
        self.command(21, 0, self.fall_time)
        self.command(22, 0, self.rise_time)
        self.command(25, 0, self.pulse_rate)
        self.command(26, 0, DISTRIBUTIONS[self.distribution])
        self.command(29, 0, 0) # start generator
        
    # <- Functions for setting up the RedPitaya
    
    # -> Functions for reading the config dict
        
    def load_config_from_dict(self, config_dict):
        # general configuration
        self.ip = config_dict["ip"] if "ip" in config_dict else "rp-f0c38f.local"
        self.port = config_dict["port"] if "port" in config_dict else 1001
        self.sample_rate = config_dict["sample_rate"] if "sample_rate" in config_dict else 4
        self.ch1_negated = config_dict["ch1_negated"] if "ch1_negated" in config_dict else False
        self.ch2_negated = config_dict["ch2_negated"] if "ch2_negated" in config_dict else False
        
        # oscilloscope configuration
        self.trigger_source = config_dict["trigger_source"] if "trigger_source" in config_dict else 1
        self.trigger_slope = config_dict["trigger_slope"] if "trigger_slope" in config_dict else "rising"
        self.trigger_mode = config_dict["trigger_mode"] if "trigger_mode" in config_dict else "normal"
        self.trigger_level = config_dict["trigger_level"] if "trigger_level" in config_dict else 500
        self.pretrigger_samples = config_dict["pretrigger_samples"] if "pretrigger_samples" in config_dict else 100
        self.total_samples = config_dict["total_samples"] if "total_samples" in config_dict else 1000

        # generator configuration
        self.fall_time = config_dict["fall_time"] if "fall_time" in config_dict else 10
        self.rise_time = config_dict["rise_time"] if "rise_time" in config_dict else 50
        self.pulse_rate = config_dict["pulse_rate"] if "pulse_rate" in config_dict else 1000
        self.distribution = config_dict["distribution"] if "distribution" in config_dict else 'poisson'
        self.spectrum = config_dict["spectrum"] if "spectrum" in config_dict else generator_array #TODO das ist nicht so schön
        self.start_generator = config_dict["start_generator"] if "start_generator" in config_dict else True
        
        
    def check_config(self):
        if self.sample_rate not in SAMPLE_RATES:
            raise ValueError(str(self.sample_rate) + " is not a valid sample rate. Must be in " + str(SAMPLE_RATES))
        if self.trigger_source not in TRIGGER_SOURCES:
            raise ValueError(str(self.trigger_source) + " is not a valid trigger source. Must be in " + str(TRIGGER_SOURCES))
        if self.trigger_slope not in TRIGGER_SLOPES:
            raise ValueError(str(self.trigger_slope) + " is not a valid trigger slope. Must be in " + str(TRIGGER_SLOPES))
        if self.trigger_mode not in TRIGGER_MODES:
            raise ValueError(str(self.trigger_mode) + " is not a valid trigger mode. Must be in " + str(TRIGGER_MODES))
        if abs(self.trigger_level) > ADC_RANGE:
            raise ValueError(str(self.trigger_level) + " is not a valid trigger level. Must be in [-" + str(ADC_RANGE) + ", " + str(ADC_RANGE) + "]")
        if self.pretrigger_samples > self.total_samples:
            raise ValueError("Pretrigger samples must be less than total samples")
        if self.total_samples > MAXIMUM_SAMPLES:
            raise ValueError(str(self.total_samples) + " is not a valid number of total samples. Must be less than " + str(MAXIMUM_SAMPLES))
        if self.distribution not in DISTRIBUTIONS:
            raise ValueError(str(self.distribution) + " is not a valid distribution. Must be in " + str(DISTRIBUTIONS))
        
    # <- Functions for reading the config dict
    
        





if __name__ == "__main__":
    com = rpCommunication()



