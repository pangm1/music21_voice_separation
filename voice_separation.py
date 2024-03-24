from sys import argv, platform
from music21 import *
import random
import string
from queue import Queue

PITCH_MAX = int(pitch.Pitch('B9').ps)
PITCH_MIN = int(pitch.Pitch('C0').ps)

def segmentContigs(part):
    # TODO: fix
    f = (note.Note,)
    timespans = part.asTimespans(classList=f)
    maxOverlap = timespans.maximumOverlap()
    maxContigs = []
    verticalities = timespans.iterateVerticalities()
    # label verticalities and overlaps
    i = 0
    for v in verticalities:
        for n in v.startTimespans:
            n.element.addLyric(f"{i}:{len(v.startAndOverlapTimespans)}")
        # maximal contigs
        if (len(v.startAndOverlapTimespans) == maxOverlap):
            # print("appending")
            # print(v.startAndOverlapTimespans)
            maxContigs.append([v.startAndOverlapTimespans, v])
            for n in v.startTimespans:
                n.element.addLyric(f"{maxOverlap}m")
            for n in v.overlapTimespans:
                n.element.addLyric(f"{maxOverlap}mo")
        # print(i, v, v.overlapTimespans, v.startTimespans, "sum:", len(v.startAndOverlapTimespans))
        i += 1
    # print("maximum overlap:", maxOverlap)
    # print("maximal contigs: ", maxContigs)
    # part.show("t")
    # part.show()

    return maxContigs

# 
def assignVoices(contig, dir):
    if dir == "l":
        contig
        pass
    if dir == "r":
        contig
        pass

# bfs
def crawlScore(frontier, partdict, currid):
    id = currid
    while len(frontier):
        # for c in frontier:
        #     print(f"id:{c[1]}", c[0])
        # both directions (maxcontigs)
        item = frontier.pop(0)
        if item[2] == "m":
            left = item[0][1].previousVerticality
            right = item[0][1].nextVerticality
            print("m", item, left, right)
            if left:
                assignVoices(item, "l")
                frontier.append(([left.startAndOverlapTimespans, left], id, "l"))
                id += 1
            if right:
                assignVoices(item, "r")
                frontier.append(([right.startAndOverlapTimespans, right], id, "r"))
                id += 1
        # go left
        elif item[2] == "l":
            left = item[0][1].previousVerticality
            print("l", item, left)
            if left:
                assignVoices(item, "l")
                frontier.append(([left.startAndOverlapTimespans, left], id, "l"))
                id += 1
        # go right
        elif item[2] == "r":
            right = item[0][1].nextVerticality
            print("r", item, right)
            if right:
                assignVoices(item, "r")
                frontier.append(([right.startAndOverlapTimespans, right], id, "r"))
                id += 1

def connectContigs(maxcontigs):
    # generate colors
    partdict = {}
    for i in range(len(maxcontigs[0][0])):
        # print(i, partdict)
        if i not in partdict:
            partdict[i] = {"stream": stream.Part(), "color": ""}
            newcolor = ''
            while (True):
                newcolor = f"#{''.join(random.choices(string.hexdigits, k=6))}"
                if newcolor not in [k["color"] for k in partdict.values()]:
                    break
            partdict[i]["color"] = newcolor
    # assign voices to maximal contigs
    for m in maxcontigs:
        # print(m)
        m[0] = sorted(m[0], key=lambda n: n.element.pitch)
        i = 0
        for n in m[0]:
            n.element.groups.append(str(i))
            n.element.style.color = partdict[i]["color"]
            # print(n.element.pitch, n.element.groups, n.element.style.color)
            i += 1
    # bfs (queue) initialized with maxcontigs 
    id = 0
    frontier = []
    for m in maxcontigs:
        frontier.append((m, id, "m"))
        id += 1
    crawlScore(frontier, partdict, id)
    
def separateVoices(part):
    maxcontigs = segmentContigs(part)
    voices = connectContigs(maxcontigs)
    return part

# set up the environment
if platform == 'win32':
    # Windows
    path = 'C:/Program Files/MuseScore 4/bin/Musescore4.exe' # was 3 previously (how to use any musicxml reader)
elif platform == 'darwin':
    # Mac OS - TODO
    pass
else:
    # assume Linux
    path = '/usr/bin/musescore'

env = environment.Environment()
env['musicxmlPath'] = path

argc = len(argv)
if argc < 3:
    print('arguments: [input file] [output name (no extension)]')
else:
    # parse musicxml
    song = converter.parse(argv[1])
    # song.show()
    # dechordify
    for c in song.recurse(classFilter=(chord.Chord)):
        for n in c.notes:
            c.activeSite.insert(c.offset, n)
        a = c.activeSite
        a.remove(c)
    # song.quantize((32,), recurse=True, inPlace=True)
    # remove grace notes 
    graceNotes = []
    for n in song.recurse().notes:
        # n.quarterLength = n.quarterLength # and inexpressible durations (idk if this part works)
        if n.duration.isGrace:
            graceNotes.append(n)
            n.activeSite.remove(n, shiftOffsets=True)
    # make it visible in musescore for Testing
    for m in song.recurse(classFilter=(stream.Measure,)):
        m.makeVoices(inPlace=True)
    # TODO: recurse parts and clefs
    reduced = separateVoices(song)
    # print("reduced score:")
    # reduced.show("t")
    # reduced.show()
    


    ''' TEST COMMANDs
        python3 ./voice_separation.py ./examples/carol_of_the_bells/before.mxl ./examples/carol_of_the_bells/before > output
        
        python3 ./voice_separation.py ./examples/puttin_on_the_ritz/before.mxl ./examples/puttin_on_the_ritz/before > output2

        python3 ./voice_separation.py ./examples/fur_elise/before.mxl ./examples/fur_elise/before > output3

        python3 ./voice_separation.py ./examples/moonlight_sonata/before.mxl ./examples/moonlight_sonata/before > output4

        python3 ./voice_separation.py ./examples/clair_de_lune/before.mxl ./examples/clair_de_lune/before > output5

        python3 ./voice_separation.py ./examples/nocturne/before.mxl ./examples/nocturne/before > output6

        python3 ./voice_separation.py ./examples/nutcracker/before.mxl ./examples/nutcracker/before > output7

        python3 ./voice_separation.py ./examples/beethoven/before.mxl ./examples/beethoven/before > output8
    '''
    

