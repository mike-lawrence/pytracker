# class dummyQTo:
# 	def empty(self):
# 		return True

# class dummyQFrom:
# 	def put(self,message):
# 		print message

# qTo = dummyQTo()
# qFrom = dummyQFrom()

# camIndex = 0
# camRes = [1920,1080]
# previewDownsize = 2
# previewLoc = [0,0]
# faceDetectionScale = 10
# eyeDetectionScale = 5
# timestampMethod = 0
# viewingDistance = 100
# stimDisplayWidth = 100
# stimDisplayRes = [1920,1080]
# stimDisplayPosition = [0,0]
# mirrorDisplayPosition = [0,0]
# mirrorDownSize = 2
# manualCalibrationOrder = True
# calibrationDotSizeInDegrees = 1
# saccadeAlertSizeInDegrees = 1


import numpy
import cv2
import scipy.ndimage.filters
# import scipy.interpolate
import sys
import sdl2
import sdl2.ext
import sdl2.sdlmixer

#define a class for a clickable text UI
class clickableText:
	def __init__(self,x,y,text,rightJustified=False,valueText=''):
		self.x = x
		self.y = y
		self.text = text
		self.rightJustified = rightJustified
		self.valueText = valueText
		self.isActive = False
		self.clicked = False
		self.updateSurf()
	def updateSurf(self):
		if self.isActive:
			self.surf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,self.text+self.valueText,sdl2.pixels.SDL_Color(r=0, g=255, b=255, a=255),previewWindow.size[0]).contents
		else:
			self.surf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,self.text+self.valueText,sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
	def checkIfActive(self,event):
		if self.rightJustified:
			xLeft = self.x - self.surf.w
			xRight = self.x
		else:
			xLeft = self.x
			xRight = self.x + self.surf.w
		if (event.button.x>xLeft) & (event.button.x<xRight) & (event.button.y>self.y) & (event.button.y<(self.y+fontSize)):
			self.isActive = True
		else:
			self.isActive = False
		self.updateSurf()
	def draw(self,targetWindowSurf):
		if self.rightJustified:
			sdl2.SDL_BlitSurface(self.surf, None, targetWindowSurf, sdl2.SDL_Rect(self.x-self.surf.w,self.y,self.surf.w,self.surf.h))
		else:
			sdl2.SDL_BlitSurface(self.surf, None, targetWindowSurf, sdl2.SDL_Rect(self.x,self.y,self.surf.w,self.surf.h))


#define a class for settings
class settingText(clickableText):
	def __init__(self,value,x,y,text,rightJustified=False):
		self.value = value
		self.valueText = str(value)
		clickableText.__init__(self,x,y,text,rightJustified,self.valueText)
	def addValue(self,toAdd):
		self.valueText = self.valueText+toAdd
		self.updateSurf()
	def delValue(self):
		if self.valueText!='':
			self.valueText = self.valueText[0:(len(self.valueText)-1)]
			self.updateSurf()
	def finalizeValue(self):
		try:
			self.value = int(self.valueText)
		except:
			print 'Non-numeric value entered!'

