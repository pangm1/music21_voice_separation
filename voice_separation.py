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
    # bfsItem is an item used in the frontier in crawlScore
def assignVoices(start, dest):
    toAssign = [] # notes of destination contig
    toConnect = [] # notes of start contig
    assignedPairs = [[],[]] # keep track of bin,group pairs already assigned
    # print([(n.pitch.nameWithOctave, n.groups) for n in start])
    # print("assigning to:", [(n.pitch.nameWithOctave, n.groups) for n in dest])

    # populate toAssign with target notes
        # visited notes (groups already assigned) should be excluded and registered in assignedPairs
    for n in dest:
        if not len(n.groups) and not n.id in start:
            toAssign.append([n, []])  
        elif len(n.groups):
            assignedPairs[0].append(n)
            assignedPairs[1].append(n.groups[0])
    if not len(toAssign):# whole contig visited already
        return
    # populate toConnect with reference notes
        # visited notes (groups already assigned) are excluded
    for n in start:
        if n.groups[0] not in assignedPairs[1]:
            toConnect.append(n)

    # naive assign first
        # all notes won't be assigned if reference verticality has less notes (not enough groups to assign)
    for a in toAssign:
        for c in toConnect:
            a[1].append((c.groups, distance(c, a[0])))
    # all permutations sorted by distance [(note, groups)]
    options = sorted([(a[0], g) for a in toAssign for g in a[1]], key=lambda t: t[1][1])

    # select options with lowest penalty
    for o in options:
        if o[0].id not in [a.id for a in assignedPairs[0]] and o[1][0] not in assignedPairs[1]:
            o[0].groups = o[1][0]
            assignedPairs[0].append(o[0])
            assignedPairs[1].append(o[1][0])
    # print([(n.pitch.nameWithOctave, n.groups) for n in start])
    # print([(n.pitch.nameWithOctave, n.groups) for n in dest])
    # print("finish")

# assign voices across fragments (in the notes' groups)
    #*** sorting order is important (notes with the same pitch and duration are considered equal even if they are different instances)
# TODO: experiment with sorting order (something to do with melody being high notes, or soprano and bass notes varying more)
def groupFragments(contig, dir):
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
            if n and n.id in [c.id for c in curr]:
                temp[i] = n
        e = (n for n in curr if n.id not in [p.id if p else None for p in prev])
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
    # print(f"grouping {len(contig[0])} fragments {startV.offset}<->{destV.offset} of length {len(startV.startAndOverlapTimespans)},{len(destV.startAndOverlapTimespans)}")
    # print("contig:", [(t.element.id, t.element.pitch.nameWithOctave, t.element.groups) for v in contig[0] for t in v.startAndOverlapTimespans])
    # print("fragments:", [(n.id, n.pitch.nameWithOctave, n.groups) for f in fragments for n in f])
    # make fragments non-empty and homogenous where there are groups
    for f in fragments:
        startN = None
        destN = None
        for n in f:
            # print(n.pitch.nameWithOctave)
            if n.id in [t.element.id for t in startV.startAndOverlapTimespans]: 
                startN = n
                # print("start", startN.id, startN.pitch.nameWithOctave)
            if n.id in [t.element.id for t in destV.startAndOverlapTimespans]: 
                destN = n
                # print("dest", destN.id, destN.pitch.nameWithOctave)
        if not startN or not destN: 
            print(startN, destN)
            # continue # this should not happen
        if startN and len(startN.groups): voice = startN.groups 
        if destN and len(destN.groups): voice = destN.groups 
        # print(f"assigning group {voice}: ({startN.id}, {startN.pitch})<->({destN.pitch}, {destN.id})")
        for n in f:
            n.groups = voice 
            # print(n.id, n.pitch, n.groups)
    # temp1 = [(n.pitch.nameWithOctave, n.groups) for f in fragments for n in f if len(n.groups)]
    # temp2 = [(n.pitch.nameWithOctave) for f in fragments for n in f if not len(n.groups)]
    # if len(temp): print("assigned notes:", temp1)
    # if len(temp): print("unassigned notes:", temp2)

# score bfs
    # assigns notes using helper function
    # frontier: [(contig, direction, ref)]
