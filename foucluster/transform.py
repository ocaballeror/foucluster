import multiprocessing as mp
import os
import json
import subprocess
from .print import fourier_plot
import numpy as np
from scipy.io.wavfile import read


def removing_spaces(source_folder):
    for song in os.listdir(source_folder):
        new_song = list()
        string_list = song.split() if len(song.split()) > 1 else song.split('_')
        for string in string_list:
            if string != '-' and not string.isdigit():
                new_song.append(string)
        new_song = '_'.join(new_song)
        file = os.path.join(source_folder, song)
        new_file = os.path.join(source_folder, new_song)
        os.rename(file, new_file)


def transform_wav(mp3_file, wav_file):
    """
    Transform mp3 file into wav format using mpg123
    or ffmpeg.

    :param str mp3_file:
    :param str wav_file:
    :return:
    """
    if not os.path.isfile(wav_file):
        try:
            bash_command = ['mpg123', '-w', wav_file, mp3_file]
            subprocess.run(bash_command)
        except Exception as e:
            print(e)
            print('Trying with ffmpeg...')
            alt_command = ['ffmpeg', '-i', mp3_file, wav_file]
            subprocess.run(alt_command)


def fourier_song(wav_file,
                 rate_limit=6000.0):
    rate, aud_data = read(wav_file)
    # Should be mono
    if len(aud_data) != len(aud_data.ravel()):
        aud_data = np.mean(aud_data, axis=1)

    # Zero padding
    len_data = len(aud_data)
    channel_1 = np.zeros(2 ** (int(np.ceil(np.log2(len_data)))))
    channel_1[0:len_data] = aud_data

    # Fourier analysis
    fourier = np.abs(np.fft.fft(channel_1))
    w = np.linspace(0, rate, len(fourier))

    w, fourier_to_plot = limit_by_freq(w, fourier, upper_limit=rate_limit)
    w, fourier_to_plot = group_by_freq(w, fourier_to_plot)

    # a = np.mean(fourier_to_plot)
    fourier_to_plot[np.argmax(fourier_to_plot)] = 0.0
    a = np.max(fourier_to_plot) / 100.0  # Max frequency will be 100.0
    fourier_to_plot = fourier_to_plot / a

    return w, fourier_to_plot


def group_by_freq(freq, features, max_rate=None, min_freq=1):
    """

    :param freq:
    :param features:
    :param max_rate:
    :param min_freq:
    :return:
    """
    if max_rate is None:
        max_rate = np.max(freq)
    final_length = int(max_rate / min_freq)
    new_freq = np.empty(final_length)
    new_features = np.empty(final_length)
    for i in range(final_length):
        mask_1 = freq >= i
        mask_2 = freq < (i + min_freq)
        mask = mask_1 * mask_2
        new_freq[i] = np.mean(freq[mask])
        new_features[i] = np.mean(features[mask])
    return new_freq, new_features


def limit_by_freq(freq, features, upper_limit, bottom_limit=None):
    """
    Limit arrays of frequency and features by maximum frequency and
    bottom frequency.

    :param freq: array of frequencies.
    :param features: array of amplitude.
    :param float upper_limit: maximum frequency.
    :param float bottom_limit: minimum frequency.
    :return:
    """
    # Copy into arrays, in order to apply mask
    freq = np.array(freq[:], dtype=np.float)
    features = np.array(features[:], dtype=np.float)
    # Mask for bottom limit
    if bottom_limit is not None:
        bottom_mask = freq >= bottom_limit
        features = features[bottom_mask]
        freq = freq[bottom_mask]
    # Mask for upper limit
    upper_mask = freq <= upper_limit
    features = features[upper_mask]
    freq = freq[upper_mask]
    return freq, features


def dict_to_array(song_dict):
    """

    :param dict song_dict: load form dictionary to array
    :return:
    """
    len_song = len(song_dict.keys())
    freq = np.empty(len_song, dtype=np.float)
    features = np.empty_like(freq)
    for i, k in enumerate(song_dict.keys()):
        freq[i] = k
        features[i] = song_dict[k]
    return freq, features


def time_to_frequency(song,
                      source_folder,
                      temp_folder,
                      output_folder,
                      rate_limit=6000.0,
                      overwrite=True,
                      plot=True,
                      image_folder=None):
    """
    Transform a MP3 song into WAV format, and then into
    Fourier series.

    :param str song: name of the song, with MP3 extension.
    :param str source_folder: folder where MP3 files are.
    :param str output_folder: folder where pickle files from
        frequency series are saved.
    :param str temp_folder: folder where wav files are saved.
    :param float rate_limit: maximum frequency of the frequency
        series.
    :param bool overwrite:
    :param bool plot: if True, frequency series is plotted.
    :param image_folder: if plotting is True, is the folder
        where the Fourier data is saved.
    :return:
    """
    song_name = os.path.splitext(song)[0]
    json_name = song_name + '.json'

    # Name of files
    mp3_file = os.path.join(source_folder, song)
    wav_file = os.path.join(temp_folder, song_name + '.wav')

    # Transform MP3 into WAV
    transform_wav(mp3_file=mp3_file,
                  wav_file=wav_file)

    full_json_name = os.path.join(output_folder, json_name)
    if not os.path.isfile(full_json_name) or overwrite is True:
        # Fourier transformation
        frequencies, fourier_series = fourier_song(wav_file=wav_file,
                                                   rate_limit=rate_limit)

        # Transform to dict
        freq_dict = dict()
        for x, y in zip(frequencies, fourier_series):
            freq_dict.update({str(x): y})

        # Save as JSON
        json_to_save = {song: freq_dict}
        with open(full_json_name, 'w') as output:
            json.dump(json_to_save, output)

        # Plotting
        if plot is True:
            fourier_plot(freq=frequencies,
                         features=fourier_series,
                         folder=image_folder,
                         filename=song_name)


def all_songs(source_folder,
              output_folder,
              temp_folder,
              rate_limit=6000.0,
              overwrite=True,
              plot=False,
              image_folder=None):
    """
    Transform a directory full of MP3 files
    into WAVE files, and then into Fourier series,
    working with directories.

    :param str source_folder: folder where MP3 files are.
    :param str output_folder: folder where pickle files from
        frequency series are saved.
    :param str temp_folder: folder where wav files are saved.
    :param float rate_limit: maximum frequency of the frequency
        series.
    :param bool overwrite:
    :param bool plot: if True, frequency series is plotted.
    :param image_folder: if plotting is True, is the folder
        where the Fourier data is saved.
    """
    if not os.path.isdir(temp_folder):
        os.makedirs(temp_folder)

    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    if plot is True and not os.path.isdir(image_folder):
        os.makedirs(image_folder)

    songs = [(song, source_folder, temp_folder, output_folder, rate_limit,
              overwrite, plot, image_folder)
             for song in os.listdir(source_folder)]

    with mp.Pool(processes=int(mp.cpu_count() / 2)) as p:
        p.starmap(time_to_frequency, songs)
