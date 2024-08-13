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

        
class rpControll:
    def __init__(self ,config_dict = {}, callback = None):
        self.load_config_from_dict(config_dict)
        self.check_config()
        
        if callback is not None:
            self.callback = callback
        else:
            self.callback = self.standard_callback
            

        # oscilloscope buffer
        self.osc_buffer = np.zeros(2 * self.total_samples, np.int16)
        self.osc_view = self.osc_buffer.view(np.uint8)
        self.OSC_SIZE = self.osc_view.size
        
        # status buffer
        self.status_buffer = np.zeros(9, np.uint32)
        self.status_view = self.status_buffer.view(np.uint8)
        self.STATUS_SIZE = self.status_view.size
        
        # daq

        
        # socket
        self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(5)
        
        
        self.setup_general()
        self.setup_generator() #TODO test if überhaupt gewünscht
        self.setup_oscilloscope()
        
        print("Setup done, starting Osci")
        self.start_first_osc()

        self.test_rates()
        #self.main_loop()
        
        
    def command(self, code, number, value):
        self.socket.sendall(struct.pacrbPutk("<Q", code << 56 | number << 52 | (int(value) & 0xFFFFFFFFFFFFF)))
        
    def recv_osc(self):
        data = bytearray()
        while len(data) < self.OSC_SIZE:
            data += self.socket.recv(self.OSC_SIZE - len(data)) #TODO recv_into
        self.osc_view[:] = np.frombuffer(data, np.uint8)
        self.callback([self.osc_buffer[0::2], self.osc_buffer[1::2]])
        
    def recv_osc_into_buffer(self, buffer):
        pass 
        
    def test_rates(self):
        input_rates = [r for r in range(100,10001,100)]
        output_rates = []
        ratio = []
        for rate in input_rates:
            self.command(25, 0, rate)
            time.sleep(1)
            out = self.main_loop()
            output_rates.append(out)
            print("Input rate: " + str(rate) + " Hz, Output rate: " + str(out) + " Hz" + ", Ratio: " + str(out / rate))
            ratio.append(out / rate)
        np.save("output_rates.npy", output_rates)
        np.save("input_rates.npy", input_rates)
        np.save("ratio.npy", ratio)
        plt.plot(input_rates, ratio)
        plt.show()
        plt.plot(input_rates, output_rates)
        plt.show()
    
    
        
    
    def main_loop(self): #TODO optimize
        start = time.time()
        event_counter = self.total_events
        while event_counter > 0:
            val = min(self.events_per_loop, event_counter)
            self.command(31, 0, val)
            for i in range(val):
                self.recv_osc()
            event_counter -= val
        stop = time.time()
        rate = self.total_events / (stop - start)
        return rate
        
    def drain_daq(self):
        self.command(32, 0, 0)
        try:
            while True:
                self.socket.recv(1) #TODO ist das die beste Taktik?
        except socket.timeout:
            pass
        
    def __del__(self): #TODO implement on server side
        self.drain_daq()
        self.socket.close()
        
        
        
 

    def start_first_osc(self):
        self.command(2, 0, 0)
        self.command(19, 0, 0)
        # while not self.test_for_trigger():
        #     time.sleep(1)
        #     pass
        
    def recv_status(self):
        data = bytearray()
        while len(data) < self.STATUS_SIZE:
            data += self.socket.recv(self.STATUS_SIZE - len(data))
        return data
    
    def test_for_trigger(self):
        self.command(11, 0, 0)
        self.status_view = np.frombuffer(self.recv_status(), np.uint8)
        print(self.status_buffer)
        return self.status_buffer[8] % 2 == 1
        
    
    def standard_callback(self, data):
        print(data)

            
            
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
        #self.command(30, 0, 0) # stop generator
        #self.command(3, 0, 0) # reset generator
        self.command(21, 0, self.fall_time)
        self.command(22, 0, self.rise_time)
        self.command(25, 0, self.pulse_rate)
        self.command(26, 0, DISTRIBUTIONS[self.distribution])
        for value in np.arange(GENERATOR_BINS, dtype=np.uint64) << 32 | self.spectrum:
            self.command(28, 0, value)
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
        self.total_events = config_dict["total_events"] if "total_events" in config_dict else 100000
        self.events_per_loop = config_dict["events_per_loop"] if "events_per_loop" in config_dict else 1000
        
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
        self.pulse_rate = config_dict["pulse_rate"] if "pulse_rate" in config_dict else 2000
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
        if self.total_events < 0:
            raise ValueError("Invalid number of events")
        if self.events_per_loop < 0:
            raise ValueError("Invalid number of events per loop")
        
    # <- Functions for reading the config dict
    
        


# class rp_mimocorb:
#     """Interface for rpControll to the daq rinbuffer mimoCoRB"""

#     def __init__(self, source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
#         # initialize mimoCoRB interface
#         self.rb_exporter = rbPut(config_dict=config_dict, sink_list=sink_list, **rb_info)
#         self.number_of_channels = len(self.rb_exporter.sink.dtype)
#         self.events_required = 100000 if "eventcount" not in config_dict else config_dict["eventcount"]

#         self.event_count = 0
#         self.active = True

#     def __call__(self, data):
#         """function called by redPoscdaq"""
#         if (self.events_required == 0 or self.event_count < self.events_required) and self.active:
#             # deliver pulse data and no metadata
#             self.active = self.rb_exporter(data, None)  # send data
#             self.event_count += 1
#         else:
#             self.active = self.rb_exporter(None, None)  # send None when done
#             print("redPoscdaq exiting")
#             sys.exit()
            
# def rp_to_rb(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
#     """Main function,
#     executed as a multiprocessing Process, to pass data from the RedPitaya to a mimoCoRB buffer

#     :param config_dict: configuration dictionary
#       - events_required: number of events to be taken
#       - number_of_samples, sample_time_ns, pretrigger_samples and analogue_offset
#       - decimation index, invert flags, trigger mode and trigger direction for RedPitaya
#     """

#     # initialize mimocorb class
#     rb_source = rp_mimocorb(config_dict=config_dict, sink_list=sink_list, **rb_info)
#     rpControll(config_dict=config_dict, callback=rb_source)


# if __name__ == "__main__":  # --------------------------------------
#     # run mimoCoRB data acquisition suite
#     # the code below is idenical to the mimoCoRB script run_daq.py
#     import argparse
#     import sys
#     import time
#     from mimocorb.buffer_control import run_mimoDAQ

#     # define command line arguments ...
#     parser = argparse.ArgumentParser(description=__doc__)
#     parser.add_argument("filename", nargs="?", default="demo_setup.yaml", help="configuration file")
#     parser.add_argument("-v", "--verbose", type=int, default=2, help="verbosity level (2)")
#     parser.add_argument("-d", "--debug", action="store_true", help="switch on debug mode (False)")
#     # ... and parse command line input
#     args = parser.parse_args()

#     print("\n*==* script " + sys.argv[0] + " running \n")
#     daq = run_mimoDAQ(args.filename, verbose=args.verbose, debug=args.debug)
#     daq.setup()
#     daq.run()
#     print("\n*==* script " + sys.argv[0] + " finished " + time.asctime() + "\n")


def none_function(data):
    pass

rpControll({}, none_function)

