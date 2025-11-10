#!/usr/bin/env python3
"""
Halloween Motion Detection Scare System for Raspberry Pi
Monitors camera stream and plays scary sounds when motion is detected
With GUI for easy configuration
"""

import cv2
import numpy as np
import pygame
import time
import random
from datetime import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path
from PIL import Image, ImageTk

class HalloweenScareSystem:
    def __init__(self, stream_url="http://192.168.29.215:81/stream"):
        self.stream_url = stream_url
        self.running = False
        self.paused = False
        
        # Motion detection parameters
        self.sensitivity = 25
        self.min_motion_area = 500
        self.cooldown_seconds = 5
        self.last_scare_time = 0
        
        # Background subtraction - optimized for lower latency
        self.bg_subtractor = None
        
        # Statistics
        self.detection_count = 0
        self.last_detection_time = None
        
        # Video capture
        self.cap = None
        self.current_frame = None
        self.display_frame = None
        self.motion_mask = None
        
        # Threading for async processing
        self.processing_lock = threading.Lock()
        
        # Initialize pygame for audio
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.audio_files = []
        self.load_scary_sounds()
        
    def load_scary_sounds(self):
        """Load all audio files from scary_sounds folder"""
        self.audio_files = []
        sounds_dir = Path("scary_sounds")
        
        if not sounds_dir.exists():
            print("Warning: 'scary_sounds' folder not found, creating it...")
            sounds_dir.mkdir(exist_ok=True)
            print("   Please add MP3/WAV files to the 'scary_sounds' folder")
            return
        
        # Supported audio formats
        audio_extensions = ['.mp3', '.wav', '.ogg']
        
        for ext in audio_extensions:
            for audio_file in sounds_dir.glob(f'*{ext}'):
                try:
                    sound = pygame.mixer.Sound(str(audio_file))
                    self.audio_files.append(sound)
                    print(f" Loaded: {audio_file.name}")
                except Exception as e:
                    print(f" Failed to load {audio_file.name}: {e}")
        
        if not self.audio_files:
            print(" No audio files found in 'scary_sounds' folder")
            print("   Using default beep sound")
            self.create_default_sound()
        else:
            print(f" Loaded {len(self.audio_files)} scary sound(s)")
    
    def create_default_sound(self):
        """Create a default scary beep if no audio files found"""
        sample_rate = 22050
        duration = 1.0
        frequency = 200
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * frequency * t)
        tremolo = np.sin(2 * np.pi * 6 * t)
        scary_tone = tone * (0.5 + 0.5 * tremolo)
        scary_tone = (scary_tone * 32767).astype(np.int16)
        stereo_tone = np.column_stack((scary_tone, scary_tone))
        
        self.audio_files = [pygame.sndarray.make_sound(stereo_tone)]
    
    def play_scare_sound(self):
        """Play a random scary sound"""
        try:
            if self.audio_files:
                sound = random.choice(self.audio_files)
                sound.set_volume(1.0)
                sound.play()
                return True
        except Exception as e:
            print(f" Audio error: {e}")
            return False
    
    def detect_motion(self, frame):
        """Detect motion using background subtraction - optimized for speed"""
        if self.bg_subtractor is None:
            return False, None, [], 0
        
        fg_mask = self.bg_subtractor.apply(frame, learningRate=0.01)  # Faster learning
        _, fg_mask = cv2.threshold(fg_mask, 250, 255, cv2.THRESH_BINARY)
        
        # Simplified morphological operations for speed
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Smaller kernel
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        contours_result = cv2.findContours(
            fg_mask, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]
        
        motion_detected = False
        total_motion_area = 0
        motion_contours = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_motion_area:
                motion_contours.append(contour)
                total_motion_area += area
                motion_detected = True
        
        return motion_detected, fg_mask, motion_contours, total_motion_area
    
    def draw_overlay(self, frame, fg_mask, motion_contours, motion_detected):
        """Draw motion detection overlay on frame"""
        display_frame = frame.copy()
        
        if fg_mask is not None:
            motion_overlay = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
            motion_overlay[:, :, 0] = 0
            motion_overlay[:, :, 1] = 0
            display_frame = cv2.addWeighted(display_frame, 0.7, motion_overlay, 0.3, 0)
        
        for contour in motion_contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
        
        status_color = (0, 0, 255) if motion_detected else (0, 255, 0)
        status_text = "MOTION DETECTED!" if motion_detected else "Monitoring..."
        
        cv2.putText(display_frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        cv2.putText(display_frame, f"Detections: {self.detection_count}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if self.last_detection_time:
            cv2.putText(display_frame, f"Last: {self.last_detection_time}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        current_time = time.time()
        time_since_scare = current_time - self.last_scare_time
        if time_since_scare < self.cooldown_seconds:
            cooldown_remaining = self.cooldown_seconds - time_since_scare
            cv2.putText(display_frame, f"Cooldown: {cooldown_remaining:.1f}s", (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return display_frame
    
    def connect_stream(self):
        """Connect to video stream"""
        if self.cap is not None:
            self.cap.release()
        
        self.cap = cv2.VideoCapture(self.stream_url)
        
        if not self.cap.isOpened():
            return False
        
        # Optimize capture settings for lower latency
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Initialize background subtractor with faster parameters
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100,  # Reduced from 500 for faster adaptation
            varThreshold=16,
            detectShadows=False  # Disable shadow detection for speed
        )
        
        # Quick warm up - reduced from 30 to 10 frames
        for _ in range(10):
            ret, frame = self.cap.read()
            if ret:
                self.bg_subtractor.apply(frame)
        
        return True
    
    def process_frame(self):
        """Process a single frame - optimized for low latency"""
        if self.cap is None or not self.running:
            return None, None
        
        ret, frame = self.cap.read()
        if not ret:
            return None, None
        
        with self.processing_lock:
            self.current_frame = frame
            
            if self.paused:
                return frame, None
            
            motion_detected, fg_mask, motion_contours, motion_area = self.detect_motion(frame)
            
            current_time = time.time()
            time_since_last_scare = current_time - self.last_scare_time
            
            if motion_detected and time_since_last_scare >= self.cooldown_seconds:
                # Play sound in separate thread to avoid blocking
                threading.Thread(target=self.play_scare_sound, daemon=True).start()
                self.last_scare_time = current_time
                self.detection_count += 1
                self.last_detection_time = datetime.now().strftime('%H:%M:%S')
            
            self.display_frame = self.draw_overlay(frame, fg_mask, motion_contours, motion_detected)
            self.motion_mask = fg_mask
            
            return self.display_frame, fg_mask
    
    def stop(self):
        """Stop the system"""
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.bg_subtractor = None


class HalloweenGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Halloween Scare System")
        self.root.geometry("1200x750")
        self.root.configure(bg='#1a1a2e')
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#1a1a2e')
        style.configure('TLabel', background='#1a1a2e', foreground='#ffffff', font=('Arial', 10))
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#ff6b35')
        style.configure('TButton', font=('Arial', 10, 'bold'))
        style.map('TButton', background=[('active', '#ff6b35')])
        
        self.scare_system = HalloweenScareSystem()
        self.update_thread = None
        self.is_updating = False
        
        self.setup_gui()
        self.update_stats()
    
    def setup_gui(self):
        """Setup the GUI layout"""
        # Title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=10, fill='x')
        
        title_label = ttk.Label(
            title_frame, 
            text="HALLOWEEN SCARE SYSTEM",
            style='Title.TLabel'
        )
        title_label.pack()
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side='left', fill='both', padx=5)
        
        # Connection settings
        conn_frame = ttk.LabelFrame(left_panel, text=" Camera Settings", padding=10)
        conn_frame.pack(fill='x', pady=5)
        
        ttk.Label(conn_frame, text="Stream URL:").pack(anchor='w')
        self.url_entry = ttk.Entry(conn_frame, width=30)
        self.url_entry.insert(0, self.scare_system.stream_url)
        self.url_entry.pack(fill='x', pady=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(left_panel, text=" Controls", padding=10)
        control_frame.pack(fill='x', pady=5)
        
        self.start_btn = tk.Button(
            control_frame, 
            text="Start Monitoring",
            command=self.start_monitoring,
            bg='#28a745',
            fg='white',
            font=('Arial', 12, 'bold'),
            relief='raised',
            bd=3
        )
        self.start_btn.pack(fill='x', pady=5)
        
        self.stop_btn = tk.Button(
            control_frame,
            text="Stop",
            command=self.stop_monitoring,
            bg='#dc3545',
            fg='white',
            font=('Arial', 12, 'bold'),
            relief='raised',
            bd=3,
            state='disabled'
        )
        self.stop_btn.pack(fill='x', pady=5)
        
        self.pause_btn = tk.Button(
            control_frame,
            text="Pause Detection",
            command=self.toggle_pause,
            bg='#ffc107',
            fg='black',
            font=('Arial', 10, 'bold'),
            relief='raised',
            bd=2,
            state='disabled'
        )
        self.pause_btn.pack(fill='x', pady=5)
        
        self.test_btn = tk.Button(
            control_frame,
            text="Test Sound",
            command=self.test_sound,
            bg='#17a2b8',
            fg='white',
            font=('Arial', 10, 'bold'),
            relief='raised',
            bd=2
        )
        self.test_btn.pack(fill='x', pady=5)
        
        # Settings
        settings_frame = ttk.LabelFrame(left_panel, text="Detection Settings", padding=10)
        settings_frame.pack(fill='x', pady=5)
        
        ttk.Label(settings_frame, text="Sensitivity:").pack(anchor='w')
        self.sensitivity_scale = tk.Scale(
            settings_frame,
            from_=10,
            to=100,
            orient='horizontal',
            bg='#1a1a2e',
            fg='white',
            highlightbackground='#1a1a2e',
            troughcolor='#ff6b35',
            command=self.update_sensitivity
        )
        self.sensitivity_scale.set(self.scare_system.sensitivity)
        self.sensitivity_scale.pack(fill='x')
        
        ttk.Label(settings_frame, text="Cooldown (seconds):").pack(anchor='w', pady=(10, 0))
        self.cooldown_scale = tk.Scale(
            settings_frame,
            from_=1,
            to=30,
            orient='horizontal',
            bg='#1a1a2e',
            fg='white',
            highlightbackground='#1a1a2e',
            troughcolor='#ff6b35',
            command=self.update_cooldown
        )
        self.cooldown_scale.set(self.scare_system.cooldown_seconds)
        self.cooldown_scale.pack(fill='x')
        
        ttk.Label(settings_frame, text="Min Motion Area:").pack(anchor='w', pady=(10, 0))
        self.area_scale = tk.Scale(
            settings_frame,
            from_=100,
            to=2000,
            orient='horizontal',
            bg='#1a1a2e',
            fg='white',
            highlightbackground='#1a1a2e',
            troughcolor='#ff6b35',
            command=self.update_area
        )
        self.area_scale.set(self.scare_system.min_motion_area)
        self.area_scale.pack(fill='x')
        
        # Statistics
        stats_frame = ttk.LabelFrame(left_panel, text="Statistics", padding=10)
        stats_frame.pack(fill='x', pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="", justify='left')
        self.stats_label.pack(anchor='w')
        
        # Audio info
        audio_frame = ttk.LabelFrame(left_panel, text="Audio Files", padding=10)
        audio_frame.pack(fill='x', pady=5)
        
        audio_count = len(self.scare_system.audio_files)
        audio_text = f"Loaded: {audio_count} sound(s)"
        if audio_count == 0:
            audio_text += "\nAdd files to 'scary_sounds' folder"
        
        ttk.Label(audio_frame, text=audio_text, justify='left').pack(anchor='w')
        
        reload_btn = tk.Button(
            audio_frame,
            text="Reload Sounds",
            command=self.reload_sounds,
            bg='#6c757d',
            fg='white',
            font=('Arial', 9)
        )
        reload_btn.pack(fill='x', pady=5)
        
        # Right panel - Video feeds
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side='right', fill='both', expand=True, padx=5)
        
        # Main video feed
        video_frame = ttk.LabelFrame(right_panel, text="Live Feed", padding=5)
        video_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        self.video_label = tk.Label(video_frame, bg='black')
        self.video_label.pack(fill='both', expand=True)
        
        # Motion detection feed
        motion_frame = ttk.LabelFrame(right_panel, text="Motion Detection", padding=5)
        motion_frame.pack(fill='both', expand=True)
        
        self.motion_label = tk.Label(motion_frame, bg='black')
        self.motion_label.pack(fill='both', expand=True)
        
        # Status bar
        self.status_label = ttk.Label(
            self.root,
            text="Status: Idle",
            relief='sunken',
            anchor='w'
        )
        self.status_label.pack(side='bottom', fill='x')
    
    def update_sensitivity(self, value):
        self.scare_system.sensitivity = int(float(value))
    
    def update_cooldown(self, value):
        self.scare_system.cooldown_seconds = int(float(value))
    
    def update_area(self, value):
        self.scare_system.min_motion_area = int(float(value))
    
    def test_sound(self):
        """Test playing a scare sound"""
        if self.scare_system.play_scare_sound():
            self.status_label.config(text="Status: Playing test sound...")
            self.root.after(1000, lambda: self.status_label.config(text="Status: Ready"))
        else:
            messagebox.showerror("Error", "Failed to play sound")
    
    def reload_sounds(self):
        """Reload audio files from scary_sounds folder"""
        self.scare_system.load_scary_sounds()
        audio_count = len(self.scare_system.audio_files)
        messagebox.showinfo("Audio Reloaded", f"Loaded {audio_count} sound file(s)")
        self.setup_gui()  # Refresh the GUI to update audio count
    
    def start_monitoring(self):
        """Start the monitoring system"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a stream URL")
            return
        
        self.scare_system.stream_url = url
        self.status_label.config(text="Status: Connecting to stream...")
        self.root.update()
        
        if not self.scare_system.connect_stream():
            messagebox.showerror("Error", "Failed to connect to stream.\nCheck the URL and network connection.")
            self.status_label.config(text="Status: Connection failed")
            return
        
        self.scare_system.running = True
        self.is_updating = True
        
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.pause_btn.config(state='normal')
        self.url_entry.config(state='disabled')
        
        self.status_label.config(text="Status: Monitoring for motion...")
        
        self.update_video()
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_updating = False
        self.scare_system.stop()
        
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.pause_btn.config(state='disabled')
        self.url_entry.config(state='normal')
        
        self.video_label.config(image='')
        self.status_label.config(text="Status: Stopped")
    
    def toggle_pause(self):
        """Toggle motion detection pause"""
        self.scare_system.paused = not self.scare_system.paused
        if self.scare_system.paused:
            self.pause_btn.config(text="Resume Detection")
            self.status_label.config(text="Status: Detection Paused")
        else:
            self.pause_btn.config(text="Pause Detection")
            self.status_label.config(text="Status: Monitoring for motion...")
    
    def update_video(self):
        """Update video feed - optimized for low latency"""
        if not self.is_updating:
            return
        
        frame, motion_mask = self.scare_system.process_frame()
        
        if frame is not None:
            # Update main video feed with reduced processing
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
            # Fixed display size
            display_width = 640
            display_height = 360
            img = img.resize((display_width, display_height), Image.Resampling.NEAREST)  # Faster resize
            
            photo = ImageTk.PhotoImage(image=img)
            self.video_label.config(image=photo)
            self.video_label.image = photo
        
        if motion_mask is not None:
            # Update motion detection feed
            motion_rgb = cv2.cvtColor(motion_mask, cv2.COLOR_GRAY2RGB)
            motion_img = Image.fromarray(motion_rgb)
            motion_img = motion_img.resize((display_width, display_height), Image.Resampling.NEAREST)
            
            motion_photo = ImageTk.PhotoImage(image=motion_img)
            self.motion_label.config(image=motion_photo)
            self.motion_label.image = motion_photo
        
        # Reduced delay for faster updates
        self.root.after(16, self.update_video)  # ~60fps update rate
    
    def update_stats(self):
        """Update statistics display"""
        stats_text = (
            f"Total Detections: {self.scare_system.detection_count}\n"
            f"Last Detection: {self.scare_system.last_detection_time or 'None'}"
        )
        self.stats_label.config(text=stats_text)
        self.root.after(1000, self.update_stats)
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.is_updating = False
            self.scare_system.stop()
            pygame.mixer.quit()
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = HalloweenGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
