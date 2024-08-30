from scipy import signal
import numpy as np


# def tag_peaks(input_data, peak_config):
#     peaks = {}
#     peaks_prop = {}
#     for key in input_data.dtype.names:
#         peaks[key], peaks_prop[key] = signal.find_peaks(
#             input_data[key], prominence=peak_config['prominence'], distance=peak_config['distance'], width=peak_config['width']
#         )
#         # remove peaks that clip
#         clipped = []
#         for i in range(len(peaks[key])):
#             if input_data[key][peaks[key][i]] >= peak_config['clip_value']:
#                 clipped.append(i)
#         peaks[key] = np.delete(peaks[key], clipped)
#         for prop in peaks_prop[key]:
#             peaks_prop[key][prop] = np.delete(peaks_prop[key][prop], clipped)
                
                
#     return peaks, peaks_prop

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
        raise ValueError("Index i is out of the array bounds")
    
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
    
    return int(valid_indices[-1]) if direction == "left" else int(valid_indices[0] + i) #TODO kann das grad net denken ob der right part stimmt

def pha(osc_data, peak_config):
    #TODO it would be nice to be able to look at peaks that are not valid
    prominence = peak_config['prominence']
    width = peak_config['width']
    clip_value = peak_config['clip_value']
    gradient_min = peak_config['gradient_min']
    fluctuation = peak_config['fluctuation']
    constant_length = peak_config['constant_length']
    
    
    peaks, peaks_prop = signal.find_peaks(osc_data, prominence=prominence, width=width)

    # remove peaks that clip
    clipped = []
    for i in range(len(peaks)):
        if osc_data[peaks[i]] >= clip_value:
            clipped.append(i)
    peaks = np.delete(peaks, clipped)
    for prop in peaks_prop:
        peaks_prop[prop] = np.delete(peaks_prop[prop], clipped)
        

    # find start of peak
    left_ips = peaks_prop['left_ips']
    start = []
    for ips in left_ips:
        start.append(find_first_value(np.gradient(osc_data), int(ips), gradient_min,'left'))
    # check if start is valid
    invalid = []
    for i in range(len(peaks)):
        if start[i] == -1:
            invalid.append(i)
            continue
        if start[i] - constant_length < 0:
            invalid.append(i)
            continue
        std = np.std(osc_data[start[i]-constant_length:start[i]])
        if std > fluctuation:
            invalid.append(i)
            continue
    peaks = np.delete(peaks, invalid)
    start = np.delete(start, invalid)
    if len(peaks) == 0:
        return [], []
    else:
        heights = osc_data[peaks] - osc_data[start]
    return peaks, heights


# def pha_jump(input_data, config):
#     # read config
#     peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
#     gradient_min = config['gradient_min']
    
#     peaks, peaks_prop = tag_peaks(input_data, peak_config)
#     for key in input_data.dtype.names:
#         jumps = []
#         no_start = []
#         #for index in range(len(peaks[key])):
#         for index in range(min(len(peaks[key]),1)):
#             peak = peaks[key][index]
#             left_ips = peaks_prop[key]['left_ips'][index]
#             start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), gradient_min,'left')
#             if start_position != -1:
#                 jumps.append(int(input_data[key][peak] - input_data[key][start_position]))
#             else:
#                 no_start.append(index)
#                 jumps.append(0)
#         peaks_prop[key]['jump'] = jumps
        
#         # remove peaks that have no start
#         peaks[key] = np.delete(peaks[key], no_start)
#         for prop in peaks_prop[key]:
#             peaks_prop[key][prop] = np.delete(peaks_prop[key][prop], no_start)
#             if len(peaks[key]) != len(peaks_prop[key][prop]):
#                 print("Error in pha_jump aber wttttffff")
#     return peaks, peaks_prop

# def pha_integral(input_data, config):
#     # read config
#     peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
    
#     peaks, peaks_prop = tag_peaks(input_data, peak_config)
#     for key in input_data.dtype.names:
#         integrals = []
#         for peak, left_ips, right_ips in zip(peaks[key], peaks_prop[key]['left_ips'], peaks_prop[key]['right_ips']):
#             integrals.append(np.trapezoid(input_data[key][int(left_ips):int(right_ips)]))
#         peaks_prop[key]['integral'] = integrals
#     return peaks, peaks_prop

# def pha_matched(input_data, config):
#     # Doesnt work for multiple channels
#     # read config
#     minimum_overlap = config['minimum_overlap']
#     file_name = config['file_name']
#     # read average pulse
#     average_pulse = np.loadtxt(file_name)
    
#     # get maximum of convolution
#     max_conv = np.max(np.convolve(input_data['ch1'], average_pulse, mode='valid'))
#     return max_conv if max_conv > minimum_overlap else None


    
    
