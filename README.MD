# Purpose

Display the status of your Enphase Envoy solar system by querying the Envoy on the local network. The script outputs the results in a format which can be used by the BitBar utility (see https://github.com/matryer/bitbar) to display the results in your Mac OS X Menu Bar.

# Examples

![Example 1](https://raw.githubusercontent.com/Iamrodos/EnvoyStats/main/envoy%20menu%20bar%20example%201.png)

![Example 3](https://raw.githubusercontent.com/Iamrodos/EnvoyStats/main/envoy%20menu%20bar%20example%203.png)

# Setup

## 1. Installation

### 1a. Install BitBar

Follow the instructions for this on the BitBar page at https://github.com/matryer/bitbar#get-started

### 1b. Copy the script to the correct folder

Download the script and place it in your BitBar plugins directory.

### 1c. Ensure the script is executable.

Ensure that the script is executable on the system.

Open the ``terminal`` application and execute ``chmod +x solar.4m.rb``. Note you may need to change directory to where the script is or specify its path on the command. 

## 2. Configure

### 2a. Set the IP address of your system

The script will make requests to your Envoy over the local network and therefore needs its IP address. It will look like 4 sets of numbers separated by dots. For example 192.168.0.100 or 10.0.0.40.

If you don't know the IP addres of you Envoy you can do this via the app. 

1. Open the Enlighten application on your device.
2. Click the "Menu" button on the bottom right of the screen.
3. Click "Devices".
4. Click "Envoy".
5. Click "Connect Locally".
6. Click the "Connect" button. This will open the local browser on your device. 

If you don't have the app, you might be able to find it via looking at your local router and listing its connected devices. How do do that is beyond these instructions. 

Once you have the IP address, edit the script in a text editor and replacing the placeholder value with the IP address.

`ENVOY_IP = "enter your IP address here"`

### 2b. Set the size of your system

The script changes its icon depending on how much power is being consumed and generated. If you are consuming more than you are generating it will show a power plug to show that pulling from the grid. If you are generating more than you are using it will show either a sun covered by a cloud, or a bright sun. It uses the cloudy icon if the amount being generated is less than half of the size of your system. Above half and it uses the sun icon. There is no way to determine system size from the local ENVOY (that I have found), so you need to set the value in the script. Enter a value in watts. 

Here is the line you want to change.

`SYSTEM_SIZE_WATTS = 6000`

### 2b. Set how often you want to update the value

BitBar uses the file name of the script to determine how freqently it is run. 

For example a filename of `solar.4m.rb` will run every 4 minutes. Change the number for how frequently to refresh. Having a low value will place a great load on your Envoy's processing. Don't recomend going under a minute. The script comes set to 4 minute (4m). 