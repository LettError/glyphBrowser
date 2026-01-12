# a script for drawbot.app that generates the icon
size(512, 512)

c1 = (0.6,0,.27)
c2 = (0.4,.05,.63)
c3 = (.55,.6,.74)

fn = "MicrogrammaD-BoldExte"
font(fn)
s = 148
h = 391
f = 0.75
fontSize(148)

fill(*c1)

text("GLYP", (10, h))
t = FormattedString()
t.font(fn)
t.fontSize(148)
t.fill(*c1)

t += "H"
t.fill(*c2)
t += "BR"
fill(*c2)
text(t, (89, h-f*s))
text("OWS", (25, h-f*2*s))
text("ER", (10, h-f*3*s))

fill(*c3)

fontSize(50)
text("unicode", (274, h-f*3*s-38))
fontSize(s)
text("16", (256, h-f*3*s))


saveImage("icon.pdf")
saveImage("GlyphBrowserMechanicIcon.png")
saveImage("html/GlyphBrowserMechanicIcon.png")