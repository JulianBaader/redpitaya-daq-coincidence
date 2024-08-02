"""Module **pulse_filter** 

This (rather complex) module filters waveform data to search for valid signal pulses. 
The code first validates the trigger pulse, identifies coincidences of signals in 
different layers (indiating the passage of a cosmic ray particle, a muon) and finally
searches for double-pulse signatures indicating that a muon was stopped in or near 
a detection layer where the resulting decay-electron produced a delayed pulse. 
The time difference between the initial and the delayed pulses is the individual 
lifetime of the muon.

The decay time and the properties of the signal pulses (height, integral and 
postition in time) are written to a buffer; the raw wave forms are optionally
also written to another buffer. 

The callable functions *find_peaks()* and *calulate_decay_time()* depend on the 
buffer manager *mimoCoRB* and provide the filter functionality described above. 
These functions support multiple sinks to be configured for output. 

The relevant configuration parameters can be found in the section *find_peaks:* 
and *calculate_decay_time:* in the configuration file. 

""" 

from mimocorb.buffer_control import rbTransfer
import numpy as np
import pandas as pd
import os, sys


from analyzers import *

def analyzer(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")

    mode = config_dict['mode']


    pulse_par_dtype = sink_list[-1]['dtype']
    
    def jump_filter(input_data):
        peak_data = np.zeros((1,), dtype=pulse_par_dtype)
        peaks, peaks_prop = pha_jump(input_data, config_dict)
        for key in input_data.dtype.names:
            if len(peaks_prop[key]['jump']) > 0:
                peak_data[key + '_height'][0] = peaks_prop[key]['jump'][0]
        return [peak_data]
    
    def int_filter(input_data):
        peak_data = np.zeros((1,), dtype=pulse_par_dtype)
        peaks, peaks_prop = pha_integral(input_data, config_dict)
        for key in input_data.dtype.names:
            if len(peaks_prop[key]['integral']) > 0:
                peak_data[key + '_height'][0] = peaks_prop[key]['integral'][0]
        return [peak_data]
    
    def matched_filter(input_data):
        peak_data = np.zeros((1,), dtype=pulse_par_dtype)
        conv = pha_matched(input_data, config_dict)
        peak_data['ch1_height'][0] = conv
        return [peak_data]

    if mode == 'jump':
        p_filter = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=jump_filter, **rb_info)
    elif mode == 'integral':
        p_filter = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=int_filter, **rb_info)
    elif mode == 'matched':
        p_filter = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=matched_filter, **rb_info)
    else:
        raise ValueError("ERROR! Wrong mode passed (in pulse_filter)!!")
    p_filter()

if __name__ == "__main__":
    print("Script: " + os.path.basename(sys.argv[0]))
    print("Python: ", sys.version, "\n".ljust(22, '-'))
    print("THIS IS A MODULE AND NOT MEANT FOR STANDALONE EXECUTION")
