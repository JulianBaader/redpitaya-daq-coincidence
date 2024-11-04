from scipy import signal
import numpy as np


# Pulse height detection like Pavels algorhythm
def find_first_value(arr, i, min_value, direction="left"):
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

    return (
        int(valid_indices[-1]) if direction == "left" else int(valid_indices[0] + i)
    )  # TODO kann das grad net denken ob der right part stimmt


def pha(osc_data, peak_config):
    """This will return false if there are multiple peaks or no peak with valid start is found"""
    prominence = peak_config['prominence']
    width = peak_config['width']
    gradient_min = peak_config['gradient_min']

    peaks, peaks_prop = signal.find_peaks(osc_data, prominence=prominence, width=width)

    if len(peaks) != 1:
        return False

    # find start of peaks
    left_ips = peaks_prop['left_ips']
    starts = []
    for ips in left_ips:
        starts.append(find_first_value(np.gradient(osc_data), int(ips), gradient_min, 'left'))
    if -1 in starts:
        return False

    heights = osc_data[peaks] - osc_data[starts]
    times = peaks

    return peaks, heights, times
