# DWM1001-DEV Position Reader

A Python program to read position data from Decawave DWM1001-DEV Ultra-Wideband (UWB) tags. This program provides both basic functionality for communicating with DWM1001-DEV tags via serial interface.

# ssh commands
ip address to ssh to: 100.71.52.88
static ip address to ssh to: 192.168.1.1

Run to find com port
```bash
bash find_com_port.sh
```

Run to listen for position data with the com port passed as an argument
```bash
bash uwb_listener.sh [com_port]
```

The bash files runs these commands
cd Desktop/Code/UWB-Subsytem
source .venv/bin/activate
python com_port_finder.py
python dwm1001_reader.py [com_port]
