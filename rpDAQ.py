import numpy as np
import struct
import sys
import time
import socket
import matplotlib.pyplot as plt
import argparse
import signal
import os
import yaml

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
TRIGGER_MODES = {"normal": 0,"auto": 1}
MAXIMUM_SAMPLES = 8388607 #TODO überprüfen
ADC_RANGE = 4095 #TODO prob -4095 bis 4096 oder so ach keine Ahnung
GENERATOR_BINS = 4096
DISTRIBUTIONS = {'uniform': 0, 'poisson': 1}
ACQUISITION_MODES = ['time', 'loops', 'infinite']

PORT = 1001

generator_array = np.zeros(GENERATOR_BINS, np.uint32)
for i in range(16):  # initialize with delta-functions
    generator_array[(i + 1) * 256 - 1] = 1
    
#generator_array[2048] = 1


        
class rpControl:
    """
    TODO
    """
    def __init__(self ,config_dict):
        self.load_config_from_dict(config_dict)
        
        # oscilloscope buffer
        self.osc_buffer = np.zeros(2 * self.total_samples, np.int16)
        self.osc_view = self.osc_buffer.view(np.uint8)
        self.osc_reshaped = self.osc_buffer.reshape((2, self.total_samples), order='F') # order='F' is so that [1,2,3,4,5,6] -> [[1,3,5], [2,4,6]] which is the way the data is sent
        self.OSC_SIZE = self.osc_view.size
        
        self.event_count = 0

        # socket
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.connect((self.ip, PORT))
        self.socket.settimeout(5)
        
        
        self.setup_general()
        if self.start_generator:
            self.setup_generator()
        self.setup_oscilloscope()
        
        self.stop_daq = False
        signal.signal(signal.SIGINT, self.interrupt_handler)
        
        self.start_first_osc()
        print("Setup done")
        

        
    def command(self, code, number, value):
        self.socket.sendall(struct.pack("<Q", code << 56 | number << 52 | (int(value) & 0xFFFFFFFFFFFFF)))
        
    def interrupt_handler(self, signal, frame):
        self.stop_daq = True
        
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
        self.spectrum = np.load(self.spectrum_file)
        plt.plot(self.spectrum)
        plt.show()
        if self.spectrum.size != GENERATOR_BINS:
            raise ValueError("Spectrum file must have " + str(GENERATOR_BINS) + " entries")

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
    
    
    # -> Functions for saving the data to file
    
    def osc_to_npy(self):
        bytes_received = 0
        while bytes_received < self.OSC_SIZE:
            bytes_received += self.socket.recv_into(self.osc_view[bytes_received:], self.OSC_SIZE - bytes_received)
        self.event_count += 1
        self.npa.append(np.array([self.osc_reshaped]))
        
        
    def execute_loop(self):
        self.command(31, 0, self.events_per_loop)
        for j in range(self.events_per_loop):
            self.osc_to_npy()
        

    def run_and_save(self):
        # TODO optimize
        self.start = time.time()
        loop_counter = 0
        if self.acquisition_mode != 'infinite':
            progress_bar = ProgressBar(total=self.acquisition_value, prefix='Acquiring Events:', length=50)
        with NpyAppendArray(self.data_file) as self.npa:
            if self.acquisition_mode == 'time':
                time_expired = 0
                while time_expired < self.acquisition_value and not self.stop_daq:
                    self.execute_loop()
                    time_expired = time.time() - self.start
                    loop_counter += 1
                    progress_bar.print_progress_bar(time_expired)
            elif self.acquisition_mode == 'loops':
                while loop_counter < self.acquisition_value and not self.stop_daq:
                    self.execute_loop()
                    time_expired = time.time() - self.start
                    loop_counter += 1
                    progress_bar.print_progress_bar(loop_counter)
            elif self.acquisition_mode == 'infinite':
                while not self.stop_daq:
                    self.execute_loop()
                    time_expired = time.time() - self.start
                    loop_counter += 1
                    print(f"\r{loop_counter*self.events_per_loop} events recorded at a rate of {round(loop_counter*self.events_per_loop/time_expired)}Hz", end="")
            events = loop_counter * self.events_per_loop
            print(f"\r{events} events recorded at a rate of {round(events/time_expired)}Hz")
            metadata = {
                'events': events,
                'rate': events / time_expired,
                'time': time_expired
            }
            yaml.dump(metadata, open(self.metadata_file, 'w'))

        
    # <- Functions for saving the data to file
    



        
    def load_config_from_dict(self, config_dict):
        # general config
        self.ip = config_dict['ip']
        
        self.sample_rate = config_dict['sample_rate']
        if self.sample_rate not in SAMPLE_RATES:
            raise ValueError(str(self.sample_rate) + " is not a valid sample rate. Must be in " + str(SAMPLE_RATES))
        
        self.ch1_negated = config_dict['ch1_negated']
        self.ch2_negated = config_dict['ch2_negated']
        
        # data acquisition config
        output_name = config_dict['output_name'] + "-" + time.strftime("%Y%m%d-%H%M") + "/"
        os.makedirs(os.path.dirname(output_name), exist_ok=False)
        self.data_file = output_name + "/data.npy"
        self.metadata_file = output_name + "/metadata.yaml"
        
        config_file = output_name + "/config.yaml"
        yaml.dump(config_dict, open(config_file, 'w'))
        
        self.events_per_loop = config_dict['events_per_loop']
        if self.events_per_loop < 0:
            raise ValueError("Invalid number of events per loop")
        self.acquisition_mode = config_dict['acquisition_mode']
        if self.acquisition_mode not in ACQUISITION_MODES:
            raise ValueError(str(self.acquisition_mode) + " is not a valid acquisition mode. Must be in " + str(ACQUISITION_MODES))
        if self.acquisition_mode != 'infinite':
            self.acquisition_value = config_dict['acquisition_value']
            if self.acquisition_value < 0:
                raise ValueError("Invalid acquisition value")
        
        # oscilloscope config
        self.trigger_source = config_dict['trigger_source']
        if self.trigger_source not in TRIGGER_SOURCES:
            raise ValueError(str(self.trigger_source) + " is not a valid trigger source. Must be in " + str(TRIGGER_SOURCES.keys()))
        self.trigger_slope = config_dict['trigger_slope']
        if self.trigger_slope not in TRIGGER_SLOPES:
            raise ValueError(str(self.trigger_slope) + " is not a valid trigger slope. Must be in " + str(TRIGGER_SLOPES.keys()))
        self.trigger_mode = config_dict['trigger_mode']
        if self.trigger_mode not in TRIGGER_MODES:
            raise ValueError(str(self.trigger_mode) + " is not a valid trigger mode. Must be in " + str(TRIGGER_MODES.keys()))
        self.trigger_level = config_dict['trigger_level']
        if abs(self.trigger_level) > ADC_RANGE:
            raise ValueError(str(self.trigger_level) + " is not a valid trigger level. Must be in [-" + str(ADC_RANGE) + ", " + str(ADC_RANGE) + "]")
        self.total_samples = config_dict['total_samples']
        if self.total_samples > MAXIMUM_SAMPLES:
            raise ValueError(str(self.total_samples) + " is not a valid number of total samples. Must be less than " + str(MAXIMUM_SAMPLES))
        self.pretrigger_samples = config_dict['pretrigger_samples']
        if self.pretrigger_samples > self.total_samples:
            raise ValueError("Pretrigger samples must be less than total samples")
        
        
        # generator config
        self.start_generator = config_dict['start_generator']
        if self.start_generator:
            self.rise_time = config_dict['rise_time'] #TODO valid values
            self.fall_time = config_dict['fall_time'] #TODO valid values
            self.pulse_rate = config_dict['pulse_rate'] #TODO valid values
            self.distribution = config_dict['distribution']
            if self.distribution not in DISTRIBUTIONS:
                raise ValueError(str(self.distribution) + " is not a valid distribution. Must be in " + str(DISTRIBUTIONS.keys()))
            self.spectrum_file = config_dict['spectrum_file']
            if not os.path.isfile(self.spectrum_file):
                raise ValueError("Spectrum file not found")

        

    

    
def rp_mimocorb(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    control = rpControl(config_dict)
    control.setup_mimoCoRB(config_dict=config_dict, sink_list=sink_list, **rb_info)
    control.run_mimo_daq()
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RedPitaya Data Acquisition')
    parser.add_argument('config_file', nargs='?', default='config/rp-config.yaml', help='Configuration file')
    args = parser.parse_args()
    config_dict = yaml.load(open(args.config_file, 'r'), Loader=yaml.FullLoader)
    control = rpControl(config_dict)
    control.run_and_save()



