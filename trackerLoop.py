def loop(qTo,qFrom,camIndex,camRes,previewDownsize,faceDetectionScale,eyeDetectionScale,timestampMethod):
	import numpy
	import cv2
	import scipy.ndimage.filters
	import scipy.interpolate
	import sys
	import sdl2
	import sdl2.ext
	import billiard
	import pytracker
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
	faceCascade = cv2.CascadeClassifier('./pytracker/Resources/haarcascade_frontalface_alt2.xml')
	eyeLeftCascade = cv2.CascadeClassifier('./pytracker/Resources/LEye18x12.1.xml')
	eyeRightCascade = cv2.CascadeClassifier('./pytracker/Resources/REye18x12.1.xml')
	########
	# Define a class for the dot object
	########
	class dotObj:
		def __init__(self,isFid,xPixel,yPixel,radiusPixel):
			self.isFid = isFid
			self.xPixel = xPixel
			self.yPixel = yPixel
			self.radiusPixel = radiusPixel
			self.first = True
			self.radii = []
			self.SDs = []
			self.lostCount = 0
		def getDarkEllipse(self,img,neighborhoodSize=3):
			smoothedImg = cv2.GaussianBlur(img,(3,3),0)
			dataMin = scipy.ndimage.filters.minimum_filter(smoothedImg, 3)
			if dataMin!=None:
				minLocs = numpy.where(dataMin<(numpy.min(dataMin)+numpy.std(dataMin)))
				if len(minLocs[0])>=5:
					ellipse = cv2.fitEllipse(numpy.reshape(numpy.column_stack((minLocs[1],minLocs[0])),(len(minLocs[0]),1,2)))
					return ellipse
		def cropImage(self,img,cropSize):
			xLo = self.xPixel - cropSize
			xHi = self.xPixel + cropSize
			yLo = self.yPixel - cropSize
			yHi = self.yPixel + cropSize
			return [img[yLo:yHi,xLo:xHi],xLo,yLo]
		def search(self,img):
			if self.lost:
				searchSize = 5
			else:
				searchSize = 3
			if self.first:
				searchSize = 1
				self.first = False
			img,xLo,yLo = self.cropImage(img=img,cropSize=searchSize*self.radiusPixel)
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
		def checkSearch(self):
			self.radii.append(self.radius2)
			self.medianRadius = numpy.median(self.radii)
			self.critRadius = 10*((numpy.median((self.radii-self.medianRadius)**2))**.5)
			if len(self.radii)>=30:
					#fid diameter is 6mm, so range from .1 to 12mm
				if (self.radius2<(1/6)) or (self.radius2>2) or (self.radius2<(self.medianRadius - self.critRadius)) or (self.radius2>(self.medianRadius + self.critRadius)): #(radius2<(fid.radius/6.0)) or (radius2>fid.radius*2) or 
					self.lost = True
					self.lostCount += 1
				else:
					self.lostCount = 0
				if len(self.radii)>=300:
					self.radii.pop()
		def makeRelativeToFid(self,fid):
			self.x2 = (self.x-fid.x)/fid.radius
			self.y2 = (self.y-fid.y)/fid.radius
			self.radius2 = self.radius/fid.radius
		def checkSD(self,img,fid):
			obsSD = numpy.std(self.cropImage(img=img,cropSize=5*fid.radiusPixel)[0])
			self.SDs.append(obsSD)
			self.medianSD = numpy.median(self.SDs)
			self.critSD = 10*((numpy.median((self.SDs-self.medianSD)**2))**.5)
			if len(self.SDs)>=30:
				if (obsSD<(self.medianSD - self.critSD)):
					self.blink = True
					self.SDs.pop(-1);
				if len(self.SDs)>=300:
					self.SDs.pop()
		def update(self,img,fid=None):
			lastPixels = [self.xPixel,self.yPixel,self.radiusPixel]
			self.blink = False
			self.lost = True
			if self.isFid:
				self.search(img=img)
			else:
				self.checkSD(img=img,fid=fid)
				if self.blink:
					self.xPixel,self.yPixel,self.radiusPixel = lastPixels
				else:
					self.search(img=img)
					if self.lost:
						self.xPixel,self.yPixel,self.radiusPixel = lastPixels
					else:
						self.makeRelativeToFid(fid=fid)
						self.checkSearch()
						if self.lost:
							self.xPixel,self.yPixel,self.radiusPixel = lastPixels
			if self.lost:
				self.lostCount += 1
			else:
				self.lostCount = 0
	def rescaleBiggestHaar(detected,scale,addToX=0,addToY=0):
		x,y,w,h = detected[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detected])]
		return [x*scale+addToX,y*scale+addToY,w*scale,h*scale]
	def exitSafely():
		camera.stop()
		print 'camera stopped'
		qFrom.put('done')
		print 'tracker stopped'
		sys.exit()
	#initialize variables
	lastTime = 0
	dotList = []
	displayLagList = []
	frameToFrameTimeList = []
	doDots = False
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
							dotList.append(dotObj(isFid=True,xPixel=faceX+faceW/2,yPixel=(faceY+(eyeLeftY+eyeRightY)/2)/2,radiusPixel=(eyeLeftH+eyeRightH)/4))
							#initialize left
							dotList.append(dotObj(isFid=False,xPixel=eyeLeftX+eyeLeftW/2,yPixel=eyeLeftY+eyeLeftH/2,radiusPixel=eyeLeftH/2))
							#initialize right
							dotList.append(dotObj(isFid=False,xPixel=eyeRightX+eyeRightW/2,yPixel=eyeRightY+eyeRightH/2,radiusPixel=eyeRightH/2))
			for i in range(len(dotList)): #update the dots given the new image
				dotList[i].update(img=image,fid=dotList[0])
			if len(dotList)>0:
				# print [imageNum,imageTime,dotList[1].blink,dotList[1].SDs[-1],dotList[1].medianSD,dotList[1].critSD,dotList[2].blink,dotList[2].SDs[-1],dotList[2].medianSD,dotList[2].critSD,dotList[1].lost,dotList[1].radii[-1],dotList[1].medianRadius,dotList[1].critRadius,dotList[2].lost,dotList[2].radii[-1],dotList[2].medianRadius,dotList[2].critRadius,dotList[0].lost]
				if dotList[0].lost:
					dotList = [] #triggers haar detection for next frame
					print 'fid lost'
				elif (dotList[1].lostCount>10):
					if (not dotList[1].blink) and (not dotList[2].blink): #only trigger haar detection if not blinking
						dotList = [] #triggers haar detection for next frame
			if previewDownsize!=1:
				image = cv2.resize(image,dsize=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),interpolation=cv2.INTER_NEAREST)
			image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
			for dot in dotList:
				xPixel = dot.xPixel/previewDownsize
				yPixel = dot.yPixel/previewDownsize
				size = dot.radiusPixel/previewDownsize
				if dot.blink:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,0,255,255),thickness=2)
				else:
					cv2.circle(image,(xPixel,yPixel),size,color=(0,255,0,255),thickness=2)
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


