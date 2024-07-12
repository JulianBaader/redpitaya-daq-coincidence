from scipy import signal
import numpy as np
from numpy.lib import recfunctions as rfn
import sys
import os


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


def tag_peaks(input_data, prominence, distance, width):
    peaks = {}
    peaks_prop = {}
    for key in input_data.dtype.names:
        peaks[key], peaks_prop[key] = signal.find_peaks(
            input_data[key], prominence=prominence, distance=distance, width=width
        )
    return peaks, peaks_prop


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

def clipping(input_data, clipping_config):
    """
    Check if any channel in the input data exceeds the clipping level.


    Currently clipping_config is a float, can be later eddited to be a dict if more requirements are neccesary
    Args:
        input_data (ndarray): The input data to check for clipping.
        clipping_level (float): The clipping level to check against.

    Returns:
        ndarray:  returns the input_data.
    """
    for channel in input_data.dtype.names:
        if np.max(input_data[channel]) >= clipping_config or np.min(input_data[channel]) <= -clipping_config:
            return None
    return input_data

def coincidence(peaks, coincidence_config, trigger_channel):
    """
    Check if any channel has a peak within the specified coincidence window.

    Args:
        peaks (dict): A dictionary containing the peak data for each channel.
        coincidence_window (int): The maximum distance between peaks for them to be considered coincident.
        trigger_channel (str): The channel to use as the trigger.

    Returns:
        peaks or None: peaks if any channel has a peak within the coincidence window, None otherwise.
    """
    if len(peaks) == 0:
        return None
    for key in peaks.keys():
        if key != trigger_channel and abs(peaks[key][0] - peaks[trigger_channel][0]+coincidence_config['offset']) <= coincidence_config['width']:
            return peaks
    return None


def range_filter(input_data, range_config):
    """
        bin unsischer mit der Implementierung. Pulse Height Analysis wäre vlt etwas übertrieben besonders, wenn die vermutlich im nächsten Schritt gleich kommt
        aber nur über max zu gehen ist auch blöd weil dann der offset von 0 fehlt
    """

if __name__ == "__main__":
    print("Script: " + os.path.basename(sys.argv[0]))
    print("Python: ", sys.version, "\n".ljust(22, "-"))
    print("THIS IS A MODULE AND NOT MEANT FOR STANDALONE EXECUTION")
