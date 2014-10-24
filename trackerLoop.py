def loop(qTo,qFrom,camIndex,camRes,previewDownsize,previewLoc,faceDetectionScale,eyeDetectionScale,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,mirrorDownSize,manualCalibrationOrder,calibrationDotSizeInDegrees,saccadeAlertSizeInDegrees):
	import numpy
	import cv2
	import scipy.ndimage.filters
	import scipy.interpolate
	import sys
	import sdl2
	import sdl2.ext
	import sdl2.sdlmixer
	import pytracker
	import pytracker.dotObj
	import billiard
	sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO)
	sdl2.sdlmixer.Mix_OpenAudio(44100, sdl2.sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024)
	########
	# Define a class that handles playing sounds in PySDL2
	########
	class Sound:
		def __init__(self, fileName):
			self.sample = sdl2.sdlmixer.Mix_LoadWAV(sdl2.ext.compat.byteify(fileName, "utf-8"))
		def play(self):
			self.channel = sdl2.sdlmixer.Mix_PlayChannel(-1, self.sample, 0)
		def doneYet(self):
			if sdl2.sdlmixer.Mix_Playing(self.channel):
				return False
			else:
				return True
	#tell billiard to enable forking
	billiard.forking_enable(0)
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
	#initialize video
	sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
	previewWindow = sdl2.ext.Window("Preview",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=previewLoc,flags=sdl2.SDL_WINDOW_SHOWN)
	previewWindowSurf = sdl2.SDL_GetWindowSurface(previewWindow.window)
	previewWindowArray = sdl2.ext.pixels3d(previewWindowSurf.contents)
	sdl2.ext.fill(previewWindowSurf.contents,sdl2.pixels.SDL_Color(r=255, g=255, b=255, a=255))
	previewWindow.refresh()
	lastRefreshTime = time.time()
	settingsWindow = sdl2.ext.Window("Settings",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=[previewLoc[0]+camRes[0]/previewDownsize+1,previewLoc[1]])
	settingsWindowSurf = sdl2.SDL_GetWindowSurface(settingsWindow.window)
	settingsWindowArray = sdl2.ext.pixels3d(settingsWindowSurf.contents)
	sdl2.ext.fill(settingsWindowSurf.contents,sdl2.pixels.SDL_Color(r=0, g=0, b=0, a=255))
	settingsWindow.hide()
	settingsWindow.refresh()
	faceCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/haarcascade_frontalface_alt2.xml')
	eyeLeftCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/LEye18x12.1.xml')
	eyeRightCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/REye18x12.1.xml')
	def exitSafely():
		camera.stop()
		qFrom.put('done')
		sys.exit()
	def rescaleBiggestHaar(detected,scale,addToX=0,addToY=0):
		x,y,w,h = detected[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detected])]
		return [x*scale+addToX,y*scale+addToY,w*scale,h*scale]
	def getGazeLoc(dotList,coefs,last):
		xCoefLeft,xCoefRight,yCoefLeft,yCoefRight = coefs
		if dotList[1].lost:
			xLoc = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
			yLoc = yCoefRight[0] + yCoefRight[1]*dotList[2].y2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].x2
		elif dotList[2].lost:
			xLoc = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
			yLoc = yCoefLeft[0] + yCoefLeft[1]*dotList[1].y2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].x2
		elif dotList[1].lost and dotList[2].lost:
			xLoc = last[0]
			yLoc = last[1]
		else:
			xLocLeft = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
			yLocLeft = yCoefLeft[0] + yCoefLeft[1]*dotList[1].y2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].x2
			xLocRight = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
			yLocRight = yCoefRight[0] + yCoefRight[1]*dotList[2].y2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].x2
			xLoc = (xLocLeft+xLocRight)/2
			yLoc = (yLocLeft+yLocRight)/2
			# print [xLoc,yLoc,dotList[1].x2,dotList[1].y2,dotList[2].x2,dotList[2].y2]
		return [xLoc,yLoc]
	previewInFocus = True
	settingsInFocus = False
	#initialize variables
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
	settingsDict = {}
	settingsDict['blink'] = settingText(value=75,x=fontSize,y=fontSize,text='Blink (0-100) = ')
	settingsDict['blur'] = settingText(value=3,x=fontSize,y=fontSize*2,text='Blur (0-; odd only) = ')
	settingsDict['filter'] = settingText(value=3,x=fontSize,y=fontSize*3,text='Filter (0-; odd only) = ')
	clickableTextDict = {}
	clickableTextDict['manual'] = clickableText(x=0,y=0,text='Manual')
	clickableTextDict['auto'] = clickableText(x=0,y=fontSize,text='Auto')
	clickableTextDict['calibrate'] = clickableText(x=0,y=previewWindow.size[1]-fontSize,text='Calibrate')
	clickableTextDict['settings'] = clickableText(x=previewWindow.size[0],y=0,text='Settings',rightJustified=True)
	clickableTextDict['lag'] = clickableText(x=previewWindow.size[0],y=previewWindow.size[1]-fontSize*2,text='Lag: ',rightJustified=True)
	clickableTextDict['f2f'] = clickableText(x=previewWindow.size[0],y=previewWindow.size[1]-fontSize,text='Frame-to-frame: ',rightJustified=True)
	saccadeSoundWaiting = False
	lastSaccadeSoundTime = 0
	lastTime = 0
	dotList = []
	displayLagList = []
	frameToFrameTimeList = []
	doHaar = False
	clickingForDots = False
	calibrating = False
	doneCalibration = False
	doSounds = True
	soundPlaying = False
	queueDataToParent = False
	#initialize camera
	camera = pytracker.cameraClass(camIndex=camIndex,camRes=camRes,timestampMethod=timestampMethod)
	camera.start()
	#start the loop
	while True:
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
		#check for images from the camera
		if not camera.qFrom.empty():
			imageNum,imageTime,image = camera.qFrom.get()
			if doHaar: #do haar detection
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
			for i in range(len(dotList)): #update the dots given the new image
				dotList[i].update(img=image,fid=dotList[0],blinkCriterion=settingsDict['blink'].value/100.0,blurSize=settingsDict['blur'].value,filterSize=settingsDict['filter'].value)
				# print 'ok'
			blink = False
			saccade = False
			if len(dotList)==3:
				# print [dotList[1].blink,dotList[1].lost,dotList[1].lostCount,dotList[2].blink,dotList[2].lost,dotList[2].lostCount,dotList[1].obsSD,dotList[1].medianSD,dotList[1].critSD,dotList[1].radius2,dotList[1].medianRadius,dotList[1].critRadius,dotList[2].obsSD,dotList[2].medianSD,dotList[2].critSD,dotList[2].radius2,dotList[2].medianRadius,dotList[2].critRadius]
				if dotList[0].lost:
					dotList = []
					print 'fid lost'
				elif (dotList[1].lostCount>30) or (dotList[2].lostCount>30):
					print "lost lots"
					if (not dotList[1].blink) and (not dotList[2].blink): #only trigger haar detection if not blinking
						dotList = []
				elif dotList[1].blink and dotList[2].blink:
					blink = True
					if saccadeSoundWaiting:
						saccadeSoundWaiting = False
				elif doneCalibration:
					xLoc,yLoc = getGazeLoc(dotList,calibrationCoefs,lastLocs)
					#print [xLoc,yLoc]
					if len(lastLocs)==2:
						# locDiff = ( ((xLoc-lastLocs[0])**2) + ((yLoc-lastLocs[1])**2) )**.5
						locDiff = abs(xLoc-lastLocs[0])
						if locDiff>saccadeAlertSizeInDegrees:
							saccade = True
							if not saccadeSoundWaiting:
								if getTime()>(lastSaccadeSoundTime+1):
									saccadeSoundWaiting = True
									saccadeSoundWaitStart = getTime()
					lastLocs = [xLoc,yLoc]
					if queueDataToParent:
						qFrom.put(['eyeData',[str.format('{0:.3f}',imageTime),xLoc,yLoc,saccade,blink,dotList[1].lost,dotList[2].lost,dotList[1].blink,dotList[2].blink]])
			if doSounds:
				if not soundPlaying:
					if blink:
						sound = Sound('./pytracker/Resources/sounds/beep.wav')
						sound.play()
						soundPlaying = True
					if saccadeSoundWaiting:
						if getTime()>(saccadeSoundWaitStart+.1):
							lastSaccadeSoundTime = getTime()
							saccadeSoundWaiting = False
							sound = Sound('./pytracker/Resources/sounds/stop.wav')
							sound.play()
							soundPlaying = True
				else:
					if sound.doneYet():
						soundPlaying = False
						del sound
			if previewDownsize!=1:
				image = cv2.resize(image,dsize=previewWindow.size,interpolation=cv2.INTER_NEAREST)
			image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
			if clickingForDots:
				if clickingForFid:
					if definingFidFinderBox:
						cv2.circle(image,(fidFinderBoxX,fidFinderBoxY),fidFinderBoxSize,color=(255,0,0,255),thickness=1)
			for dot in dotList:
				ellipse = ((dot.ellipse[0][0]/previewDownsize,dot.ellipse[0][1]/previewDownsize),(dot.ellipse[1][0]/previewDownsize,dot.ellipse[1][1]/previewDownsize),dot.ellipse[2])
				if dot.blink or dot.lost:
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



