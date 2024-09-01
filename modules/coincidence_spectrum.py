from mimocorb.buffer_control import rbExport
import numpy as np
import time
import os
from npy_append_array import NpyAppendArray


def rb_to_coincidence_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    coincidence_spectrum_config = config_dict['coincidence_spectrum']
    filename = config_dict['directory_prefix'] + coincidence_spectrum_config['filename'] + '.npy'
    
    exp = rbExport(source_list=source_list, config_dict=config_dict, **rb_info)
    with NpyAppendArray(filename) as npaa:
        while True:
            d = next(exp(), None)  # this blocks until new data provided !
            if d is not None:  # new data received ------start_gui
                data, metadata = d
                npaa.append(data)
            else: # last data received -> finish execution
                break
            
