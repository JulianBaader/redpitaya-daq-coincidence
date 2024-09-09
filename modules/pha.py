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
        peaks, heights, times = ana.pha(osc, peak_config)
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
    

def deltaT_x_x(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    if sink_list[0]['values_per_slot'] != 1:
        raise ValueError("ERROR! Sink 0 must have channel_per_slot = 1")
    sink_keys = [dtype[0] for dtype in sink_list[0]['dtype']]
    
    
    source_dtypes = source_list[0]['dtype']
    ch1 = source_dtypes[0][0]
    ch2 = source_dtypes[1][0]
    if ch1 == 'trigger_channel':
        peak_config_trigger = config_dict['peak_config1']
        peak_config_coincidence = config_dict['peak_config2']
        coincidence_channel = ch2
    elif ch2 == 'trigger_channel':
        peak_config_trigger = config_dict['peak_config2']
        peak_config_coincidence = config_dict['peak_config1']
        coincidence_channel = ch1
    else:
        raise ValueError("ERROR! No trigger channel found")
    
    

    entry_out = np.zeros((1,), dtype=sink_list[0]['dtype'])
    
    def main(input_data):
        if input_data is None:
            return None
        osc_trig = input_data['trigger_channel']
        osc_coin = input_data[coincidence_channel]
        peaks_trig, heights_trig, times_trig = ana.pha(osc_trig, peak_config_trigger)
        peaks_coin, heights_coin, times_coin = ana.pha(osc_coin, peak_config_coincidence)
        if len(peaks_trig) == 0:
            return None
        if len(peaks_coin) == 0:
            return None
        
        out = []
        if 3100<=heights_trig[0]<=3110: #trig hat gamma1
            for i in range(len(peaks_coin)):
                if 2950<=heights_coin[i]<=3075:
                    entry_out['deltaT_1_1'] = times_coin[i] - times_trig[0]
                    out.append(entry_out.copy())
                if 3350<=heights_coin[i]<=3500:
                    entry_out['deltaT_1_2'] = times_coin[i] - times_trig[0]
                    out.append(entry_out.copy())
        if 3522<=heights_trig[0]<=3532: #trig hat gamma2
            for i in range(len(peaks_coin)):
                if 2950<=heights_coin[i]<=3075:
                    entry_out['deltaT_2_1'] = times_coin[i] - times_trig[0]
                    out.append(entry_out.copy())
                if 3350<=heights_coin[i]<=3500:
                    entry_out['deltaT_2_2'] = times_coin[i] - times_trig[0]
                    out.append(entry_out.copy())
        return [out]
    
    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()

            
            
        
        
    
    
def deltaT(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    if sink_list[0]['values_per_slot'] != 1:
        raise ValueError("ERROR! Sink 0 must have channel_per_slot = 1")
    sink_key = sink_list[0]['dtype'][0][0]
    
    
    source_dtypes = source_list[0]['dtype']
    ch1 = source_dtypes[0][0]
    ch2 = source_dtypes[1][0]
    if ch1 == 'trigger_channel':
        peak_config_trigger = config_dict['peak_config1']
        peak_config_coincidence = config_dict['peak_config2']
        coincidence_channel = ch2
    elif ch2 == 'trigger_channel':
        peak_config_trigger = config_dict['peak_config2']
        peak_config_coincidence = config_dict['peak_config1']
        coincidence_channel = ch1
    else:
        raise ValueError("ERROR! No trigger channel found")
    
    
    dtype = sink_list[0]['dtype']
    entry_out = np.zeros((1,), dtype=dtype)
    
    def main(input_data):
        if input_data is None:
            return None
        osc_trig = input_data['trigger_channel']
        osc_coin = input_data[coincidence_channel]
        peaks_trig, heights_trig, times_trig = ana.pha(osc_trig, peak_config_trigger)
        peaks_coin, heights_coin, times_coin = ana.pha(osc_coin, peak_config_coincidence)
        if len(peaks_trig) == 0:
            return None
        if len(peaks_coin) == 0:
            return None
        
        out = []
        for i in range(len(peaks_coin)):
            entry_out[sink_key] = times_coin[i] - times_trig[0]
            out.append(entry_out.copy())
        return [out]
    
    transfer = rbTransfer(source_list=source_list, sink_list=sink_list, config_dict=config_dict,
                        ufunc=main, **rb_info)
    transfer()