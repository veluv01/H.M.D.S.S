# Halloween Motion Detection Scare System

A real-time motion detection system designed for Raspberry Pi that monitors a camera stream and automatically plays scary sounds when motion is detected. Perfect for Halloween pranks and spooky decorations!

![Version](https://img.shields.io/badge/version-1.0-orange)
![Python](https://img.shields.io/badge/python-3.7+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 🎥 **Real-time RTSP/HTTP stream monitoring**
- 👻 **Background subtraction motion detection**
- 🔊 **Automatic scary sound playback**
- 🖥️ **Modern GUI interface**
- 📊 **Live video preview with motion overlay**
- 🔴 **Background subtraction visualization**
- ⚙️ **Adjustable sensitivity settings**
- ⏱️ **Configurable cooldown between scares**
- 📈 **Detection statistics tracking**
- 🎵 **Support for multiple audio formats (MP3, WAV, OGG)**

## System Requirements

### Hardware
- Raspberry Pi 3/4 (or any Linux system)
- IP Camera with RTSP/HTTP stream support
- Audio output device (speakers/headphones)
- Network connection

### Software
- Python 3.7 or higher
- OpenCV 4.x
- Pygame
- Tkinter
- PIL/Pillow

## Installation

### 1. System Update
```bash
sudo apt-get update
sudo apt-get upgrade
```

### 2. Install System Dependencies
```bash
# Install OpenCV and required libraries
sudo apt-get install python3-opencv python3-pygame python3-pil python3-tk

# Install additional dependencies
sudo apt-get install libatlas-base-dev libjasper-dev libqtgui4 libqt4-test
```

### 3. Install Python Packages
```bash
# Using pip (alternative method)
pip3 install opencv-python pygame pillow numpy
```

### 4. Create Project Directory
```bash
mkdir halloween-scare-system
cd halloween-scare-system
```

### 5. Create Sounds Directory
```bash
mkdir scary_sounds
```

### 6. Add Your Scary Sounds
Place your scary audio files (MP3, WAV, or OGG format) in the `scary_sounds` folder:

```
halloween-scare-system/
├── halloween_scare.py
└── scary_sounds/
    ├── scream1.mp3
    ├── evil_laugh.wav
    ├── ghost_moan.mp3
    └── creepy_whisper.ogg
```

## Usage

### Starting the Application
```bash
python3 halloween_scare.py
```

### GUI Controls

#### Connection Settings
1. **Stream URL**: Enter your camera's RTSP/HTTP stream URL
   - Example: `http://192.168.1.100:81/stream`
   - Example: `rtsp://192.168.1.100:554/stream`

#### Control Buttons
- **▶ Start Monitoring**: Connect to camera and begin motion detection
- **⏹ Stop**: Stop monitoring and disconnect from camera
- **⏸ Pause Detection**: Pause motion detection (keeps video running)
- **🔊 Test Sound**: Test audio playback

#### Detection Settings (Sliders)
- **Sensitivity** (10-100): Adjust motion detection sensitivity
  - Lower values = more sensitive
  - Higher values = less sensitive
  - Default: 25
  
- **Cooldown** (1-30 seconds): Time between scare triggers
  - Prevents continuous scaring
  - Default: 5 seconds
  
- **Min Motion Area** (100-2000 pixels): Minimum motion area to trigger
  - Filters out small movements
  - Default: 500 pixels

#### Display Windows
- **Live Feed**: Main camera view with motion detection overlay
- **Motion Detection**: Background subtraction visualization (white = motion)

#### Statistics
- **Total Detections**: Number of times motion was detected
- **Last Detection**: Timestamp of last motion event

### Keyboard Shortcuts
- Press `q` in video window to quit (if using OpenCV windows)

## Configuration Tips

### Camera Stream URLs

Different cameras use different URL formats:

#### Xiao ESP32S3 Sense
```
http://192.168.1.100:81/stream (Correct the IP Address of the camera)

http://192.168.1.100/cam-lo.jpg  (for MJPEG)
```

#### Generic IP Cameras
```
rtsp://username:password@192.168.1.100:554/stream
http://192.168.1.100:8080/video.mjpg
```

#### Testing Your Stream
```bash
# Test with VLC
vlc http://192.168.1.100:81/stream (Correct the IP Address of the camera)

# Test with ffplay
ffplay http://192.168.1.100:81/stream
```

### Optimizing Detection

1. **Too Many False Triggers**:
   - Increase sensitivity value (30-50)
   - Increase min motion area (800-1500)
   - Increase cooldown time (8-15 seconds)

2. **Not Detecting Motion**:
   - Decrease sensitivity value (15-25)
   - Decrease min motion area (300-500)
   - Check camera placement and lighting

3. **Detecting Non-Human Motion** (trees, shadows):
   - Increase min motion area significantly
   - Place camera in stable lighting conditions
   - Avoid areas with moving backgrounds

### Audio Setup

1. **Finding Scary Sounds**:
   - Freesound.org (free sound effects)
   - YouTube Audio Library
   - Record your own with Audacity

2. **Audio Not Playing**:
   ```bash
   # Test audio output
   speaker-test -t wav -c 2
   
   # Check audio devices
   aplay -l
   
   # Set default audio output (Raspberry Pi)
   sudo raspi-config
   # Navigate to: System Options > Audio
   ```

3. **Supported Formats**:
   - MP3 (recommended)
   - WAV (uncompressed, larger files)
   - OGG (compressed, good quality)

## Troubleshooting

### Stream Connection Issues

**Error: "Failed to connect to stream"**
- Verify camera is powered on and connected to network
- Check if URL is correct
- Ping the camera IP: `ping 192.168.1.100` (Correct the IP Address of the camera)
- Try accessing stream in VLC or web browser

**High Latency/Delay**
- Use wired Ethernet instead of WiFi
- Reduce camera resolution/bitrate
- Check network bandwidth
- Close other applications

### Performance Issues

**Low FPS**
```bash
# On Raspberry Pi, increase GPU memory
sudo raspi-config
# Navigate to: Performance Options > GPU Memory
# Set to at least 128MB
```

**High CPU Usage**
- Lower camera resolution to 640x480
- Increase GUI update interval in code
- Use lightweight desktop environment

### GUI Issues

**GUI Not Displaying**
```bash
# Install Tkinter if missing
sudo apt-get install python3-tk

# Test Tkinter
python3 -c "import tkinter; tkinter.Tk()"
```

**Images Not Updating**
- Check if camera stream is active
- Verify network connection
- Restart the application

## Project Structure

```
halloween-scare-system/
├── halloween_scare.py          # Main application
├── scary_sounds/                # Audio files directory
│   ├── scream1.mp3
│   ├── evil_laugh.wav
│   └── ghost_moan.mp3
└── README.md                    # This file
```

## Advanced Configuration

### Modifying Code Parameters

Edit `halloween_scare.py` to adjust advanced settings:

```python
# In HalloweenScareSystem.__init__()

# Background subtractor settings
self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
    history=100,        # Number of frames for background model
    varThreshold=16,    # Threshold for pixel variance
    detectShadows=False # Shadow detection (slower if True)
)

# Audio settings
pygame.mixer.init(
    frequency=22050,    # Sample rate
    size=-16,          # Bit depth
    channels=2,        # Stereo
    buffer=512         # Buffer size (lower = less latency)
)
```

### Camera Buffer Settings

```python
# In connect_stream() method
self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
self.cap.set(cv2.CAP_PROP_FPS, 30)        # Frame rate
```

## Safety & Ethics

⚠️ **Important Considerations**:
- Ensure you have permission to monitor the area
- Place warning signs if recording public spaces
- Be mindful of people with heart conditions
- Don't use excessively loud sounds
- Comply with local privacy laws

## License

MIT License - feel free to modify and distribute

### v1.0 (Current)
- Initial release
- Basic motion detection
- GUI interface
- Multi-audio support
- Real-time monitoring

---

**Happy Halloween! 🎃👻**

*May your scares be frightful and your detections be accurate!*