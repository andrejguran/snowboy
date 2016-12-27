# -*- coding: utf-8 -*-
import json
import subprocess
import tempfile
import wave
import audioop
import os
import urllib2
import time
from collections import deque
from pprint import pprint

import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
# The threshold intensity that defines silence signal (lower than).
THRESHOLD = 180
# Silence limit in seconds. The max amount of seconds where only silence is recorded.
# When this time passes the recording finishes and the file is delivered.
SILENCE_LIMIT = 2
# We need a WAV to FLAC converter.
FLAC_CONV = '/usr/local/bin/flac'
LANG_CODE = 'pl-PL'

API_URL = 'http://0.0.0.0:9876/api/v1/'
KEYWORD = 'darek'
ON_COMMAND = u'włącz'
OFF_COMMAND = u'wyłącz'

def listen_for_speech():
    """
    Does speech recognition using Google's speech recognition service.
    Records sound from microphone until silence is found and save it as WAV and then converts it to FLAC.
    Finally, the file is sent to Google and the result is returned.
    """

    # Open stream
    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

    print "* listening. CTRL+C to finish."
    samples = []
    chunks_per_second = RATE / CHUNK
    # 2s buffer for checking sound is louder than threshold
    silence_buffer = deque(maxlen=SILENCE_LIMIT * chunks_per_second)
    # Buffer used to append data before detection
    samples_buffer = deque(maxlen=SILENCE_LIMIT * RATE)

    started = False

    while (True):
        data = stream.read(CHUNK)
        silence_buffer.append(abs(audioop.avg(data, 2)))
        samples_buffer.extend(data)
        if (True in [x > THRESHOLD for x in silence_buffer]):
            if (not started):
                print "starting record"
                started = True
                samples.extend(samples_buffer)
                samples_buffer.clear()
            else:
                samples.extend(data)


        elif (started == True):
            print "finished"
            # The limit was reached, finish capture and deliver
            stream.stop_stream()
            submit_samples(samples, audio)
            # Reset all
            stream.start_stream()
            started = False
            silence_buffer.clear()
            samples = []
            print "done"
            break

    print "* done recording"
    stream.close()
    audio.terminate()


def submit_samples(data, audio):
    filename = tempfile.mkdtemp() + 'output_' + str(int(time.time()))
    # Write data to WAVE file
    data = ''.join(data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()

if (__name__ == '__main__'):
    listen_for_speech()
