# -*- coding: UTF-8 -*-
import os

import unicodeRangeNames
reload(unicodeRangeNames)
from unicodeRangeNames import getRangeName, getRangeAndName, getPlaneName
import unicodedata
import vanilla


"""
    
    Browser for unicode categories, unicode ranges and glyphlists
    as defined in the Adobe AGD list.
    Goal: make a window similar to OSX Character Viewer but with a button
    that will add the selected glyphs to the current font with the appopriate
    names and unicode values.
    
    - Just a sketch.
    - Depends on the AGD.txt file from the ADFDKO.
    - Should use the unicode wisdom from defcon.
    - Offer the selected glyphs as unicode text.
    - Offer the selected glyphs in glyphname syntax.
    - Add the selected names as new glyphs if they don't already exist.
    - options: 
        - checkbox for overwriting existing glyphs
        - select mark color
        - larger preview of the unicode string in the list
        - better display of errors, private use, unencoded glyphs
        
    
    20160228 erik

"""


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
        
        self.other = {} # Hash of any unknown tags
        
        self.unicodeRange = None
        self.unicodeRangeName = None
        self.unicodeCategory = None
        self.unicodeCategoryName = None
        self.unicodeString = ""
        self.unicodeName = None
                
    def uniString(self):
        # return a unicode string with this character, if possible
        return self.unicodeString
    
    def asDict(self):
        d = {}
        d['name'] = self.name
        d['uni'] = self.uni
        d['string'] = self.unicodeString
        d['category'] = self.unicodeCategory
        if self.uni is not None:
            d['uniHex'] = "%05x"%self.uni
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
            self.unicodeName = unicodedata.name(c)
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
            allCats.append(u"💬\t"+self.unicodeRangeName)
        if self.unicodeCategoryName is not None:
            allCats.append(u"📕\t"+ self.unicodeCategoryName)
        if self.uni is not None:
            allCats.append(u"🔣\t"+ getPlaneName(self.uni))
        for s in self.set:
            allCats.append(u"☰\t"+s)
        if "_" in self.name:
            allCats.append(u"f_f_l\tCombined glyphs")
        if u"." in self.name and self.name[0]!=u".":
            # catch glyph names with extensions, but not .notdef
            extension = self.name.split(".")[-1]
            allCats.append(u"…\t"+extension)
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
            #for name, glyph in self.items():
                #if glyph.uni == record.uni:
                oldName = glyph.name
                glyph.update(record)
                self[record.name] = glyph
                del self[oldName]
                added = True
                self.uniMap[record.uni] = record.name
                #break
            if added:
                return
        # option 3: just new glyph
        self.uniMap[record.uni] = record.name
        self[record.name] = record


def readUniNames(path, glyphDictionary=None):
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
            print "bah unicode", hexCandidate, name
            continue
        entryObject = SimpleGlyphName(name, niceFileName)
        entryObject.uni = hexCandidate
        entryObject.unicodeCategory = unicodeCategory
        glyphDictionary.update(entryObject)
    for name, glyph in glyphDictionary.items():
        glyph.lookupRefs()
    return unicodeVersionString, versionString, glyphDictionary
       

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
    k = sortedItems.keys()
    k.sort()
    sortedList = []
    for i in k:
        sortedItems[i].sort()
        for j in sortedItems[i]:
            sortedList.append(j)       
    return sortedList

