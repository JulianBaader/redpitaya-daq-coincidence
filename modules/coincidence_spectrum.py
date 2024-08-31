from mimocorb.buffer_control import rbExport
import numpy as np
import time
import os
from npy_append_array import NpyAppendArray


def rb_to_coincidence_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    filename = config_dict['directory_prefix'] + config_dict['filename'] + '.npy'
    
    exp = rbExport(source_list=source_list, config_dict=config_dict, **rb_info)
    with NpyAppendArray(filename) as npaa:
        while True:
            d = next(exp(), None)  # this blocks until new data provided !
            if d is not None:  # new data received ------
                data, metadata = d
                npaa.append(data)
            else: # last data received -> finish execution
                break
            

def plot_coincidence_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    import matplotlib.pyplot as plt
    filename = config_dict['directory_prefix'] + config_dict['filename'] + '.npy'
    update_interval = 5

    x_config = config_dict['x']
    y_config = config_dict['y']
    z_config = config_dict['z']
    colormap = "viridis"
   
    
    plt.style.use('default')
    plt.ion()
    fig = plt.figure(num='Coincidence Plot')
    ax = fig.add_subplot(111)
    ax.set_xlabel(x_config[0])
    ax.set_ylabel(y_config[0])
    
    ax.set_xlim(x_config[1], x_config[2])
    ax.set_ylim(y_config[1], y_config[2])
    
    ax.scatter([], [], c=[], cmap=colormap, marker=',')
    #plot colorbar
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=plt.Normalize(vmin=z_config[1], vmax=z_config[2]))
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label(z_config[0])
    
    plt.show()
    
    
    
    while not os.path.exists(filename):
        time.sleep(1)
    
    last_update_time = time.time()
    while True:
        if time.time() - last_update_time > update_interval:
            last_update_time = time.time()
            data = np.load(filename)
            x = data[x_config[0]]
            y = data[y_config[0]]
            z = data[z_config[0]]
            ax.scatter(x, y, c=z, cmap='viridis', marker=',', s=1)
            fig.canvas.draw()
        
        fig.canvas.flush_events()
        time.sleep(0.025)
        
    
