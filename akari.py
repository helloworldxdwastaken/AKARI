import os
import sys
import threading
import time
import logging
import configparser
import json
import readchar
import speech_recognition as sr
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import inquirer  # For interactive menu
from pynput import keyboard  # For keyboard event handling
from cryptography.fernet import Fernet

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("akari_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Define constants and configurations
CONFIG_FILE = os.path.join(os.path.expanduser("~"), 'Documents', 'akari_config.ini')
CREDENTIALS_FILE = os.path.join(os.path.expanduser("~"), 'Documents', 'akari_credentials.enc')
DEFAULT_TRIGGER_KEY = 't'  # Default trigger key is 'T'

# Initialize global variables
TRIGGER_KEY = DEFAULT_TRIGGER_KEY
listening = False  # Flag to indicate if we're currently listening
recognizer = sr.Recognizer()
audio_thread = None  # Thread for audio listening
sp = None  # Spotify client instance
selected_device_id = None  # Selected Spotify device ID
stop_listening_event = threading.Event()  # Event to signal the listening thread to stop


def print_headline():
    ascii_art = f"""
         _                   _              _                   _            _
        / /\                /\_\           / /\                /\ \         /\ \\
       / /  \\              / / /  _       / /  \\              /  \\ \\        \\ \\ \\
      / / /\\ \\            / / /  /\\_\\    / / /\\ \\            / /\\ \\ \\       /\\ \\_\\
     / / /\\ \\ \\          / / /__/ / /   / / /\\ \\ \\          / / /\\ \\_\\     / /\\/_/
    / / /  \\ \\ \\        / /\\_____/ /   / / /  \\ \\ \\        / / /_/ / /    / / /
   / / /___/ /\\ \\      / / /\\_______/   / / /___/ /\\ \\      / / /__\\/ /    / / /
  / / /_____/ /\\ \\    / / /\\ \\ \\     / / /_____/ /\\ \\    / / /_____/    / / /
 / /_________/\\ \\ \\  / / /  \\ \\ \\   / /_________/\\ \\ \\  / / /\\ \\ \\  ___/ / /__
/ / /_       __\\ \\_\\/ / /    \\ \\ \\ / / /_       __\\ \\_\\/ / /  \\ \\ \\/\\__/\\/_/___\\
\\_\\___\\     /____/_/\\/_/      \\_\\_\\\\_\\___\\     /____/_/\\/_/    \\_\\/\\/_________/

    """
    logging.info(ascii_art)


def load_config():
    """Load or create the configuration file."""
    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = {
            'TriggerKey': DEFAULT_TRIGGER_KEY,
            'CredentialsFile': CREDENTIALS_FILE
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        logging.info(f"Configuration file created at {CONFIG_FILE}")
    else:
        config.read(CONFIG_FILE)
        logging.info("Configuration file loaded.")

    global TRIGGER_KEY
    TRIGGER_KEY = config['DEFAULT'].get('TriggerKey', DEFAULT_TRIGGER_KEY).lower()
    return config


def save_config(config):
    """Save the configuration to file."""
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    logging.info("Configuration saved.")


def generate_key():
    """Generate a key for encryption."""
    return Fernet.generate_key()


def encrypt_credentials(client_id, client_secret, key):
    """Encrypt Spotify credentials."""
    credentials = {'CLIENT_ID': client_id, 'CLIENT_SECRET': client_secret}
    credentials_json = json.dumps(credentials).encode()
    fernet = Fernet(key)
    encrypted = fernet.encrypt(credentials_json)
    return encrypted


def decrypt_credentials(encrypted_credentials, key):
    """Decrypt Spotify credentials."""
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_credentials)
    credentials = json.loads(decrypted.decode())
    return credentials['CLIENT_ID'], credentials['CLIENT_SECRET']


def get_spotify_credentials(config):
    """Get Spotify credentials, prompting the user if necessary."""
    key = None

    # Check if credentials file exists
    if os.path.exists(CREDENTIALS_FILE):
        key = config['DEFAULT'].get('EncryptionKey')
        if not key:
            logging.error("Encryption key not found in configuration.")
            sys.exit(1)
        key = key.encode()
        with open(CREDENTIALS_FILE, 'rb') as file:
            encrypted_credentials = file.read()
        try:
            client_id, client_secret = decrypt_credentials(encrypted_credentials, key)
            logging.info("Spotify credentials loaded and decrypted successfully.")
            return client_id, client_secret
        except Exception as e:
            logging.error(f"Failed to decrypt credentials: {e}")
            sys.exit(1)
    else:
        # Prompt for credentials
        logging.info("Spotify credentials not found. Please enter them now.")
        questions = [
            inquirer.Text('client_id', message="Enter your Spotify Client ID"),
            inquirer.Text('client_secret', message="Enter your Spotify Client Secret"),
        ]
        answers = inquirer.prompt(questions)
        client_id = answers['client_id']
        client_secret = answers['client_secret']

        # Generate encryption key
        key = generate_key()
        encrypted_credentials = encrypt_credentials(client_id, client_secret, key)

        # Save encrypted credentials
        with open(CREDENTIALS_FILE, 'wb') as file:
            file.write(encrypted_credentials)
        logging.info(f"Encrypted credentials saved to {CREDENTIALS_FILE}")

        # Save the encryption key in the config
        config['DEFAULT']['EncryptionKey'] = key.decode()
        save_config(config)

        return client_id, client_secret


def select_device():
    """Prompt the user to select a Spotify device."""
    try:
        devices = sp.devices()
        device_list = devices['devices']
        if not device_list:
            logging.error("No devices found. Please make sure Spotify is open on at least one device.")
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
                logging.info(f"Selected device: {device['name']}")
                return device['id']

    except spotipy.SpotifyException as e:
        logging.error(f"Error retrieving devices: {e}")
        return None


def on_press(key):
    """Handle key press events."""
    global listening, audio_thread
    try:
        if hasattr(key, 'char') and key.char == TRIGGER_KEY and not listening:
            listening = True
            logging.info(f"'{TRIGGER_KEY.upper()}' key pressed. Starting to listen...")
            # Clear the stop event
            stop_listening_event.clear()
            # Start a new thread to listen for commands
            audio_thread = threading.Thread(target=listen_for_command)
            audio_thread.start()
    except Exception as e:
        logging.error(f"Error in on_press: {e}")


def on_release(key):
    """Handle key release events."""
    global listening
    if key == keyboard.Key.esc:
        # Stop listener
        logging.info("ESC key pressed. Exiting...")
        return False
    try:
        if hasattr(key, 'char') and key.char == TRIGGER_KEY and listening:
            listening = False
            logging.info(f"'{TRIGGER_KEY.upper()}' key released. Stopping listening.")
            # Signal the listening thread to stop
            stop_listening_event.set()
    except Exception as e:
        logging.error(f"Error in on_release: {e}")


def listen_for_command():
    """Listen for voice commands and process them."""
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        logging.info("Microphone is ready.")
        try:
            while not stop_listening_event.is_set():
                logging.info("Listening...")
                try:
                    audio_text = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    command = recognizer.recognize_google(audio_text).lower()
                    logging.info(f"Command recognized: {command}")
                    process_command(command)
                except sr.WaitTimeoutError:
                    # Timeout reached, check if we should stop listening
                    continue
                except sr.UnknownValueError:
                    logging.warning("Could not understand audio.")
                except sr.RequestError as e:
                    logging.error(f"Speech Recognition service error: {e}")
        except Exception as e:
            logging.error(f"Error in listen_for_command: {e}")
        finally:
            logging.info("Listening thread exiting.")


def process_command(command):
    """Process the recognized voice command."""
    if "play playlist" in command or "play my playlist" in command:
        # Extract the playlist name from the command
        playlist_name = command.replace("play playlist", "").replace("play my playlist", "").strip()
        play_playlist_on_spotify(playlist_name)
    elif "play" in command:
        # Extract the song title from the command
        song_title = command.replace("play", "").strip()
        play_song_on_spotify(song_title)
    elif "skip" in command or "next" in command:
        skip_song()
    elif "pause" in command:
        pause_spotify()
    elif "resume" in command:
        resume_song()
    elif "volume" in command:
        set_volume(command)
    else:
        logging.warning("Command not recognized.")


def play_playlist_on_spotify(playlist_name):
    """Play a playlist on Spotify."""
    try:
        playlists = sp.current_user_playlists()
        found_playlists = [p for p in playlists['items'] if playlist_name.lower() in p['name'].lower()]

        if found_playlists:
            # Get the URI of the first found playlist
            uri = found_playlists[0]['uri']
            # Start playback with the playlist URI
            sp.start_playback(context_uri=uri, device_id=selected_device_id)
            logging.info(f"Playing playlist '{found_playlists[0]['name']}' on Spotify...")
        else:
            logging.warning(f"Playlist '{playlist_name}' not found on Spotify.")
    except spotipy.SpotifyException as e:
        logging.error(f"Error playing playlist on Spotify: {e}")


def get_song_uri(song_title):
    """Retrieve the Spotify URI for a song."""
    if not song_title:
        logging.error("Empty song title provided.")
        return None

    try:
        results = sp.search(q=song_title, type='track', limit=1)
        if results['tracks']['items']:
            uri = results['tracks']['items'][0]['uri']
            return uri
        else:
            logging.warning(f"Song '{song_title}' not found on Spotify.")
            return None
    except spotipy.SpotifyException as e:
        logging.error(f"Error during Spotify search: {e}")
        return None


def play_song_on_spotify(song_title):
    """Play a song on Spotify."""
    uri = get_song_uri(song_title)
    try:
        if uri:
            sp.start_playback(uris=[uri], device_id=selected_device_id)
            logging.info(f"Playing '{song_title}' on Spotify...")
        else:
            logging.error("Unable to obtain a valid track URI.")
    except spotipy.SpotifyException as e:
        logging.error(f"Error starting playback on Spotify: {e}")


def pause_spotify():
    """Pause Spotify playback."""
    try:
        sp.pause_playback(device_id=selected_device_id)
        logging.info("Pausing Spotify...")
    except spotipy.SpotifyException as e:
        logging.error(f"Error pausing Spotify playback: {e}")


def set_volume(command):
    """Set the Spotify playback volume."""
    words = command.split()

    if "volume" in words:
        index = words.index("volume")

        if index + 1 < len(words):
            new_volume_str = words[index + 1].rstrip('%')
            if new_volume_str.isdigit():
                new_volume = int(new_volume_str)

                if 0 <= new_volume <= 100:
                    try:
                        sp.volume(new_volume, device_id=selected_device_id)
                        logging.info(f"Setting volume to {new_volume}%...")
                    except spotipy.SpotifyException as e:
                        logging.error(f"Error setting volume: {e}")
                else:
                    logging.warning("Volume should be between 0 and 100.")
            else:
                logging.warning("Invalid volume value.")
        else:
            logging.warning("Volume value not found in the command.")
    else:
        logging.warning("Command does not contain 'volume'.")


def skip_song():
    """Skip to the next song on Spotify."""
    try:
        current_track = sp.current_playback()
        if current_track and current_track['is_playing']:
            sp.next_track(device_id=selected_device_id)
            logging.info("Skipping to the next song...")
        else:
            logging.info("No currently playing track. Playing a random playlist...")
            play_random_playlist_on_spotify()
    except spotipy.SpotifyException as e:
        logging.error(f"Error skipping song on Spotify: {e}")


def play_random_playlist_on_spotify():
    """Play a random playlist on Spotify."""
    try:
        playlists = sp.current_user_playlists()
        if playlists['items']:
            random_playlist = random.choice(playlists['items'])
            uri = random_playlist['uri']
            sp.start_playback(context_uri=uri, device_id=selected_device_id)
            logging.info(f"Playing random playlist: {random_playlist['name']}...")
        else:
            logging.warning("No playlists available to play.")
    except spotipy.SpotifyException as e:
        logging.error(f"Error playing random playlist on Spotify: {e}")


def resume_song():
    """Resume Spotify playback."""
    try:
        sp.start_playback(device_id=selected_device_id)
        logging.info("Resuming playback...")
    except spotipy.SpotifyException as e:
        logging.error(f"Error resuming song on Spotify: {e}")


def configure_trigger_key(config):
    """Configure the trigger key for voice commands."""
    global TRIGGER_KEY
    question = [
        inquirer.Text('key', message=f"Enter the trigger key you want to use (default is '{TRIGGER_KEY.upper()}')", default=TRIGGER_KEY)
    ]
    answer = inquirer.prompt(question)
    TRIGGER_KEY = answer['key'].lower()
    config['DEFAULT']['TriggerKey'] = TRIGGER_KEY
    save_config(config)
    logging.info(f"Trigger key set to '{TRIGGER_KEY.upper()}'.")


def main():
    """Main function to run the Akari bot."""
    global sp, selected_device_id

    print_headline()

    # Load configuration
    config = load_config()

    # Get Spotify credentials
    client_id, client_secret = get_spotify_credentials(config)

    # Create a Spotify client instance
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri='http://localhost:8888/callback',
        scope='user-modify-playback-state user-read-playback-state user-read-currently-playing'
    ))

    # Configure the trigger key
    configure_trigger_key(config)

    # Select Spotify device
    selected_device_id = select_device()
    if not selected_device_id:
        logging.error("No device selected. Exiting.")
        sys.exit(1)

    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    logging.info(f"Press and hold '{TRIGGER_KEY.upper()}' key to give a voice command. Release to stop listening. Press 'ESC' to exit.")

    try:
        listener.join()  # Wait for the listener thread to finish
    except KeyboardInterrupt:
        logging.info("Program interrupted by user. Exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