#define a class for dots
class dotObj:
	def __init__(self,name,isFid,xPixel,yPixel,radiusPixel,blinkCriterion,blurSize,filterSize):
		self.name = name
		self.isFid = isFid
		self.xPixel = xPixel
		self.yPixel = yPixel
		self.radiusPixel = radiusPixel
		self.radius = radiusPixel
		self.first = True
		self.lost = False
		self.blinkHappened = False
		self.radii = []
		self.SDs = []
		self.lostCount = 0
		self.blinkCriterion = blinkCriterion
		self.blurSize = blurSize
		self.filterSize = filterSize
	def getDarkEllipse(self,img):
		#if not self.isFid:
		#	#cv2.imwrite(self.name + "_" + "%.2d" % imageNum + "_raw.png" , img)
		try:
			smoothedImg = cv2.GaussianBlur(img,(self.blurSize,self.blurSize),0)
			#if not self.isFid:
			#	#cv2.imwrite(self.name + "_" + "%.2d" % imageNum + "_smoothed.png" , img)
		except:
			print 'cv2.GaussianBlur failed'
			# cv2.imwrite('temp.png',img)
			return None
		try:
			dataMin = scipy.ndimage.filters.minimum_filter(smoothedImg, self.filterSize)
		except:
			print 'scipy.ndimage.filters.minimum_filter failed'
			# cv2.imwrite('temp.png',img)
			return None
		if dataMin!=None:
			try:
				minLocs = numpy.where(dataMin<(numpy.min(dataMin)+numpy.std(dataMin)))
			except:
				print 'numpy.where failed'
				# cv2.imwrite('temp.png',img)
				return None
			if len(minLocs[0])>=5:
				try:
					ellipse = cv2.fitEllipse(numpy.reshape(numpy.column_stack((minLocs[1],minLocs[0])),(len(minLocs[0]),1,2)))
				except:
					print 'cv2.fitEllipse failed'
					# cv2.imwrite('temp.png',img)
					return None
				return ellipse
	def cropImage(self,img,cropSize):
		xLo = self.xPixel - cropSize
		if xLo<0:
			xLo = 0
		xHi = self.xPixel + cropSize
		if xHi>img.shape[1]:
			xHi = img.shape[1]
		yLo = self.yPixel - cropSize
		if yLo<0:
			yLo = 0
		yHi = self.yPixel + cropSize
		if yHi>img.shape[0]:
			yHi = img.shape[0]
		return [img[yLo:yHi,xLo:xHi],xLo,xHi,yLo,yHi]
	def search(self,img):
		if self.lost or self.first:
			searchSize = 5
		else:
			searchSize = 3
		if self.first:
			self.first = False
		img,xLo,xHi,yLo,yHi = self.cropImage(img=img,cropSize=searchSize*self.radiusPixel)
		self.ellipse = self.getDarkEllipse(img=img)
		if self.ellipse!=None:
			self.ellipse = ((self.ellipse[0][0]+xLo,self.ellipse[0][1]+yLo),self.ellipse[1],self.ellipse[2])
			self.lost = False
			self.x = self.ellipse[0][0]
			self.y = self.ellipse[0][1]
			self.major = self.ellipse[1][0]
			self.minor = self.ellipse[1][1]
			self.angle = self.ellipse[2]
			self.xPixel = int(self.x)
			self.yPixel = int(self.y)
			self.radius = (self.ellipse[1][0]+self.ellipse[1][1])/4
			self.radiusPixel = int(self.radius)
		else:
			self.lost = True
	def checkSearch(self):
		self.medianRadius = numpy.median(self.radii)
		self.critRadius = 10*((numpy.median((self.radii-self.medianRadius)**2))**.5)
		#print [self.name, self.radius2,(self.radius2<(1/6)) , (self.radius2>2)]
		if len(self.radii)<30:
			self.radii.append(self.radius2)
			self.lost = False
		else:
			#fid diameter is 6mm, so range from 1mm to 12mm
			#if (self.radius2<(1/6)) or (self.radius2>2) or (self.radius2<(self.medianRadius - self.critRadius)) or (self.radius2>(self.medianRadius + self.critRadius)):
			if (self.radius2<(1/6)) or (self.radius2>2):
				self.lost = True
			else:
				self.lost = False
				self.radii.append(self.radius2)
			if len(self.radii)>=300:
				self.radii.pop()
	def makeRelativeToFid(self,fid):
		self.x2 = (self.x-fid.x)/fid.radius
		self.y2 = (self.y-fid.y)/fid.radius
		self.radius2 = self.radius/fid.radius
	def checkSD(self,img,fid):
		self.obsSD = numpy.std(self.cropImage(img=img,cropSize=5*fid.radiusPixel)[0])
		self.medianSD = numpy.median(self.SDs)
		self.critSD = self.medianSD*self.blinkCriterion
		#print [self.name,self.obsSD,self.medianSD,self.critSD,self.blinkCriterion]
		if len(self.SDs)<30:
			self.SDs.append(self.obsSD)
			self.blinkHappened = False
		else:
			if (self.obsSD<self.critSD):
				self.blinkHappened = True
			else:
				self.SDs.append(self.obsSD)
				self.blinkHappened = False
			if len(self.SDs)>=300:
				self.SDs.pop()
	def update(self,img,fid,blinkCriterion,blurSize,filterSize):
		self.blinkCriterion = blinkCriterion
		self.blurSize = blurSize
		self.filterSize = filterSize
		lastPixels = [self.xPixel,self.yPixel,self.radiusPixel]
		if self.isFid:
			self.search(img=img)
		else:
			self.checkSD(img=img,fid=fid) #alters the value of self.blinkHappened, amongst other things
			if self.blinkHappened:
				self.xPixel,self.yPixel,self.radiusPixel = lastPixels
			else:
				self.search(img=img) #alters the value of self.lost, amongst other things
				if self.lost:
					self.xPixel,self.yPixel,self.radiusPixel = lastPixels
				else:
					self.makeRelativeToFid(fid=fid)
					self.checkSearch() #alters the value of self.lost, among other things
					if self.lost:
						self.xPixel,self.yPixel,self.radiusPixel = lastPixels
		if self.lost and not self.blinkHappened:
			self.lostCount += 1
		else:
			self.lostCount = 0



