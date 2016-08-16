# Akari

I wanted to emit the state of my Phillips Hue lights to my local influxdb, so I made this.

# Installation

- Checkout this repo and enter:
  ```bash
  $ git clone https://github.com/kennydo/akari.git
  $ cd akari
  ```

- Create a Python 3.5 virtualenv:
  ```bash
  $ pyvenv venv
  ```

- Install the dependencies:
  ```bash
  $ pip install -r requirements.txt
  ```

- Install akari:
  ```bash
  $ python setup.py install
  ```
  
- Create a config file based on the contents of `config/example.conf`:
  ```bash
  $ vim my-config.conf
  ```

- Install the systemd timer and service into `/etc/systemd/system/multi-user.target.wants`:
  ```bash
  $ cp etc/systemd/system/multi-user.target.wants/akari-*{.timer,.service} /etc/systemd/system/multi-user.target.wants/
  ```
