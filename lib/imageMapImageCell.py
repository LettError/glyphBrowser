import AppKit
import objc

class ImageMapImageCell(AppKit.NSTextFieldCell):
    
    @objc.python_method
    def setImages(self, imageMap):
        self._imageMap = imageMap
        
    def drawWithFrame_inView_(self, frame, view):
        value = self.objectValue()
        if value in self._imageMap:
            image = self._imageMap[value]
            srcWidth, srcHeight = image.size()
            viewHeight = view.rowHeight()
            scaledWidth = srcWidth / (srcHeight / viewHeight)
            x, y = frame.origin
            image.drawInRect_(((x, y), (scaledWidth, view.rowHeight())))