########
# Initialize audio and define a class that handles playing sounds in PySDL2
########
sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
class Sound:
	def __init__(self, fileName):
		self.sample = sdl2.sdlmixer.Mix_LoadWAV(sdl2.ext.compat.byteify(fileName, "utf-8"))
		self.started = False
	def play(self):
		self.channel = sdl2.sdlmixer.Mix_PlayChannel(-1, self.sample, 0)
		self.started = True
	def stillPlaying(self):
		if self.started:
			if sdl2.sdlmixer.Mix_Playing(self.channel):
				return True
			else:
				self.started = False
				return False


########
# define some useful functions
########

#define a function to exit safely
def exitSafely():
	qFrom.put('done')
	sys.exit()

#define a function to rescale
def rescaleBiggestHaar(detected,scale,addToX=0,addToY=0):
	x,y,w,h = detected[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detected])]
	return [x*scale+addToX,y*scale+addToY,w*scale,h*scale]

#define a function to compute gaze location from image and calibration coeficients
def getGazeLoc(dotList,coefs,last):
	xCoefLeft,xCoefRight,yCoefLeft,yCoefRight = coefs
	if dotList[1].lost:
		xLoc = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
		yLoc = yCoefRight[0] + yCoefRight[1]*dotList[2].x2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].x2
	elif dotList[2].lost:
		xLoc = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
		yLoc = yCoefLeft[0] + yCoefLeft[1]*dotList[1].x2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].x2
	elif dotList[1].lost and dotList[2].lost:
		xLoc = last[0]
		yLoc = last[1]
	else:
		xLocLeft = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
		yLocLeft = yCoefLeft[0] + yCoefLeft[1]*dotList[1].x2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].x2
		xLocRight = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
		yLocRight = yCoefRight[0] + yCoefRight[1]*dotList[2].x2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].x2
		xLoc = (xLocLeft+xLocRight)/2
		yLoc = (yLocLeft+yLocRight)/2
	return [xLoc,yLoc]


########
# Initialize variables
########

#initialize sounds
blinkSound = Sound('./pytracker/Resources/sounds/beep.wav')
saccadeSound = Sound('./pytracker/Resources/sounds/stop.wav')

#specify the getTime function
if (timestampMethod==0) or (timestampMethod==1):
	#initialize timer
	sdl2.SDL_Init(sdl2.SDL_INIT_TIMER)
	if timestampMethod==0:
		#define a function to use the high-precision timer, returning a float in seconds
		def getTime():
			return sdl2.SDL_GetPerformanceCounter()*1.0/sdl2.SDL_GetPerformanceFrequency()
	elif timestampMethod==1:
		#use the SDL_GetTicks timer
		def getTime():
			return sdl2.SDL_GetTicks()/1000.0
elif timestampMethod==2:
	#use time.time()
	import time
	getTime = time.time

#initialize font
fontSize = camRes[1]/previewDownsize/10
sdl2.sdlttf.TTF_Init()
font = sdl2.sdlttf.TTF_OpenFont('./pytracker/Resources/DejaVuSans.ttf', fontSize)

#initialize preview video
sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
previewWindow = sdl2.ext.Window("Preview",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=previewLoc,flags=sdl2.SDL_WINDOW_SHOWN)
previewWindowSurf = sdl2.SDL_GetWindowSurface(previewWindow.window)
previewWindowArray = sdl2.ext.pixels3d(previewWindowSurf.contents)
sdl2.ext.fill(previewWindowSurf.contents,sdl2.pixels.SDL_Color(r=255, g=255, b=255, a=255))
previewWindow.refresh()
lastRefreshTime = time.time()

