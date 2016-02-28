# glyphBrowser

![Screenshot of the GlyphBrowser panel in RoboFont](glyphBrowserScreen.jpg)

A sketch for a RoboFont extension for browsing and selecting unicode values, glyphnames, categories, lists.
This combines glyphnames from the AGD.txt file in the [Adobe AFDKO](https://github.com/adobe-type-tools/afdko/blob/master/FDK/Tools/SharedData/AGD.txt) with the unicode categories and range information. A preview of the unicode character is drawn by OSX.

## To do:

  * Solve the dependency on the AGD.txt more elegantly
  * The AGD.txt list has a lot of unencoded glyphs and glyphs that are assigned to the Private Use area. These need to be marked better, or could be subject to some editorial discretion.
  * Better preview of the glyphs in the list
  * Better typography for the column of hex values
  * Maybe report in the list if a glyph is present in the current font?
  * How to handle the glyphs in the .Error category?
  