class Browser(object):
    def __init__(self, data, unicodeVersionString, versionString):
        self.data = data
        self.dataByCategory = collectSearchCategories(data)
        self.catNames = self.dataByCategory.keys()
        self.catNames.sort()
        self.currentSelection = []
        self.unicodeVersion = unicodeVersionString
        self.w = vanilla.Window((1100, 500), ("Glyphname Browser with %s and %s"%(self.unicodeVersion, versionString)).upper(), minSize=(800, 500))
        columnDescriptions = [
            {'title': "Categories, ranges, namelists", 'key': 'name'},
        ]
        self.w.catNames = vanilla.List((5, 30, 215, -5), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackCatNameSelect)
        columnDescriptions = [
            {    'title': "GNUFL Glyph Name",
                 'key': 'name',
                 'width': 220, },
            {    'title': "Unicode",
                 'key': 'uniHex',
                 'width': 70},
            {    'title': "Cat",
                 'key': 'category',
                 'width': 30},
            {    'title': "Char",
                 'key': 'string',
                 'width': 30},
            {    'title': "Unicode Description",
                 'key': 'uniName',
                     },
            ]
        self.w.searchBox = vanilla.SearchBox((-200, 4, -5, 22), "", callback=self.callbackSearch)
        self.w.selectedNames = vanilla.List((225, 30, -205, -5), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackGlyphNameSelect)
        self.w.selectionUnicodeText = vanilla.EditText((-200, 30, -5, 180), "Selectable Unicode Text")
        self.w.selectionGlyphNames = vanilla.EditText((-200, 215, -5, 200), "Selectable Glyph Names", sizeStyle="small")
        self.w.addGlyphPanelButton = vanilla.Button((-190, -60, -10, 20), "Add to Glyphpanel", callback=self.callbackAddToNewGlyphPanel)
        self.w.progress = vanilla.TextBox((-190, -35, -10, 40), "", sizeStyle="small")
        self.w.addGlyphPanelButton.enable(False)
        self.w.bind("became main", self.callbackWindowMain)
        self.w.setDefaultButton(self.w.addGlyphPanelButton)
        self.update()
        self.w.open()
    
    def update(self):
        items = [dict(name=name) for name in self.catNames]
        self.w.catNames.set(items)
    
    def callbackSearch(self, sender):
        searchString = self.w.searchBox.get()
        glyphSelection = findGlyphs(self.data, searchString)
        glyphSelection.sort()
        items = [g.asDict() for g in glyphSelection]
        items = sorted(items, key=lambda x: x['uni'], reverse=False)
        self.w.selectedNames.set(items)
        self.w.catNames.setSelection([])
        
    def callbackAddGlyphsButton(self, sender):
        f = CurrentFont()
        if f is None: return
        actualCount = 0
        if self.currentSelection:
            for glyph in self.currentSelection:
                if glyph.name in f:
                    # skip existing ?
                    self.w.progress.set("skipping %s"%glyph.name)
                    continue
                f.newGlyph(glyph.name)
                g = f[glyph.name]
                g.unicode = glyph.uni
                self.w.progress.set("added %s"%glyph.name)
                actualCount += 1
        self.w.progress.set("%d glyphs added"%actualCount)

    def callbackAddToNewGlyphPanel(self, sender):
        #glyphs = [
        #    "Amacron=A+macron|0100" # mss handig want AGD heeft ook cmp support
        #]
        from mojo.UI import CurrentFontWindow
        f = CurrentFont()
        if f is None: return
        glyphs = []
        if self.currentSelection:
            for glyph in self.currentSelection:
                if glyph.name in f:
                    # skip existing ?
                    self.w.progress.set("skipping %s"%glyph.name)
                    continue
                glyphs.append(u"%s|%04x"%(glyph.name, glyph.uni))
        controller = CurrentFontWindow()
        controller.addGlyphs(glyphs)
        
    def callbackWindowMain(self, sender):
        f = CurrentFont()
        if f is not None:
            self.w.addGlyphPanelButton.enable(True)
        else:
            self.w.addGlyphPanelButton.enable(False)
        
    def callbackGlyphNameSelect(self, sender):
        f = CurrentFont()
        existing = 0
        new = 0
        glyphNames = u""
        selectionString = u""
        self.currentSelection = []
        for i in sender.getSelection():
            name = self.w.selectedNames[i]['name']
            selectionString += self.data[name].unicodeString
            glyphNames += "/%s"%name
            if f is not None:
                if name in f:
                    existing += 1
                else:
                    new += 1
            self.currentSelection.append(self.data[name])    # means they're not sorted. Problem?
        if new == 0 and existing == 0:         
            self.w.progress.set("")
        else:
            self.w.progress.set("New glyphs: %d\nExisting: %d"%(new,existing))
        self.w.selectionUnicodeText.set(selectionString)
        self.w.selectionGlyphNames.set("".join(glyphNames))
        if len(self.currentSelection) == 0:
            self.w.addGlyphPanelButton.setTitle("Select glyphs")
        else:
            self.w.addGlyphPanelButton.setTitle("Add to glyph panel")
            
    def callbackCatNameSelect(self, sender):
        glyphSelection = []
        self.currentSelection = []
        for i in sender.getSelection():
            thisCat = self.catNames[i]
            for glyph in self.dataByCategory[thisCat]:
                if glyph not in glyphSelection:
                    glyphSelection.append(glyph)
        glyphSelection.sort()
        items = [g.asDict() for g in glyphSelection]
        items = sorted(items, key=lambda x: x['uni'], reverse=False)
        self.w.selectedNames.set(items)
    
if __name__ == "__main__":
    glyphDictionary = GlyphDict()
    UnicodeVersion, GNFULversion, glyphDictionary = readUniNames("./data/glyphNamesToUnicode.txt", glyphDictionary)
    browser = Browser(glyphDictionary, UnicodeVersion, GNFULversion)
