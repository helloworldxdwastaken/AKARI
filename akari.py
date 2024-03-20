import os
import time
import speech_recognition as sr
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random


# Define your constants here
CLIENT_ID = '1561fa4eab8b4e518c71abd38bc02c19'
CLIENT_SECRET = '5c9a2d35b55c470eb04bb13b11964b52'
REDIRECT_URI = 'http://localhost:8888/callback'
DEVICE_ID = 'TOKYO'

# Create a single instance of Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope='user-modify-playback-state user-read-playback-state'))


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


def handle_user_interaction():
    recognizer = sr.Recognizer()
    volume = 50  # Default volume

    while True:
        with sr.Microphone() as source:
            print("Listening for commands...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio_text = recognizer.listen(source, timeout=5)  # Adjust the timeout value as needed
                print("Audio captured successfully.")
            except sr.WaitTimeoutError:
                print("Listening timed out. Trying again...")
                continue

        try:
            command = recognizer.recognize_google(audio_text).lower()
            print(f"Command recognized: {command}")

            if "play playlist" in command:
                # Extract the playlist name from the command
                playlist_name = command.replace("play playlist", "").strip()
                play_playlist_on_spotify(playlist_name)
            elif "play my playlist" in command:
                # Extract the playlist name from the command
                playlist_name = command.replace("play my playlist", "").strip()
                play_playlist_on_spotify(playlist_name)
            elif "play" in command:
                # Extract the song title from the command
                song_title = command.replace("play", "").strip()
                play_song_on_spotify(song_title)
            elif "skip" in command or "next" in command:
                skip_song()  # Call the skip_song function
            elif "pause" in command:
                pause_spotify()
            elif "resume" in command:
                resume_song()
            elif "volume" in command:
                volume = set_volume(command, volume)

        except sr.UnknownValueError:
            print("Speech Recognition could not understand audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}\n")


def play_playlist_on_spotify(playlist_name):
    try:
        playlists = sp.current_user_playlists()
        found_playlists = [p for p in playlists['items'] if playlist_name.lower() in p['name'].lower()]

        if found_playlists:
            # Get the URI of the first found playlist
            uri = found_playlists[0]['uri']
            # Start playback with the playlist URI
            sp.start_playback(context_uri=uri)
            print(f"Playing playlist '{found_playlists[0]['name']}' on Spotify...", end='\r')
        else:
            print(f"Playlist '{playlist_name}' not found on Spotify.", end='\r')
    except spotipy.SpotifyException as e:
        print(f"Error playing playlist on Spotify: {e}", end='\r')


def get_song_uri(song_title):
    # Check if song_title is empty or None
    if not song_title:
        print("Error: Empty or None song title provided.", end='\r')
        return None

    try:
        # Search for the song
        results = sp.search(q=song_title, type='track', limit=1)

        if results['tracks']['items']:
            # Get the URI of the first result
            uri = results['tracks']['items'][0]['uri']
            return uri
        else:
            print(f"Song '{song_title}' not found on Spotify.", end='\r')
            return None

    except spotipy.SpotifyException as e:
        print(f"Error during Spotify search: {e}", end='\r')
        return None


def play_song_on_spotify(song_title):
    uri = get_song_uri(song_title)

    try:
        devices = sp.devices()
        device = next((d for d in devices['devices'] if d['name'] == DEVICE_ID), None)

        if device:
            if uri:
                # Start playback with the device ID
                sp.start_playback(uris=[uri], device_id=device['id'])
                print(f"Playing '{song_title}' on Spotify...", end='\r')
            else:
                print("Unable to obtain a valid track URI.", end='\r')
        else:
            # If no active device, try playing on the default device
            default_device = next((d for d in devices['devices'] if d['is_active']), None)

            if default_device:
                sp.start_playback(uris=[uri], device_id=default_device['id'])
                print(f"Playing '{song_title}' on default device...", end='\r')
            else:
                # Dynamic path to Spotify executable based on the username
                spotify_executable_path = os.path.join(os.path.expanduser("~"), 'AppData', 'Roaming', 'Spotify',
                                                       'Spotify.exe')

                print(f"No active devices found. Attempting to open Spotify at {spotify_executable_path}...", end='\r')
                try:
                    # Open Spotify
                    os.startfile(spotify_executable_path)
                    # Wait for Spotify to open (adjust this time if needed)
                    time.sleep(2)
                    print("Retrying command...", end='\r')
                    # Retry the command after waiting
                    play_song_on_spotify(song_title)
                except Exception as e:
                    print(f"Error opening Spotify: {e}", end='\r')

    except spotipy.SpotifyException as e:
        print(f"Error starting playback on Spotify: {e}", end='\r')


def pause_spotify():
    try:
        devices = sp.devices()
        device = next((d for d in devices['devices'] if d['name'] == DEVICE_ID), None)

        if device:
            sp.pause_playback(device_id=device['id'])
            print("Pausing Spotify...", end='\r')
        else:
            print(f"Device '{DEVICE_ID}' not found or not active.", end='\r')
    except spotipy.SpotifyException as e:
        print(f"Error pausing Spotify playback: {e}", end='\r')


def set_volume(command, current_volume):
    words = command.split()

    # Check if "volume" is present in the command
    if "volume" in words:
        index = words.index("volume")

        # Check if there are enough words after "volume" to get the volume value
        if index + 2 < len(words):
            # Remove the percentage symbol ("%") before converting to int
            new_volume = int(words[index + 2].rstrip('%'))

            if 0 <= new_volume <= 100:
                try:
                    sp.volume(new_volume)
                    print(f"Setting volume to {new_volume}%...", end='\r')
                    return new_volume
                except spotipy.SpotifyException as e:
                    print(f"Error setting volume: {e}", end='\r')
                    return current_volume
            else:
                print("Volume should be between 0 and 100.", end='\r')
                return current_volume
        else:
            print("Volume value not found in the command.", end='\r')
            return current_volume
    else:
        print("Command does not contain 'volume'.", end='\r')
        return current_volume


def skip_song():
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            sp.next_track()
            print("Skipping to the next song...", end='\r')
        else:
            print("No currently playing track. Playing a random playlist...", end='\r')
            play_random_playlist_on_spotify()
    except spotipy.SpotifyException as e:
        print(f"Error skipping song on Spotify: {e}", end='\r')


def play_random_playlist_on_spotify():
    try:
        playlists = sp.current_user_playlists()
        if playlists['items']:
            random_playlist = random.choice(playlists['items'])
            uri = random_playlist['uri']
            sp.start_playback(context_uri=uri)
            print(f"Playing random playlist: {random_playlist['name']}...", end='\r')
        else:
            print("No playlists available to play.", end='\r')
    except spotipy.SpotifyException as e:
        print(f"Error playing random playlist on Spotify: {e}", end='\r')


def resume_song():
    try:
        sp.start_playback()
        print("Resuming playback...", end='\r')
    except spotipy.SpotifyException as e:
        print(f"Error resuming song on Spotify: {e}", end='\r')


if __name__ == "__main__":
    handle_user_interaction()
