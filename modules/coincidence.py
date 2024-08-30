from rbTransfer_v2 import rbTransfer_v2 as rbTransfer
import numpy as np
import pandas as pd
import os, sys

import analyzers as ana

# first sink is for just the height of the trigger channel peaks.
# second sink if for the height of coincidce peaks and their time difference.


# config_dict must contain trigger_channel, coincidence_channel, offset, window, peak_config, gradient_min


def coincidence(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    
    trigger_channel = config_dict['trigger_channel']
    coincidence_channel = config_dict['coincidence_channel']
    
    offset = config_dict['offset']
    window = config_dict['window']
    
    dtype_trigger = sink_list[0]['dtype']
    dtype_coincidence = sink_list[1]['dtype']
    
    entry_out_trigger = np.zeros((1,), dtype=dtype_trigger)
    entry_out_coincidence = np.zeros((1,), dtype=dtype_coincidence)
    
    def main(input_data):
        out_trigger = []
        out_coincidence = []
        peaks, peaks_prop = ana.pha_jump(input_data, config_dict)
        if len(peaks[trigger_channel]) == 0:
            return None
        for height in peaks_prop[trigger_channel]['jump']:
            entry_out_trigger['height'][0] = height
            out_trigger.append(entry_out_trigger)
        if len(peaks[coincidence_channel]) == 0:
            # no event in coincidence channel. Just return the trigger channel peak height
            return [out_trigger,None]
        for trigger_index, trigger_position in enumerate(peaks[trigger_channel]):
            for coincidence_index, coincidence_position in enumerate(peaks[coincidence_channel]):
                if abs(trigger_position - coincidence_position + offset) < window:
                    entry_out_coincidence['height_trigger'][0] = peaks_prop[trigger_channel]['jump'][trigger_index]
                    entry_out_coincidence['height_coincidence'][0] = peaks_prop[coincidence_channel]['jump'][coincidence_index]
                    entry_out_coincidence['DeltaT'][0] = trigger_position - coincidence_position + offset
                    out_coincidence.append(entry_out_coincidence)
        out_trigger = [np.max(input_data[trigger_channel])]
        return [out_trigger,out_coincidence]
        

            
            
        

    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()