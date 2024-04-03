from sys import argv, platform, maxsize
from music21 import *
import random
import string

PITCH_MAX = int(pitch.Pitch('B9').ps)
PITCH_MIN = int(pitch.Pitch('C0').ps)

def segmentContigs(part):
    # TODO: fix for rests
    # TODO: figure out how to recognize ties
    f = (note.Note,)
    timespans = part.asTimespans(classList=f)
    maxOverlap = timespans.maximumOverlap()
    maxContigs = []
    contigs = []
    verticalities = list(timespans.iterateVerticalities())
    # make contigs instead of using verticalities
        # step 1. put boundaries at places where the number of overlaps changes
    boundaries = set()
    i = 0
    while i < len(verticalities):
        refV = verticalities[i]
        boundaries.add(refV.offset)
        while i < len(verticalities) and (refV == verticalities[i] or len(verticalities[i].startAndOverlapTimespans) == len(refV.startAndOverlapTimespans)):
            i += 1
        # step 2. look at notes overlapping boundaries, put another boundary at that note's start and end (where there aren't already boundaries)
    for o in boundaries.intersection(set(timespans.overlapTimePoints(includeStopPoints=True))):
        for e in timespans.elementsOverlappingOffset(o):
            if e.offset not in boundaries: 
                boundaries.add(e.offset)
            if e.endTime not in boundaries: 
                boundaries.add(e.endTime)
    bList = sorted(boundaries)
    vi = 0
    bi = 1
    while vi < len(verticalities) and bi < len(bList):
        # contig: list of verticalities, start and end offsets
        contigs.append([[], (bList[bi - 1], bList[bi])])
        while vi < len(verticalities) and bi < len(bList) and verticalities[vi].offset < bList[bi]:
            contigs[-1][0].append(verticalities[vi])
            vi += 1
        # print(contigs[-1])
        if not len(contigs[-1][0]):
            contigs.pop()
            bi += 1
            continue
        if len(contigs[-1][0][0].startAndOverlapTimespans) == maxOverlap:
            maxContigs.append(contigs[-1])
        bi += 1


    # label contigs
    i = 0
    for c in contigs:
        for v in c[0]:
            for n in v.startTimespans:
                n.element.addLyric(f"{i}")
            # for n in v.overlapTimespans:
            #     n.element.addLyric(f"{i}o")
        i += 1
    for c in maxContigs:
        for v in c[0]:
            for n in v.startTimespans:
                n.element.addLyric("m")
            # for n in v.overlapTimespans:
            #     n.element.addLyric(f"mo")
    # part.show()

    # generate dictionary of voices with streams and colors
    partdict = {}
    for i in range(maxOverlap):
        if i not in partdict:
            partdict[str(i)] = {"stream": stream.Part(), "color": ""}
            newcolor = ''
            while (True):
                newcolor = f"#{''.join(random.choices(string.hexdigits, k=6))}"
                if newcolor not in [k["color"] for k in partdict.values()]:
                    break
            partdict[str(i)]["color"] = newcolor

    return (maxContigs, contigs, partdict)

# heuristic function
# probably better to do generic intervals here
# TODO: distance from the top and bottom of the ranges of two contigs (ex. jumping chords)
# TODO: average pitch in fragment
def distance(f, t):
    res = interval.Interval(f, t).generic.undirected
    # print(t.pitch, f.pitch, res)
    return res

