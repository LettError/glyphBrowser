# -*- coding: UTF-8 -*-
import os
import objc
import AppKit
import unicodeRangeNames
import traceback

import mojo
from mojo.roboFont import version
import mojo.UI
from imageMapImageCell import ImageMapImageCell

if version >= "3.0":
    from importlib import reload
reload(unicodeRangeNames)


from glyphNameFormatter.reader import *
from pprint import pprint

from fontTools.misc.py23 import unichr

from AppKit import NSFont, NSFocusRingTypeNone, NSPredicate
from mojo.UI import CurrentFontWindow, SmartSet
from mojo.events import publishEvent

import webbrowser

try:
    # in py3
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import unicodeRangeNames
from defconAppKit.windows.baseWindow import BaseWindowController

from unicodeRangeNames import getRangeName, getRangeAndName, getPlaneName
import unicodedata
import vanilla

from AppKit import NSPasteboardTypeString, NSPasteboard

from mojo.roboFont import version

"""

    Browser for unicode categories, unicode ranges and glyphlists
    as defined in the Adobe AGD list.
    Goal: make a window similar to OSX Character Viewer but with a button
    that will add the selected glyphs to the current font with the appopriate
    names and unicode values.

    - Offer the selected glyphs as unicode text.
    - Offer the selected glyphs in glyphname syntax.
    - Add the selected names as new glyphs if they don't already exist.
    - options:
        - checkbox for overwriting existing glyphs
        - select mark color

"""

from random import choice
glyphNameBrowserNames = [
    '\u2714\ufe0e\u0262\u029f\u028f\u1d18\u029c\u0299\u0280\u1d0f\u1d21s\u1d07\u0280',
    '\u2714\ufe0eGLYPHBROWSER',
    '\u2714GlyphBrowser',
]

unicodeCategoryNames = {
        "Ps": "Punctuation, open",
        "Pe": "Punctuation, close",
        "Nl": "Number, letter",
        "No": "Number, other",
        "Lo": "Letter, other",
        "Ll": "Letter, lowercase",
        "Lm": "Letter, modifier",
        "Nd": "Number, decimal digit",
        "Pc": "Punctuation, connector",
        "Lt": "Letter, titlecase",
        "Lu": "Letter, uppercase",
        "Pf": "Punctuation, final quote",
        "Pd": "Punctuation, dash",
        "Pi": "Punctuation, initial quote",
        "Po": "Punctuation, other",
        "Me": "Mark, enclosing",
        "Mc": "Mark, spacing combining",
        "Mn": "Mark, nonspacing",
        "Sk": "Symbol, modifier",
        "So": "Symbol, other",
        "Sm": "Symbol, math",
        "Sc": "Symbol, currency",
        "Co": "Other, private use",
        "Cn": "Other, not assigned",
        "Cc": "Other, control",
        "Cf": "Other, format",
        "Zs": "Separator, space",
    }

# some fontlab names from .enc files that these lists have no value for
# but we know what they are, so let's assign these values.
fontLabNames = {
	"CR" : 0x0D	,
	"DC1": 0x11	,
	"DC2": 0x12	,
	"DC3": 0x13	,
	"DC4": 0x14	,
	"DEL": 0x7F	,
	"DLE": 0x10	,
	"HT" : 0x09	,
	"LF" : 0x10	,
	"NUL": 0x1E	,
	"RS" : 0x1E	,
	"US" : 0x1F	,
	"apple": 0xF8FF	,
	"Apple": 0xF8FF	,
	"florin": 0x0192	,
	"guillemotleft": 0x00AB	,
	"guillemotright": 0x00BB	,
	"uni00A0": 0x00A0	,
	'uni03C2': 0x03C2,

}


import time
from fontTools.ttLib import TTFont, TTLibError

genericListPboardType = "genericListPboardType"

glyphBrowserBundle = mojo.extensions.ExtensionBundle("GlyphBrowser")

def makeNSImage(path):
    return AppKit.NSImage.alloc().initWithContentsOfFile_(path)

_joiningTypeImage_C = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_C.pdf"))
_joiningTypeImage_D = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_D.pdf"))
_joiningTypeImage_L = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_L.pdf"))
_joiningTypeImage_R = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_R.pdf"))
_joiningTypeImage_U = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_U.pdf"))
_joiningTypeImage_T = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_U.pdf"))
_joiningTypeImage_none = makeNSImage(os.path.join(glyphBrowserBundle.resourcesPath(), "joiningtype_none.pdf"))

joiningTypesimageMap = dict(
    C=_joiningTypeImage_C,
    D=_joiningTypeImage_D,
    L=_joiningTypeImage_L,
    R=_joiningTypeImage_R,
    #U=_joiningTypeImage_U,
    #T=_joiningTypeImage_T,
    X=_joiningTypeImage_none,
)

def extractUnicodesFromEncodingFile(path):
    # read glyphnames from encoding file
    # match them with a unicode from our list
    #print("extractUnicodesFromEncodingFile", path)
    values = []
    f = open(path, 'r')
    data = f.read()
    f.close()
    l = []
    for line in data.split("\n"):
        if len(line) == 0:
            continue
        if line[0] == "%":
            continue
        if "%" in line:
            line = line.split('%')[0]
            line = line.strip()
        if " " in line:
            # it contains an index
            line = line.split(" ")[0]
            line = line.strip()
        if "\t" in line:
            # it contains an index
            line = line.split("\t")[0]
            line = line.strip()
        uni = n2u(line)
        if uni is not None:
            values.append(uni)
        elif line in fontLabNames:
            values.append(fontLabNames.get(line))
        else:
            print("GlyphBrowser: ENC importer: can't find a value for %s" % line)
    return values
    
