from mimocorb.buffer_control import rbProcess
import numpy as np
import analyzers as ana


def coincidence_sorter(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")

    values_per_slot = source_list[0]['values_per_slot']
    if sink_list[0]['values_per_slot'] != values_per_slot or sink_list[1]['values_per_slot'] != values_per_slot:
        raise ValueError("ERROR! Source and sink must have the same values_per_slot")

    source_dtypes = source_list[0]['dtype']
    ch1 = source_dtypes[0][0]
    ch2 = source_dtypes[1][0]
    if ch1 == 'trigger_channel':
        peak_config_trig = config_dict['peak_config1']
        peak_config_coin = config_dict['peak_config2']
    elif ch2 == 'trigger_channel':
        peak_config_trig = config_dict['peak_config2']
        peak_config_coin = config_dict['peak_config1']
    else:
        raise ValueError("ERROR! No trigger channel found")

    def main(input_data):
        if input_data is None:
            return None
        osc_trig = input_data['trigger_channel']
        osc_coin = input_data['coincidence']
        ana_trig = ana.pha(osc_trig, peak_config_trig)
        ana_coin = ana.pha(osc_coin, peak_config_coin)
        if ana_trig is False or ana_coin is False:
            return [True, None]
        else:
            return [None, True]

    process = rbProcess(source_list=source_list, sink_list=sink_list, config_dict=config_dict, ufunc=main, **rb_info)
    process()


def analyzer(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    if config_dict is None:
        raise ValueError("ERROR! Wrong configuration passed (in lifetime_modules: calculate_decay_time)!!")
    source_dtypes = source_list[0]['dtype']
    ch1 = source_dtypes[0][0]
    ch2 = source_dtypes[1][0]
    if ch1 == 'trigger_channel':
        peak_config_trig = config_dict['peak_config1']
        peak_config_coin = config_dict['peak_config2']
    elif ch2 == 'trigger_channel':
        peak_config_trig = config_dict['peak_config2']
        peak_config_coin = config_dict['peak_config1']
    else:
        raise ValueError("ERROR! No trigger channel found")

    def main(input_data):
        if input_data is None:
            return None
        osc_trig = input_data['trigger_channel']
        osc_coin = input_data['coincidence']

        osc_trig = input_data['trigger_channel']
        osc_coin = input_data['coincidence']
        ana_trig = ana.pha(osc_trig, peak_config_trig)
        ana_coin = ana.pha(osc_coin, peak_config_coin)
        if ana_trig is False or ana_coin is False:
            print("This should not happen")
            return None

        peaks_trig, heights_trig, times_trig = ana_trig
        peaks_coin, heights_coin, times_coin = ana_coin

        entry_out = np.zeros((1,), dtype=sink_list[0]['dtype'])

        entry_out['height_trigger'] = heights_trig[0]
        entry_out['height_coincidence'] = heights_coin[0]
        entry_out['deltaT'] = times_coin[0] - times_trig[0]
        return [entry_out]

    process = rbProcess(source_list=source_list, sink_list=sink_list, config_dict=config_dict, ufunc=main, **rb_info)
    process()
