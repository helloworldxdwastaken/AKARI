import os
import time
import speech_recognition as sr
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import inquirer  # New import for interactive menu

# Define your constants here
CLIENT_ID = 'your_client_id'
CLIENT_SECRET = 'your_client_secret'
REDIRECT_URI = 'http://localhost:8888/callback'

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

    while True:
        with sr.Microphone() as source:
            print("Listening for commands...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio_text = recognizer.listen(source, timeout=5)
                print("Audio captured successfully.")
            except sr.WaitTimeoutError:
                print("Listening timed out. Trying again...")
                continue

        try:
            command = recognizer.recognize_google(audio_text).lower()
            print(f"Command recognized: {command}")

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
                volume = set_volume(command, volume, selected_device_id)
        except sr.UnknownValueError:
            print("Speech Recognition could not understand audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}\n")

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

def set_volume(command, current_volume, device_id):
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
                        return new_volume
                    except spotipy.SpotifyException as e:
                        print(f"Error setting volume: {e}")
                        return current_volume
                else:
                    print("Volume should be between 0 and 100.")
                    return current_volume
            else:
                print("Invalid volume value.")
                return current_volume
        else:
            print("Volume value not found in the command.")
            return current_volume
    else:
        print("Command does not contain 'volume'.")
        return current_volume

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

if __name__ == "__main__":
    selected_device_id = select_device()
    if selected_device_id:
        handle_user_interaction(selected_device_id)
    else:
        print("No device selected. Exiting.")