def crawlScore(frontier, contigs, partdict):
    while len(frontier):
        item = frontier.pop(0)
        leftIndex = contigs.index(item[0]) - 1
        rightIndex = contigs.index(item[0]) + 1
        if item[1] == "m": # both directions (maxcontigs)
            # print("m")
            if leftIndex >= 0:
                start = [t.element for t in item[0][0][0].startAndOverlapTimespans]
                assignVoices(start, [t.element for t in contigs[leftIndex][0][-1].startAndOverlapTimespans])
                groupFragments(contigs[leftIndex], "l")
                # update ref
                curr = [t.element for t in contigs[leftIndex][0][0].startAndOverlapTimespans]
                ref = [next(n for n in curr if n.groups[0] == s.groups[0]) if s.groups[0] in [n.groups[0] for n in curr] else s for s in start]
                frontier.append((contigs[leftIndex], "l", ref))
            if rightIndex < len(contigs):
                start = [t.element for t in item[0][0][-1].startAndOverlapTimespans]
                assignVoices(start, [t.element for t in contigs[rightIndex][0][0].startAndOverlapTimespans])
                groupFragments(contigs[rightIndex], "r")
                # update ref
                curr = [t.element for t in contigs[rightIndex][0][-1].startAndOverlapTimespans]
                # print("start", [(s.id, s.pitch.nameWithOctave, s.groups) for s in start])
                # print("curr", [(c.id, c.pitch.nameWithOctave, c.groups) for c in curr])
                ref = [next(n for n in curr if n.groups[0] == s.groups[0]) if s.groups[0] in [n.groups[0] for n in curr] else s for s in start]
                frontier.append((contigs[rightIndex], "r", ref))
        elif item[1] == "l": # go left
            if leftIndex >= 0:
                # print("l")
                # replace with ref
                assignVoices(ref, [t.element for t in contigs[leftIndex][0][-1].startAndOverlapTimespans])
                groupFragments(contigs[leftIndex], "l")
                # update ref
                curr = [t.element for t in contigs[leftIndex][0][0].startAndOverlapTimespans]
                ref = [next(n for n in curr if n.groups[0] == s.groups[0]) if s.groups[0] in [n.groups[0] for n in curr] else s for s in ref]
                frontier.append((contigs[leftIndex], "l", ref))
        elif item[1] == "r": # go right
            if rightIndex < len(contigs):
                # print("r")
                # replace with ref
                assignVoices(ref, [t.element for t in contigs[rightIndex][0][0].startAndOverlapTimespans])
                groupFragments(contigs[rightIndex], "r")
                # update ref
                curr = [t.element for t in contigs[rightIndex][0][-1].startAndOverlapTimespans]
                ref = [next(n for n in curr if n.groups[0] == s.groups[0]) if s.groups[0] in [n.groups[0] for n in curr] else s for s in ref]
                frontier.append((contigs[rightIndex], "r", ref))   
    
# given a part/score return 
    # contigs  [[verticalities], (startBoundary, endBoundary)]
    # maximal contigs (contigs having maximal overlap)
    # dictionary of voices (which will be separated into parts)
# TODO: recognize rests
# TODO: figure out how to recognize ties
def segmentContigs(part):
    f = (note.Note,) # music21 class filter
    timespans = part.asTimespans(classList=f)
    verticalities = list(timespans.iterateVerticalities())
    maxOverlap = timespans.maximumOverlap()
    maxContigs = []
    contigs = []
    boundaries = set()
    partdict = {}

    # make contigs instead of using verticalities
    ## step 1. put boundaries at places where the number of overlaps changes
    i = 0
    while i < len(verticalities):
        refV = verticalities[i]
        boundaries.add(refV.offset)
        while i < len(verticalities) and (refV == verticalities[i] or len(verticalities[i].startAndOverlapTimespans) == len(refV.startAndOverlapTimespans)):
            i += 1
    boundaries.add(timespans.endTime)
    ## step 2. look at notes overlapping boundaries, put another boundary at that note's start and end (where there aren't already boundaries)
    for o in boundaries.intersection(set(timespans.overlapTimePoints(includeStopPoints=True))):
        for e in timespans.elementsOverlappingOffset(o):
            boundaries.add(e.offset)
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
    for i in range(maxOverlap):
        partdict[str(i)] = {"stream": stream.Part(), "color": ""}
        newcolor = ''
        while (True):
            newcolor = f"#{''.join(random.choices(string.hexdigits, k=6))}"
            if newcolor not in [k["color"] for k in partdict.values()]:
                break
        partdict[str(i)]["color"] = newcolor

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

    return (maxContigs, contigs, partdict)

# main algorithm
# TODO: generate new parts for each group
def separateVoices(part):
    (maxcontigs, contigs, partdict) = segmentContigs(part)
    # bfs (queue) initialized with maxcontigs 
    frontier = []
    for m in maxcontigs:
        groupFragments(m, "m")
        frontier.append((m, "m", m))
    crawlScore(frontier, contigs, partdict)

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