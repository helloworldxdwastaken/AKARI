import os
import time
import speech_recognition as sr
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import inquirer  # For interactive menu
from pynput import keyboard  # For keyboard event handling
import threading

# Define your constants here
CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:8888/callback'

# Set the default trigger key (configurable)
TRIGGER_KEY = 't'  # Default trigger key is 'T'

# Create a single instance of Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope='user-modify-playback-state user-read-playback-state user-read-currently-playing'))

def print_headline():
    ascii_art = f"""
         _                   _              _                   _            _     
        / /\                /\_\           / /\                /\ \         /\ \   
       / /  \              / / /  _       / /  \              /  \ \        \ \ \  
      / / /\ \            / / /  /\_\    / / /\ \            / /\ \ \       /\ \_\ 
     / / /\ \ \          / / /__/ / /   / / /\ \ \          / / /\ \_\     / /\/_/ 
    / / /  \ \ \        / /\_____/ /   / / /  \ \ \        / / /_/ / /    / / /    
   / / /___/ /\ \      / /\_______/   / / /___/ /\ \      / / /__\/ /    / / /     
  / / /_____/ /\ \    / / /\ \ \     / / /_____/ /\ \    / / /_____/    / / /      
 / /_________/\ \ \  / / /  \ \ \   / /_________/\ \ \  / / /\ \ \  ___/ / /__     
/ / /_       __\ \_\/ / /    \ \ \ / / /_       __\ \_\/ / /  \ \ \/\__\/_/___\    
\_\___\     /____/_/\/_/      \_\_\\_\___\     /____/_/\/_/    \_\/\/_________/    

    """
    print(ascii_art)

print_headline()

def select_device():
    try:
        devices = sp.devices()
        device_list = devices['devices']
        if not device_list:
            print("No devices found. Please make sure Spotify is open on at least one device.")
            return None

        device_names = [f"{device['name']} ({device['type']})" for device in device_list]

        questions = [
            inquirer.List(
                'device',
                message="Select the device you want to play music on:",
                choices=device_names
            )
        ]
        answers = inquirer.prompt(questions)
        selected_device_name = answers['device']

        # Find the selected device in the device list
        for device in device_list:
            name_with_type = f"{device['name']} ({device['type']})"
            if name_with_type == selected_device_name:
                print(f"Selected device: {device['name']}")
                return device['id']

    except spotipy.SpotifyException as e:
        print(f"Error retrieving devices: {e}")
        return None

def handle_user_interaction(selected_device_id):
    recognizer = sr.Recognizer()
    volume = 50  # Default volume
    listening = False  # Flag to indicate if we're currently listening
    audio_thread = None  # Thread for audio listening

    def on_press(key):
        nonlocal listening, audio_thread
        try:
            if key.char == TRIGGER_KEY and not listening:
                listening = True
                print(f"'{TRIGGER_KEY.upper()}' key pressed. Starting to listen...")
                # Start a new thread to listen for commands
                audio_thread = threading.Thread(target=listen_for_command, args=(recognizer, selected_device_id))
                audio_thread.start()
        except AttributeError:
            pass  # Special keys (e.g., function keys) can be ignored

    def on_release(key):
        nonlocal listening
        try:
            if key.char == TRIGGER_KEY and listening:
                listening = False
                print(f"'{TRIGGER_KEY.upper()}' key released. Stopping listening.")
                # Interrupt the recognizer if possible
                recognizer.abort_on_phrase = True  # Set abort flag
        except AttributeError:
            if key == keyboard.Key.esc:
                # Stop listener
                print("ESC key pressed. Exiting...")
                return False

    # Start keyboard listener in a separate thread
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    print(f"Press and hold '{TRIGGER_KEY.upper()}' key to give a voice command. Release to stop listening. Press 'ESC' to exit.")

    # Keep the main thread alive
    listener.join()  # Wait for the listener thread to finish

def listen_for_command(recognizer, selected_device_id):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            # Continuously listen until the key is released
            while True:
                if recognizer.abort_on_phrase:
                    print("Listening stopped by key release.")
                    recognizer.abort_on_phrase = False  # Reset abort flag
                    break
                print("Listening...")
                audio_text = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                try:
                    command = recognizer.recognize_google(audio_text).lower()
                    print(f"Command recognized: {command}")
                    process_command(command, selected_device_id)
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service; {e}")
        except sr.WaitTimeoutError:
            print("Listening timed out.")

