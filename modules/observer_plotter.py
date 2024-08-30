import mimocorb.buffer_control as bc
import numpy as np
import time
import matplotlib.pyplot as plt
import os
import yaml


import analyzers as ana

ADC_LIMIT = 2**12


min_sleeptime = 1
    

    

def observer_plotter(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    directory_prefix = config_dict['directory_prefix']
    
    # config from coincidence-config -> config of the pha
    while not os.path.exists(directory_prefix + 'coincidence-config.yaml'):
        time.sleep(.5)
    with open(directory_prefix + 'coincidence-config.yaml') as f:
        coincidence_config = yaml.load(f, Loader=yaml.FullLoader)
    trigger_channel = coincidence_config['trigger_channel']
    coincidence_channel = coincidence_config['coincidence_channel']
    peak_config_trigger = coincidence_config['peak_config_trigger']
    peak_config_coincidence = coincidence_config['peak_config_coincidence']
    
    
    xlen = observe_list[0]['values_per_slot']
    
    obs = bc.rbObserver(observe_list=observe_list, config_dict=config_dict, **rb_info)
    
    plt.ion()
    fig = plt.figure("Trigger and Coincidence Signal")
    ax = fig.add_subplot(111)
    x = np.arange(xlen)
    y = np.zeros(xlen)
    line_trigger, = ax.plot(x, y, label='trigger')
    line_coincidence, = ax.plot(x, y, label='coincidence')
    
    vlines_trigger = ax.vlines([], ymin=-ADC_LIMIT, ymax=ADC_LIMIT, label='Trigger Peaks')
    vlines_coincidence = ax.vlines([], ymin=-ADC_LIMIT, ymax=ADC_LIMIT, label='Coincidence Peaks')
    ax.set_xlabel('Sample Number')
    ax.set_ylabel('ADC-Value')
    ax.set_xlim(0, xlen)
    ax.set_ylim(-ADC_LIMIT, ADC_LIMIT)
    ax.legend()
    plt.show()
    
    
    
    while True:
        data = next(obs())
        if data is not None:
            osc_trigger = data[0][trigger_channel]
            osc_coincidence = data[0][coincidence_channel]
            
            peaks_trigger, heights_trigger = ana.pha(osc_trigger, peak_config_trigger)
            peaks_coincidence, heights_coincidence = ana.pha(osc_coincidence, peak_config_coincidence)
            
            
            vlines_trigger.remove()
            vlines_coincidence.remove()
            
            max_trigger = osc_trigger[peaks_trigger]
            max_coincidence = osc_coincidence[peaks_coincidence]
            min_trigger = max_trigger-heights_trigger
            min_coincidence = max_coincidence-heights_coincidence
            
            vlines_trigger = ax.vlines(peaks_trigger, ymin=min_trigger, ymax=max_trigger, label='Trigger Peaks')
            vlines_coincidence = ax.vlines(peaks_coincidence, ymin=min_coincidence, ymax=max_coincidence, label='Coincidence Peaks')

            
            line_trigger.set_ydata(osc_trigger)
            line_coincidence.set_ydata(osc_coincidence)
            fig.canvas.draw()
            fig.canvas.flush_events()
            dt = 0
            while obs.source._active.is_set():
                time.sleep(0.025)
                dt += 0.025
                if dt >= min_sleeptime:
                    break
        else:
            break
    plt.close()