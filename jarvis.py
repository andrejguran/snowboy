import snowboydecoder
import sys
import signal
from sys import byteorder
from array import array
from struct import pack
import copy
import pyaudio
import wave
import time
from wit import Wit
import requests

THRESHOLD = 500  # audio levels not normalised.
CHUNK_SIZE = 1024
SILENT_CHUNKS = 1 * 44100 / 1024 / 2  # about 3sec
FORMAT = pyaudio.paInt16
FRAME_MAX_VALUE = 2 ** 15 - 1
NORMALIZE_MINUS_ONE_dB = 10 ** (-1.0 / 20)
RATE = 44100
CHANNELS = 1
TRIM_APPEND = RATE / 4
interrupted = False
RECORD_SECONDS = 3

detector = False

def is_silent(data_chunk):
    """Returns 'True' if below the 'silent' threshold"""
    return max(data_chunk) < THRESHOLD

def normalize(data_all):
    """Amplify the volume out to max -1dB"""
    # MAXIMUM = 16384
    normalize_factor = (float(NORMALIZE_MINUS_ONE_dB * FRAME_MAX_VALUE)
                        / max(abs(i) for i in data_all))

    r = array('h')
    for i in data_all:
        r.append(int(i * normalize_factor))
    return r

def trim(data_all):
    _from = 0
    _to = len(data_all) - 1
    for i, b in enumerate(data_all):
        if abs(b) > THRESHOLD:
            _from = max(0, i - TRIM_APPEND)
            break

    for i, b in enumerate(reversed(data_all)):
        if abs(b) > THRESHOLD:
            _to = min(len(data_all) - 1, len(data_all) - 1 - i + TRIM_APPEND)
            break

    return copy.deepcopy(data_all[_from:(_to + 1)])

def record():
    """Record a word or words from the microphone and 
    return the data as an array of signed shorts."""

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, output=True, frames_per_buffer=CHUNK_SIZE)

    silent_chunks = 0
    audio_started = False
    data_all = array('h')

    for i in range(0, RATE / CHUNK_SIZE * RECORD_SECONDS):
        # little endian, signed short
        data_chunk = array('h', stream.read(CHUNK_SIZE, False))
        if byteorder == 'big':
            data_chunk.byteswap()
        data_all.extend(data_chunk)

        silent = is_silent(data_chunk)

        if audio_started:
            if silent:
                silent_chunks += 1
                if silent_chunks > SILENT_CHUNKS:
                    break
            else: 
                silent_chunks = 0
        elif not silent:
            audio_started = True              

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    data_all = trim(data_all)  # we trim before normalize as threshhold applies to un-normalized wave (as well as is_silent() function)
    data_all = normalize(data_all)
    return sample_width, data_all

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    sample_width, data = record()
    data = pack('<' + ('h' * len(data)), *data)

    wave_file = wave.open(path, 'wb')
    wave_file.setnchannels(CHANNELS)
    wave_file.setsampwidth(sample_width)
    wave_file.setframerate(RATE)
    wave_file.writeframes(data)
    wave_file.close()

def signal_handler(signal, frame):
    global interrupted
    interrupted = True


def interrupt_callback():
    global interrupted
    return interrupted

def play_music():
	print('PLaying music...')

def send_action():
    print('sending action')

actions = {
    'play_music': play_music,
    'send': send_action
}
client = Wit(access_token='Z4EWWHOU5UHRAL22EZ4CFO3RYPV7RSYJ', actions=actions)


def listener():
    global detector
    global client

    detector.terminate()
    #snowboydecoder.play_audio_file()
    print('Started Recording')
    snowboydecoder.play_audio_file()
    record_to_file('jarvis_detect.wav')
    snowboydecoder.play_audio_file()
    snowboydecoder.play_audio_file('jarvis_detect.wav')
    print('Detected! Sending...')
    f = open('jarvis_detect.wav', 'r')
    response = requests.post(url='https://api.wit.ai/speech?v=20160526', data=f, headers={'Authorization': 'Bearer Z4EWWHOU5UHRAL22EZ4CFO3RYPV7RSYJ', 'Content-Type': 'audio/wav'})
    j = response.json()

    print('Response: '+str(j))
    
    if ('intent' in j['entities'] and j['entities']['intent']):
        intent = j['entities']['intent'][0]['value']
        if (intent == 'play_music'):
            print('playing music........')
            response = requests.post(url='http://mopidy.musky.duckdns.org/mopidy/rpc', data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.play"}')
            print('Respo:' + str(response))
        elif (intent == 'pause_music'):
            print('pausing music........')
            response = requests.post(url='http://mopidy.musky.duckdns.org/mopidy/rpc', data='{"jsonrpc": "2.0", "id": 1, "method": "core.playback.pause"}')
            print('Respo:' + str(response))
        else:
            snowboydecoder.play_audio_file("resources/dong.wav")
    else:
        snowboydecoder.play_audio_file("resources/dong.wav")

    decoder_loop()

def decoder_loop():
	global detector

	detector = snowboydecoder.HotwordDetector('jarvis.pmdl', sensitivity=0.5)
	print('Listening... Press Ctrl+C to exit')
	detector.start(detected_callback=listener,
               interrupt_check=interrupt_callback,
               sleep_time=0.03)
	detector.terminate()

# capture SIGINT signal, e.g., Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

# main loop
decoder_loop()

# f = open('jarvis_detect.wav', 'r')
# response = requests.post(url='https://api.wit.ai/speech?v=20160526',
#                     data=f,
#                     headers={'Authorization': 'Bearer Z4EWWHOU5UHRAL22EZ4CFO3RYPV7RSYJ', 'Content-Type': 'audio/wav'})
# j = response.json()
# intent = 
# print('Done: '+str(j['entities']['intent'][0]['value']))   

