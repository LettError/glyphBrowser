# -*- coding: UTF-8 -*-

from lib.tools.misc import unicodeToChar, charToUnicode
from unicodeRangeNames import getRangeName, getRangeAndName
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


class AGDGlyph(object):

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
                
    def uniString(self):
        # return a unicode string with this character, if possible
        return self.unicodeString
    
    def asDict(self):
        d = {}
        d['name'] = self.name
        d['uni'] = self.uni
        d['string'] = self.unicodeString
        if self.uni is not None:
            d['uniHex'] = "%05x"%self.uni
        else:
            d['uniHex'] = ""
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
        return "[AGD: %s %s %s %s]"%(self.name, u, cat, r)
    
    def lookupRefs(self):
        # find out more things based on the unicode
        if self.uni is None: return
        # category
        try:
            c = unicodeToChar(self.uni)
            self.unicodeString = c
            self.unicodeCategory = unicodedata.category(c)
            self.unicodeCategoryName = unicodeCategoryNames.get(self.unicodeCategory)
        except ValueError:
            self.error = True
            pass
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
            allCats.append(u"☰\t%s"%self.srcPath)
        if self.error:
            allCats.append(u"⚠️\tError")
        if self.uni is None:
            allCats.append(u"⋯\tNo unicode")
        if self.unicodeRangeName is not None:
            allCats.append(u"💬\t"+self.unicodeRangeName)
        if self.unicodeCategoryName is not None:
            allCats.append(u"📕\t"+ self.unicodeCategoryName)
        for s in self.set:
            allCats.append(u"☰\t"+s)
        if "_" in self.name:
            allCats.append(u"☰\tCompound glyphs")
        if u"." in self.name and self.name[0]!=u".":
            # catch glyph names with extensions, but not .notdef
            extension = self.name.split(".")[-1]
            allCats.append(u"\t"+extension)
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
        if self.unicodeRangeName is not None:
            if anything.lower() in self.unicodeRangeName.lower():
                return True
        if self.unicodeCategory is not None:
            if anything.lower() in self.unicodeCategory.lower():
                return True
        if self.unicodeCategoryName is not None:
            if anything.lower() in self.unicodeCategoryName.lower():
                return True
        if self.unicodeString is not None:
            if anything == self.unicodeString:
                return True
        for s in self.set:
            if anything in s:
                return True
        return False
        
def readAGD(path, glyphDictionary=None):
    if glyphDictionary is None:
        glyphDictionary = {}
    f = open(path, 'r')
    d = f.read()
    f.close()
    lines = d.split("\n")
    entryObject = None
    name = None
    allTags = {}
    for l in lines:
        if len(l)==0:
            continue
        if l[0] == "#": 
            continue
        if l[0]!="\t":
            # new entry
            if entryObject:
                #if entryObject.uni is not None:
                #    # in order to avoid glyphs with different names
                #    # but with the same unicode, look for older glyphs
                #    # with the same unicode and remove those.
                #    # this way we can overwrite entries.
                #    # But only for glyphs with unicodes.
                #    for n, o in glyphDictionary.items():
                #        print o.uni, entryObject.uni
                #        if o.uni == entryObject.uni:
                #            print "removing", o.name
                #            del glyphDictionary[o.name]
                glyphDictionary[name] = entryObject
                entryObject = None
            name = l
            entryObject = AGDGlyph(name, path)
            continue
        parts = l.split(":")
        tag = parts[0].strip()
        allTags[tag] = True
        items = [p.strip() for p in parts[1].split(" ") if len(p)>0]
        if tag == "uni":
            hexCanditate = items[0]
            if "0x" in hexCanditate:
                hexCanditate = hexCanditate[2:]
            hexCanditate = int("0x"+hexCanditate, 16)
            entryObject.uni = hexCanditate
        elif tag == "min":
            entryObject.min = items[0]
        elif tag == "maj":
            entryObject.maj = items[0]
        elif tag == "cmp":
            entryObject.cmp = items[0]
        elif tag == "fin":
            entryObject.fin = items[0]
        elif tag == "set":
            entryObject.set = items
        # BE tags
        elif tag == "typ":
            entryObject.typ = items[0]
        elif tag == "lan":
            entryObject.lan = items[0].split(",")
        elif tag == "con":
            entryObject.lan = items[0]
    for name, glyph in glyphDictionary.items():
        glyph.lookupRefs()
    # add the trailing entryObject
    return glyphDictionary

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
    def __init__(self, data):
        self.data = data
        self.dataByCategory = collectSearchCategories(data)
        self.catNames = self.dataByCategory.keys()
        self.catNames.sort()
        self.currentSelection = []
        self.w = vanilla.Window((800, 500), "AGD Glyph and Unicode Browser using Unicode %s"%unicodedata.unidata_version)
        columnDescriptions = [
            {'title': "Categories, ranges, namelists", 'key': 'name'},
        ]
        self.w.catNames = vanilla.List((0,0,200, 0), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackCatNameSelect)
        columnDescriptions = [
            {    'title': "Adobe Glyph Name",
                 'key': 'name',
                 'width': 200, },
            {    'title': "Unicode",
                 'key': 'uniHex',
                 'width': 80},
            {    'title': "Char",
                 'key': 'string',
                 'width': 80},
            ]
        self.w.selectedNames = vanilla.List((200,0,-200,0), [], columnDescriptions=columnDescriptions, selectionCallback=self.callbackGlyphNameSelect)
        self.w.selectionUnicodeText = vanilla.EditText((-200, 0, 0, 200), "Selectable Unicode Text")
        self.w.selectionGlyphNames = vanilla.EditText((-200, 200, 0, 200), "Selectable Glyph Names", sizeStyle="small")
        self.w.addButton = vanilla.Button((-190, -60, -10, 20), "Add glyphs", callback=self.callbackAddGlyphsButton)
        self.w.progress = vanilla.TextBox((-190, -35, -10, 40), "", sizeStyle="small")
        self.w.addButton.enable(False)
        self.w.bind("became main", self.callbackWindowMain)
        self.update()
        self.w.open()
    
    def update(self):
        items = [dict(name=name) for name in self.catNames]
        self.w.catNames.set(items)
    
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
        
    def callbackWindowMain(self, sender):
        f = CurrentFont()
        if f is not None:
            self.w.addButton.enable(True)
        else:
            self.w.addButton.enable(False)
        
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
            self.w.addButton.setTitle("Select glyphs")
        else:
            self.w.addButton.setTitle("Add glyphs")
            
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
    glyphDictionary = {}
    glyphDictionary = readAGD("AGD.txt", glyphDictionary)
    #glyphDictionary = readAGD("arabic.AGD.txt", glyphDictionary)
    browser = Browser(glyphDictionary)