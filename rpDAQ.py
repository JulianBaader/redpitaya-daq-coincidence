import numpy as np
import struct
import sys
import time
import socket
import matplotlib.pyplot as plt
import argparse

from console_progressbar import ProgressBar

from mimocorb.activity_logger import Gen_logger
from mimocorb import mimo_buffer as bm

from npy_append_array import NpyAppendArray



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
    31: "start daq"
}

SAMPLE_RATES = [1, 4, 8, 16, 32, 64, 128, 256]
TRIGGER_SOURCES = {1: 0, 2: 1}
TRIGGER_SLOPES = {"rising": 0, "falling": 1}
TRIGGER_MODES = {"normal": 0, "auto": 1}
MAXIMUM_SAMPLES = 8388607 #TODO überprüfen
ADC_RANGE = 4095 #TODO prob -4095 bis 4096 oder so ach keine Ahnung
GENERATOR_BINS = 4096
DISTRIBUTIONS = {'uniform': 0, 'poisson': 1}

generator_array = np.zeros(GENERATOR_BINS, np.uint32)
for i in range(16):  # initialize with delta-functions
    generator_array[(i + 1) * 256 - 1] = 1

        
class rpControl:
    """
    TODO
    """
    def __init__(self ,config_dict = {}):
        self.load_config_from_dict(config_dict)
        self.check_config()
        
        
        # oscilloscope buffer
        self.osc_buffer = np.zeros(2 * self.total_samples, np.int16)
        self.osc_view = self.osc_buffer.view(np.uint8)
        self.osc_reshaped = self.osc_buffer.reshape((2, self.total_samples), order='F') # order='F' is so that [1,2,3,4,5,6] -> [[1,3,5], [2,4,6]] which is the way the data is sent
        self.OSC_SIZE = self.osc_view.size
        #TODO das muss dann anders gemacht werden
        
        self.event_count = 0

        # socket
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(5)
        
        
        self.setup_general()
        if self.start_generator:
            self.setup_generator()
        self.setup_oscilloscope()
        
        self.start_first_osc()
        print("Setup done")
        

        
    def command(self, code, number, value):
        self.socket.sendall(struct.pack("<Q", code << 56 | number << 52 | (int(value) & 0xFFFFFFFFFFFFF)))
        
    # -> Functions for setting up the RedPitaya
            
    def setup_general(self):
        self.command(4, 0, self.sample_rate)
        self.command(5, 0, int(self.ch1_negated))
        self.command(5, 1, int(self.ch2_negated))
            
    def setup_oscilloscope(self):
        self.command(15, 0, TRIGGER_MODES[self.trigger_mode])
        self.command(13, 0, TRIGGER_SOURCES[self.trigger_source])
        self.command(14, 0, TRIGGER_SLOPES[self.trigger_slope])
        self.command(16, 0, self.trigger_level)
        self.command(17, 0, self.pretrigger_samples)
        self.command(18, 0, self.total_samples)
            
    def setup_generator(self):
        self.command(21, 0, self.fall_time)
        self.command(22, 0, self.rise_time)
        self.command(25, 0, self.pulse_rate)
        self.command(26, 0, DISTRIBUTIONS[self.distribution])
        for value in np.arange(GENERATOR_BINS, dtype=np.uint64) << 32 | self.spectrum:
            self.command(28, 0, value)
        self.command(29, 0, 0) # start generator
    
    def start_first_osc(self):
        self.command(2, 0, 0) # reset oscilloscope
        self.command(19, 0, 0) # start oscilloscope
        
    # <- Functions for setting up the RedPitaya
    
    # -> Functions for interaction with mimoCoRB
    
    def setup_mimoCoRB(self, sink_list=None, config_dict=None, ufunc=None, **rb_info):
        # basically the __init__ function of mimocorb.buffer_control.rbPut
        
        # sub-logger for this class
        self.logger = Gen_logger(__class__.__name__)

        # general part for each function (template)
        if sink_list is None:
            self.logger.error("Faulty ring buffer configuration passed, 'sink_list' missing!")
            raise ValueError("ERROR! Faulty ring buffer configuration passed ('sink_list' missing)!")

        self.sink = None
        for key, value in rb_info.items():
            if value == "read":
                self.logger.error("Reading buffers not foreseen!!")
                raise ValueError("ERROR! reading buffers not foreseen!!")
            elif value == "write":
                self.logger.info(f"Writing to buffer {sink_list[0]}")
                self.sink = bm.Writer(sink_list[0])
                if len(sink_list) > 1:
                    self.logger.error("More than one sink presently not foreseen!")
                    print("!!! More than one sink presently not foreseen!!")
            elif value == "observe":
                self.logger.error("Observer processes not foreseen!")
                raise ValueError("ERROR! obervers not foreseen!!")

        if self.sink is None:
            self.logger.error("Faulty ring buffer configuration passed. No sink found!")
            raise ValueError("Faulty ring buffer configuration passed. No sink found!")

        
        self.T_last = time.time()
        
    def osc_to_mimocorb(self):
        if self.sink._active.is_set():
            # do not write data if in paused mode
            if self.sink._paused.is_set():
                time.sleep(0.1)
                return
            T_data_ready = time.time()
            timestamp = time.time_ns() * 1e-9  # in s as type float64
            
            
            # get new buffer and store event data and meta-data
            buffer = self.sink.get_new_buffer()

            view = buffer.view(np.uint8)
            # fill data
            bytes_received = 0
            while bytes_received < self.OSC_SIZE:
                
                bytes_received += self.socket.recv_into(view[bytes_received:], self.OSC_SIZE - bytes_received)

            
            self.event_count += 1
            
            # calculate deadtime
            T_buffer_ready = time.time()
            deadtime = T_buffer_ready - T_data_ready
            deadtime_fraction = deadtime / (T_buffer_ready - self.T_last)

            # set metadata
            self.sink.set_metadata(self.event_count, timestamp, deadtime_fraction)
            

            self.T_last = T_buffer_ready
            return True

        else:
            # make sure last data entry is also processed
            self.sink.process_buffer()
            return False
            
    def drain(self, n):
        self.stop = time.time()
        for i in range(n):
            data = bytearray()
            while len(data) < self.OSC_SIZE:
                data += self.socket.recv(self.OSC_SIZE - len(data))
        self.finish()

    def finish(self):
        rate = self.event_count / (self.stop - self.start)
        print("Data acquisition done. Rate: " + str(rate) + " Hz")
        self.socket.close()
            
    def run_mimo_daq(self):
        self.start = time.time()
        for i in range(self.number_of_loops):
            self.command(31, 0, self.events_per_loop)
            for j in range(self.events_per_loop):
                if not self.osc_to_mimocorb():
                    self.drain(self.events_per_loop - i)
                    return
        self.stop = time.time()
        self.finish()

            
    # <- Functions for interaction with mimoCoRB
    
    # -> Functions for saving the data to file
    
    def osc_to_npy(self, npa):
        bytes_received = 0
        while bytes_received < self.OSC_SIZE:
            bytes_received += self.socket.recv_into(self.osc_view[bytes_received:], self.OSC_SIZE - bytes_received)
        self.event_count += 1
        npa.append(np.array([self.osc_reshaped]))
    
    def run_and_save(self):
        start = time.time()
        progress_bar = ProgressBar(total=self.number_of_loops, prefix='Loops done:', length=50)
        with NpyAppendArray(self.filename) as npa:
            for i in range(self.number_of_loops):
                progress_bar.print_progress_bar(i)
                self.command(31, 0, self.events_per_loop)
                for j in range(self.events_per_loop):
                    self.osc_to_npy(npa)
        stop = time.time()
        progress_bar.print_progress_bar(self.number_of_loops)
        rate = self.number_of_loops * self.events_per_loop / (stop - start)
        print("Data acquisition done. Rate: " + str(rate) + " Hz")

        
    # <- Functions for saving the data to file
    

    
    # -> Functions for reading the config
        
    def load_config_from_dict(self, config_dict):
        # general configuration
        self.ip = config_dict["ip"] if "ip" in config_dict else "rp-f0c38f.local"
        self.port = config_dict["port"] if "port" in config_dict else 1001
        self.sample_rate = config_dict["sample_rate"] if "sample_rate" in config_dict else 4
        self.ch1_negated = config_dict["ch1_negated"] if "ch1_negated" in config_dict else False
        self.ch2_negated = config_dict["ch2_negated"] if "ch2_negated" in config_dict else False
        self.number_of_loops = config_dict["number_of_loops"] if "number_of_loops" in config_dict else 100
        self.events_per_loop = config_dict["events_per_loop"] if "events_per_loop" in config_dict else 1000
        
        self.filename = config_dict["filename"] if "filename" in config_dict else "data.npy"
        
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
        
    def load_config_from_parser(self):
        print("Not implemented yet. Use load_config_from_dict instead. Think of important parameters.")
        # ip
        
    def config(self):
        return {
            "ip": self.ip,
            "port": self.port,
            "sample_rate": self.sample_rate,
            "ch1_negated": self.ch1_negated,
            "ch2_negated": self.ch2_negated,
            "number_of_loops": self.number_of_loops,
            "events_per_loop": self.events_per_loop,
            "trigger_source": self.trigger_source,
            "trigger_slope": self.trigger_slope,
            "trigger_mode": self.trigger_mode,
            "trigger_level": self.trigger_level,
            "pretrigger_samples": self.pretrigger_samples,
            "total_samples": self.total_samples,
            "fall_time": self.fall_time,
            "rise_time": self.rise_time,
            "pulse_rate": self.pulse_rate,
            "distribution": self.distribution,
            "spectrum": self.spectrum,
            "start_generator": self.start_generator
        }
        
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
        if self.number_of_loops < 0:
            raise ValueError("Invalid number of loops")
        if self.events_per_loop < 0:
            raise ValueError("Invalid number of events per loop")
        
    # <- Functions for reading the config dict
    

    
def rp_mimocorb(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    control = rpControl(config_dict)
    control.setup_mimoCoRB(config_dict=config_dict, sink_list=sink_list, **rb_info)
    control.run_mimo_daq()
    

if __name__ == "__main__":
    control = rpControl()
    control.run_and_save()

