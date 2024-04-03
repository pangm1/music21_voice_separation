from sys import argv, platform
from music21 import *
import random
import string


# heuristic function for assigning voices
    # uses generic intervals so far
# TODO: distance from the top and bottom of the ranges of two contigs (ex. jumping chords)
# TODO: average pitch in fragment
def distance(f, t):
    res = interval.Interval(f, t).generic.undirected
    # print(t.pitch, f.pitch, res)
    return res

# assign voices across verticalities
    # direction is needed to find the verticalities connecting the contigs
def assignVoices(bfsItem, dir):
    if dir == "l":
        startV = bfsItem[0][0][0]
        destV = startV.previousVerticality
        maxV = bfsItem[3][0][0]
    elif dir == "r":
        startV = bfsItem[0][0][-1]
        destV = startV.nextVerticality
        maxV = bfsItem[3][0][-1]
    assignedPairs = [[],[]] # keep track of bin,group pairs already assigned
    toAssign = [] # notes of destination contig
    toConnect = [] # notes of start contig
    # print("start", startV.offset, "->", destV.offset)

    # populate toAssign with target notes
        # visited notes (groups already assigned) should be excluded and registered in assignedPairs
    for t in destV.startAndOverlapTimespans:
        element = t.element
        if not len(element.groups) and not element.id in [t.element.id for t in startV.startAndOverlapTimespans]:
            # print(f"appending1 {element.pitch} to toAssign with groups {element.groups}")
            toAssign.append([element, []])  
        elif len(element.groups):
            assignedPairs[0].append(element)
            assignedPairs[1].append(element.groups[0])
    if not len(toAssign):# whole contig visited already
        return
    # populate toConnect with reference notes
        # visited notes (groups already assigned) are excluded
    for t in startV.startAndOverlapTimespans:
        if len(t.element.groups) and t.element.groups[0] not in assignedPairs[1]:
            # print(f"appending1 {t.element} to toConnect with groups {t.element.groups}")
            toConnect.append(t.element)


    # naive assign first
        # all notes won't be assigned if reference vaarticality has less notes (not enough groups to assign)
    for a in toAssign:
        for c in toConnect:
            a[1].append((c.groups, distance(c, a[0])))
    # all permutations sorted by distance [(note, groups)]
    options = sorted([(a[0], g) for a in toAssign for g in a[1]], key=lambda t: t[1][1])

    # select options with lowest penalty
    for o in options:
        if o[0].id not in [a.id for a in assignedPairs[0]] and o[1][0] not in assignedPairs[1]:
            o[0].groups = o[1][0]
            # print(f"assigning {o[0].pitch.nameWithOctave} <- {o[1][0]} distance: {o[1][1]} -> groups:{o[0].groups}")
            assignedPairs[0].append(o[0])
            assignedPairs[1].append(o[1][0])

    # TODO: connect with maxcontigs (aware)
    
    # print("finish")

# assign voices across fragments (in the notes' groups)
    #*** sorting order is important (notes with the same pitch and duration are considered equal even if they are different instances)
# TODO: experiment with sorting order (something to do with melody being high notes, or soprano and bass notes varying more)
def groupFragments(contig, dir, maxContig):
    grouphash = [] # verticalities with fragments as columns
    fragments = [] # transposed

    # make sure that held notes stay in same fragment (column)
    prev = [None] * len(contig[0][0].startAndOverlapTimespans)
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
    # transpose grouphash -> fragments
    for i in range(len(grouphash[0])):
        fragments.append([])
        for row in grouphash:
            fragments[-1].append(row[i])

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

    # make fragments non-empty and homogenous where there are groups
    for f in fragments:
        startN = None
        destN = None
        for n in f:
            if n.id in [t.element.id for t in startV.startAndOverlapTimespans]: startN = n
            elif n.id in [t.element.id for t in destV.startAndOverlapTimespans]: destN = n
        if not startN or not destN: continue # this should not happen
        voice = startN.groups if len(startN.groups) else destN.groups
        # print((startN.id, startN.pitch, startN.groups), (destN.id, destN.pitch, destN.groups))
        # print(f"assigning group {voice}: ({startN.id}, {startN.pitch})<->({destN.pitch}, {destN.id})")
        if len(voice):
            for n in f:
                if not len(n.groups): # you should not need this conditional
                    # print(n.id, n.pitch, n.groups)
                    n.groups = voice 

# score bfs
    # assigns notes using helper function
    # frontier: [(contig, bfsID, direction, maxcontig)]
