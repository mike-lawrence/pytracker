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
	previewWindow = sdl2.ext.Window("test",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=previewLoc,flags=sdl2.SDL_WINDOW_SHOWN)
	previewWindowSurf = sdl2.SDL_GetWindowSurface(previewWindow.window)
	previewWindowArray = sdl2.ext.pixels3d(previewWindowSurf.contents)
	sdl2.ext.fill(previewWindowSurf.contents,sdl2.pixels.SDL_Color(r=255, g=255, b=255, a=255))
	previewWindow.refresh()
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
	autoTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,'Auto',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
	manTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,'Manual',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
	calTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,'Calibrate',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents	
	blinkCriterion = .75
	blinkTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,str(int(blinkCriterion*100)),sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
	blinkSliderTop = int(autoTextSurf.h*2.5)
	blinkSliderBottom = previewWindow.size[1]-int(calTextSurf.h*1.5)
	blinkSliderSize = blinkSliderBottom - blinkSliderTop
	blinkCriterionPosition = blinkSliderBottom - blinkSliderSize*blinkCriterion	
	#initialize variables
	saccadeSoundWaiting = False
	lastSaccadeSoundTime = 0
	autoBoxOn = False
	manBoxOn = False
	calBoxOn = False
	mouseInAutoText = False
	mouseInManText = False
	mouseInCalText = False
	mouseInBlinkText = False
	blinkTextButtonDown = False
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
			if event.type==sdl2.SDL_KEYDOWN:
				key = sdl2.SDL_GetKeyName(event.key.keysym.sym).lower()
				if key=='escape': #exit
					exitSafely()
			if event.type==sdl2.SDL_MOUSEMOTION:
				if clickingForDots:
					if definingFidFinderBox:
						fidFinderBoxSize = abs(fidFinderBoxX - (previewWindow.size[0]-event.button.x) )
				else:
					autoBoxOn = False
					manBoxOn = False
					calBoxOn = False
					mouseInAutoText = False
					mouseInManText = False
					mouseInCalText = False
					mouseInBlinkText = False
					if ( event.button.x > (previewWindow.size[0]-autoTextSurf.w) ) & ( event.button.x < previewWindow.size[0] ) & ( event.button.y > 0 ) & ( event.button.y < autoTextSurf.h ):
						autoBoxOn = True
						mouseInAutoText = True
					elif ( event.button.x > (previewWindow.size[0]-manTextSurf.w) ) & ( event.button.x < previewWindow.size[0] ) & ( event.button.y > autoTextSurf.h ) & ( event.button.y < (autoTextSurf.h+manTextSurf.h) ):
						manBoxOn = True
						mouseInManText = True
					elif ( event.button.x > (previewWindow.size[0]-calTextSurf.w) ) & ( event.button.x < previewWindow.size[0] ) & ( event.button.y > (previewWindow.size[1]-calTextSurf.h) ) & ( event.button.y < previewWindow.size[1] ):
						calBoxOn = True
						mouseInCalText = True
					elif ( event.button.x > previewWindow.size[0]-fontSize-blinkTextSurf.w ) & ( event.button.x < previewWindow.size[0]-fontSize ) & ( event.button.y > blinkCriterionPosition-blinkTextSurf.h/2 ) & ( event.button.y < blinkCriterionPosition+blinkTextSurf.h/2 ) :
						mouseInBlinkText = True
						if blinkTextButtonDown:
							blinkCriterion = ( ( blinkSliderBottom - event.button.y ) * 1.0 / blinkSliderSize )
							if blinkCriterion>1:
								blinkCriterion=1
							elif blinkCriterion<0:
								blinkCriterion=0
							blinkTextSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,str(int(blinkCriterion*100)),sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
							blinkCriterionPosition = blinkSliderBottom - blinkSliderSize*blinkCriterion
							for i in range(len(dotList)):
								dotList[i].blinkCriterion = blinkCriterion
			if event.type==sdl2.SDL_MOUSEBUTTONUP:
				if not clickingForDots:
					if blinkTextButtonDown:
						blinkTextButtonDown = False
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
							dotList.append(pytracker.dotObj.dotObj(name='fid',isFid=True,xPixel=fidFinderBoxX * previewDownsize,yPixel=fidFinderBoxY * previewDownsize,radiusPixel=fidFinderBoxSize * previewDownsize,blinkCriterion=blinkCriterion))
					else:
						clickX = (previewWindow.size[0]-event.button.x)
						clickY = event.button.y
						if len(dotList)==1:
							dotList.append(pytracker.dotObj.dotObj(name = 'left',isFid=False,xPixel=clickX * previewDownsize,yPixel=clickY * previewDownsize,radiusPixel=fidFinderBoxSize * previewDownsize,blinkCriterion=blinkCriterion))
						else:
							dotList.append(pytracker.dotObj.dotObj(name = 'right',isFid=False,xPixel=clickX * previewDownsize,yPixel=clickY * previewDownsize,radiusPixel=fidFinderBoxSize * previewDownsize,blinkCriterion=blinkCriterion))
							clickingForDots = False
				else:
					if mouseInBlinkText:
						blinkTextButtonDown = True
					elif mouseInAutoText:
						waitingforHaar = False
						doHaar = True #triggers haar detection for next frame
						dotList = [] 
					elif mouseInManText:
						clickingForDots = True
						clickingForFid = True
						definingFidFinderBox = False
						dotList = []
					elif mouseInCalText:
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
						dotList.append(pytracker.dotObj.dotObj(isFid=True,xPixel=faceX+faceW/2,yPixel=(faceY+(eyeLeftY+eyeRightY)/2)/2,radiusPixel=(eyeLeftH+eyeRightH)/4,blinkCriterion=blinkCriterion))
						#initialize left
						dotList.append(pytracker.dotObj.dotObj(isFid=False,xPixel=eyeLeftX+eyeLeftW/2,yPixel=eyeLeftY+eyeLeftH/2,radiusPixel=eyeLeftH/2,blinkCriterion=blinkCriterion))
						#initialize right
						dotList.append(pytracker.dotObj.dotObj(isFid=False,xPixel=eyeRightX+eyeRightW/2,yPixel=eyeRightY+eyeRightH/2,radiusPixel=eyeRightH/2,blinkCriterion=blinkCriterion))
			for i in range(len(dotList)): #update the dots given the new image
				dotList[i].update(img=image,imageNum=imageNum,fid=dotList[0])
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
				xPixel = dot.xPixel/previewDownsize
				yPixel = dot.yPixel/previewDownsize
				size = dot.radiusPixel/previewDownsize
				if dot.blink:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,0,255,255),thickness=1)
				else:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,255,0,255),thickness=1)
			if autoBoxOn:
				# cv2.rectangle(image,(previewWindow.size[0]-autoTextSurf.w,0),(previewWindow.size[0],autoTextSurf.h),(0,255,0,255),1)
				cv2.rectangle(image,(0,0),(autoTextSurf.w,autoTextSurf.h),(0,255,0,255),1)
			if manBoxOn:
				cv2.rectangle(image,(0,autoTextSurf.h),(manTextSurf.w,autoTextSurf.h+manTextSurf.h),(0,255,0,255),1)
			if calBoxOn:
				cv2.rectangle(image,(0,previewWindow.size[1]-calTextSurf.h),(calTextSurf.w,previewWindow.size[1]),(0,255,0,255),1)
			cv2.rectangle(image,(0,blinkSliderTop),(fontSize,blinkSliderBottom),(255,0,0,255),1)
			cv2.rectangle(image,(0,int(blinkCriterionPosition)-2),(fontSize,int(blinkCriterionPosition)+2),(255,0,0,255),-1)
			image = numpy.rot90(image)
			previewWindowArray[:,:,0:3] = image
			frameToFrameTimeList.append(imageTime-lastTime)
			lastTime = imageTime
			displayLagList.append(getTime()-imageTime)
			displayLag = str(int(numpy.median(displayLagList)*1000))
			frameToFrameTime = str(int(numpy.median(frameToFrameTimeList)*1000))
			if len(displayLagList)>30:
				displayLagList.pop(0)
				frameToFrameTimeList.pop(0)
			sdl2.SDL_BlitSurface(autoTextSurf, None, previewWindowSurf, sdl2.SDL_Rect(previewWindow.size[0]-autoTextSurf.w,0,autoTextSurf.w,autoTextSurf.h))
			sdl2.SDL_BlitSurface(manTextSurf, None, previewWindowSurf, sdl2.SDL_Rect(previewWindow.size[0]-manTextSurf.w,autoTextSurf.h,manTextSurf.w,manTextSurf.h))
			sdl2.SDL_BlitSurface(calTextSurf, None, previewWindowSurf, sdl2.SDL_Rect(previewWindow.size[0]-calTextSurf.w,previewWindow.size[1]-calTextSurf.h,calTextSurf.w,calTextSurf.h))
			sdl2.SDL_BlitSurface(blinkTextSurf, None, previewWindowSurf, sdl2.SDL_Rect(previewWindow.size[0]-fontSize-blinkTextSurf.w,int(blinkCriterionPosition-blinkTextSurf.h/2),blinkTextSurf.w,blinkTextSurf.h))
			timeSurf = sdl2.sdlttf.TTF_RenderText_Blended_Wrapped(font,'Lag: '+displayLag+'\r'+'f2f: '+frameToFrameTime+'\r',sdl2.pixels.SDL_Color(r=0, g=0, b=255, a=255),previewWindow.size[0]).contents
			sdl2.SDL_BlitSurface(timeSurf, None, previewWindowSurf, sdl2.SDL_Rect(0,0,timeSurf.w,timeSurf.h))
			previewWindow.refresh()
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