def process_command(command, selected_device_id):
    if "play playlist" in command or "play my playlist" in command:
        # Extract the playlist name from the command
        playlist_name = command.replace("play playlist", "").replace("play my playlist", "").strip()
        play_playlist_on_spotify(playlist_name, selected_device_id)
    elif "play" in command:
        # Extract the song title from the command
        song_title = command.replace("play", "").strip()
        play_song_on_spotify(song_title, selected_device_id)
    elif "skip" in command or "next" in command:
        skip_song(selected_device_id)
    elif "pause" in command:
        pause_spotify(selected_device_id)
    elif "resume" in command:
        resume_song(selected_device_id)
    elif "volume" in command:
        set_volume(command, selected_device_id)
    else:
        print("Command not recognized.")

def play_playlist_on_spotify(playlist_name, device_id):
    try:
        playlists = sp.current_user_playlists()
        found_playlists = [p for p in playlists['items'] if playlist_name.lower() in p['name'].lower()]

        if found_playlists:
            # Get the URI of the first found playlist
            uri = found_playlists[0]['uri']
            # Start playback with the playlist URI
            sp.start_playback(context_uri=uri, device_id=device_id)
            print(f"Playing playlist '{found_playlists[0]['name']}' on Spotify...")
        else:
            print(f"Playlist '{playlist_name}' not found on Spotify.")
    except spotipy.SpotifyException as e:
        print(f"Error playing playlist on Spotify: {e}")

def get_song_uri(song_title):
    # Check if song_title is empty or None
    if not song_title:
        print("Error: Empty or None song title provided.")
        return None

    try:
        # Search for the song
        results = sp.search(q=song_title, type='track', limit=1)

        if results['tracks']['items']:
            # Get the URI of the first result
            uri = results['tracks']['items'][0]['uri']
            return uri
        else:
            print(f"Song '{song_title}' not found on Spotify.")
            return None

    except spotipy.SpotifyException as e:
        print(f"Error during Spotify search: {e}")
        return None

def play_song_on_spotify(song_title, device_id):
    uri = get_song_uri(song_title)

    try:
        if uri:
            # Start playback with the device ID
            sp.start_playback(uris=[uri], device_id=device_id)
            print(f"Playing '{song_title}' on Spotify...")
        else:
            print("Unable to obtain a valid track URI.")
    except spotipy.SpotifyException as e:
        print(f"Error starting playback on Spotify: {e}")

def pause_spotify(device_id):
    try:
        sp.pause_playback(device_id=device_id)
        print("Pausing Spotify...")
    except spotipy.SpotifyException as e:
        print(f"Error pausing Spotify playback: {e}")

def set_volume(command, device_id):
    words = command.split()

    # Check if "volume" is present in the command
    if "volume" in words:
        index = words.index("volume")

        # Check if there are enough words after "volume" to get the volume value
        if index + 1 < len(words):
            # Remove the percentage symbol ("%") before converting to int
            new_volume_str = words[index + 1].rstrip('%')
            if new_volume_str.isdigit():
                new_volume = int(new_volume_str)

                if 0 <= new_volume <= 100:
                    try:
                        sp.volume(new_volume, device_id=device_id)
                        print(f"Setting volume to {new_volume}%...")
                    except spotipy.SpotifyException as e:
                        print(f"Error setting volume: {e}")
                else:
                    print("Volume should be between 0 and 100.")
            else:
                print("Invalid volume value.")
        else:
            print("Volume value not found in the command.")
    else:
        print("Command does not contain 'volume'.")

def skip_song(device_id):
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            sp.next_track(device_id=device_id)
            print("Skipping to the next song...")
        else:
            print("No currently playing track. Playing a random playlist...")
            play_random_playlist_on_spotify(device_id)
    except spotipy.SpotifyException as e:
        print(f"Error skipping song on Spotify: {e}")

def play_random_playlist_on_spotify(device_id):
    try:
        playlists = sp.current_user_playlists()
        if playlists['items']:
            random_playlist = random.choice(playlists['items'])
            uri = random_playlist['uri']
            sp.start_playback(context_uri=uri, device_id=device_id)
            print(f"Playing random playlist: {random_playlist['name']}...")
        else:
            print("No playlists available to play.")
    except spotipy.SpotifyException as e:
        print(f"Error playing random playlist on Spotify: {e}")

def resume_song(device_id):
    try:
        sp.start_playback(device_id=device_id)
        print("Resuming playback...")
    except spotipy.SpotifyException as e:
        print(f"Error resuming song on Spotify: {e}")

def configure_trigger_key():
    global TRIGGER_KEY
    question = [
        inquirer.Text('key', message="Enter the trigger key you want to use (default is 'T')", default=TRIGGER_KEY)
    ]
    answer = inquirer.prompt(question)
    TRIGGER_KEY = answer['key'].lower()
    print(f"Trigger key set to '{TRIGGER_KEY.upper()}'.")

if __name__ == "__main__":
    # Option to configure the trigger key
    configure_trigger_key()

    selected_device_id = select_device()
    if selected_device_id:
        handle_user_interaction(selected_device_id)
    else:
        print("No device selected. Exiting.")