def extractUnicodesFromUFO(path):
    f = RFont(path, showInterface=False)
    values = []
    for g in f:
        for u in g.unicodes:
            values.append(u)
    f.close()
    return values
    
def extractUnicodesFromOpenType(pathOrFile):
    source = TTFont(pathOrFile)
    cmap = source["cmap"]
    preferred = [
        (3, 10, 12),
        (3, 10, 4),
        (3, 1, 12),
        (3, 1, 4),
        (0, 3, 12),
        (0, 3, 4),
        (3, 0, 12),
        (3, 0, 4),
        (1, 0, 12),
        (1, 0, 4)
    ]
    found = {}
    for table in cmap.tables:
        found[table.platformID, table.platEncID, table.format] = table
        table = None
    for key in preferred:
        if key not in found:
            continue
        table = found[key]
        break
    reversedMapping = {}
    if table is not None:
        for uniValue, glyphName in table.cmap.items():
            reversedMapping[glyphName] = uniValue
    return reversedMapping
    
def unicodeToChar(uni):
    import struct
    if uni < 0xFFFF:
        return unichr(uni)
    else:
        return struct.pack('i', uni).decode('utf-32')

class AddGlyphsSheet(BaseWindowController):
    _title = "Add Glyphs"

    def __init__(self,
            theseGlyphs,
            parentWindow,
            cancelCallback,
            applyCallback,
            targetFonts = None
            ):
        self.theseGlyphs = theseGlyphs    # list of these unicode glyph objects
        self.targetFonts = targetFonts
        self.cancelCallback = cancelCallback
        self.applyCallback = applyCallback
        self.buildBaseWindow(parentWindow)
        self.makeFinalNamesList()

    def callbackCancelButton(self, sender):
        """ """
        if self.cancelCallback:
            self.cancelCallback(None)
        self.close()

    def makeFinalNamesList(self):
        # fill the list with the names we're going to add
        # nothing to edit here
        names = []
        for glyph in self.theseGlyphs:
            variantNames = glyph.getAllNames()
            for vn in variantNames:
                nameItem = {}
                vu = n2u(vn)
                if vu is not None:
                    nameItem['value'] = hex(vu)
                else:
                    nameItem['value'] = ''
                nameItem['name'] = vn
                nameItem['string'] = glyph.unicodeString
                names.append(nameItem)
        self.w.proposedNames.set(names)
        text = ""
        if len(self.theseGlyphs) > 1:
            text = "Add %d unicodes, %d glyphnames" % (len(self.theseGlyphs), len(names))
        else:
            text = "Add this unicode"
        if self.targetFonts is not None:
            text += f" to {len(self.targetFonts)} UFOs"
        text += ":"
        self.w.namesCaption.set(text)

    def callbackApplyAddGlyphsToTargetFont(self, sender=None):
        # see if the current data is any different from the original data

        self.w.markGlyphsCheck, self.w.selectGlyphsCheck
        selection = []
        newGlyphs = {}
        
        targetFonts = []
        if self.targetFonts is not None:
            targetFonts = self.targetFonts
        for font in targetFonts:
            for glyph in self.theseGlyphs:
                variantNames = glyph.getAllNames()
                for variantName in variantNames:
                    if variantName in font:
                        continue
                    if not variantName in font:
                        font.newGlyph(variantName)
                    g = font[variantName]
                    g.width = 500    # default Width
                    if variantName == variantNames[0]:
                        g.unicode = glyph.uni
                    #print("variant unicode", variantName, n2u(variantName))
                    newGlyphs[g.name] = g.unicode
                    if self.w.markGlyphsCheck.get():
                        if version >= "3.0":
                            # RF 3.0
                            g.markColor = (0, 0.95, 0.95, .25)
                        else:
                            # RF 1.8.x
                            g.mark = (0, 0.95, 0.95, .25)
                    selection.append(variantName)
        if self.w.selectGlyphsCheck.get():
            for font in self.targetFonts:
                font.selection = selection
        if self.applyCallback:
            self.applyCallback(None)
        if selection:
            for font in self.targetFonts:
                publishEvent("glyphbrowser.newGlyphs", newGlyphs=newGlyphs, font=font)
        self.close()

    def _breakCycles(self):
        self.cancelCallback = None
        self.applyCallback = None
        self._fonts = None

    def close(self):
        self._breakCycles()
        self.w.close()

    def buildBaseWindow(self, parentWindow):
        """ Make the base window. """
        self._dirty = False
        self._sheetWidth = 400
        self._sheetHeight = 500
        if parentWindow is None:
            self.w = vanilla.Window((self._sheetWidth, self._sheetHeight),
                title = self._title,
                closable=False,
                miniaturizable=False,
                minSize=(self._sheetWidth, self._sheetHeight),
                textured=False)
        else:
            self.w = vanilla.Sheet((self._sheetWidth, self._sheetHeight),
                parentWindow,
                minSize=(self._sheetWidth, self._sheetHeight),
            )
        # cancel button
        self.w.cancelButton = vanilla.Button((-205, -30, 100, 20),
            'Cancel',
            callback=self.callbackCancelButton,
            sizeStyle='small')
        self.w.cancelButton.bind(".", ["command"])
        self.w.cancelButton.bind(unichr(27), [])
        # ok button
        self.w.applyButton = vanilla.Button((-100, -30, -10, 20),
            'Add Glyphs',
            callback=self.callbackApplyAddGlyphsToTargetFont,
            sizeStyle='small')
        self.w.setDefaultButton(self.w.applyButton)

        # get the specialised stuff in
        self.fillSheet()
        self.setUpBaseWindowBehavior()
        #self.refresh()
        self.w.open()

    def fillSheet(self):
        self.w.namesCaption = vanilla.TextBox((5, 10, -10, 20), "Add these glyphs")
        self.w.markGlyphsCheck = vanilla.CheckBox((5, 40, 150, 20), "Mark new glyphs", value=True)
        self.w.selectGlyphsCheck = vanilla.CheckBox((5, 60, 150, 20), "Select new glyphs", value=True)
        cD = [
                {    'title': u"Unicode",
                     'key': 'value',
                     'width': 80},
                {    'title': u"Char",
                     'key': 'string',
                     'width': 60},
                {    'title': u"GNUFL Name",
                     'key': 'name',
                     'width': 200},
            ]
        self.w.proposedNames = vanilla.List((0, 90, 0, -50), [], columnDescriptions=cD)


