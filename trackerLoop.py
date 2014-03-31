def loop(qTo,qFrom,camIndex,camRes,previewDownsize,faceDetectionScale,eyeDetectionScale,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,manualCalibrationOrder,calibrationDotSizeInDegrees,saccadeAlertSizeInDegrees):
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
	sdl2.sdlttf.TTF_Init()
	font = sdl2.sdlttf.TTF_OpenFont('./pytracker/Resources/DejaVuSans.ttf', camRes[1]/previewDownsize/10)
	#initialize video
	sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
	window = sdl2.ext.Window("test",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=(0,0),flags=sdl2.SDL_WINDOW_SHOWN)
	windowSurf = sdl2.SDL_GetWindowSurface(window.window)
	windowArray = sdl2.ext.pixels3d(windowSurf.contents)
	sdl2.ext.fill(windowSurf.contents,sdl2.pixels.SDL_Color(r=255, g=255, b=255, a=255))
	window.refresh()
	faceCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/haarcascade_frontalface_alt2.xml')
	eyeLeftCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/LEye18x12.1.xml')
	eyeRightCascade = cv2.CascadeClassifier('./pytracker/Resources/cascades/REye18x12.1.xml')
	def exitSafely():
		camera.stop()
		print 'camera stopped'
		qFrom.put('done')
		print 'tracker stopped'
		sys.exit()
	def rescaleBiggestHaar(detected,scale,addToX=0,addToY=0):
		x,y,w,h = detected[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detected])]
		return [x*scale+addToX,y*scale+addToY,w*scale,h*scale]
	def getGazeLoc(dotList,coefs,last):
		xCoefLeft,xCoefRight,yCoefLeft,yCoefRight = coefs
		if dotList[1].lost:
			xLoc = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
			yLoc = yCoefRight[0] + yCoefRight[1]*dotList[2].y2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].y2
		elif dotList[2].lost:
			xLoc = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
			yLoc = yCoefLeft[0] + yCoefLeft[1]*dotList[1].y2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].y2
		elif dotList[1].lost and dotList[2].lost:
			xLoc = last[0]
			yLoc = last[1]
		else:
			xLocLeft = xCoefLeft[0] + xCoefLeft[1]*dotList[1].x2 + xCoefLeft[2]*dotList[1].y2 + xCoefLeft[3]*dotList[2].y2*dotList[1].x2
			yLocLeft = yCoefLeft[0] + yCoefLeft[1]*dotList[1].y2 + yCoefLeft[2]*dotList[1].y2 + yCoefLeft[3]*dotList[2].y2*dotList[1].y2
			xLocRight = xCoefRight[0] + xCoefRight[1]*dotList[2].x2 + xCoefRight[2]*dotList[2].y2 + xCoefRight[3]*dotList[2].y2*dotList[2].x2
			yLocRight = yCoefRight[0] + yCoefRight[1]*dotList[2].y2 + yCoefRight[2]*dotList[2].y2 + yCoefRight[3]*dotList[2].y2*dotList[2].y2
			xLoc = (xLocLeft+xLocRight)/2
			yLoc = (yLocLeft+yLocRight)/2
			# print [xLoc,yLoc,dotList[1].x2,dotList[1].y2,dotList[2].x2,dotList[2].y2]
		return [xLoc,yLoc]		
	#initialize variables
	lastTime = 0
	dotList = []
	displayLagList = []
	frameToFrameTimeList = []
	doDots = False
	calibrating = False
	doneCalibration = False
	doSounds = True
	soundPlaying = False
	queuDataToParent = False
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
			if event.type==sdl2.SDL_KEYDOWN:
				key = sdl2.SDL_GetKeyName(event.key.keysym.sym).lower()
				if key=='escape': #exit
					exitSafely()
				elif key=='0': #start defining dots
					waitingforHaar = False
					doDots = True#not doDots
					dotList = [] #triggers haar detection for next frame
				elif key=='9':
					calibrator = pytracker.calibrationClass(timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,calibrationDotSizeInDegrees,manualCalibrationOrder)
					calibrator.start()
					calibrating = True
					checkCalibrationStopTime = False
					queueDataToCalibrator = False
		#check for images from the camera
		if not camera.qFrom.empty():
			imageNum,imageTime,image = camera.qFrom.get()
			if len(dotList)==0: #no dots found yet, find using haar detection
				if doDots: #do haar detection
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
							dotList.append(pytracker.dotObj.dotObj(isFid=True,xPixel=faceX+faceW/2,yPixel=(faceY+(eyeLeftY+eyeRightY)/2)/2,radiusPixel=(eyeLeftH+eyeRightH)/4))
							#initialize left
							dotList.append(pytracker.dotObj.dotObj(isFid=False,xPixel=eyeLeftX+eyeLeftW/2,yPixel=eyeLeftY+eyeLeftH/2,radiusPixel=eyeLeftH/2))
							#initialize right
							dotList.append(pytracker.dotObj.dotObj(isFid=False,xPixel=eyeRightX+eyeRightW/2,yPixel=eyeRightY+eyeRightH/2,radiusPixel=eyeRightH/2))
			for i in range(len(dotList)): #update the dots given the new image
				dotList[i].update(img=image,fid=dotList[0])
			blink = False
			saccade = False
			if len(dotList)>0:
				if dotList[0].lost:
					dotList = [] #triggers haar detection for next frame
					print 'fid lost'
				elif (dotList[1].lostCount>10) or (dotList[2].lostCount>10):
					if (not dotList[1].blink) and (not dotList[2].blink): #only trigger haar detection if not blinking
						dotList = [] #triggers haar detection for next frame
				elif dotList[1].blink and dotList[2].blink:
					blink = True
				elif doneCalibration:
					xLoc,yLoc = getGazeLoc(dotList,calibrationCoefs,lastLocs)
					print [xLoc,yLoc]
					if len(lastLocs)==2:
						# locDiff = ( ((xLoc-lastLocs[0])**2) + ((yLoc-lastLocs[1])**2) )**.5
						locDiff = abs(xLoc-lastLocs[0])
						if locDiff>saccadeAlertSizeInDegrees:
							saccade = True
					lastLocs = [xLoc,yLoc]
					if queuDataToParent:
						qFrom.put([imageTime,xLoc,yLoc,saccade,dotList[1].lost,dotList[2].lost,dotList[1].blink,dotList[2].blink])
			if doSounds:
				if not soundPlaying:
					if blink:
						sound = Sound('./pytracker/Resources/sounds/beep.wav')
						sound.play()
						soundPlaying = True
					if saccade:
						sound = Sound('./pytracker/Resources/sounds/stop.wav')
						sound.play()
						soundPlaying = True
				else:
					if sound.doneYet():
						soundPlaying = False
						del sound
			if previewDownsize!=1:
				image = cv2.resize(image,dsize=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),interpolation=cv2.INTER_NEAREST)
			image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
			for dot in dotList:
				xPixel = dot.xPixel/previewDownsize
				yPixel = dot.yPixel/previewDownsize
				size = dot.radiusPixel/previewDownsize
				if dot.blink:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,0,255,255),thickness=1)
				else:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,255,0,255),thickness=1)
			image = numpy.rot90(image)
			windowArray[:,:,0:3] = image
			frameToFrameTimeList.append(imageTime-lastTime)
			lastTime = imageTime
			displayLagList.append(getTime()-imageTime)
			displayLag = str(int(numpy.median(displayLagList)*1000))
			frameToFrameTime = str(int(numpy.median(frameToFrameTimeList)*1000))
			if len(displayLagList)>30:
				displayLagList.pop(0)
				frameToFrameTimeList.pop(0)
			timeSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,displayLag+'\r'+frameToFrameTime+'\r',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),window.size[0]).contents
			sdl2.SDL_BlitSurface(timeSurf, None, windowSurf, sdl2.SDL_Rect(0,0,timeSurf.w,timeSurf.h))
			window.refresh()
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
						print calibrationCoefs
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



