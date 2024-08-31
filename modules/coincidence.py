from rbTransfer_v2 import rbTransfer_v2 as rbTransfer
import numpy as np
import pandas as pd
import os, sys

import analyzers as ana

# first sink is for just the height of the trigger channel peaks.
# second sink is for the height of coincidce peaks and their time difference.


# config_dict must contain trigger_channel, coincidence_channel, offset, window, peak_config, gradient_min


def pha_and_split_coincidence(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    
    trigger_channel = config_dict['trigger_channel']
    coincidence_channel = config_dict['coincidence_channel']
    
    peak_config_trigger = config_dict['peak_config_trigger']
    peak_config_coincidence = config_dict['peak_config_coincidence']
    
    window = config_dict['window']
    offset = config_dict['offset']
    
    
    if sink_list[0]['values_per_slot'] != 1:
        raise ValueError("ERROR! Sink 0 must have channel_per_slot = 1")
    if source_list[0]['values_per_slot'] != sink_list[1]['values_per_slot']:
        raise ValueError("ERROR! Source and sink 1 must have the same channel_per_slot")
    
    dtype = sink_list[0]['dtype']
    entry_out = np.zeros((1,), dtype=dtype)

    
    def main(input_data):
        # first look at the trigger channel
        osc_trigger = input_data[trigger_channel]
        peaks_trigger, heights_trigger = ana.pha(osc_trigger, peak_config_trigger)
        if len(peaks_trigger) == 0:
            return None
        
        # peak found in trigger channel -> save height
        out_trigger = []
        for i in range(len(peaks_trigger)):
            entry_out['height'] = heights_trigger[i]
            out_trigger.append(entry_out.copy())
        # now check coincidence channel
        osc_coincidence = input_data[coincidence_channel]
        peaks_coincidence, heights_coincidence = ana.pha(osc_coincidence, peak_config_coincidence)
        if len(peaks_coincidence) == 0:
            return[out_trigger, None]
        for i in range(len(peaks_trigger)):
            for j in range(len(peaks_coincidence)):
                if abs(peaks_trigger[i] - peaks_coincidence[j] + offset) < window:
                    return [out_trigger, True]


        

    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()
    
    
def coincidence_analysis(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    trigger_channel = config_dict['trigger_channel']
    coincidence_channel = config_dict['coincidence_channel']
    
    peak_config_trigger = config_dict['peak_config_trigger']
    peak_config_coincidence = config_dict['peak_config_coincidence']
    
    offset = config_dict['offset']
    window = config_dict['window']
    
    dtype = sink_list[0]['dtype']
    entry_out = np.zeros((1,), dtype=dtype)
    
    def main(input_data):
        osc_trigger = input_data[trigger_channel]
        peaks_trigger, heights_trigger = ana.pha(osc_trigger, peak_config_trigger)
        osc_coincidence = input_data[coincidence_channel]
        peaks_coincidence, heights_coincidence = ana.pha(osc_coincidence, peak_config_coincidence)
        out = []
        for i in range(len(peaks_trigger)):
            for j in range(len(peaks_coincidence)):
                if abs(peaks_trigger[i] - peaks_coincidence[j] + offset) < window:
                    entry_out['height_trigger'] = heights_trigger[i]
                    entry_out['height_coincidence'] = heights_coincidence[j]
                    entry_out['DeltaT'] = peaks_trigger[i] - peaks_coincidence[j]
                    out.append(entry_out.copy())
        return out
    
    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()
        