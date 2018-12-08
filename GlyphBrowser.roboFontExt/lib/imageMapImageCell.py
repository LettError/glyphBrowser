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
            x, y = frame.origin
            image.drawInRect_(((x, y), (view.rowHeight(), view.rowHeight())))