class SimpleGlyphName(object):

    def __init__(self, name, srcPath):
        self.name = name
        self.srcPath = srcPath    # the filename of the document this data come from
        self.error = False
        self.uni = None # The Unicode
        self.fin = None # The final name
        self.ali = [] # list of name aliases
        self.sub = [] # list of substitutions
        self.set = [] # list of glyph set IDs
        self.min = None # minuscule
        self.maj = None # majuscule
        self.cmp = None # components used to create this composite glyph
        self.typ = None    # BE tag
        self.con = None    # BE tag, connection
        self.lan = None    # BE tag, language
        self.jT = None
        self.other = {} # Hash of any unknown tags
        self.unicodeRange = None
        self.unicodeRangeName = None
        self.unicodeCategory = None
        self.unicodeCategoryName = None
        self.unicodeString = ""
        self.unicodeName = None

    def __cmp__(self, other):
        if self.uni is None or other.uni is None:
            return 0
        if self.uni > other.uni:
            return 1
        elif self.uni< other.uni:
            return -1
        else:
            return 0

    def getAllNames(self):
        # based on the category data, give suggestion for which extensions we need for any unicode
        extensions = {
            # XXXX no idea if it works this way...
            #   D Dual_Joining
            # 		&----G----&
            'D': ['init', 'medi', 'fina'],
            #   C Join_Causing
            # 		&----G----&		????
            'C': [         					   ],
            #   R Right_Joining
            # 		   x G----&
            'R': [ 				 'fina'],
            #   L Left_Joining
            # 		&----G x
            'L': ['init',		 'fina'],
            #   U Non_Joining
            # 	       x G x
            'U': [         					   ],
            #   T Transparent
            # 	       x G x
            'T': [         					   ],
        }

        if self.joiningType is not None:
            variants = [self.name]
            ext = extensions.get(self.joiningType)
            if ext:
                for e in ext:
                    variants.append("%s.%s"%(self.name, e))
                return variants
        return [self.name]

    def uniString(self):
        # return a unicode string with this character, if possible
        return self.unicodeString

    def asU(self):
        return "U+%04X"%(self.uni)

    def asDict(self, fontUnicodes, fontNames, joiningTypes):
        d = {}
        d['name'] = self.name
        d['uni'] = self.uni
        if self.joiningType is None:
            d['joiningType'] = 'X'
        else:
            d['joiningType'] = self.joiningType
        d['unicodeinfont'] = ''
        d['nameinfont'] = ''
        if self.uni in fontUnicodes:
            d['unicodeinfont'] += '•'
            #d['unicodeinfont'] += 'F'
        if self.name in fontNames:
            d['nameinfont'] += '•'
            #d['nameinfont'] += 'U'
        d['string'] = self.unicodeString
        d['category'] = self.unicodeCategory
        if self.uni is not None:
            d['uniHex'] = "%05X"%self.uni
        else:
            d['uniHex'] = ""
        d["parts"] = ""
        if self.cmp is not None:
            if len(self.cmp)>0:
                d["parts"] = self.cmp[0]
        if self.fin is not None:
            d['final'] = self.fin
        else:
            d['final'] = ""
        if self.unicodeName is not None:
            d['uniName'] = self.unicodeName
        else:
            d['uniName'] = ""
        return d

    def __repr__(self):
        if self.uni is not None:
            u = "%05x"%self.uni
        else:
            u = "-"
        if self.unicodeCategory is not None:
            cat = self.unicodeCategory
        else:
            cat = "-"
        if self.unicodeRangeName is not None:
            r = self.unicodeRangeName
        else:
            r = "-"
        return "[Glyph: %s %s %s %s]"%(self.name, u, cat, r)

    def lookupRefs(self):
        # find out more things based on the unicode
        if self.uni is None: return
        # category
        try:
            c = unicodeToChar(self.uni)
            self.unicodeString = c
        except ValueError:
            self.error = True
        try:
            self.unicodeName = unicodedata.name(c ).lower()
        except ValueError:
            pass
        self.unicodeCategoryName = unicodeCategoryNames.get(self.unicodeCategory)
        self.unicodeRange, self.unicodeRangeName = getRangeAndName(self.uni)

    def sameRange(self, value):
        if self.unicodeRange is None: return
        if self.unicodeRange[0]<=value<=self.unicodeRange[1]:
            return True
        return False

    def getCategories(self):
        # return a list of all names, tags, strings that could serve as selection criteria
        allCats = []
        if self.srcPath:
            allCats.append("\U0001f4e6\t%s"%self.srcPath)
        if self.error:
            allCats.append("\u26a0\ufe0f\tError")
        if self.uni is None:
            allCats.append("⋯\tNo unicode")
        if self.unicodeRangeName is not None:
            a, b = self.unicodeRange
            allCats.append("%05X\t%05X\t%s"%(a, b, self.unicodeRangeName))
        if self.unicodeCategoryName is not None:
            allCats.append("\U0001f4c1\t"+ self.unicodeCategoryName)
        if self.uni is not None:
            allCats.append("\U0001f523\t"+ getPlaneName(self.uni))
        for s in self.set:
            allCats.append("XX\t"+s)
        if "_" in self.name:
            allCats.append("f_f_l\tCombined glyphs")
        if u"." in self.name and self.name[0]!=u".":
            # catch glyph names with extensions, but not .notdef
            extension = self.name.split(".")[-1]
            allCats.append(u"\U0001f3f7\t."+extension)
        return allCats

    def matchCategory(self, catName):
        if self.unicodeCategoryName is not None:
            if catName.lower() in self.unicodeCategoryName.lower():
                return True
        if self.unicodeCategory is not None:
            if catName.lower() in self.unicodeCategory.lower():
                return True
        return False

    def match(self, anything):
        # return True if we match any part of this string
        if anything.lower() in self.name.lower():
            return True
        if self.unicodeCategoryName is not None:
            if anything in self.unicodeCategoryName:
                return True
        if self.unicodeRangeName is not None:
            if anything.lower() in self.unicodeRangeName.lower():
                return True
        if self.unicodeCategory is not None:
            if anything.lower() in self.unicodeCategory.lower():
                return True
        if self.unicodeName is not None:
            if anything.lower() in self.unicodeName.lower():
                return True
        if self.unicodeString is not None:
            if anything.lower() in self.unicodeString.lower():
                return True
        if self.uni is not None:
            # search hex values
            if anything.lower()[:2] == "0x":
                val = anything.lower()[2:]
            else:
                val = anything.lower()
            while True:
                if val[0] == "0":
                    val = val[1:]
                else:
                    break
            if val in hex(self.uni):
                return True
        for s in self.set:
            if anything in s:
                return True
        return False

    def update(self, other):
        # update this record with values from the other
        # so we can change everything but the name
        if other.uni is not None:
            self.uni = other.uni
            self.lookupRefs()
        if other.joiningType is not None:
            self.joiningType = other.joiningType
        if other.name is not None:
            self.name = other.name
        if other.sub:
            self.sub = other.sub
        if other.set:
            self.set = other.set
        if other.fin is not None:
            self.fin = other.fin
        if other.min is not None:
            self.min = other.min
        if other.maj is not None:
            self.maj = other.maj
        if other.cmp is not None:
            self.cmp = other.cmp



