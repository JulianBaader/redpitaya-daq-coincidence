# Setup
Clone this repo
Clone the mimoCoRB repo (tested version: https://github.com/GuenterQuast/mimoCoRB/tree/af59dc24915f25d95c82944d6aeff0a67fc8080f)

Create a Python11 enviroment (according to Günter never pyhton should work with mimoCoRB, this wasn't tested).

Install packages (mimoCoRB, ...) in this enviroment-> ... needs to be tested which packages are required exactly.
kafe2 and PhyPraKit should suffice

To install mimoCoRB browse to the mimoCoRB folder and run
```console
pip install .
```


Connect the RedPitaya to the setup (HPGe to In1 and NaI to In2). Make sure the jumpers on the redpitaya are both set to low voltage.
Set the configuration of the amplifiers according to the Appendix.


To record a spectrum browse to the redpitaya-daq-coincidence folder and run
```console
python run_mimo_daq.py spectrum1_setup.yaml
python run_mimo_daq.py spectrum2_setup.yaml
```


To record coincidences run
```console
python run_mimo_daq.py coincidence_setup.yaml
```

