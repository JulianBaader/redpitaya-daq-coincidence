import numpy as np
import time
import matplotlib.pyplot as plt
import os
import mimocorb.buffer_control as bc
import analyzers as ana

#TODO refactor

ADC_LIMIT = 2**12

def real_time_plot(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    window = config_dict['window']
    spectrum_update_interval = config_dict['spectrum_update_interval']
    osci_update_interval = config_dict['osci_update_interval']
    
    
    total_samples = observe_list[0]['values_per_slot']
    
    norm_osc_obs = bc.rbObserver(observe_list=observe_list[0:1], config_dict=config_dict, **rb_info)
    coin_osc_obs = bc.rbObserver(observe_list=observe_list[1:2], config_dict=config_dict, **rb_info)
    
    colormap = "viridis"
    
    directory_prefix = config_dict['directory_prefix']
    
    plt.style.use('default')
    plt.ion()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    fig = plt.figure(num='Real Time Plot')
    
    ax = {}
    
    ax['norm_spectrum'] = fig.add_subplot(223)
    norm_spectrum_config = config_dict['normal_spectrum']
    
    norm_spectrum_x = np.linspace(norm_spectrum_config['min'], norm_spectrum_config['max'], norm_spectrum_config['nbins'])
    norm_spectrum_y = np.zeros(norm_spectrum_config['nbins'])
    norm_spectrum_line, = ax['norm_spectrum'].plot(norm_spectrum_x, norm_spectrum_y)
    ax['norm_spectrum'].set_xlim(norm_spectrum_config['min'], norm_spectrum_config['max'])
    ax['norm_spectrum'].set_title('Spectrum of trigger channel')
    
    
    ax['coin_spectrum'] = fig.add_subplot(224)
    coin_spectrum_config = config_dict['coincidence_spectrum']
    x_config = coin_spectrum_config['x']
    y_config = coin_spectrum_config['y']
    ax['coin_spectrum'].set_xlabel(x_config[0])
    ax['coin_spectrum'].set_ylabel(y_config[0])
    
    ax['coin_spectrum'].set_xlim(x_config[1], x_config[2])
    ax['coin_spectrum'].set_ylim(y_config[1], y_config[2])
    
    ax['coin_spectrum'].scatter([], [], c=[], cmap=colormap, marker=',', s=1)
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=plt.Normalize(vmin=0, vmax=window))
    cbar = fig.colorbar(sm, ax=ax['coin_spectrum'])
    cbar.set_label('$\Delta T$')
    
    ax['coin_spectrum'].set_title('Coincidence Plot')
    
    ax['norm_osci'] = fig.add_subplot(221)
    ax['norm_osci'].set_title('Random Oscilloscope')
    ax['coin_osci'] = fig.add_subplot(222)
    ax['coin_osci'].set_title('Oscilloscope for Coincidence events')
    
    x = np.arange(total_samples)
    y = np.zeros(total_samples)

    
    

    
    
    line_norm_trig, = ax['norm_osci'].plot(x, y, label='trigger', color=colors[0])
    line_norm_coin, = ax['norm_osci'].plot(x, y, label='coincidence', color=colors[1])
    line_coin_trig, = ax['coin_osci'].plot(x, y, label='trigger', color=colors[0])
    line_coin_coin, = ax['coin_osci'].plot(x, y, label='coincidence', color=colors[1])
    
    lines = {
        'norm': {'trigger': line_norm_trig, 'coincidence': line_norm_coin}, 
        'coin': {'trigger': line_coin_trig, 'coincidence': line_coin_coin}
        }


    
    vlines_norm_trig = ax['norm_osci'].vlines([], ymin=-1, ymax=1, color=colors[0])
    vlines_norm_coin = ax['norm_osci'].vlines([], ymin=-1, ymax=1, color=colors[1])
    vlines_coin_trig = ax['coin_osci'].vlines([], ymin=-1, ymax=1, color=colors[0])
    vlines_coin_coin = ax['coin_osci'].vlines([], ymin=-1, ymax=1, color=colors[1])
    
    vlines = {
        'norm': {'trigger': vlines_norm_trig, 'coincidence': vlines_norm_coin},
        'coin': {'trigger': vlines_coin_trig, 'coincidence': vlines_coin_coin}
    }

    for key in ['norm_osci', 'coin_osci']:
        ax[key].set_xlabel('Sample Number')
        ax[key].set_ylabel('ADC-Value')
        ax[key].set_xlim(0, total_samples)
        ax[key].set_ylim(-ADC_LIMIT, ADC_LIMIT)
        ax[key].legend()
    
    
    plt.show()
    
    last_update_time_spectrum = time.time()
    last_update_time_osci = time.time()
    while True:
        if time.time() - last_update_time_spectrum > spectrum_update_interval:
            last_update_time_spectrum = time.time()
            update_spectrum(ax['norm_spectrum'], norm_spectrum_line, directory_prefix, norm_spectrum_config)
            update_coincidence_spectrum(ax['coin_spectrum'], directory_prefix, coin_spectrum_config, colormap)
            fig.canvas.draw()
        
        if time.time() - last_update_time_osci > osci_update_interval:
            data_norm = next(norm_osc_obs())
            data_coin = next(coin_osc_obs())
            if data_norm is not None and data_coin is not None:
                update_osc(ax['norm_osci'], lines['norm'], vlines['norm'], data_norm, config_dict, colors)
                update_osc(ax['coin_osci'], lines['coin'], vlines['coin'], data_coin, config_dict, colors)
                fig.canvas.draw()
            else:
                break
        time.sleep(0.025) # 25 ms delay to prevent high CPU usage
        fig.canvas.flush_events()
        

            
        

    
    
    