class GlyphDict(dict):
    uniMap = {}
    def getUniMap(self):
        um = {}
        for name, glyph in self.items():
            if glyph.uni is not None:
                um[glyph.uni] = glyph.name
        self.uniMap = um
        return self.uniMap

    def findMissingUnicodes(self):
        self.getUniMap()
        uniNames = {}
        maxUni = max(self.uniMap.keys())
        allUni = set(range(1, 0xffff))
        missing = set(allUni)-set(self.uniMap.keys())
        for v in list(missing):
            c = unicodeToChar(v)
            try:
                name = unicodedata.name(c)
                uniNames[name] = v
            except ValueError:
                continue
        for name, value in uniNames.items():
            g = SimpleGlyphName(name, None)
            g.uni = value
            self[name] = g

    def update(self, record):
        # find a record
        #     - with the same name
        #     - with the same unicode
        # then update the parts
        # option 1: same name, different values
        added = False
        if record.name in self:
            # a record exists with the same name
            # update the unicode, other values
            other = self[record.name]
            other.update(record)
            if record.uni is not None:
                if record.uni in self.uniMap:
                    del self.uniMap[record.uni]
                self.uniMap[record.uni] = record.name
            return
        # option 2: same unicode, different values, name
        elif record.uni is not None:
            if record.uni in self.uniMap:
                name = self.uniMap[record.uni]
                glyph = self[name]
                oldName = glyph.name
                glyph.update(record)
                self[record.name] = glyph
                del self[oldName]
                added = True
                self.uniMap[record.uni] = record.name
            if added:
                return
        # option 3: just new glyph
        self.uniMap[record.uni] = record.name
        self[record.name] = record

def readJoiningTypes(path):
    # read the joiningTypes.txt
    joiningTypes = {}
    f = open(path, 'r')
    d = f.read()
    f.close()
    lines = d.split("\n")
    for l in lines:
        if not l: continue
        if l[0] == "#": continue
        parts = l.split("\t")
        uni = int('0x'+parts[0], 0)
        jT = parts[1]
        joiningTypes[uni] = jT
    return joiningTypes