#initialize the settings window
settingsWindow = sdl2.ext.Window("Settings",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=[previewLoc[0]+camRes[0]/previewDownsize+1,previewLoc[1]])
settingsWindowSurf = sdl2.SDL_GetWindowSurface(settingsWindow.window)
settingsWindowArray = sdl2.ext.pixels3d(settingsWindowSurf.contents)
sdl2.ext.fill(settingsWindowSurf.contents,sdl2.pixels.SDL_Color(r=0, g=0, b=0, a=255))
settingsWindow.hide()
settingsWindow.refresh()

#import the haar cascades
faceCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/haarcascade_frontalface_alt2.xml')
eyeLeftCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/LEye18x12.1.xml')
eyeRightCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/REye18x12.1.xml')

#create some settings 
settingsDict = {}
settingsDict['blink'] = settingText(value=75,x=fontSize,y=fontSize,text='Blink (0-100) = ')
settingsDict['blur'] = settingText(value=3,x=fontSize,y=fontSize*2,text='Blur (0-; odd only) = ')
settingsDict['filter'] = settingText(value=3,x=fontSize,y=fontSize*3,text='Filter (0-; odd only) = ')

#create some text UIs
clickableTextDict = {}
clickableTextDict['manual'] = clickableText(x=0,y=0,text='Manual')
clickableTextDict['auto'] = clickableText(x=0,y=fontSize,text='Auto')
clickableTextDict['calibrate'] = clickableText(x=0,y=previewWindow.size[1]-fontSize,text='Calibrate')
clickableTextDict['settings'] = clickableText(x=previewWindow.size[0],y=0,text='Settings',rightJustified=True)
clickableTextDict['lag'] = clickableText(x=previewWindow.size[0],y=previewWindow.size[1]-fontSize*2,text='Lag: ',rightJustified=True)
clickableTextDict['f2f'] = clickableText(x=previewWindow.size[0],y=previewWindow.size[1]-fontSize,text='Frame-to-frame: ',rightJustified=True)

#initialize variables
previewInFocus = True
settingsInFocus = False
lastTime = 0
dotList = []
displayLagList = []
frameToFrameTimeList = []
doHaar = False
clickingForDots = False
calibrating = False
doneCalibration = False
doSounds = True
queueDataToParent = False

#set dummy calibration coefficients (yields untransformed pixel locs)
calibrationCoefs = [[0,1,0,0],[0,0,1,0],[0,1,0,0],[0,0,1,0]]

########
# Initialize camera
########
vc = cv2.VideoCapture(camIndex)
vc.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,camRes[0])
vc.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,camRes[1])
imageNum = 0

