from scipy import signal
import numpy as np

def tag_peaks(input_data, peak_config):
    peaks = {}
    peaks_prop = {}
    for key in input_data.dtype.names:
        peaks[key], peaks_prop[key] = signal.find_peaks(
            input_data[key], prominence=peak_config['prominence'], distance=peak_config['distance'], width=peak_config['width']
        )
        # remove peaks that clip
        clipped = []
        for i in range(len(peaks[key])):
            if input_data[key][peaks[key][i]] >= peak_config['clip_value']:
                clipped.append(i)
        peaks[key] = np.delete(peaks[key], clipped)
        for prop in peaks_prop[key]:
            peaks_prop[key][prop] = np.delete(peaks_prop[key][prop], clipped)
                
                
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


def pha_jump(input_data, config):
    # read config
    peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
    gradient_min = config['gradient_min']
    
    peaks, peaks_prop = tag_peaks(input_data, peak_config)
    for key in input_data.dtype.names:
        jumps = []
        no_start = []
        #for index in range(len(peaks[key])):
        for index in range(min(len(peaks[key]),1)):
            peak = peaks[key][index]
            left_ips = peaks_prop[key]['left_ips'][index]
            start_position = find_first_value(np.gradient(input_data[key]), int(left_ips), gradient_min,'left')
            if start_position != -1:
                jumps.append(int(input_data[key][peak] - input_data[key][start_position]))
            else:
                no_start.append(index)
                jumps.append(0)
        peaks_prop[key]['jump'] = jumps
        
        # remove peaks that have no start
        peaks[key] = np.delete(peaks[key], no_start)
        for prop in peaks_prop[key]:
            peaks_prop[key][prop] = np.delete(peaks_prop[key][prop], no_start)
        
    return peaks, peaks_prop

def pha_integral(input_data, config):
    # read config
    peak_config = config['peak_config'] # peak_config can be copied from tag_peaks
    
    peaks, peaks_prop = tag_peaks(input_data, peak_config)
    for key in input_data.dtype.names:
        integrals = []
        for peak, left_ips, right_ips in zip(peaks[key], peaks_prop[key]['left_ips'], peaks_prop[key]['right_ips']):
            integrals.append(np.trapezoid(input_data[key][int(left_ips):int(right_ips)]))
        peaks_prop[key]['integral'] = integrals
    return peaks, peaks_prop

def pha_matched(input_data, config):
    # Doesnt work for multiple channels
    # read config
    minimum_overlap = config['minimum_overlap']
    file_name = config['file_name']
    # read average pulse
    average_pulse = np.loadtxt(file_name)
    
    # get maximum of convolution
    max_conv = np.max(np.convolve(input_data['ch1'], average_pulse, mode='valid'))
    return max_conv if max_conv > minimum_overlap else None


height=None
threshold=None
distance=None
prominence=10
width=None
wlen=None
rel_height=0.5
plateau_size=None

gradient_min=0

constant_length = 50
constant_max_gradient = 1

def first_jump(input_data, config):
    for key in input_data.dtype.names:
        data = input_data[key]
        invalid = []
        peaks, peaks_prop = signal.find_peaks(data, height, threshold, distance, prominence, width, wlen, rel_height, plateau_size)
        for i in range(len(peaks)):
            start = find_first_value(np.gradient(data), peaks[i], gradient_min,'left')
            if start == -1:
                invalid.append(i)
            if np.abs(data[start]-data[start-constant_length])/constant_length > constant_max_gradient:
                invalid.append(i)
        peaks = np.delete(peaks, invalid)
        for prop in peaks_prop:
            peaks_prop[prop] = np.delete(peaks_prop[prop], invalid)
        return peaks, peaks_prop
            
    