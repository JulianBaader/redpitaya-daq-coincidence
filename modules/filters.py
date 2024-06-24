from mimocorb import mimo_buffer as bm
from scipy import signal
import numpy as np
from numpy.lib import recfunctions as rfn
import sys
import os

def find_rightmost_valid_position(array, upper_bound, lower_bound, right_bound_index):
    """
    Finds the rightmost position in the array where the values are within specified bounds.

    Parameters:
        array (ndarray): Array of values.
        upper_bound (float): Upper bound for the values.
        lower_bound (float): Lower bound for the values.
        right_bound_index (int): Right boundary index for searching positions within bounds.

    Returns:
        int: The rightmost index of the position where the value is within bounds if found, otherwise None.
    """
    # Find positions where the array values are within the specified bounds
    valid_range = np.logical_and(array[:right_bound_index] <= upper_bound, 
                                 array[:right_bound_index] >= lower_bound)
    valid_positions = np.nonzero(valid_range)[0]
    
    # Return the last position where the value is within bounds, if any
    if valid_positions.size > 0:
        return valid_positions[-1]
    else:
        return None

def compute_peak_properties(input_signal, peaks_indices, peaks_properties, array, upper_bound, lower_bound):
    """
    Computes and filters properties of the peaks in the input signal based on criteria.

    Parameters:
        input_signal (ndarray): The input signal data.
        peaks_indices (ndarray): Indices of the peaks.
        peaks_properties (dict): Properties of the peaks.
        array (ndarray): Array used for additional computations (e.g., gradient).
        upper_bound (float): Upper bound for valid positions in the array.
        lower_bound (float): Lower bound for valid positions in the array.

    Returns:
        tuple: Filtered peaks indices and their properties.
    """
    start_positions = []
    start_heights = []
    peak_heights = []
    height_differences = []
    filtered_peaks_indices = []
    filtered_peaks_properties = {prop: [] for prop in peaks_properties.keys()}

    right_bound_indices = peaks_properties['left_ips']

    for i, peak_index in enumerate(peaks_indices):
        right_bound_index = int(right_bound_indices[i])
        start_position = find_rightmost_valid_position(array, upper_bound, lower_bound, right_bound_index)
        
        if start_position is not None:
            start_height = input_signal[start_position]
            peak_height = input_signal[peak_index]
            height_difference = peak_height - start_height

            start_positions.append(start_position)
            start_heights.append(start_height)
            peak_heights.append(peak_height)
            height_differences.append(height_difference)
            filtered_peaks_indices.append(peak_index)

            for prop in peaks_properties.keys():
                filtered_peaks_properties[prop].append(peaks_properties[prop][i])

    filtered_peaks_properties['start_position'] = start_positions
    filtered_peaks_properties['absolute_height_at_start'] = start_heights
    filtered_peaks_properties['absolute_height_at_peak'] = peak_heights
    filtered_peaks_properties['relative_height'] = height_differences
    
    return filtered_peaks_indices, filtered_peaks_properties

def tag_peaks(input_data, prominence, distance, width, upper_bound, lower_bound):
    """
    Tags peaks in the input data and computes their properties.

    Parameters:
        input_data (ndarray): Structured array with signal data.
        prominence (dict): Prominence values for each signal.
        distance (dict): Minimum distance between peaks for each signal.
        width (dict): Width values for each signal.
        upper_bound (dict): Upper bounds for valid positions in the gradient array for each signal.
        lower_bound (dict): Lower bounds for valid positions in the gradient array for each signal.

    Returns:
        tuple: Peaks indices and their properties for each signal.
    """
    peaks = {}
    peaks_properties = {}

    for key in input_data.dtype.names:
        peaks_indices, initial_peaks_properties = signal.find_peaks(
            input_data[key], prominence=prominence[key], distance=distance[key], width=width[key]
        )

        gradient_array = np.gradient(input_data[key])  # Here you can pass any array, not just gradient
        filtered_peaks_indices, filtered_peaks_properties = compute_peak_properties(
            input_data[key], peaks_indices, initial_peaks_properties, gradient_array, upper_bound[key], lower_bound[key]
        )

        peaks[key] = filtered_peaks_indices
        peaks_properties[key] = filtered_peaks_properties

    return peaks, peaks_properties


def normed_pulse(ch_input, position, prominence, analogue_offset):
    # > Compensate for analogue offset
    ch_data = ch_input - analogue_offset
    # > Find pulse area
    #       rel_height is not good because of the quantized nature of the picoscope data
    #       so we have to "hack" a little bit to always cut 10mV above the analogue offset
    width_data = signal.peak_widths(ch_data, [int(position)], rel_height=(ch_data[int(position)] - 10) / prominence)
    left_ips, right_ips = width_data[2], width_data[3]
    # Crop pulse area and normalize
    pulse_data = ch_data[int(np.floor(left_ips)) : int(np.ceil(right_ips))]
    pulse_int = sum(pulse_data)
    pulse_data *= 1 / pulse_int
    return pulse_data, int(np.floor(left_ips)), pulse_int


def correlate_pulses(data_pulse, reference_pulse):
    correlation = signal.correlate(data_pulse, reference_pulse, mode="same")
    shift_array = signal.correlation_lags(data_pulse.size, reference_pulse.size, mode="same")
    shift = shift_array[np.argmax(correlation)]
    return shift


def correlate_peaks(peaks, tolerance):
    m_dtype = []
    for key in peaks.keys():
        m_dtype.append((key, np.int32))
    next_peak = {}
    for key, data in peaks.items():
        if len(data) > 0:
            next_peak[key] = data[0]
    correlation_list = []
    while len(next_peak) > 0:
        minimum = min(next_peak.values())
        line = []
        for key, data in peaks.items():
            if key in next_peak:
                if abs(next_peak[key] - minimum) < tolerance:
                    idx = data.tolist().index(next_peak[key])
                    line.append(idx)
                    if len(data) > idx + 1:
                        next_peak[key] = data[idx + 1]
                    else:
                        del next_peak[key]
                else:
                    line.append(-1)
            else:
                line.append(-1)
        correlation_list.append(line)
    array = np.zeros(len(correlation_list), dtype=m_dtype)
    for idx, line in enumerate(correlation_list):
        array[idx] = tuple(line)
    return array


def match_signature(peak_matrix, signature):
    if len(signature) > len(peak_matrix):
        return False
    # Boolean array with found peaks
    input_peaks = rfn.structured_to_unstructured(peak_matrix) >= 0
    must_have_peak = np.array(signature, dtype=np.str0) == "+"
    must_not_have_peak = np.array(signature, dtype=np.str0) == "-"
    match = True
    # Check the signature for each peak (1st peak with 1st signature, 2nd peak with 2nd signature, ...)
    for idx in range(len(signature)):
        # Is everywhere a peak, where the signature expects one -> Material_conditial(A, B): (not A) OR B
        first = (~must_have_peak[idx]) | input_peaks[idx]
        # Is everywhere no peak, where the signature expects no peak -> NAND(A, B): not (A and B)
        second = ~(must_not_have_peak[idx] & input_peaks[idx])
        match = match & (np.all(first) & np.all(second))
    return match


if __name__ == "__main__":
    print("Script: " + os.path.basename(sys.argv[0]))
    print("Python: ", sys.version, "\n".ljust(22, "-"))
    print("THIS IS A MODULE AND NOT MEANT FOR STANDALONE EXECUTION")
