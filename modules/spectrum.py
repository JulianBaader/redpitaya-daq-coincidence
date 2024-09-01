from mimocorb.buffer_control import rbExport
import numpy as np
import time
import os



def rb_to_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if len(source_list) > 1:
        print("!!! More than one source presently not foreseen!!")
    if source_list[0]['values_per_slot'] != 1:
        print("!!! Only one value per slot presently foreseen!!")

    spectrum_config = config_dict['normal_spectrum']
    update_interval = config_dict['spectrum_update_interval']
    filename = config_dict['directory_prefix'] + spectrum_config['filename']
    
    key = spectrum_config['key']
    min = spectrum_config['min']
    max = spectrum_config['max']
    nbins = spectrum_config['nbins']
    factor = nbins / (max - min)
    hist = np.zeros(nbins)
    discarded = []
    
    
    exp = rbExport(source_list=source_list, config_dict=config_dict, **rb_info)
    
    
    last_update_time = time.time()
    while True:
        d = next(exp(), None)  # this blocks until new data provided !
        if d is not None:  # new data received ------
            val = d[0][key][0] # first index is for [data, metadata], second for key, third for first value
            if val is not None:
                if min <= val <= max:
                    hist[int((val - min) * factor)] += 1
                else:
                    discarded.append(val)
        else: # last data received -> finish execution
            break
        if time.time() - last_update_time > update_interval:
            last_update_time = time.time()
            np.save(filename, hist)
    
    #print('Discarded values:', discarded) #TODO if interested in discarded values they may be saved to a file
    np.save(filename, hist)