def update_spectrum(ax, line, directory_prefix, config):
    path = directory_prefix + config['filename'] + '.npy'
    if not os.path.exists(path):
        return
    data = np.load(path)
    line.set_ydata(data)
    ax.relim()
    ax.autoscale_view()
    
def update_coincidence_spectrum(ax, directory_prefix, config, colormap):
    path = directory_prefix + config['filename'] + '.npy'
    if not os.path.exists(path):
        return
    data = np.load(path)
    ax.scatter(data[config['x'][0]], data[config['y'][0]], c=data['DeltaT'], cmap=colormap, marker=',', s=1)
    

def update_osc(ax, lines, vlines, data, config_dict, colors):
    trigger_channel = config_dict['trigger_channel']
    coincidence_channel = config_dict['coincidence_channel']
    
    peak_config_trigger = config_dict['peak_config_trigger']
    peak_config_coincidence = config_dict['peak_config_coincidence']
    
    osc_trigger = data[0][trigger_channel]
    osc_coincidence = data[0][coincidence_channel]
    
    peaks_trigger, heights_trigger = ana.pha(osc_trigger, peak_config_trigger)
    peaks_coincidence, heights_coincidence = ana.pha(osc_coincidence, peak_config_coincidence)
    
    for key in vlines.keys():
        vlines[key].remove()
    
    max_trigger = osc_trigger[peaks_trigger]
    max_coincidence = osc_coincidence[peaks_coincidence]
    min_trigger = max_trigger-heights_trigger
    min_coincidence = max_coincidence-heights_coincidence
    
    vlines['trigger'] = ax.vlines(peaks_trigger, ymin=min_trigger, ymax=max_trigger, color=colors[0])
    vlines['coincidence'] = ax.vlines(peaks_coincidence, ymin=min_coincidence, ymax=max_coincidence, color=colors[1])
    
    lines['trigger'].set_ydata(osc_trigger)
    lines['coincidence'].set_ydata(osc_coincidence)

    

    
    
    
    

    

    
    
    
    
    
    
    
    
    