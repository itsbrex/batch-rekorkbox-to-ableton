# usage: python3 ableton-to-cues.py $ALS_FILENAME $REKORDBOX_XML_FILENAME
# converts ableton warp markers to rekordbox cue points.
# use '--reverse' to convert rekordbox cues to ableton warp markers instead
# writes output to output.xml if converting ableton to rekordbox
# in reverse mode, it writes to output.als

# https://gist.github.com/sandhose/b6903fe3bca799063300cce28832dfdc

import argparse
import datetime
import gzip
import logging
import sys
from tkinter import Tk, Button
from tkinter.filedialog import askopenfile, asksaveasfile
from tkinter.scrolledtext import ScrolledText
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import os

logger = logging.getLogger(__name__)


def run():
    stderrHandler = logging.StreamHandler()
    logger.addHandler(stderrHandler)
    logger.setLevel(logging.INFO)

    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description='convert between cues and warp markers')
        parser.add_argument(
            'als_file', type=str, nargs='?', default=None, help='path to ALS file')
        parser.add_argument(
            'rekordbox_file', type=str, help='path to Rekordbox xml file')
        parser.add_argument(
            '--reverse', action='store_true',
            help='set to true to convert Rekordbox to Ableton')
        args = parser.parse_args()

        if args.reverse and args.als_file is None:
            output_als_file = create_output_als_file(args.rekordbox_file)
        else:
            output_als_file = args.als_file

        with open(args.rekordbox_file, mode='rb') as rekordbox_file, \
             open(output_als_file, mode='rb') as als_file:
            if not args.reverse:
                with open('output.xml', 'wb') as outfile:
                    ableton_to_rekordbox(als_file, rekordbox_file, outfile)
            else:
                with open(output_als_file, 'wb') as outfile:
                    rekordbox_to_ableton(als_file, rekordbox_file, outfile)

        logger.info('Finished writing ' + outfile) 
    else:
        app = App(None)
        app.title('Ableton to cues')

        guiHandler = MyHandlerText(app.logbox)
        logger.addHandler(guiHandler)

        app.mainloop()

def create_output_als_file(rekordbox_file_path):
    # Create an output.als file in the same folder as the rekordbox_file
    output_als_file_path = os.path.join(os.path.dirname(rekordbox_file_path), 'output.als')
    return output_als_file_path

def normalize_time(time):
    if time == 0:
        return "0.001"
    else:
        return "{0:.3f}".format(time)


def get_memcue(time):
    child = ET.Element('POSITION_MARK')
    child.set('Name', '')
    child.set('Type', '0')
    child.set('Num', '-1')
    child.set('Start', normalize_time(time))
    return child


def get_hotcue(time, num):
    child = ET.Element('POSITION_MARK')
    child.set('Name', '')
    child.set('Type', '0')
    child.set('Red', '40')
    child.set('Green', '226')
    child.set('Blue', '20')
    child.set('Num', str(num))
    child.set('Start', normalize_time(time))
    return child


def get_warp_marker(time, num, bpm):
    child = ET.Element('WarpMarker')
    child.set('Id', str(num))
    child.set('SecTime', time)
    beat_time = float(time) * bpm / 60
    child.set('BeatTime', str(beat_time))
    return child


def get_rekordbox_filename(rekordbox_track):
    parts = rekordbox_track.get('Location').split('/')
    return unquote(parts[-1])


def get_ableton_filename(track):
    return track.find('.//FileRef').find('./Name').get('Value')


def ableton_to_rekordbox(als_file, rekordbox_file, output):
    logger.info('Converting Ableton warp markers to Rekordbox cues.')
    tree = ET.parse(gzip.GzipFile(fileobj=als_file))
    tracks = tree.getroot().findall('.//AudioClip')

    rekordbox_tree = ET.parse(rekordbox_file)
    rekordbox_tracks = rekordbox_tree.getroot().findall('./COLLECTION/TRACK')

    for track in tracks:
        filename = get_ableton_filename(track)
        warp_markers = track.findall('.//WarpMarkers/WarpMarker')
        # Find the corresponding track in rekordbox
        for rekordbox_track in rekordbox_tracks:
            if (get_rekordbox_filename(rekordbox_track) == filename):
                logger.info('processing ' + filename)
                # clear all existing cues
                for element in rekordbox_track.findall('./POSITION_MARK'):
                    rekordbox_track.remove(element)
                # create a hotcue and mem cue for each warp marker
                num = 0
                times = [float(marker.get('SecTime')) for marker in warp_markers]
                times.sort()
                # ignore last item cuz it gets duplicated for some reason
                del times[-1]
                for time in times:
                    hotcue = get_hotcue(time, num)
                    memcue = get_memcue(time)
                    num = num + 1
                    rekordbox_track.append(hotcue)
                    rekordbox_track.append(memcue)
    rekordbox_tree.write(output, encoding='UTF-8', xml_declaration=True)

