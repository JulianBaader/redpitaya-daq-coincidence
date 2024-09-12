from scipy import signal
import numpy as np



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
        

    # find start of peaks
    left_ips = peaks_prop['left_ips']
    starts = []
    for ips in left_ips:
        starts.append(find_first_value(np.gradient(osc_data), int(ips), gradient_min,'left'))
    # check if start is valid
    invalid = []
    for i in range(len(peaks)):
        if starts[i] == -1:
            invalid.append(i)
            continue
        if starts[i] - constant_length < 0:
            invalid.append(i)
            continue
        std = np.std(osc_data[starts[i]-constant_length:starts[i]])
        if std > fluctuation:
            invalid.append(i)
            continue
    peaks = np.delete(peaks, invalid)
    starts = np.delete(starts, invalid)
    if len(peaks) == 0:
        return [], [], []
    else:
        heights = osc_data[peaks] - osc_data[starts]
    
    times = []
    invalid = []
    # get times
    # as zero crossing
    # for i in range(len(peaks)):
    #     time = find_first_value(osc_data,peaks[i],0,'right')
    #     times.append(time)
    #     if time == -1:
    #         invalid.append(i)
    # peaks = np.delete(peaks, invalid)
    # heights = np.delete(heights, invalid)
    # times = np.delete(times, invalid)
    
    # position of the maximum
    times = peaks
    # evaluated start of the peak
    # times = starts
    
    # in testing with Na22 and Co60 the position of the peak had the smalles uncertainty on the timing.
    

    
    return peaks, heights, times