def readUniNames(path, glyphDictionary=None, joiningTypes=None):
    if glyphDictionary is None:
        glyphDictionary = GlyphDict()
    f = open(path, 'r')
    d = f.read()
    f.close()
    lines = d.split("\n")
    niceFileName = os.path.basename(path)
    versionString = "-"
    unicodeVersionString = "-"
    for l in lines:
        if l[0] == "#":
            if l.find("GlyphNameFormatter version")!=-1:
                versionString = l[1:].strip()
                versionString = versionString.replace("GlyphNameFormatter version", "GNFUL")
            elif l.find("Unicode version:")!=-1:
                unicodeVersionString = l[l.find(":")+1:].strip()
            continue
        if len(l.split(" ")) != 3:
            continue
        name, hexCandidate, unicodeCategory = l.split(" ")
        try:
            hexCandidate = int("0x"+hexCandidate, 16)
        except ValueError:
            print("bah unicode %s %s" % (hexCandidate, name))
            continue
        entryObject = SimpleGlyphName(name, niceFileName)
        entryObject.uni = hexCandidate
        entryObject.unicodeCategory = unicodeCategory
        if joiningTypes is not None:
            entryObject.joiningType = joiningTypes.get(hexCandidate)
        glyphDictionary.update(entryObject)
    for name, glyph in glyphDictionary.items():
        glyph.lookupRefs()
    return unicodeVersionString, versionString, glyphDictionary

def findText(data, text):
    # find the names for this text
    results = []
    need = [ord(c) for c in text]
    for name, glyph in data.items():
        if glyph.uni in need:
            results.append(glyph)
    return sortByUnicode(results)

def findCategory(data, category):
    results = []
    for name, glyph in data.items():
        if glyph.matchCategory(category):
            results.append(glyph)
    return sortByUnicode(results)

def findSameRange(data, value):
    results = []
    for name, glyph in data.items():
        if glyph.sameRange(value):
            results.append(glyph)
    return sortByUnicode(results)

def findGlyphs(data, searchString):
    results = []
    for name, glyph in data.items():
        if glyph.match(anything=searchString):
            results.append(glyph)
    return sortByUnicode(results)

def collectSearchCategories(data):
    # collect all the things we can search by
    allCategories = {}
    for name, glyph in data.items():
        for cat in glyph.getCategories():
            if not cat in allCategories:
                allCategories[cat] = []
            allCategories[cat].append(glyph)
    return allCategories

def sortByUnicode(items, ascending=True):
    sortedItems = {}
    for i in items:
        if i.uni not in sortedItems:
            sortedItems[i.uni] = []
        sortedItems[i.uni].append(i)
    k = sorted(sortedItems.keys())
    sortedList = []
    for i in k:
        for j in sorted(sortedItems[i]):
            sortedList.append(j)
    return sortedList

