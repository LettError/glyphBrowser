# -*- coding: UTF-8 -*-
import os

try:
    # in py3
    from importlib import reload
except NameError:
    reload


from pprint import pprint

from fontTools.misc.py23 import unichr

from AppKit import NSFont, NSFocusRingTypeNone, NSPredicate
from mojo.UI import CurrentFontWindow, SmartSet

import webbrowser

try:
    # in py3
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import unicodeRangeNames
from defconAppKit.windows.baseWindow import BaseWindowController

reload(unicodeRangeNames)
from unicodeRangeNames import getRangeName, getRangeAndName, getPlaneName
import unicodedata
import vanilla


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
glyphNameBrowserNames = [u" ✔︎ɢʟʏᴘʜʙʀᴏᴡsᴇʀ", u" ✔︎GLYPHBROWSER", 'GlyphBrowser', '']

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
            ):
        self.theseGlyphs = theseGlyphs    # list of these unicode glyph objects
        self.cancelCallback = cancelCallback
        self.applyCallback = applyCallback
        self.buildBaseWindow(parentWindow)

    def callbackCancelButton(self, sender):
        """ """
        if self.cancelCallback:
            self.cancelCallback(None)
        self.close()

    def callbackApplyButton(self, sender):
        # see if the current data is any different from the original data

        self.w.markGlyphsCheck, self.w.selectGlyphsCheck
        f = CurrentFont()
        selection = []
        for glyph in self.theseGlyphs:
            variantNames = glyph.getAllNames()
            for variantName in variantNames:
                if not variantName in f:
                    f.newGlyph(variantName)
                g = f[variantName]
                if variantName == variantNames[0]:
                    g.unicode = glyph.uni
                if self.w.markGlyphsCheck.get():
                    if version < '2.0':
                        # RF 1.8.x
                        g.mark = (0, 0.95, 0.95, 1)
                    else:
                        # RF 2.0
                        g.markColor = (0, 0.95, 0.95, 1)
                selection.append(variantName)
        if self.w.selectGlyphsCheck.get():
            f.selection = selection
        if self.applyCallback:
            self.applyCallback(None)
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
        self._sheetWidth = 315
        self._sheetHeight = 200
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
            callback=self.callbackApplyButton,
            sizeStyle='small')
        self.w.setDefaultButton(self.w.applyButton)

        # get the specialised stuff in
        self.fillSheet()
        self.setUpBaseWindowBehavior()
        #self.refresh()
        self.w.open()

    def fillSheet(self):
        text = ""
        if len(self.theseGlyphs) > 1:
            text = "Add %d glyphs"%len(self.theseGlyphs)
        else:
            text = "Add this glyph"
        f = CurrentFont()
        if f.path is not None:
            text += " to font <%s>"%os.path.basename(f.path)
        else:
            text += " to <Unsaved UFO>"
        text += "."
        self.w.namesCaption = vanilla.TextBox((40, 30, -10, 20), text)
        self.w.markGlyphsCheck = vanilla.CheckBox((50, 60, 150, 20), "Mark new glyphs", value=True)
        self.w.selectGlyphsCheck = vanilla.CheckBox((50, 85, 150, 20), "Select new glyphs", value=True)



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

    def getAllNames(self):
        # based on the category data, give suggestion for which extensions we need for any unicode
        extensions = {
            # XXXX no idea if it works this way...
            #   D Dual_Joining
            # 		&----G----&
            'D': ['ini', 'medi', 'fina'],
            #   C Join_Causing
            # 		&----G----&		????
            'C': [         					   ],
            #   R Right_Joining
            # 		   x G----&
            'R': [ 				 'fina'],
            #   L Left_Joining
            # 		&----G x
            'L': ['ini',		 'fina'],
            #   U Non_Joining
            # 	       x G x
            'U': [         					   ],
            #   T Transparent
            # 	       x G x
            'T': [         					   ],
        }

        if self.joiningType is not None:
            variants = []
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
        if self.joiningType is not None:
            d['joiningType'] = self.joiningType
        else:
            d['joiningType'] = ""
        if self.uni in fontUnicodes:
            d['unicodeinfont'] = u"•"    # 🔢
        else:
            d['unicodeinfont'] = ""
        if self.name in fontNames:
            d['nameinfont'] = u"•"    # 🔤
        else:
            d['nameinfont'] = ""
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
        #if self.sub is not None:
        #    if len(self.sub)>0:
        #        d["parts"] += self.sub[0]
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
            allCats.append(u"📦\t%s"%self.srcPath)
        if self.error:
            allCats.append(u"⚠️\tError")
        if self.uni is None:
            allCats.append(u"⋯\tNo unicode")
        if self.unicodeRangeName is not None:
            a, b = self.unicodeRange
            allCats.append(u"%05X\t%05X\t%s"%(a, b, self.unicodeRangeName))
        if self.unicodeCategoryName is not None:
            allCats.append(u"📕\t"+ self.unicodeCategoryName)
        if self.uni is not None:
            allCats.append(u"🔣\t"+ getPlaneName(self.uni))
        for s in self.set:
            allCats.append(u"☰\t"+s)
        if "_" in self.name:
            allCats.append(u"f_f_l\tCombined glyphs")
        #if ":" in self.name:
        #    allCats.append(u"📎\t%s"%self.name.split(":")[0])
        if u"." in self.name and self.name[0]!=u".":
            # catch glyph names with extensions, but not .notdef
            extension = self.name.split(".")[-1]
            allCats.append(u"…\t."+extension)
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
            if anything == self.unicodeString:
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
    lookupURL = u"http://unicode.scarfboy.com/?"
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

        self.w = vanilla.Window((1200, 500), ("GlyphNameBrowser with %s and %s"%(self.unicodeVersion, versionString)), minSize=(800, 500))
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
        self.w.catNames = vanilla.List((5, topRow, catWidth, -5), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackCatNameSelect)
        charWidth = 18
        columnDescriptions = [
            {    'title': u"❡",
                 'key': 'nameinfont',
                 'width': charWidth},
            {    'title': "#",
                 'key': 'unicodeinfont',
                 'width': charWidth},
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
                 'width': 30},
            {    'title': "Char",
                 'key': 'string',
                 'width': 30},
            {    'title': "Unicode Description",
                 'key': 'uniName',
                     },
            ]
        self.w.searchBox = vanilla.SearchBox((-200, topRow, -5, 22), "", callback=self.callbackSearch)
        self.w.selectedNames = vanilla.List((catWidth+10, topRow, -205, -5), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackGlyphNameSelect)
        self.w.selectionUnicodeText = vanilla.EditText((0, 0, -0, topRow-5), placeholder=choice(glyphNameBrowserNames), callback=self.callbackEditUnicodeText)
        s = self.w.selectionUnicodeText.getNSTextField()
        s.setFocusRingType_(NSFocusRingTypeNone)

        self.w.selectionGlyphNames = vanilla.EditText((-200, topRow+28, -5, -300), "Selectable Glyph Names", sizeStyle="small")
        self.checkSampleSize()
        self.w.addGlyphPanelButton = vanilla.Button((-200, -65, -5, 20), "Add to Font", callback=self.callbackOpenGlyphSheet)
        self.w.lookupSelected = vanilla.Button((-200, -90, -5, 20), "Lookup", callback=self.callbackLookup)
        self.w.progress = vanilla.TextBox((-190, -35, -10, 40), "", sizeStyle="small")
        self.w.addGlyphPanelButton.enable(False)
        self.w.bind("became main", self.callbackWindowMain)
        self.w.setDefaultButton(self.w.addGlyphPanelButton)
        self.update()
        self.w.open()
        self.w.catNames.setSelection([0])

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

    def callbackLookup(self, sender):
        lookupThese = []
        if self.currentSelection:
            if len(self.currentSelection)!=1: return
            for glyph in self.currentSelection:
                lookupThese.append(glyph)
        url = self.lookupURL + urlencode(dict(s=",".join([a.asU() for a in lookupThese])))
        webbrowser.get().open(url)

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
        if text:
            glyphSelection = sorted(findText(self.data, text))
            items = [g.asDict(self._unicodes, self._names, self.joiningTypes) for g in glyphSelection]
            items = sorted(items, key=lambda x: x['uni'], reverse=False)
            self.w.selectedNames.set(items)
        self.w.selectionUnicodeText.set(text)
        self._typing = False
        self.checkSampleSize()

    def callbackSearch(self, sender):
        # get the searchstring from the box and try to match as many characters as possible,
        f = CurrentFont()
        searchString = self.w.searchBox.get()
        glyphSelection = sorted(findGlyphs(self.data, searchString))
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
            self._unicodes = list(set([g.unicode for g in f]))
            self._names = f.keys()
        else:
            self.w.addGlyphPanelButton.enable(False)
            self._unicodes = []
            self._names = []
        self.checkSampleSize()

    def callbackOpenGlyphSheet(self, sender):
        theseGlyphs = self.currentSelection
        self._addGlyphsSheet = AddGlyphsSheet(theseGlyphs,
            self.w,
            self.callbackCancelGlyphsSheet,
            self.callbackApplyGlyphsSheet,
        )

    def callbackCancelGlyphsSheet(self, sender):
        pass

    def callbackApplyGlyphsSheet(self, sender):
        pass

    def callbackGlyphNameSelect(self, sender):
        f = CurrentFont()
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
            selectionString += self.data[name].unicodeString
            for variantName in glyphVariantNames:
                glyphNames += "/%s "%variantName
                if f is not None:
                    if variantName in f:
                        existing += 1
                    else:
                        new += 1
            self.currentSelection.append(self.data[name])    # means they're not sorted. Problem?
        if new == 0 and existing == 0:
            self.w.progress.set("")
        else:
            self.w.progress.set("New glyphs: %d\nExisting: %d"%(new,existing))
        if not self._typing:
            self.w.selectionUnicodeText.set(selectionString)
        self.w.selectionGlyphNames.set("".join(glyphNames))
        self.checkSampleSize()

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
            #print("query", query)
            queryObj = NSPredicate.predicateWithFormat_(query)
            CurrentFontWindow().getGlyphCollection().setQuery(queryObj)


if __name__ == "__main__":
    glyphDictionary = GlyphDict()
    joiningTypes = readJoiningTypes("./data/joiningTypes.txt")
    UnicodeVersion, GNFULversion, glyphDictionary = readUniNames("./data/glyphNamesToUnicode.txt", glyphDictionary, joiningTypes)

    browser = Browser(glyphDictionary, UnicodeVersion, GNFULversion, joiningTypes)
