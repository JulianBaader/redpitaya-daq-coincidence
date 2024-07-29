from scipy import signal
import numpy as np

def tag_peaks(input_data, peak_config):
    peaks = {}
    peaks_prop = {}
    for key in input_data.dtype.names:
        peaks[key], peaks_prop[key] = signal.find_peaks(
            input_data[key], prominence=peak_config['prominence'], distance=peak_config['distance'], width=peak_config['width']
        )
    return peaks, peaks_prop

# Pulse height detection like Pavels algorhythm
def find_first_value(arr, i, min_value,direction="left"):
    """
    Find the first value in the array `arr` that is less than or equal to `min_value`
    to the left or to the right of the given index `i`.

    Args:
        arr (array-like): The input array.
        i (int): The index to search around.
        min_value (float): The minimum value to compare against.
        direction (str): The direction to search in. Can be "left" or "right".

    Returns:
        int: The index of the first value that satisfies the condition, or -1 if no such value is found.
    """
    
    if i < 0 or i > len(arr):
        return -1  # return -1 if i is out of the array bounds
    
    # Convert to numpy array if not already
    arr = np.array(arr)
    
    # Get indices where the value is less than or equal to min_value
    if direction == "left":
        valid_indices = np.where(arr[:i] <= min_value)[0]
    elif direction == "right":
        valid_indices = np.where(arr[i:] <= min_value)[0]
    else:
        print("Invalid direction given")
    
    if valid_indices.size == 0:
        return -1  # No values less than or equal to min_value found before index i
    
    return valid_indices[-1]


def pulse_height_pavel(input_data, pulse_height_pavel_config):
    peaks, peaks_prop = tag_peaks(input_data, pulse_height_pavel_config['peak_config'])
    for key in input_data.dtype.names:
        #if len(peaks[key])==0:
        #    return None, None
        heights = []
        #start_positions = []
        for peak, left_ips in zip(peaks[key], peaks_prop[key]['left_ips']):
            if pulse_height_pavel_config['baseline_mode'][key] == "gradient":
                start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), pulse_height_pavel_config['baseline_value'][key],'left')
                if start_position != -1:
                    heights.append(int(input_data[key][peak] - input_data[key][start_position]))
                    #start_positions.append(start_position)
                else: 
                    return None, None
            elif pulse_height_pavel_config['baseline_mode'][key] == "constant":
                heights.append(int(input_data[key][peak]-pulse_height_pavel_config['baseline_value'][key]))
            else:
                print("No configuration for pulse_height_pavel[baseline_mode] given")
        peaks_prop[key]['height'] = heights
        #peaks_prop[key]['start'] = start_positions
    
    return peaks, peaks_prop
        
# <--- End Pulse height detection like Pavel

def pha_jump(input_data, config):
    # read config
    peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
    gradient_min = config['gradient_min']
    
    peaks, peaks_prop = tag_peaks(input_data, peak_config)
    for key in input_data.dtype.names:
        jumps = []
        for index in range(len(peaks[key])):
            peak = peaks[key][index]
            left_ips = peaks_prop[key]['left_ips'][index]
            start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), gradient_min,'left')
            if start_position != -1:
                jumps.append(int(input_data[key][peak] - input_data[key][start_position]))
            else:
                # ToDo Error Handeling peak löschen oder None zurückgeben
                jumps.append(None)
                peaks[key][index] = None
                print("No start position found in pha_jump. If this occours often, consider changing the gradient_min value or the error handeling.")
        peaks_prop[key]['jump'] = jumps
    return peaks, peaks_prop

def pha_integral(input_data, config):
    # read config
    peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
    
    peaks, peaks_prop = tag_peaks(input_data, peak_config)
    for key in input_data.dtype.names:
        integrals = []
        for peak, left_ips, right_ips in zip(peaks[key], peaks_prop[key]['left_ips'], peaks_prop[key]['right_ips']):
            integrals.append(np.trapezoid(input_data[key][left_ips:right_ips]))
        peaks_prop[key]['integral'] = integrals
    return peaks, peaks_prop

def pha_matched(input_data, config):
    # read config
    minimum_overlap = config['minimum_overlap']
    file_name = config['file_name']
    # read average pulse
    average_pulse = np.loadtxt(file_name)
    
    # get maximum of convolution
    max_conv = np.max(np.convolve(input_data, average_pulse, mode='valid'))
    return max_conv if max_conv > minimum_overlap else None
            


def pulse_height_integral(input_data, pulse_height_integral_config):
    peaks, peaks_prop = tag_peaks(input_data, pulse_height_integral_config['peak_config'])
    for key in input_data.dtype.names:
        heights = []
        for peak, left_ips, right_ips in zip(peaks[key], peaks_prop[key]['left_ips'], peaks_prop[key]['right_ips']):
            if pulse_height_integral_config['start_stop_mode'][key] == "gradient":
                start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), pulse_height_integral_config['baseline_value'][key],'left')
                stop_position = find_first_value(np.gradient(input_data[key]), int(right_ips), pulse_height_integral_config['baseline_value'][key],'right')
            elif pulse_height_integral_config['start_stop_mode'][key] == "constant":
                start_position = find_first_value(input_data[key], int(left_ips), pulse_height_integral_config['baseline_value'][key],'left')
                stop_position = find_first_value(input_data[key], peak, pulse_height_integral_config['baseline_value'][key],'right')
            elif pulse_height_integral_config['start_stop_mode'][key] == "left_ips_to_peak":
                start_position = int(left_ips)
                stop_position = peak
            elif pulse_height_integral_config['start_stop_mode'][key] == "left_ips_to_right_ips":
                start_position = int(left_ips)
                stop_position = int(right_ips)
            elif pulse_height_integral_config['start_stop_mode'][key] == "left_gradient_to_peak":
                start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), pulse_height_integral_config['baseline_value'][key],'left')
                stop_position = peak
            else:
                print("No configuration for pulse_height_pavel[baseline_mode] given")
            if start_position != -1 and stop_position != -1:
                heights.append(np.trapz(input_data[key][start_position:stop_position]-input_data[key][start_position])/(stop_position-start_position))
            else: 
                return None, None

        peaks_prop[key]['height'] = heights

    return peaks, peaks_prop