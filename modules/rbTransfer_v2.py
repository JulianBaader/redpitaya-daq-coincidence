from mimocorb import mimo_buffer as bm
# from mimocorb bufferinfoGUI import bufferinfoGUI
# from mimocorb.activity_logger import Gen_logger

# import time
# import os
# import sys
# import shutil
# import yaml
# from pathlib import Path
# import numpy as np
# from numpy.lib import recfunctions as rfn
# from multiprocessing import Process, active_children, Queue
# import threading
# import pandas as pd
# import io
# import tarfile
# import logging


class rbTransfer_v2:
    """Read data from input buffer, filter/analyze data and write to output buffer(s)
    Data is provided as the argument to a user-defined filter function
    returing
    None if data to be discarded or a list mapping to the output buffers. Each element of the list can be
        None: data to be rejected
        True: raw data to be copied
        numpy structured array: data to be written to output buffer
        list of numpy structured arrays: data to be copied to output buffer: each element of the list into a slot.

    Args:

    - buffer configurations (only one source and severals sinks, no observers!)

    - function ufunc() must return

        -  None if data to be rejected,
        -  list mapping to the output buffers. Each element of the list can be
            -  None if data to be rejected
            -  True if raw data to be copied
            -  numpy structured array to be written to output buffer
            -  list of numpy structured arrays to be copied to output buffer: each element of the list into a slot.

    Action:

        store accepted data in buffers

    """

    def __init__(self, source_list=None, sink_list=None, config_dict=None, ufunc=None, **rb_info):
        """
        Class to filter data in input buffer and transfer to output buffer(s)

        :param _list: list of length 1 with dictionary for source buffer
        :param _list: list with dictionary(ies) for destination buffer(s)
        :param observe_list: list of length 1 with dictionary for observer (not implemented yet)
        :param config_dict: application-specific configuration
        :param ufunc: user-supplied function to filter, process and store data
        :param rb_info: dictionary with names and function (read, write, observe) of ring buffers
        """

        if not callable(ufunc):
            self.logger.error("User-supplied function is not callable!")
            raise ValueError("ERROR! User-supplied function is not callable!")
        else:
            self.filter = ufunc  # external function to filter data
        #   get source
        if source_list is not None:
            self.reader = bm.Reader(source_list[0])
            if len(source_list) > 1:
                print("!!! more than one reader process currently not supported")
        else:
            self.reader = None

        #   get sinks and start writer process(es)
        self.number_of_output_buffers = len(sink_list)
        if sink_list is not None:
            self.writers = []
            for i in range(self.number_of_output_buffers):
                self.writers.append(bm.Writer(sink_list[i]))
        else:
            self.writers = None

        if self.reader is None or self.writers is None:
            ValueError("ERROR! Faulty ring buffer configuration!!")

    def __call__(self):
        # process_data
        while self.reader._active.is_set():
            # Get new data from buffer ...
            input_data = self.reader.get()

            #  ... and process data with user-provided filter function
            filter_data = self.filter(input_data)
            # expected return values:
            #   None to discard data or
            #   List mapping to the output buffers. Each element of the list can be
            #       None: data to be rejected
            #       True: raw data to be copied
            #       numpy structured array: data to be written to output buffer
            #       list of numpy structured arrays: data to be copied to output buffer: each element of the list into a slot.

            if filter_data is None:
                #  data rejected by filter
                continue
            
            if len(filter_data) != self.number_of_output_buffers:
                ValueError("ERROR! Number of output buffers does not match number of filter return values!!")
            
            for i in range(self.number_of_output_buffers):
                if filter_data[i] is None:
                    #  data rejected by filter
                    continue
                if filter_data[i] is True:
                    #  raw data to be copied
                    buf = self.writers[i].get_new_buffer()
                    for ch in input_data.dtype.names:
                        buf[ch] = input_data[ch]
                    self.writers[i].set_metadata(*self.reader.get_metadata())
                    self.writers[i].process_buffer()
                elif isinstance(filter_data[i], (list, tuple)):
                    #  data to be copied to output buffer: each element of the list into a slot
                    for d in filter_data[i]:
                        if d is not None:
                            buf = self.writers[i].get_new_buffer()
                            buf[:] = 0
                            for ch in d.dtype.names:
                                buf[ch] = d[ch]
                            self.writers[i].set_metadata(*self.reader.get_metadata())
                            self.writers[i].process_buffer()
                else:
                    #  data to be written to output buffer
                    buf = self.writers[i].get_new_buffer()
                    buf[:] = 0
                    for ch in filter_data[i].dtype.names:
                        buf[ch] = filter_data[i][ch]
                    self.writers[i].set_metadata(*self.reader.get_metadata())
                    self.writers[i].process_buffer()




# <-- end class rbTransfer