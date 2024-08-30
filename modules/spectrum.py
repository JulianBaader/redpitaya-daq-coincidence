from mimocorb.buffer_control import rbExport
import numpy as np
import time
import os



def rb_to_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if len(source_list) > 1:
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
    min = {}
    max = {}
    discarded = {}
    for key in spectrum_config:
        keys.append(key)
        start, stop, nbins = spectrum_config[key]
        min[key] = start
        max[key] = stop
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
                    if min[key] <= val <= max[key]:
                        hist[key][int((val - min[key]) * factor[key])] += 1
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


def plot_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    update_interval = config_dict['update_interval']
    filename = config_dict['directory_prefix'] + config_dict['filename']
    spectrum_config = config_dict['spectrum_config']
    keys = [key for key in spectrum_config]
    
    import matplotlib.pyplot as plt
    
    plt.style.use('default')
    plt.ion()
    fig = plt.figure(num='Spectrum of trigger channel')
    ax = fig.add_subplot(111)
    
    lines = {}
    xs = {}
    ys = {}
    for key in keys:
        xs[key] = np.linspace(spectrum_config[key][0], spectrum_config[key][1], spectrum_config[key][2])
        ys[key] = np.zeros(spectrum_config[key][2])
        lines[key], = ax.plot(xs[key],ys[key], label=key)
    # make the title the total number of events
    ax.set_title('Total number of events: 0')
    ax.legend()
    plt.show()
    

    last_update_time = time.time()
    
    while True:
        if time.time() - last_update_time > update_interval:
            last_update_time = time.time()
            for key in config_dict['spectrum_config']:
                # check if file exists
                if not os.path.exists(filename + '_' + key + '.npy'):
                    continue
                hist = np.load(filename + '_' + key + '.npy')
                lines[key].set_ydata(hist)
                ax.set_title('Total number of events: ' + str(int(np.sum(hist))))
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.025) # to avoid to much CPU load but still provide interaction at 30FPS
        
            
        