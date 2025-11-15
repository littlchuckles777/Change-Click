# Change-Click

Change-Click is a small background utility that listens for Mouse 5 press
and hold events (commonly the second side button). While the button is held
down, the application captures the colours of ten pixels clustered around
the centre of the primary monitor. If the colour of any of those pixels
changes, Change-Click simulates a natural-looking press of the `x` key.

## Features

- Global listener that works even when the script is out of focus.
- Samples only the necessary pixels for responsiveness.
- Adds subtle randomness to key presses to avoid robotic behaviour.

## Requirements

- Python 3.10+
- [mss](https://python-mss.readthedocs.io/)
- [pynput](https://pynput.readthedocs.io/)

Install the dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

Run the tool from a terminal:

```bash
python main.py
```

Hold Mouse 5 to capture the baseline colours. While the button remains held,
the script monitors for colour changes and taps `x` when a change is detected.
Release the button to stop monitoring. Press `Ctrl+C` in the terminal to exit.