def rekordbox_to_ableton(als_file, rekordbox_file, output):
    logger.info('Converting Rekordbox cues to Ableton warp markers.')
    tree = ET.parse(gzip.GzipFile(fileobj=als_file))
    tracks = tree.getroot().findall('.//AudioClip')

    rekordbox_tree = ET.parse(rekordbox_file)
    rekordbox_tracks = rekordbox_tree.getroot().findall('./COLLECTION/TRACK')
    for rekordbox_track in rekordbox_tracks:
        filename = get_rekordbox_filename(rekordbox_track)
        # find the corresponding ableton track
        for track in tracks:
            if (get_ableton_filename(track) == filename):
                logger.info('processing ' + filename)
                # clear all existing warp markers
                # create new <WarpMarkers> group
                child = ET.Element('WarpMarkers')
                # ableton warp marker IDs seem to start at 2??
                num = 2
                # get rekordbox bpm
                bpm = float(rekordbox_track.find('./TEMPO').get('Bpm'))
                time = None
                for element in rekordbox_track.findall('./POSITION_MARK'):
                    time = element.get('Start')
                    marker = get_warp_marker(time, num, bpm)
                    num = num + 1
                    child.append(marker)
                # append the last marker a 2nd time; for some reason this seems
                # needed otherwise it doesn't show up in ableton.
                if time:
                    marker = get_warp_marker(str(float(time) + 0.1), num, bpm)
                    child.append(marker)
                # attach the new WarpMarkers group
                if len(child.getchildren()) > 0:
                    for markers in track.findall('./WarpMarkers'):
                        track.remove(markers)
                    track.append(child)
    tree.write(output, encoding='UTF-8', xml_declaration=True)

class App(Tk):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.grid()

        self.to_ableton = Button(self, text="Rekordbox to Ableton", command=self.to_ableton)
        self.to_ableton.grid(column=0, row=0, ipadx=5, padx=5, pady=5)

        self.to_rekordbox = Button(self, text="Ableton to Rekordbox", command=self.to_rekordbox)
        self.to_rekordbox.grid(column=1, row=0, ipadx=5, padx=5, pady=5)

        self.logbox = ScrolledText(self, state="disabled")
        self.logbox.grid(column=0, row=1, columnspan=2)

        self.flow = None

    def to_ableton(self):
        if self.flow is None:
            self.flow = 'ableton'
            self.after(0, self.ask_ableton)
        else:
            logger.warning('A flow is already running')

    def to_rekordbox(self):
        if self.flow is None:
            self.flow = 'rekordbox'
            self.after(0, self.ask_ableton)
        else:
            logger.warning('A flow is already running')

    def abort(self):
        self.flow = None
        logger.warning('Aborting')

    def ask_ableton(self):
        logger.info("Asking the Ableton file")
        self.als_file = askopenfile(mode='rb', title="Ableton input file", filetypes=[("Ableton files", ".als")], parent=self)
        if self.als_file is None:
            self.abort()
        else:
            self.after(0, self.ask_rekordbox)

    def ask_rekordbox(self):
        logger.info("Asking the Rekordbox file")
        self.rekordbox_file = askopenfile(mode='rb', title="Rekordbox input file", filetypes=[("Rekordbox file", ".xml")], parent=self)
        if self.rekordbox_file is None:
            self.abort()
        else:
            self.after(0, self.ask_output)

    def ask_output(self):
        logger.info("Asking the output file")
        if self.flow == 'ableton':
            self.output_file = asksaveasfile(mode='wb', title="Ableton output file", defaultextension="als", parent=self)
        else:
            self.output_file = asksaveasfile(mode='wb', title="Rekordbox output file", defaultextension="xml", parent=self)

        if self.output_file is None:
            self.abort()
        else:
            self.after(0, self.run_flow)

    def run_flow(self):
        if self.flow == 'ableton':
            rekordbox_to_ableton(self.als_file, self.rekordbox_file, self.output_file)
        elif self.flow == 'rekordbox':
            ableton_to_rekordbox(self.als_file, self.rekordbox_file, self.output_file)
        else:
            logger.error("No flow running")
        logger.info("Processing done")
        self.flow = None

class MyHandlerText(logging.StreamHandler):
    def __init__(self, textctrl):
        logging.StreamHandler.__init__(self) # initialize parent
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s\n  %(message)s'))
        self.textctrl = textctrl

    def emit(self, record):
        msg = self.format(record)
        self.textctrl.config(state="normal")
        self.textctrl.insert("end", msg + "\n")
        self.flush()
        self.textctrl.config(state="disabled")

if __name__ == '__main__':
    run()