# 
def assignVoices(bfsItem, dir):
    # print(dir, bfsItem)
    if dir == "l":
        startV = bfsItem[0][0][0]
        destV = startV.previousVerticality
        maxV = bfsItem[3][0][0]
    elif dir == "r":
        startV = bfsItem[0][0][-1]
        destV = startV.nextVerticality
        maxV = bfsItem[3][0][-1]
    

    # keep track of bin,group pairs already assigned
    assignedPairs = [[],[]]

    # notes of destination contig
    toAssign = []
    for t in destV.startAndOverlapTimespans:
        element = t.element
        if not len(element.groups) and not element.id in [t.element.id for t in startV.startAndOverlapTimespans]: # unvisited
            # print(f"appending1 {element.pitch} to toAssign with groups {element.groups}")
            toAssign.append([element, []])  
        elif len(element.groups):
            assignedPairs[0].append(element)
            assignedPairs[1].append(element.groups[0])
    # check if groups already assigned (contig visited already)
    if not len(toAssign):
        return
    # print("start", startV.offset, "->", destV.offset)
    # used = set()
    # for n in startV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR3; duplicate groups {e.groups} at {startV.offset}")
    #     elif len(e.groups): used.add(eval(e.groups[0]))
    # used = set()
    # for n in destV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR3; duplicate groups {e.groups} at {destV.offset}")
    #     elif len(e.groups): used.add(eval(e.groups[0]))

    # notes of start contig
    toConnect = []
    for t in startV.startAndOverlapTimespans:
        if len(t.element.groups) and t.element.groups[0] not in assignedPairs[1]:
            toConnect.append(t.element)
            # print(f"appending1 {t.element} to toConnect with groups {t.element.groups}")

    # naive assign first 
    # enumerate all possible combinations (hash)
    for a in toAssign:
        for c in toConnect:
            a[1].append((c.groups, distance(c, a[0])))

    # print("toConnect", [(c.id, c.pitch.nameWithOctave, c.groups) for c in toConnect])
    # print("toAssign", [(a[0].id, a[0].pitch.nameWithOctave, a[1]) for a in toAssign])
    options = sorted([(a[0], g) for a in toAssign for g in a[1]], key=lambda t: t[1][1])
    # print("options:", [(o[0].id, o[0].pitch.nameWithOctave, o[1]) for o in options])

    # select options with lowest penalty
    for o in options:
        if o[0].id not in [a.id for a in assignedPairs[0]] and o[1][0] not in assignedPairs[1]:
            o[0].groups = o[1][0]
            # print(f"assigning {o[0].pitch.nameWithOctave} <- {o[1][0]} distance: {o[1][1]} -> groups:{o[0].groups}")
            assignedPairs[0].append(o[0])
            assignedPairs[1].append(o[1][0])

    # print("assigned pairs:", [(n.id, n.pitch.nameWithOctave, g) for ni,n in enumerate(assignedPairs[0]) for gi,g in enumerate(assignedPairs[1]) if ni == gi])
    # print("assigned notes:", [[a[0].pitch.nameWithOctave] + a[1:] for a in toAssign if len(a[0].groups)])
    # if len([a for a in toAssign if not len(a[0].groups)]):
    #     print("unassigned notes:", [[a[0].pitch.nameWithOctave] + a[1:] for a in toAssign if not len(a[0].groups)])
        # assignVoices(contig, dir)
    # used = set()
    # for n in startV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR0; duplicate groups {e.groups} at {startV.offset}")
    #     elif len(e.groups): used.add(eval(e.groups[0]))
    # used = set()
    # for n in destV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR0; duplicate groups {e.groups} at {destV.offset}")
    #     elif len(e.groups): used.add(eval(e.groups[0]))

    # TODO: connect with maxcontigs (aware)
    
    # print("finish")

