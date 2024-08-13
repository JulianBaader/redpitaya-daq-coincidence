from mimocorb.activity_logger import Gen_logger
from mimocorb import mimo_buffer as bm

class rp_mimocorb:
    """
    Recieve data from external source (e.g. front-end device, file, simulation, etc.)
    and put data in mimo_buffer.

    Returns False if sink is not active
    """

    def __init__(self, sink_list=None, config_dict=None, ufunc=None, **rb_info):
        """
        Class to provide external input data to a buffer, usually "RB_1"

        :param sink_list: list of length 1 with dictionary for destination buffer
        :param observe_list: list of length 1 with dictionary for observer (not implemented yet)
        :param config_dict: application-specific configuration
        :param ufunc: user-supplied function to provide input data
        :param rb_info: dictionary with names and function (read, write, observe) of ring buffers
        """

        # sub-logger for this class
        self.logger = Gen_logger(__class__.__name__)

        # general part for each function (template)
        if sink_list is None:
            self.logger.error("Faulty ring buffer configuration passed, 'sink_list' missing!")
            raise ValueError("ERROR! Faulty ring buffer configuration passed ('sink_list' missing)!")

        self.sink = None
        for key, value in rb_info.items():
            if value == "read":
                self.logger.error("Reading buffers not foreseen!!")
                raise ValueError("ERROR! reading buffers not foreseen!!")
            elif value == "write":
                self.logger.info(f"Writing to buffer {sink_list[0]}")
                self.sink = bm.Writer(sink_list[0])
                if len(sink_list) > 1:
                    self.logger.error("More than one sink presently not foreseen!")
                    print("!!! More than one sink presently not foreseen!!")
            elif value == "observe":
                self.logger.error("Observer processes not foreseen!")
                raise ValueError("ERROR! obervers not foreseen!!")

        if self.sink is None:
            self.logger.error("Faulty ring buffer configuration passed. No sink found!")
            raise ValueError("Faulty ring buffer configuration passed. No sink found!")

        self.number_of_channels = len(self.sink.dtype)
        self.chnams = [self.sink.dtype[i][0] for i in range(self.number_of_channels)]

        self.event_count = 0
        self.T_last = time.time()

    def __call__(self, data, metadata):
        if self.sink._active.is_set() and data is not None:
            # do not write data if in paused mode
            if self.sink._paused.is_set():
                time.sleep(0.1)
                return

            T_data_ready = time.time()
            timestamp = time.time_ns() * 1e-9  # in s as type float64
            self.event_count += 1

            # get new buffer and store event data and meta-data
            buffer = self.sink.get_new_buffer()
            # - fill data and metadata
            for i in range(self.number_of_channels):
                buffer[self.chnams[i]][:] = data[i]

            # - account for deadtime
            T_buffer_ready = time.time()
            deadtime = T_buffer_ready - T_data_ready
            deadtime_fraction = deadtime / (T_buffer_ready - self.T_last)
            if metadata is None:
                self.sink.set_metadata(self.event_count, timestamp, deadtime_fraction)
            else:
                self.sink.set_metadata(*metadata)  # tuple to parameter list

            self.T_last = T_buffer_ready
        else:
            # make sure last data entry is also processed
            self.sink.process_buffer()

        return self.sink._active.is_set()


# <-- end class push_to_rb



class rp_mimocorb:
    """Interface for rpControll to the daq rinbuffer mimoCoRB"""

    def __init__(self, source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
        # initialize mimoCoRB interface
        # self.rb_exporter = rbPut(config_dict=config_dict, sink_list=sink_list, **rb_info) # Wie mach ich das? weil die Argumente stimmen net überein :(
        # self.number_of_channels = len(self.rb_exporter.sink.dtype) #Brauch ich nicht, kann gelöscht werden
        # self.events_required = 100000 if "eventcount" not in config_dict else config_dict["eventcount"] # Wird in zukunft vom rpControll gehandelt

        # self.event_count = 0 # Wird von rpControll gehandelt
        self.active = True

    def __call__(self, data):
        """function called by redPoscdaq"""
        if (self.events_required == 0 or self.event_count < self.events_required) and self.active:
            # deliver pulse data and no metadata
            self.active = self.rb_exporter(data, None)  # send data
            self.event_count += 1
        else:
            self.active = self.rb_exporter(None, None)  # send None when done
            print("redPoscdaq exiting")
            sys.exit()
            
def rp_to_rb(source_list=None, sink_list=None, observe_list=None, config_dict=None, **rb_info):
    """Main function,
    executed as a multiprocessing Process, to pass data from the RedPitaya to a mimoCoRB buffer

    :param config_dict: configuration dictionary
      - events_required: number of events to be taken
      - number_of_samples, sample_time_ns, pretrigger_samples and analogue_offset
      - decimation index, invert flags, trigger mode and trigger direction for RedPitaya
    """

    # initialize mimocorb class
    rb_source = rp_mimocorb(config_dict=config_dict, sink_list=sink_list, **rb_info)
    rpControll(config_dict=config_dict, callback=rb_source)


if __name__ == "__main__":  # --------------------------------------
    # run mimoCoRB data acquisition suite
    # the code below is idenical to the mimoCoRB script run_daq.py
    import argparse
    import sys
    import time
    from mimocorb.buffer_control import run_mimoDAQ

    # define command line arguments ...
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename", nargs="?", default="demo_setup.yaml", help="configuration file")
    parser.add_argument("-v", "--verbose", type=int, default=2, help="verbosity level (2)")
    parser.add_argument("-d", "--debug", action="store_true", help="switch on debug mode (False)")
    # ... and parse command line input
    args = parser.parse_args()

    print("\n*==* script " + sys.argv[0] + " running \n")
    daq = run_mimoDAQ(args.filename, verbose=args.verbose, debug=args.debug)
    daq.setup()
    daq.run()
    print("\n*==* script " + sys.argv[0] + " finished " + time.asctime() + "\n")