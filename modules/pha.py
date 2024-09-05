from rbTransfer_v2 import rbTransfer_v2 as rbTransfer
import numpy as np
import analyzers as ana


def pha_single(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    if sink_list[0]['values_per_slot'] != 1:
        raise ValueError("ERROR! Sink 0 must have channel_per_slot = 1")
    sink_key = sink_list[0]['dtype'][0][0]
    
    
    source_dtypes = source_list[0]['dtype']
    ch1 = source_dtypes[0][0]
    ch2 = source_dtypes[1][0]
    if ch1 == 'trigger_channel':
        peak_config = config_dict['peak_config1']
    elif ch2 == 'trigger_channel':
        peak_config = config_dict['peak_config2']
    else:
        raise ValueError("ERROR! No trigger channel found")
    
    
    dtype = sink_list[0]['dtype']
    entry_out = np.zeros((1,), dtype=dtype)
    
    def main(input_data):
        if input_data is None:
            return None
        osc = input_data['trigger_channel']
        peaks, heights = ana.pha(osc, peak_config)
        if len(peaks) == 0:
            return None
        
        out = []
        for i in range(len(peaks)):
            entry_out[sink_key] = heights[i]
            out.append(entry_out.copy())
        return [out]
    
    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()
    

    

            
            
        
        
    
    
