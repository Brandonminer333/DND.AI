import subprocess
import signal

# Global handle to the recording process
_recording_process = None


def start_recording(output_file="output.wav", device_index=":0"):
    """
    Start recording from BlackHole using ffmpeg.
    
    output_file: path to save audio
    device_index: avfoundation audio index (e.g. ':1')
    """
    global _recording_process

    if _recording_process is not None:
        print("Recording already running.")
        return

    command = [
        "ffmpeg",
        "-y",                     # overwrite output
        "-f", "avfoundation",
        "-i", device_index,       # audio device
        "-ac", "2",               # stereo
        "-ar", "44100",           # sample rate
        output_file
    ]

    _recording_process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print(f"Recording started -> {output_file}")


def stop_recording():
    """
    Stop the active recording process.
    """
    global _recording_process

    if _recording_process is None:
        print("No active recording.")
        return

    # Graceful stop
    _recording_process.send_signal(signal.SIGINT)
    _recording_process.wait()

    _recording_process = None
    print("Recording stopped.")