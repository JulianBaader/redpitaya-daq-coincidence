from mimocorb.buffer_control import rbExport, rbObserver

import numpy as np
import time
import os
import matplotlib.pyplot as plt

ADC_LIMIT = 2**12


def rb_to_spectrum(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if len(source_list) > 1:
        print("!!! More than one source presently not foreseen!!")
    if source_list[0]['values_per_slot'] != 1:
        print("!!! Only one value per slot presently foreseen!!")

    update_interval = config_dict['update_interval']
    filename = config_dict['directory_prefix'] + config_dict['filename']
    
    key = config_dict['key']
    min = config_dict['min']
    max = config_dict['max']
    nbins = config_dict['nbins']
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
                ind = int((val - min) * factor)
                if 0 <= ind < nbins:
                    hist[ind] += 1
                else:
                    discarded.append(val)
        else: # last data received -> finish execution
            break
        if time.time() - last_update_time > update_interval:
            last_update_time = time.time()
            np.save(filename, hist)
    
    #print('Discarded values:', discarded) #TODO if interested in discarded values they may be saved to a file
    np.save(filename, hist)
    
    
def plot(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    show_osc = observe_list is not None
    if len(observe_list) > 1:
        print("!!! More than one observe presently not foreseen!!")
    
    update_interval = config_dict['update_interval']
    
    filename = config_dict['directory_prefix'] + config_dict['filename'] + '.npy'
    
    fig = plt.figure(num='Real Time Plot')
    
    if show_osc:
        ax_spectrum = fig.add_subplot(212)
    else:
        ax_spectrum = fig.add_subplot(111)
    ax_spectrum.set_title('Spectrum')
    spectrum_x = np.linspace(config_dict['min'], config_dict['max'], config_dict['nbins'])
    spectrum_y = np.zeros(config_dict['nbins'])
    spectrum_line, = ax_spectrum.plot(spectrum_x, spectrum_y)
    ax_spectrum.set_xlim(config_dict['min'], config_dict['max'])
    # plot text showing the total number of events
    text = ax_spectrum.text(0.5, 0.9, 'Total events: 0', horizontalalignment='center', verticalalignment='center', transform=ax_spectrum.transAxes)
    
    
    
    if show_osc:
        key_ch1 = observe_list[0]['dtype'][0][0]
        key_ch2 = observe_list[0]['dtype'][1][0]
        osci_update_interval = config_dict['osci_update_interval']
        total_samples = observe_list[0]['values_per_slot']
        osc_observer = rbObserver(observe_list=observe_list, config_dict=config_dict, **rb_info)
        ax_osci = fig.add_subplot(211)
        ax_osci.set_title('Oscilloscope')
        x = np.arange(total_samples)
        y1 = np.zeros(total_samples)
        y2 = np.zeros(total_samples)
        osc_line1, = ax_osci.plot(x, y1)
        osc_line2, = ax_osci.plot(x, y2)
        ax_osci.set_xlim(0, total_samples)
        ax_osci.set_ylim(-ADC_LIMIT, ADC_LIMIT)
        last_osci_update_time = time.time()
        
    
        
    plt.ion()
    plt.show()
    
    
    last_update_time = time.time()
    

    
    while True:
        if time.time() - last_update_time > update_interval and os.path.exists(filename):
            last_update_time = time.time()
            hist = np.load(filename)
            spectrum_line.set_ydata(hist)
            text.set_text('Total events: ' + str(np.sum(hist)))
            ax_spectrum.relim()
            ax_spectrum.autoscale_view()
            fig.canvas.draw()
        if show_osc and time.time() - last_osci_update_time > osci_update_interval:
            last_osci_update_time = time.time()
            data = next(osc_observer(), None)
            if data is not None:
                osc_line1.set_ydata(data[0][key_ch1])
                osc_line2.set_ydata(data[0][key_ch2])  
                fig.canvas.draw() 
            else:
                break 
        fig.canvas.flush_events()
        time.sleep(0.03) # to avoid 100% CPU usage but still update at 30FPS
        
        
        
    
    
    
    
    
    
