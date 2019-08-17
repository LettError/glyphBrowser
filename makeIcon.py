# a script for drawbot.app that generates the icon
size(512, 512)

c1 = (1,0,.95)
c2 = (0,.05,.95)
c3 = (.55,.5,.95)

font("MicrogrammaCom-BoldExtended")
s = 148
h = 391
f = 0.75
fontSize(148)

fill(*c1)

text("GLYP", (10, h))
t = FormattedString()
t.font("MicrogrammaCom-BoldExtended")
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
text("12", (256, h-f*3*s))


saveImage("icon.pdf")
saveImage("GlyphBrowserMechanicIcon.png")
saveImage("html/GlyphBrowserMechanicIcon.png")