# assign groups across fragments
def groupFragments(contig, dir, maxContig):
    # TODO: experiment with sorting order (something to do with melody being high notes, or soprano and bass notes varying more)
    # *** sorting order is important (notes with the same pitch and duration are considered equal even if they are different instances)
    grouphash = [] # verticalities x "fragment"
    prev = [None] * len(contig[0][0].startAndOverlapTimespans)
    # make sure that held notes stay in same fragment (column)
    for v in contig[0]:
        temp = [None] * len(prev)
        curr = [t.element for t in sorted(v.startAndOverlapTimespans, key=lambda n: n.element.id)]
        curr = sorted(curr, key=lambda n: n.pitch)
        # curr = sorted(curr, key=lambda n: n.duration.quarterLength)
        for i,n in enumerate(prev):
            if n in curr:
                temp[i] = n
        e = (n for n in curr if n not in prev)
        for i,n in enumerate(temp):
            if not temp[i]: temp[i] = next(e)
        # print("appending", temp)
        grouphash.append(temp)
        prev = temp

    if dir == "m": # populate maximum contigs
        i = 0
        used = set(eval(n.groups[0]) for n in grouphash[0] if len(n.groups))
        for n in [n for n in grouphash[0] if not len(n.groups)]:
            while i in used:
                i = (i + 1) % len(grouphash[0])
            n.groups = [str(i)]
            used.add(i)
        startV = contig[0][0]
        destV = contig[0][-1]
    elif dir == "l":
        startV = contig[0][0]
        destV = contig[0][-1]
    elif dir == "r":
        startV = contig[0][-1]
        destV = contig[0][0]

    # print(f"grouping {len(contig[0])} fragments {startV.offset}<->{destV.offset} of length {len(startV.startAndOverlapTimespans)}")
    # for r in grouphash:
    #     print("vertical", [(c.id, c.pitch.nameWithOctave, c.groups) for c in r])
    # transpose grouphash -> fragments
    fragments = []
    for i in range(len(grouphash[0])):
        fragments.append([])
        for row in grouphash:
            fragments[-1].append(row[i])

    # checks for duplicate groups
    # quit = False
    # used = set()
    # for n in startV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR1; duplicate groups {e.groups} at {startV.offset}")
    #         quit = True
    #     elif len(e.groups): used.add(eval(e.groups[0]))
    # used = set()
    # for n in destV.startAndOverlapTimespans:
    #     e = n.element
    #     if len(e.groups) and eval(e.groups[0]) in used:
    #         print(f"ERROR1; duplicate groups {e.groups} at {destV.offset}")
    #         quit = True
    #     elif len(e.groups): used.add(eval(e.groups[0]))
    # for f in fragments:
    #     # print("fragment", [(n.id, n.pitch.nameWithOctave, n.groups) for n in f], len(f))
    #     startN = None
    #     destN = None
    #     for n in f:
    #         if n.id in [t.element.id for t in startV.startAndOverlapTimespans]: startN = n
    #         elif n.id in [t.element.id for t in destV.startAndOverlapTimespans]: destN = n
    #     if not startN or not destN: continue
    #     if (len(startN.groups) and len(destN.groups)) and eval(startN.groups[0]) != eval(destN.groups[0]):
    #         print(f"ERROR2; {startN.pitch}:{startN.groups} at {startV.offset} is not equal to {destN.pitch}:{destN.groups} at {destV.offset}")
    #         quit = True
    # if quit: 
    #     print("quit")
        # return

    for f in fragments:
        startN = None
        destN = None
        for n in f:
            if n.id in [t.element.id for t in startV.startAndOverlapTimespans]: startN = n
            elif n.id in [t.element.id for t in destV.startAndOverlapTimespans]: destN = n
        if not startN or not destN: continue
        voice = startN.groups if len(startN.groups) else destN.groups
        # print((startN.id, startN.pitch, startN.groups), (destN.id, destN.pitch, destN.groups))
        # print(f"assigning group {voice}: ({startN.id}, {startN.pitch})<->({destN.pitch}, {destN.id})")
        if len(voice):
            for n in f:
                if not len(n.groups): 
                    # print(n.id, n.pitch, n.groups)
                    n.groups = voice 

# bfs
def crawlScore(frontier, contigs, currid):
    id = currid
    while len(frontier):
        # for c in frontier:
        #     print(f"id:{c[1]}", c[0])
        # both directions (maxcontigs)
        item = frontier.pop(0)
        if item[2] == "m":
            leftIndex = contigs.index(item[0]) - 1
            rightIndex = contigs.index(item[0]) + 1
            # print("m", item, leftIndex, rightIndex)
            if leftIndex >= 0:
                assignVoices(item, "l")
                groupFragments(contigs[leftIndex], "l", item[0])
                frontier.append((contigs[leftIndex], id, "l", item[0]))
                id += 1
            if rightIndex < len(contigs):
                assignVoices(item, "r")
                groupFragments(contigs[rightIndex], "r", item[0])
                frontier.append((contigs[rightIndex], id, "r", item[0]))
                id += 1
        # go left
        elif item[2] == "l":
            leftIndex = contigs.index(item[0]) - 1
            # print("l", item, leftIndex)
            if leftIndex >= 0:
                assignVoices(item, "l")
                groupFragments(contigs[leftIndex], "l", item[3])
                frontier.append((contigs[leftIndex], id, "l", item[3]))
                id += 1
        # go right
        elif item[2] == "r":
            rightIndex = contigs.index(item[0]) + 1
            # print("r", item, rightIndex)
            if rightIndex < len(contigs):
                assignVoices(item, "r")
                groupFragments(contigs[rightIndex], "r", item[3])
                frontier.append((contigs[rightIndex], id, "r", item[3]))
                id += 1

