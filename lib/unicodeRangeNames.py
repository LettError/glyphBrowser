# -*- coding: UTF-8 -*-
from unicodeRanges import unicodeRangeNames
unicodePlaneNames = {
	(0x00000,	0x0FFFF): (u"Basic Multilingual Plane", ),
	(0x10000,	0x1FFFF): (u"Supplementary Multilingual Plane", ),
	(0x20000,	0x2FFFF): (u"Supplementary Ideographic Plane"),
	(0x30000,	0xDFFFF): (u"Plane 3 - 13, unassigned", ),
	(0xE0000,	0xEFFFF): (u"Supplement­ary Special-purpose Plane", ),
	(0xF0000,	0x10FFFF): (u"Supplement­ary Private Use Area", ),
}

def getRangeName(value):
	for a, b in unicodeRangeNames.keys():
		if a <= value <= b:
			return unicodeRangeNames[(a,b)]
	return None
	
def getRangeAndName(value):
	for a, b in unicodeRangeNames.keys():
		if a <= value <= b:
			return (a,b), unicodeRangeNames[(a,b)]
	return None, None
	
def getPlaneName(value):
	for a, b in unicodePlaneNames.keys():
		if a <= value <= b:
			return unicodePlaneNames[(a,b)][0]
	return None
