from mimocorb.buffer_control import rbExport
import numpy as np
import time

def rb_to_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if len(source_list > 1):
        print("!!! More than one source presently not foreseen!!")
    if source_list[0]['values_per_slot'] != 1:
        print("!!! Only one value per slot presently foreseen!!")
    
    update_interval = config_dict['update_interval']
    filename = config_dict['directory_prefix'] + config_dict['filename']
    spectrum_config = config_dict['spectrum_config']
    # for each key to be plotted, the start, stop and number of bins must be defined in a list
    # spectrum_config = {'key1': [start1, stop1, nbins1], 'key2': [start2, stop2, nbins2], ...}
    keys = []
    
    factor = {}
    hist = {}
    discarded = {}
    for key in spectrum_config:
        keys.append(key)
        start, stop, nbins = spectrum_config[key]
        factor[key] = nbins / (stop - start)
        hist[key] = np.zeros(nbins)
        discarded[key] = []
    
    
    exp = rbExport(source_list=source_list, config_dict=config_dict, **rb_info)
    
    
    last_update_time = time.time()
    while True:
        d = next(exp(), None)  # this blocks until new data provided !
        if d is not None:  # new data received ------
            for key in keys:
                val = d[0][key][0] # first index is for [data, metadata], second for key, third for first value
                if val is not None:
                    if start[key] <= val <= stop[key]:
                        hist[key][int((val - start[key]) * factor[key])] += 1
                    else:
                        discarded[key].append(val)
        else: # last data received -> finish execution
            break
        if time.time() - last_update_time > update_interval:
            last_update_time = time.time()
            for key in keys:
                np.save(filename + '_' + key, hist[key])
    
    #print('Discarded values:', discarded) #TODO if interested in discarded values they may be saved to a file
    for key in keys:
        np.save(filename + '_' + key, hist[key])