class Browser(object):

    # this looks like a reasonable unicode reference database.
    # but it could by any other.
    lookupURL = "http://unicode.scarfboy.com/?"
    acceptedExtensionsForDrop = ['.otf', '.ttf', '.ufo', ".enc", ".ENC"]

    def __init__(self, data, unicodeVersionString, versionString, joiningTypes=None):
        self.data = data
        self.dataByCategory = collectSearchCategories(data)
        if joiningTypes is None:
            self.joiningTypes = {}
        else:
            self.joiningTypes = joiningTypes
        self.catNames = sorted(self.dataByCategory.keys())
        self.currentSelection = []
        self._typing = False
        self.unicodeVersion = unicodeVersionString
        
        
        topRow = 80
        catWidth = 320

        self.w = vanilla.Window((1200, 500), 
            ("GlyphBrowser with %s and %s"%(self.unicodeVersion, versionString)), 
            minSize=(800, 500),
            autosaveName = "com.letterror.glyphBrowser.mainWindow",
            )
        columnDescriptions = [
            {    'title': u"",
                 'key': 'col1',
                 'width': 50},
            {    'title': u"",
                 'key': 'col2',
                 'width': 50},
            {    'title': "Categories, ranges, namelists",
                    'key': 'name'},
        ]
        self.w.catNames = vanilla.List((5, topRow, catWidth, -5), [],
            columnDescriptions=columnDescriptions,
            selectionCallback=self.callbackCatNameSelect)
        charWidth = 18
        imageCell = ImageMapImageCell.alloc().init()
        imageCell.setImages(joiningTypesimageMap)
        columnDescriptions = [
            {    'title': u"❡",
                 'key': 'nameinfont',
                 'width': charWidth,
                 },
            {    'title': "#",
                 'key': 'unicodeinfont',
                 'width': charWidth,
                 },

            {    'title': "GNUFL name",
                 'key': 'name',
                 'width': 200, },
            {    'title': "Unicode",
                 'key': 'uniHex',
                 'width': 50},
            {    'title': "Cat",
                 'key': 'category',
                 'width': 30},
            {    'title': "jT",
                 'key': 'joiningType',
                 'width': 50,
                 'cell':imageCell
                 },
            {    'title': "Char",
                 'key': 'string',
                 'width': 30},
            {    'title': "Unicode Description",
                 'key': 'uniName',
                     },
            ]
        self.w.searchBox = vanilla.SearchBox((-200, topRow, -5, 22), "", callback=self.callbackSearch)


        dropSettings = {
            'type': AppKit.NSFilenamesPboardType,
            'callback': self.callbackDropOnLocationList,
            'allowDropBetweenRows': False
        }
        if version >= "3.2":
            self.w.selectedNames = vanilla.List(
                (catWidth+10, topRow, -205, -5),
                [],
                columnDescriptions=columnDescriptions,
                selectionCallback=self.callbackGlyphNameSelect,
                otherApplicationDropSettings=dropSettings,
                menuCallback = self.namesMenu_buildMenu,
            )
        else:
            self.w.selectedNames = vanilla.List(
                (catWidth+10, topRow, -205, -5),
                [],
                columnDescriptions=columnDescriptions,
                selectionCallback=self.callbackGlyphNameSelect,
                otherApplicationDropSettings=dropSettings,
            )
        self.w.selectionUnicodeText = vanilla.EditText((0, 0, -0, topRow-5), placeholder=choice(glyphNameBrowserNames), callback=self.callbackEditUnicodeText)
        s = self.w.selectionUnicodeText.getNSTextField()
        s.setFocusRingType_(NSFocusRingTypeNone)

        self.w.selectionGlyphNames = vanilla.EditText((-200, topRow+28, -5, -300), "Selectable Glyph Names", sizeStyle="small")
        self.checkSampleSize()
        self.w.addGlyphPanelButton = vanilla.Button((-200, -65, -5, 20), "Add to Font", callback=self.callbackOpenGlyphSheet)
        self.w.toSpaceCenter = vanilla.Button((-200, -115, -5, 20), "To Spacecenter", callback = self.toSpaceCenter)
        self.w.lookupSelected = vanilla.Button((-200, -90, -5, 20), "Lookup", callback=self.callbackLookup)
        self.w.progress = vanilla.TextBox((-190, -35, -10, 40), "", sizeStyle="small")
        self.w.bind("became main", self.callbackWindowMain)
        self.w.setDefaultButton(self.w.addGlyphPanelButton)

        self.w.addGlyphPanelButton.enable(False)
        self.w.toSpaceCenter.enable(False)
        self.update()
        self.w.bind("close", self.windowClosing)
        self.w.open()
        self.w.catNames.setSelection([0])
    
    def namesMenu_buildMenu(self, sender):
        try:
            items = []
            sel  = sender.getSelection()
            allNames = []
            for nameObj in self.currentSelection:
                allNames += nameObj.getAllNames() 
            if len(sel) == 1 and len(self.currentSelection)>=1:
                nameObj = self.currentSelection[0]
                allNames += nameObj.getAllNames() 
                thisName = nameObj.getAllNames()[0]
                items.append(dict(title=f"Edit {thisName}"))
                items.append(dict(title=f"Lookup {nameObj.asU()}", callback = self.callbackLookup))
                items.append("----")
                fontTitle = "Add 1 glyph to Font"
            else:
                fontTitle = f"Add {len(allNames):d} new glyphs to Font"
            copySubMenu = []
            copySubMenu.append(dict(title="Copy as Unicode Text", callback = self.menuCallbackCopyUnicodeText))
            copySubMenu.append(dict(title="Copy as Slashed Names", callback = self.menuCallbackCopySlash))
            copySubMenu.append(dict(title="Copy as Comma Separated Strings", callback = self.menuCallbackCopyStrings))
            copySubMenu.append(dict(title="Copy as Space Separated Names", callback = self.menuCallbackCopyNames))
            copySubMenu.append(dict(title="Copy as Hex Unicode", callback = self.menuCallbackCopyHexUnicode))
            copySubMenu.append(dict(title="Copy as Escaped Unicode String", callback = self.menuCallbackCopyEscapedUnicode))
            copySubMenu.append(dict(title="Copy as Feature Group", callback = self.menuCallbackCopyFeature))

            items.append(dict(title="Copy Names", items=copySubMenu))
            items.append("----")
            fontSubMenu = []
            allPaths = []
            for f in AllFonts():
                if f.path is not None:
                    path = f.path
                else:
                    path = "Unsaved UFO"
                fontSubMenu.append(dict(title=os.path.basename(path), callback=self.menuCallbackCopyToUFO, tag="one"))
            fontSubMenu.append("----")
            fontSubMenu.append(dict(title="All", callback=self.menuCallbackCopyToUFO, tag="all"))
            items.append(dict(title=fontTitle, items=fontSubMenu))
            #items.append(dict(title="Add to Font"))
            items.append(dict(title="Show in Spacecenter"))
            # for nameObj in self.currentSelection:
            #     names = nameObj.getAllNames()
            #     for n in names:
            #         items.append(dict(title="Add %s" % n))
        except:
            print("Error making Menu", traceback.format_exc())
        return items
        
    def callbackDropOnLocationList(self, sender, dropInfo):
        #   handle files droppings on the list
        #       this is how the drop info comes in
        #        {   'rowIndex': 6,
        #            'source': None,
        #            'data': (
        #                "/Users/erik/Develop/Tal/LiveInterpol.py",
        #                "/Users/erik/Develop/Tal/magic sort 1.py"
        #                ),
        #            'dropOnRow': False,
        #            'isProposal': False
        #        }
        
        # are we offered ,ufo files?
        acceptedPaths = {}
        values = []
        for path in dropInfo['data']:
            ext = os.path.splitext(path)[-1].lower()
            if ext in self.acceptedExtensionsForDrop:
                if not ext in acceptedPaths:
                    acceptedPaths[ext] = []
                acceptedPaths[ext].append(path)
        if acceptedPaths:
            if dropInfo['isProposal']:
                # self.logger.info("callbackDropOnLocationList proposal %s", path)
                # this is a proposal, we like the offer
                return True
            else:
                for ext, paths in acceptedPaths.items():
                    if ext in [".otf", '.ttf']:
                        for p in paths:
                            values += extractUnicodesFromOpenType(p).values()
                    elif ext in ['.enc']:
                        for p in paths:
                            values += extractUnicodesFromEncodingFile(p)
                    elif ext in ['.ufo']:
                        for p in paths:
                            values += extractUnicodesFromUFO(p)
                values = list(set(values))
                values = sorted(values)
                self.callbackSetUnicodesFromBinary(values)
                return True
            return False
        else:
            # nothing to accept
            return False

    def checkSampleSize(self):
        text = self.w.selectionUnicodeText.get()
        minFontSize = 20
        maxFontSize = 50
        charsForLarge = 35
        charsForSmall = 50

        if len(text) < charsForLarge:
            fontSize = maxFontSize
        elif len(text) > charsForSmall:
            fontSize = minFontSize
        else:
            fs = (len(text)-charsForLarge)/(charsForSmall-charsForLarge)
            fontSize = maxFontSize + fs * (minFontSize-maxFontSize)
        tf = self.w.selectionUnicodeText.getNSTextField()
        nsBig = NSFont.systemFontOfSize_(fontSize)
        tf.setFont_(nsBig)

    def update(self):
        items = []
        for name in self.catNames:
            p = name.split("\t")
            c1 = ""
            c2 = ""
            name = ""
            if len(p )==3:
                name = p[-1]
                c2 = p[-2]
                c1 = p[-3]
            elif len(p )==2:
                name = p[-1]
                c2 = p[-2]
            d = dict(col1=c1, col2=c2, name=name)
            items.append(d)
        #items = [dict(name=name) for name in self.catNames]
        self.w.catNames.set(items)
        self.checkSampleSize()
    
    def windowClosing(self, sender):
        # Reset the font window glyph collection query
        CurrentFontWindow().getGlyphCollection().setQuery(None)

    def callbackLookup(self, sender=None):
        lookupThese = []
        if self.currentSelection:
            if len(self.currentSelection)!=1: return
            for glyph in self.currentSelection:
                lookupThese.append(glyph)
        url = self.lookupURL + urlencode(dict(s=",".join([a.asU() for a in lookupThese])))
        webbrowser.get().open(url)

    def callbackSetUnicodesFromBinary(self, values):
        self._typing = True
        items = []
        if len(values) > 0:
            text = "".join([chr(v) for v in values])
            glyphSelection = findText(self.data, text)
            for g in glyphSelection:
                items.append(g.asDict(self._unicodes, self._names, self.joiningTypes))
            items = sorted(items, key=lambda x: x['uni'], reverse=False)
        self.w.selectedNames.set(items)
        self.w.selectionUnicodeText.set(text)
        self._typing = False
        self.checkSampleSize()

    def callbackEditUnicodeText(self, sender):
        # this is the callback for the unicode textbox.
        # if text is edited here, find the glyphs that are used in the text
        # and add those to the selection. This way we can quickly add characters
        # from cut / paste text to the selection
        f = CurrentFont()
        text = sender.get()
        text = text.replace("\r", " ")
        text = text.replace("\n", " ")
        self._typing = True
        if len(text) > 0:
            glyphSelection = findText(self.data, text)
            items = []
            for g in glyphSelection:
                items.append(g.asDict(self._unicodes, self._names, self.joiningTypes))
            items = sorted(items, key=lambda x: x['uni'], reverse=False)
            self.w.selectedNames.set(items)
        self.w.selectionUnicodeText.set(text)
        self._typing = False
        self.checkSampleSize()

    def callbackSearch(self, sender):
        # get the searchstring from the box and try to match as many characters as possible,
        f = CurrentFont()
        searchString = self.w.searchBox.get()
        glyphSelection = sorted(findGlyphs(self.data, searchString), key=lambda x:str(x))
        items = [g.asDict(self._unicodes, self._names, self.joiningTypes) for g in glyphSelection]
        items = sorted(items, key=lambda x: x['uni'], reverse=False)
        self.w.selectedNames.set(items)
        self.w.catNames.setSelection([])

    def setCurrentFontWindowSelection(self):
        self.currentSelection

    def callbackWindowMain(self, sender):
        f = CurrentFont()

        if f is not None:
            self.w.addGlyphPanelButton.enable(True)
            self.w.toSpaceCenter.enable(True)
            self._unicodes = list(set([g.unicode for g in f]))
            self._names = f.keys()
        else:
            self.w.addGlyphPanelButton.enable(False)
            self.w.toSpaceCenter.enable(False)
            self._unicodes = []
            self._names = []
        self.checkSampleSize()

    def callbackOpenGlyphSheet(self, sender=None, targetFonts=None):
        theseGlyphs = self.currentSelection
        if targetFonts is None:
            targetFonts = AllFonts()
        self._addGlyphsSheet = AddGlyphsSheet(theseGlyphs,
            self.w,
            self.callbackCancelGlyphsSheet,
            self.callbackApplyGlyphsSheet,
            targetFonts = targetFonts
        )

    def callbackCancelGlyphsSheet(self, sender):
        pass

    def callbackApplyGlyphsSheet(self, sender):
        pass

    def callbackGlyphNameSelect(self, sender):
        f = CurrentFont()
        existingCharacters = set()
        if f is not None:
            existingCharacters.update([chr(u) for u in f.getCharacterMapping().keys()])
        existing = 0
        new = 0
        glyphNames = u""
        selectionString = u""
        self.currentSelection = []
        selected = sender.getSelection()
        if len(selected) == 1:
            self.w.lookupSelected.enable(True)
        else:
            self.w.lookupSelected.enable(False)
        for i in selected:
            name = self.w.selectedNames[i]['name']
            glyphVariantNames = self.data[name].getAllNames()
            character = self.data[name].unicodeString
            selectionString += character
            if character not in existingCharacters:
                for variantName in glyphVariantNames:
                    glyphNames += "/%s "%variantName
                    if f is not None:
                        if variantName in f:
                            existing += 1
                        else:
                            new += 1
                self.currentSelection.append(self.data[name])    # means they're not sorted. Problem?
            else:
                existing += 1
        if new == 0 and existing == 0:
            self.w.progress.set("")
        else:
            self.w.progress.set("New glyphs: %d\nExisting: %d"%(new,existing))
        if not self._typing:
            self.w.selectionUnicodeText.set(selectionString)
        self.w.selectionGlyphNames.set("".join(glyphNames))
        self.checkSampleSize()
        #print('@@ self.currentSelection', self.currentSelection)

    def callbackCatNameSelect(self, sender):
        f = CurrentFont()
        items = []
        fontUniValues = []
        if f is not None:

            fontUniValues = list(set([g.unicode for g in f]))

        glyphSelection = []
        self.currentSelection = []
        for i in sender.getSelection():
            thisCat = self.catNames[i]
            for glyph in self.dataByCategory[thisCat]:
                if glyph not in glyphSelection:
                    glyphSelection.append(glyph)
        items = [g.asDict(self._unicodes, self._names, self.joiningTypes) for g in sorted(glyphSelection, key=lambda x:str(x))]
        sortedItems = sorted(items, key=lambda x: x['uni'], reverse=False)

        items = sorted(items, key=lambda x: x['uni'], reverse=False)
        self.w.selectedNames.set(sortedItems)

        selectedUniNumbers = ["%d"%it['uni'] for it in items if it['uni'] in fontUniValues]
        if selectedUniNumbers:
            query = "Unicode in {%s}"%",".join(selectedUniNumbers)
            queryObj = NSPredicate.predicateWithFormat_(query)
            CurrentFontWindow().getGlyphCollection().setQuery(queryObj)
    
    # stuff to clipboard
    def _toPasteBoard(self, text):
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.declareTypes_owner_([
            NSPasteboardTypeString,
        ], None)
        pb.setString_forType_(text,  NSPasteboardTypeString)

    def menuCallbackCopyToUFO(self, item):
        #@@
        if item.title() == "All":
            self.callbackOpenGlyphSheet(targetFonts=AllFonts())
        else:
            ufoName = str(item.title())
            for f in AllFonts():
                if f.path is not None:
                    if os.path.basename(f.path) == ufoName:
                        self.callbackOpenGlyphSheet(targetFonts=[f])
                        break
    
    def menuCallbackCopyHexUnicode(self, item):
        self.copyNamesCallback(what="hexnumbers")
    
    def menuCallbackCopyEscapedUnicode(self, item):
        self.copyNamesCallback(what="escaped")

    def menuCallbackCopyFeature(self, item):
        self.copyNamesCallback(what="feature")

    def menuCallbackCopyNames(self, item):
        self.copyNamesCallback(what="names")
    
    def menuCallbackCopyStrings(self, item):
        self.copyNamesCallback(what="comma")

    def menuCallbackCopySlash(self, item):
        self.copyNamesCallback(what="slash")
    
    def menuCallbackCopyUnicodeText(self, item):
        self.copyNamesCallback(what="unicode")
        
    def copyNamesCallback(self, sender=None, what=None):
        t = None
        if what is not None:
            t = what
        if sender is not None:
            t = sender.tag
        if t == None:
            return
        names = []
        for nameObj in self.currentSelection:
            names += nameObj.getAllNames()
        copyable = ""
        unitext = ''.join([nameObj.unicodeString for nameObj in self.currentSelection])
        #print("unitext", unitext)
        if t == "names":
            copyable = " ".join(names)
        elif t == "comma":
            copyable = ", ".join(["\"%s\""%s for s in names])
        elif t == "slash":
            copyable = "/"+"/".join(names)
        elif t == "feature":
            copyable = "[%s]"%" ".join(names)
        elif t == "unicode":
            copyable = unitext
        elif t == "hexnumbers":
            copyable = ' '.join(["0x%04x" % nameObj.uni for nameObj in self.currentSelection])
        elif t == "escaped":
            copyable = unitext.encode('ascii', 'backslashreplace')
        self._toPasteBoard(copyable)
    
    def toSpaceCenter(self, sender):
        # copy the current selection to spacecenter
        names = []
        copyable = ""
        for nameObj in self.currentSelection:
            names += nameObj.getAllNames()
            copyable = "/"+"/".join(names)
        setSomething = False
        for spaceCenter in mojo.UI.AllSpaceCenters():
            spaceCenter.setRaw(copyable)
            setSomething = True
        if not setSomething:
            # open a new spacecenter for the currentfont
            f = CurrentFont()
            if f is not None:
                mojo.UI.OpenSpaceCenter(f, newWindow=True)


if __name__ == "__main__":
    glyphDictionary = GlyphDict()
    joiningTypes = readJoiningTypes("./data/joiningTypes.txt")
    UnicodeVersion, GNFULversion, glyphDictionary = readUniNames("./data/glyphNamesToUnicode.txt", glyphDictionary, joiningTypes)

    browser = Browser(glyphDictionary, UnicodeVersion, GNFULversion, joiningTypes)
