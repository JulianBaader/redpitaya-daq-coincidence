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
import os, sys

#from filters import *
from modules.filters import *


def find_peaks(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    """filter client for mimoCoRB: Find valid signal pulses in waveform data

       Input: 

        - wave form data from source buffer defined in source_list

       Returns: 
  
         - None if filter not passed
         - list of list(s) of pulse parameters, written to sinks defined in sink_list

    """
    
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")

    # Load configuration
    sample_time_ns = config_dict["sample_time_ns"]
    number_of_samples = config_dict["number_of_samples"]
    analogue_offset = config_dict["analogue_offset"]*1000
    pre_trigger_samples = config_dict["pre_trigger_samples"]
    trigger_channel = 'ch'+config_dict["trigger_channel"]
    coincidence_window = config_dict["coincidence_window"]
    
    
    peak_config = config_dict["peak_config"]
    
    
    list_of_channels = config_dict["list_of_channels"]
    clipping_level = config_dict["clipping_level"]
    
    if len(list_of_channels)!=2:
        raise ValueError(f'{list_of_channels} has not 2 channels')
    if trigger_channel not in list_of_channels:
        raise ValueError(f'{trigger_channel} not in list of channels: {list_of_channels}') 
    trigger_position_tolerance = config_dict["trigger_position_tolerance"]
    
    for ch in list_of_channels:
        if ch!=trigger_channel:
            signal_channel=ch
    

    pulse_par_dtype = sink_list[-1]['dtype']
    
    Delta_T=coincidence_window['offest_from_trigger']/sample_time_ns
    w=coincidence_window[signal_channel]['width_of_window']/sample_time_ns
    
    
    def tag_pulses(input_data):   
        """find all valid pulses 

        This function to be called by instance of class mimoCoRB.rbTransfer

            Args:  input data as structured ndarray

            Returns: list of parameterized pulses
            

        """
        # Discard all events with clipping
        if check_for_clipping(input_data,clipping_level): return None
        # Only consider events with one peak in the trigger_channel
        if len(peaks[trigger_channel])!=1: return None
        
        
        # Find all peaks and store their properties in a dict
        peaks, peaks_prop = tag_peaks(input_data, peak_config)
        peak_data=np.zeros( (1,), dtype=pulse_par_dtype)
        
        trigger_peak=peaks[trigger_channel][0]
        
        # Check that only one peak was found in signal_channel
        if len(peaks[signal_channel])!=1: 
            return None
        signal_peak=peaks[signal_channel][0]
        

        # check for coincidences
        if -w/2<=signal_peak-Delta_T-trigger_peak<=w/2:
            # explanation: t+Delta_T-w/2<=peak<=t+Delta_T+w/2
            """ab hier erstmal nur für einen trigger und einen signal channel"""
            peak_data[0][signal_channel+'_position'] = signal_peak
            peak_data[0][trigger_channel+'_position'] = trigger_peak
            peak_data[0][signal_channel+'_height'] = peaks_prop[signal_channel]['relative_height'][0] # das muss später weg wenn man mehr als ein peak betrachtet
            peak_data[0][trigger_channel+'_height'] = peaks_prop[trigger_channel]['relative_height'][0]
            return peak_data
        else:
            return None
        
    p_filter = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=tag_pulses, **rb_info)
    p_filter()
       
        
        
if __name__ == "__main__":
    print("Script: " + os.path.basename(sys.argv[0]))
    print("Python: ", sys.version, "\n".ljust(22, "-"))
    print("THIS IS A MODULE AND NOT MEANT FOR STANDALONE EXECUTION")
