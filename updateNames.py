"""

    This script copies and collects some data from the GlyphNameFormatter.
    https://github.com/LettError/glyphNameFormatter

    Note: don't run from RoboFont, as it will find the embedded GlyphNameFormatter,
    and it really needs to look at the repository.


"""

import pprint
import os, shutil, time
import glyphNameFormatter

gnfRoot = os.path.dirname(glyphNameFormatter.__file__)
browserRoot = os.path.join(os.getcwd(), "lib")

# copy the latest name list
srcNamePath = os.path.join(gnfRoot, "names", "glyphNamesToUnicodeAndCategories_experimental.txt")
if os.path.exists(srcNamePath):
    dstNamePth = os.path.join(browserRoot, "data", "glyphNamesToUnicode.txt")
    print("srcNamePath", srcNamePath)
    print("dstNamePth", dstNamePth)
    shutil.copyfile(srcNamePath, dstNamePth)

# copy the joining types
srcJoiningTypesPath = os.path.join(gnfRoot, "data", "joiningTypes.txt")
if os.path.exists(srcJoiningTypesPath):
    dstJoiningTypesPath = os.path.join(browserRoot, "data", "joiningTypes.txt")
    print("srcJoiningTypesPath", srcJoiningTypesPath)
    print("dstJoiningTypesPath", dstJoiningTypesPath)
shutil.copyfile(srcJoiningTypesPath, dstJoiningTypesPath)


# make a range name table
from glyphNameFormatter.unicodeRangeNames import getAllRangeNames, getRangeByName

ranges = {}

for rangeName in getAllRangeNames():
    r = getRangeByName(rangeName)
    if r is None:
        print("unknown range name", rangeName)
        continue
    start, end = r
    ranges[(start,end)] = rangeName

pyText = []
pyText.append(u"# -*- coding: UTF-8 -*-")
pyText.append(u"# Generated from glyphNameFormatter range names")
pyText.append(u"# Generated on %s" % time.strftime("%Y %m %d %H:%M:%S"))
pyText.append(u"unicodeRangeNames =" + pprint.pformat(ranges, indent=4))

pyPath = os.path.join(browserRoot, "unicodeRanges.py")
print("pyPath", pyPath)
f = open(pyPath, 'w')
f.write("\n".join(pyText))
f.close()


