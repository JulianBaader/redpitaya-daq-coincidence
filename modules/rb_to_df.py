import numpy as np
import pandas as pd
from mimocorb.buffer_control import rbExport
from numpy.lib import recfunctions as rfn
import time


class rb_to_df:
    """Save data to a DataFrame which regularly saves to disk."""

    def __init__(self, source_list=None, config_dict=None, **rb_info):
        """
        Class to extract data and store in pandas DataFrame

        :param _list: list of length 1 with dictionary for source buffer
        :param observe_list: list of length 1 with dictionary for observer (not implemented yet)
        :param config_dict: application-specific configuration (file name, update interval)
        :param rb_info: dictionary with names and function (read, write, observe) of ring buffers
        """

        # general part for each function (template)
        if source_list is None:
            raise ValueError("Faulty ring buffer configuration passed ('source_list' missing)!")
        if config_dict is None:
            raise ValueError("Faulty configuration passed ('config_dict' missing)!")

        if len(source_list) != 1:
            raise ValueError("Only one source buffer allowed for rb_to_df!")

        source_dict = source_list[0]
        if source_dict['values_per_slot'] != 1:
            raise ValueError("Only one value per slot allowed for rb_to_df!")

        self.readData = rbExport(source_list=source_list, config_dict=config_dict, **rb_info)

        self.filename = config_dict["directory_prefix"] + "/" + config_dict["filename"] + ".txt"

        self.update_interval = config_dict["update_interval"]

        self.header = ['counter', 'timestamp', 'deadtime']
        keys = [val[0] for val in source_dict["dtype"]]
        for key in keys:
            self.header.append(key)

        # Construct header and corresponding dtype

        self.data = []
        df = pd.DataFrame(self.data, columns=self.header)
        df.to_csv(self.filename, sep="\t", index=False)

    def __del__(self):
        pass

    def __call__(self):
        # sart reading and save to text file
        # TODO wär das nicht eigentlich sinnvoll rbExporter zu verwenden? also schöner zumindest. Könnte aber etwas langsamer sein
        last_update_time = time.time()
        while True:
            input_data = next(self.readData())
            if input_data is None:
                break  # last event is none
            data, metadata = input_data
            data_unstructured = rfn.structured_to_unstructured(data[0])
            newline = np.append(metadata, data_unstructured)
            self.data.append(newline)
            if time.time() - last_update_time > self.update_interval:
                df = pd.DataFrame(self.data, columns=self.header)
                df.to_csv(self.filename, sep="\t", index=False, mode="a", header=False)
                last_update_time = time.time()
                self.data = []
        #  END
        print("\n ** rb_toTxtfile: end seen")
        # TODO irgendwie bekomme ich diesen print nicht, das heißt wiederum, dass man kein finales speichern machen kann.
        # TODO also wenns blöd läuft, dann sind die letzten paar Zeilen nicht gespeichert. Das sollte
        # TODO man irgendwie noch fixen. Aber das ist jetzt nicht sooo wichtig


# <-- end class rb_to_df
