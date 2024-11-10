# Setup
Clone this repo

Clone the mimoCoRB repo (tested version: https://github.com/GuenterQuast/mimoCoRB/tree/af59dc24915f25d95c82944d6aeff0a67fc8080f)

Create a Python11 environment (newer python versions should work with mimoCoRB, this wasn't tested yet).

Install packages (mimoCoRB, PhyPraKit, kafe2) in this environment.

To install mimoCoRB browse to the mimoCoRB folder and run
```console
pip install .
```
Update the mcpha-server on the RedPitaya (also available here: https://github.com/JulianBaader/red-pitaya-notes/tree/daq)

Connect the Red Pitaya to the setup (HPGe to In1 and NaI to In2). Ensure the Red Pitaya jumpers are both set to low voltage.
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