def crawlScore(frontier, contigs, currid):
    id = currid
    while len(frontier):
        item = frontier.pop(0)

        if item[2] == "m": # both directions (maxcontigs)
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
        elif item[2] == "l": # go left
            leftIndex = contigs.index(item[0]) - 1
            # print("l", item, leftIndex)
            if leftIndex >= 0:
                assignVoices(item, "l")
                groupFragments(contigs[leftIndex], "l", item[3])
                frontier.append((contigs[leftIndex], id, "l", item[3]))
                id += 1
        elif item[2] == "r": # go right
            rightIndex = contigs.index(item[0]) + 1
            # print("r", item, rightIndex)
            if rightIndex < len(contigs):
                assignVoices(item, "r")
                groupFragments(contigs[rightIndex], "r", item[3])
                frontier.append((contigs[rightIndex], id, "r", item[3]))
                id += 1        
    
# given a part/score return 
    # contigs  [[verticalities], (startBoundary, endBoundary)]
    # maximal contigs (contigs having maximal overlap)
    # dictionary of voices (which will be separated into parts)
# TODO: recognize rests
# TODO: figure out how to recognize ties
def segmentContigs(part):
    f = (note.Note,) # music21 class filter
    timespans = part.asTimespans(classList=f)
    maxOverlap = timespans.maximumOverlap()
    verticalities = list(timespans.iterateVerticalities())
    maxContigs = []
    contigs = []

    # make contigs instead of using verticalities
    ## step 1. put boundaries at places where the number of overlaps changes
    boundaries = set()
    i = 0
    while i < len(verticalities):
        refV = verticalities[i]
        boundaries.add(refV.offset)
        while i < len(verticalities) and (refV == verticalities[i] or len(verticalities[i].startAndOverlapTimespans) == len(refV.startAndOverlapTimespans)):
            i += 1
    ## step 2. look at notes overlapping boundaries, put another boundary at that note's start and end (where there aren't already boundaries)
    for o in boundaries.intersection(set(timespans.overlapTimePoints(includeStopPoints=True))):
        for e in timespans.elementsOverlappingOffset(o):
            if e.offset not in boundaries: 
                boundaries.add(e.offset)
            if e.endTime not in boundaries: 
                boundaries.add(e.endTime)
    bList = sorted(boundaries)
    ## populate contigs using boundaries as reference
    vi = 0
    bi = 1
    while vi < len(verticalities) and bi < len(bList):
        contigs.append([[], (bList[bi - 1], bList[bi])])
        while vi < len(verticalities) and bi < len(bList) and verticalities[vi].offset < bList[bi]:
            contigs[-1][0].append(verticalities[vi])
            vi += 1
        if not len(contigs[-1][0]):
            contigs.pop()
            bi += 1
            continue
        if len(contigs[-1][0][0].startAndOverlapTimespans) == maxOverlap:
            maxContigs.append(contigs[-1])
        bi += 1

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

# main algorithm
# TODO: generate new parts for each group
def separateVoices(part):
    (maxcontigs, contigs, partdict) = segmentContigs(part)
    # bfs (queue) initialized with maxcontigs 
    id = 0
    frontier = []
    for m in maxcontigs:
        groupFragments(m, "m", m)
        frontier.append((m, id, "m", m))
        id += 1
    crawlScore(frontier, contigs, id)

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

    return (part, partdict)

# parse through music21 score to use in algorithm (in-place)
    # grace notes are on the same offset as the note, this messes up the maximal contigs
# FIXME: Notation messed up for output4 (this has to do with how music21 imports the musicxml)
# TODO: recurse parts and clefs
# TODO: as well as segments the song structure (where melodies and voicing change)
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
    # remove grace notes
    graceNotes = []
    for n in song.recurse().notes:
        if n.duration.isGrace:
            graceNotes.append(n)
            n.activeSite.remove(n, shiftOffsets=True)
    


# set up the environment
if platform == 'win32':
    # Windows
    path = 'C:/Program Files/MuseScore 4/bin/Musescore4.exe' # (TODO: not hardcode the musicxml reader path?)
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
    preprocessScore(song)

    # run algorithm
    # TODO: run for each "part" (after updating preprocessScore)
    (reduced, partdict) = separateVoices(song)
    # color parts
    for n in reduced.recurse(classFilter=note.Note):
        if len(n.groups) and n.groups[0] in partdict:
            n.style.color = partdict[n.groups[0]]["color"]
            n.addLyric(n.groups)
        else: # unassigned notes
            print(n)

    # TODO: combine resulting parts into one score (later)

    # could also just show original score (object references intact)
    reduced.write("musicxml", argv[2] + '_reduced.musicxml')