def connectContigs(maxcontigs, contigs, partdict):
    # assign voices to maximal contigs
        
    # bf (queue) initialized with maxcontigs 
    id = 0
    frontier = [] # contig, bfs-ID, direction, maxContig
    for m in maxcontigs:
        groupFragments(m, "m", m)
        frontier.append((m, id, "m", m))
        id += 1
    crawlScore(frontier, contigs, id)
    
def separateVoices(part):
    (maxcontigs, contigs, partdict) = segmentContigs(part)
    connectContigs(maxcontigs, contigs, partdict)

    # FIXME: handle duplicate groups in verticalities
    groups = set()
    timetree = part.asTimespans(classList=(note.Note,))
    for o in timetree.allOffsets():
        groups.clear()
        for n in (list(timetree.elementsStartingAt(o)) + list(timetree.elementsOverlappingOffset(o))):
            if len(n.element.groups): # FIXME: delete when all groups have been assigned
                if n.element.groups[0] in groups:
                    print(f"duplicate {n.element.groups} for {n.element} at offset {o}")
                groups.add(n.element.groups[0])

    # TODO: generate new parts for each group
    return (part, partdict)

def preprocessScore(song):
    # dechordify
    for m in song.recurse(classFilter=(stream.Measure, stream.Voice)):
        for c in m.getElementsByClass(chord.Chord):
            for n in c.notes:
                d = duration.Duration(c.quarterLength)
                n = note.Note(n.pitch)
                n.duration = d
                m.insert(c.getOffsetBySite(m), n)
            m.remove(c)
        m.makeVoices(inPlace=True)
    # fix voices nested within other voices
    for v in song.recurse(classFilter=(stream.Voice,)):
        if v.hasVoices():
            m = v.activeSite
            flat = m.flatten()
            voiced = flat.makeVoices()
            m.activeSite.replace(m, voiced)
    # song.quantize((32,), recurse=True, inPlace=True)
    # remove grace notes
    graceNotes = []
    for n in song.recurse().notes:
        # n.quarterLength = n.quarterLength # and inexpressible durations (idk if this part works)
        if n.duration.isGrace:
            graceNotes.append(n)
            n.activeSite.remove(n, shiftOffsets=True)
    # print(graceNotes)
    # FIXME: Notation messed up for output4
    
    # fix notation? (idk what this does tbh)
    # song.makeNotation(inPlace=True)
        
    song.write("musicxml", argv[2] + '_processed.musicxml')
    # song.show("txt")
    # exit()

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
    song.write("musicxml", argv[2] + '_music21.musicxml')
    # song.show()
    preprocessScore(song)
    
    # TODO: recurse parts and clefs
    # TODO: as well as segments the song structure (where melodies and voicing change)
    (reduced, partdict) = separateVoices(song)
    # print(partdict)
    for n in reduced.recurse(classFilter=note.Note):
        if len(n.groups) and n.groups[0] in partdict:
            n.style.color = partdict[n.groups[0]]["color"]
            n.addLyric(n.groups)
        else:
            print(n)

    # print("reduced score:")
    # reduced.show("t")
    # reduced.show()
    # could also just show original score (object references intact)
    reduced.write("musicxml", argv[2] + '_reduced.musicxml')
    


    ''' TEST COMMANDs
        python3 ./voice_separation.py ./examples/carol_of_the_bells/before.mxl ./examples/carol_of_the_bells/before > output
        
        python3 ./voice_separation.py ./examples/puttin_on_the_ritz/before.mxl ./examples/puttin_on_the_ritz/before > output2

        python3 ./voice_separation.py ./examples/fur_elise/before.mxl ./examples/fur_elise/before > output3

        python3 ./voice_separation.py ./examples/moonlight/before.mxl ./examples/moonlight/before > output4

        python3 ./voice_separation.py ./examples/clair_de_lune/before.mxl ./examples/clair_de_lune/before > output5

        python3 ./voice_separation.py ./examples/nocturne/before.mxl ./examples/nocturne/before > output6

        python3 ./voice_separation.py ./examples/nutcracker/before.mxl ./examples/nutcracker/before > output7

    '''
    