#start the loop
while True:

	#poll the camera
	t1 = getTime() #time right before requesting the image
	_,image = vc.read() #request the image
	t2 = getTime() #time right after requesting the image
	imageTime = t1+(t2-t1)/2.0 #timestamp the image as halfway between times before and after request
	image = image[:,:,2] #grab red channel (image is BGR)
	imageNum += 1 #iterate the image number

	#check for messages from the main process
	if not qTo.empty():
		message = qTo.get()
		if message=='quit':
			exitSafely()

	#process input
	sdl2.SDL_PumpEvents()
	for event in sdl2.ext.get_events():
		if event.type==sdl2.SDL_WINDOWEVENT:
			targetWindow = sdl2.SDL_GetWindowFromID(event.window.windowID)
			title = sdl2.SDL_GetWindowTitle(targetWindow)
			# if event.window.event==sdl2.SDL_WINDOWEVENT_FOCUS_GAINED:
			# 	print title + "focused"
			# if event.window.event==sdl2.SDL_WINDOWEVENT_ENTER:
			# 	print title + " entered"
			# elif event.window.event==sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
			# 	print title + " lost focus"
			if event.window.event==sdl2.SDL_WINDOWEVENT_LEAVE:
				if title=='Preview':
					previewInFocus = False
					settingsInFocus = True
			if (event.window.event==sdl2.SDL_WINDOWEVENT_FOCUS_GAINED) or (event.window.event==sdl2.SDL_WINDOWEVENT_ENTER):
				if title=='Preview':
					previewInFocus = True
					settingsInFocus = False
				elif title=='Settings':
					previewInFocus = False
					settingsInFocus = True
			elif (event.window.event==sdl2.SDL_WINDOWEVENT_CLOSE):
				if title=='Preview':
					exitSafely()
				elif title=='Settings':
					previewInFocus = True
					settingsInFocus = False
					settingsWindow.hide()
					previewWindow.show()
		elif settingsInFocus:
			# if event.type==sdl2.SDL_MOUSEBUTTONUP:
			# 	if blinkTextButtonDown:
			# 		blinkTextButtonDown = False
			# if event.type==sdl2.SDL_MOUSEBUTTONDOWN:
			# 	if mouseInBlinkText:
			# 		blinkTextButtonDown = True
			if event.type==sdl2.SDL_MOUSEMOTION:
				alreadyClicked = False
				for setting in settingsDict:
					if (settingsDict[setting].isActive) and (settingsDict[setting].clicked):
						alreadyClicked = True
				if not alreadyClicked:
					for setting in settingsDict:
						settingsDict[setting].checkIfActive(event)
			elif event.type==sdl2.SDL_MOUSEBUTTONDOWN:
				alreadyClicked = False
				for setting in settingsDict:
					if (settingsDict[setting].isActive) and (settingsDict[setting].clicked):
						alreadyClicked = True
				if not alreadyClicked:
					for setting in settingsDict:
						if settingsDict[setting].isActive:
							settingsDict[setting].clicked = True
			elif event.type==sdl2.SDL_KEYDOWN:
				key = sdl2.SDL_GetKeyName(event.key.keysym.sym).lower()
				if key == 'backspace':
					for setting in settingsDict:
						if (settingsDict[setting].isActive) and (settingsDict[setting].clicked):
							settingsDict[setting].delValue()
				elif key=='return':
					for setting in settingsDict:
						if (settingsDict[setting].isActive) and (settingsDict[setting].clicked):
							settingsDict[setting].finalizeValue()
							settingsDict[setting].clicked = False
				else:
					for setting in settingsDict:
						if (settingsDict[setting].isActive) and (settingsDict[setting].clicked):
							settingsDict[setting].addValue(key)
		elif previewInFocus:
			if event.type==sdl2.SDL_KEYDOWN:
				key = sdl2.SDL_GetKeyName(event.key.keysym.sym).lower()
				if key=='escape': #exit
					# exitSafely()
					clickingForDots = False
					clickingForFid = False
					definingFidFinderBox = False
					dotList = []
			if event.type==sdl2.SDL_MOUSEMOTION:
					if clickingForDots:
						clickableTextDict['manual'].isActive = True #just making sure
						if definingFidFinderBox:
							fidFinderBoxSize = abs(fidFinderBoxX - (previewWindow.size[0]-event.button.x) )
					else:
						for clickableText in clickableTextDict:
							if not (clickableText in ['lag','f2f']):
								clickableTextDict[clickableText].checkIfActive(event)
			if event.type==sdl2.SDL_MOUSEBUTTONDOWN:
				if clickingForDots:
					if clickingForFid:
						if not definingFidFinderBox:
							definingFidFinderBox = True
							fidFinderBoxX = previewWindow.size[0]-event.button.x
							fidFinderBoxY = event.button.y
							fidFinderBoxSize = 0
						else:
							definingFidFinderBox = False
							clickingForFid = False
							fidFinderBoxSize = abs(fidFinderBoxX - (previewWindow.size[0]-event.button.x) )
							dotList.append(pytracker.dotObj.dotObj(name='fid',isFid=True,xPixel=fidFinderBoxX * previewDownsize,yPixel=fidFinderBoxY * previewDownsize,radiusPixel=fidFinderBoxSize * previewDownsize,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))
					else:
						clickX = (previewWindow.size[0]-event.button.x)
						clickY = event.button.y
						if len(dotList)==1:
							dotList.append(pytracker.dotObj.dotObj(name = 'left',isFid=False,xPixel=clickX * previewDownsize,yPixel=clickY * previewDownsize,radiusPixel=dotList[0].radiusPixel,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))
						else:
							dotList.append(pytracker.dotObj.dotObj(name = 'right',isFid=False,xPixel=clickX * previewDownsize,yPixel=clickY * previewDownsize,radiusPixel=dotList[1].radiusPixel,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))
							clickingForDots = False
							manTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,'Manual',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
				else:
					if clickableTextDict['settings'].isActive:
						if (sdl2.SDL_GetWindowFlags( settingsWindow.window ) & sdl2.SDL_WINDOW_SHOWN):
							settingsWindow.hide()
						else:
							settingsWindow.show()
					elif clickableTextDict['auto'].isActive:
						waitingforHaar = False
						doHaar = True #triggers haar detection for next frame
						dotList = [] 
					elif clickableTextDict['manual'].isActive:
						clickingForDots = True
						clickingForFid = True
						definingFidFinderBox = False
						dotList = []
					elif clickableTextDict['calibrate'].isActive:
						doneCalibration = False
						calibrator = pytracker.calibrationClass(timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,mirrorDownSize,calibrationDotSizeInDegrees,manualCalibrationOrder)
						calibrator.start()
						calibrating = True
						checkCalibrationStopTime = False
						queueDataToCalibrator = False

	#do haar detection if requested
	if doHaar: 
		doHaar = False #only enter this section once
		faceDetectionImage = cv2.resize(image,dsize=(image.shape[1]/faceDetectionScale,image.shape[0]/faceDetectionScale),interpolation=cv2.INTER_NEAREST)
		detectedFaces = faceCascade.detectMultiScale(faceDetectionImage)#,scaleFactor=1.1,minNeighbors=3,minSize=(10,10))
		if len(detectedFaces)==0: #no faces found!
			print 'no faces found!' #do something here
		else:
			faceX,faceY,faceW,faceH = rescaleBiggestHaar(detected=detectedFaces,scale=faceDetectionScale,addToX=0,addToY=0)
			leftFaceImage = image[faceY:(faceY+faceH),faceX:(faceX+faceW/2)]
			eyeLeftDetectionImage = cv2.resize(leftFaceImage,dsize=(leftFaceImage.shape[1]/eyeDetectionScale,leftFaceImage.shape[0]/eyeDetectionScale),interpolation=cv2.INTER_NEAREST)
			detectedEyeLefts = eyeLeftCascade.detectMultiScale(eyeLeftDetectionImage)#,minSize=(leftFaceImage.shape[0]/8,leftFaceImage.shape[0]/8))
			rightFaceImage = image[faceY:(faceY+faceH),(faceX+faceW/2):(faceX+faceW)]
			eyeRightDetectionImage = cv2.resize(rightFaceImage,dsize=(rightFaceImage.shape[1]/eyeDetectionScale,rightFaceImage.shape[0]/eyeDetectionScale),interpolation=cv2.INTER_NEAREST)
			detectedEyeRights = eyeRightCascade.detectMultiScale(eyeRightDetectionImage)#,minSize=(rightFaceImage.shape[0]/8,rightFaceImage.shape[0]/8))
			if (len(detectedEyeLefts)==0)|(len(detectedEyeRights)==0): #at least one eye is missing!
				if (len(detectedEyeLefts)==0):
					print 'left eye missing' #do something here
				else:
					print 'right eye missing' #do something here									
			else:
				eyeLeftX,eyeLeftY,eyeLeftW,eyeLeftH = rescaleBiggestHaar(detected=detectedEyeLefts,scale=eyeDetectionScale,addToX=faceX,addToY=faceY)
				eyeRightX,eyeRightY,eyeRightW,eyeRightH = rescaleBiggestHaar(detected=detectedEyeRights,scale=eyeDetectionScale,addToX=faceX+faceW/2,addToY=faceY)
				#initialize fid
				dotList.append(pytracker.dotObj.dotObj(name='fid',isFid=True,xPixel=faceX+faceW/2,yPixel=(faceY+(eyeLeftY+eyeRightY)/2)/2,radiusPixel=(eyeLeftH+eyeRightH)/4,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))
				#initialize left
				dotList.append(pytracker.dotObj.dotObj(name='left',isFid=False,xPixel=eyeLeftX+eyeLeftW/2,yPixel=eyeLeftY+eyeLeftH/2,radiusPixel=eyeLeftH/2,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))
				#initialize right
				dotList.append(pytracker.dotObj.dotObj(name='right',isFid=False,xPixel=eyeRightX+eyeRightW/2,yPixel=eyeRightY+eyeRightH/2,radiusPixel=eyeRightH/2,blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value))

	#update the dots given the latest image
	for i in range(len(dotList)): 
		dotList[i].update(img=image,fid=dotList[0],blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value)
		# print 'ok'

	#some post-processing
	blinkHappened = False
	saccadeHappened = False
	if len(dotList)==3:
		if dotList[0].lost:
			dotList = []
			print 'fid lost'
		elif (dotList[1].lostCount>30) or (dotList[2].lostCount>30):
			print "lost lots"
			if (not dotList[1].blinkHappened) and (not dotList[2].blinkHappened): #only reset if not blinking
				dotList = []
		elif dotList[1].blinkHappened and dotList[2].blinkHappened:
			blinkHappened = True
		else
			xLoc,yLoc = getGazeLoc(dotList,calibrationCoefs,lastLocs)
			if len(lastLocs)==2:
				locDiff = ( ((xLoc-lastLocs[0])**2) + ((yLoc-lastLocs[1])**2) )**.5
				if doneCalibration:
					saccadeCriterion = saccadeAlertSize
				else:
					saccadeCriterion = dotList[0].radius*2 #heuristic for uncalibrated
				if locDiff>saccadeCriterion:
					saccadeHappened = True
			lastLocs = [xLoc,yLoc]
			if queueDataToParent:
				qFrom.put(['eyeData',[str.format('{0:.3f}',imageTime),xLoc,yLoc,dotlist[1].radius2,dotlist[2].radius2,,saccadeHappened,blinkHappened,dotList[1].lost,dotList[2].lost,dotList[1].blinkHappened,dotList[2].blinkHappened]])

	#play sounds as necessary
	if doSounds:
		if (not saccadeSound.stillPlaying()) and (not blinkSound.stillPlaying()):
			if blinkHappened:
				blinkSound.play()
			elif saccadeHappened:
				saccadeSound.play()

	#do drawing
	if previewDownsize!=1:
		image = cv2.resize(image,dsize=previewWindow.size,interpolation=cv2.INTER_NEAREST)
	image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
	if clickingForDots:
		if clickingForFid:
			if definingFidFinderBox:
				cv2.circle(image,(fidFinderBoxX,fidFinderBoxY),fidFinderBoxSize,color=(255,0,0,255),thickness=1)
	for dot in dotList:
		ellipse = ((dot.ellipse[0][0]/previewDownsize,dot.ellipse[0][1]/previewDownsize),(dot.ellipse[1][0]/previewDownsize,dot.ellipse[1][1]/previewDownsize),dot.ellipse[2])
		if dot.blinkHappened or dot.lost:
			dotColor = (0,0,255,255)
		else:
			dotColor = (0,255,0,255)
		cv2.ellipse(image,ellipse,color=dotColor,thickness=1)
	image = numpy.rot90(image)
	previewWindowArray[:,:,0:3] = image
	frameToFrameTimeList.append(imageTime-lastTime)
	lastTime = imageTime
	displayLagList.append(getTime()-imageTime)
	if len(displayLagList)>30:
		displayLagList.pop(0)
		frameToFrameTimeList.pop(0)
	clickableTextDict['lag'].valueText = str(int(numpy.median(displayLagList)*1000))
	clickableTextDict['lag'].updateSurf()
	clickableTextDict['f2f'].valueText = str(int(numpy.median(frameToFrameTimeList)*1000))
	clickableTextDict['f2f'].updateSurf()
	for clickableText in clickableTextDict:
		clickableTextDict[clickableText].draw(previewWindowSurf)
	previewWindow.refresh()
	thisRefreshTime = time.time()
	# print (thisRefreshTime - lastRefreshTime)*1000
	lastRefreshTime = thisRefreshTime
	if (sdl2.SDL_GetWindowFlags( settingsWindow.window ) & sdl2.SDL_WINDOW_SHOWN):
		sdl2.ext.fill(settingsWindowSurf.contents,sdl2.pixels.SDL_Color(r=0, g=0, b=0, a=255))
		for setting in settingsDict:
			settingsDict[setting].draw(settingsWindowSurf)
		settingsWindow.refresh()

	#calibration stuff
	if calibrating:
		if not calibrator.qFrom.empty():
			message = calibrator.qFrom.get()
			if message=='startQueing':
				queueDataToCalibrator = True
			elif message[0]=='stopQueing':
				calibrationStopTime = message[1]
				checkCalibrationStopTime = True
			elif message[0]=='calibrationCoefs':
				calibrationCoefs = message[1]
				calibrating = False
				doneCalibration = True
				calibrator.stop()
				del calibrator
				lastLocs = []
				qFrom.put(['calibrationComplete',message])
				queueDataToParent = True
			else: 
				print message
		if checkCalibrationStopTime:
			if imageTime>calibrationStopTime:
				queueDataToCalibrator = False
				calibrator.qTo.put('doneQueing')
				checkCalibrationStopTime = False
		if queueDataToCalibrator:
			if len(dotList)>0:
				calibrator.qTo.put([imageTime,dotList[1].x2,dotList[1].y2,dotList[2].x2,dotList[2].y2])



