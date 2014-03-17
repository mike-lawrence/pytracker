import numpy
import cv2
import scipy.ndimage.filters
import billiard
billiard.forking_enable(0)

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
		try:
			smoothedImg = cv2.GaussianBlur(img,(3,3),0)
		except:
			print 'cv2.GaussianBlur caused an exception'
			return None
		try:
			dataMin = scipy.ndimage.filters.minimum_filter(smoothedImg, 3)
		except:
			print 'scipy.ndimage.filters.minimum_filter caused an exception'
			return None
		if dataMin!=None:
			try:
				minLocs = numpy.where(dataMin<(numpy.min(dataMin)+numpy.std(dataMin)))
			except:
				print 'numpy.where caused an exception'
				return None				
			if len(minLocs[0])>=5:
				try:
					ellipse = cv2.fitEllipse(numpy.reshape(numpy.column_stack((minLocs[1],minLocs[0])),(len(minLocs[0]),1,2)))
					return ellipse
				except:
					print 'cv2.fitEllipse caused an exception'
					return None									
			else:
				return None
		else:
			return None
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

# def rescaleBiggestHaar(detected,scale,addToX=0,addToY=0):
# 	x,y,w,h = detected[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detected])]
# 	return [x*scale+addToX,y*scale+addToY,w*scale,h*scale]

def doHaarDetection(image,faceCascade,eyeLeftCascade,eyeRightCascade,faceDetectionScale,eyeDetectionScale):
	dotList = []
	faceDetectionImage = cv2.resize(image,dsize=(image.shape[1]/faceDetectionScale,image.shape[0]/faceDetectionScale),interpolation=cv2.INTER_NEAREST)
	detectedFaces = faceCascade.detectMultiScale(faceDetectionImage)#,scaleFactor=1.1,minNeighbors=3,minSize=(10,10))
	if len(detectedFaces)==0: #no faces found!
		print 'no faces found!' #do something here
	else:
		# faceX,faceY,faceW,faceH = pytracker.rescaleBiggestHaar(detected=detectedFaces,scale=faceDetectionScale,addToX=0,addToY=0)
		faceX,faceY,faceW,faceH = detectedFaces[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detectedFaces])]
		faceX,faceY,faceW,faceH = [faceX*faceDetectionScale,faceY*faceDetectionScale,faceW*faceDetectionScale,faceH*faceDetectionScale]
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
			# eyeLeftX,eyeLeftY,eyeLeftW,eyeLeftH = pytracker.rescaleBiggestHaar(detected=detectedEyeLefts,scale=eyeDetectionScale,addToX=faceX,addToY=faceY)
			eyeLeftX,eyeLeftY,eyeLeftW,eyeLeftH = detectedEyeLefts[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detectedEyeLefts])]
			eyeLeftX,eyeLeftY,eyeLeftW,eyeLeftH = [eyeLeftX*eyeDetectionScale+faceX,eyeLeftY*eyeDetectionScale+faceY,eyeLeftW*eyeDetectionScale,eyeLeftH*eyeDetectionScale]
			# eyeRightX,eyeRightY,eyeRightW,eyeRightH = pytracker.rescaleBiggestHaar(detected=detectedEyeRights,scale=eyeDetectionScale,addToX=faceX+faceW/2,addToY=faceY)
			eyeRightX,eyeRightY,eyeRightW,eyeRightH = detectedEyeRights[numpy.argmax([numpy.sqrt(w*w+h*h) for x,y,w,h in detectedEyeRights])]
			eyeRightX,eyeRightY,eyeRightW,eyeRightH = [eyeRightX*eyeDetectionScale+(faceX+faceW/2),eyeRightY*eyeDetectionScale+faceY,eyeRightW*eyeDetectionScale,eyeRightH*eyeDetectionScale]
			# eyeLeftImage = image[eyeLeftY:(eyeLeftY+eyeLeftH),eyeLeftX:(eyeLeftX+eyeLeftW)]
			# eyeRightImage = image[eyeRightY:(eyeRightY+eyeRightH),eyeRightX:(eyeRightX+eyeRightW)]
			# fidImage = image[((eyeLeftY+eyeRightY)/2-(eyeLeftH+eyeRightH)/8):((eyeLeftY+eyeRightY)/2+(eyeLeftH+eyeRightH)/8),(((eyeLeftX+eyeLeftW/2)+(eyeRightX+eyeRightW/2))/2-(eyeLeftH+eyeRightH)/8):(((eyeLeftX+eyeLeftW/2)+(eyeRightX+eyeRightW/2))/2+(eyeLeftH+eyeRightH)/8)]
			# cv2.imwrite('temp.png',fidImage)
			#initialize fid
			dotList.append(dotObj(isFid=True,xPixel=faceX+faceW/2,yPixel=(faceY+(eyeLeftY+eyeRightY)/2)/2,radiusPixel=(eyeLeftH+eyeRightH)/4))
			#initialize left
			dotList.append(dotObj(isFid=False,xPixel=eyeLeftX+eyeLeftW/2,yPixel=eyeLeftY+eyeLeftH/2,radiusPixel=eyeLeftH/2))
			#initialize right
			dotList.append(dotObj(isFid=False,xPixel=eyeRightX+eyeRightW/2,yPixel=eyeRightY+eyeRightH/2,radiusPixel=eyeRightH/2))
	return dotList


########
# Define a class for processing individual image frames
########
class workerClass:
	def __init__(self,workerNum,qTo,qFrom,faceDetectionScale,eyeDetectionScale):
		self.qTo = qTo
		self.qFrom = qFrom
		self.process = billiard.Process( target=self.loop , args=(workerNum,qTo,qFrom,faceDetectionScale,eyeDetectionScale) )
	def start(self):
		self.process.start()
	def stop(self,):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		return None
	def loop(self,workerNum,qTo,qFrom,faceDetectionScale,eyeDetectionScale):
		import sys
		import numpy
		import cv2
		import scipy.ndimage.filters
		import pytracker
		faceCascade = cv2.CascadeClassifier('./pytracker/haarcascade_frontalface_alt2.xml')
		eyeLeftCascade = cv2.CascadeClassifier('./pytracker/LEye18x12.1.xml')
		eyeRightCascade = cv2.CascadeClassifier('./pytracker/REye18x12.1.xml')
		while True:
			if not qTo.empty():
				message = qTo.get()
				if message=='quit':
					break
				else: #image received, do processing
					imageNum,imageTime,image,dotList = message
					cv2.imwrite('images/'+str(imageNum)+'.png',image)
					if len(dotList)==0: #no dots found yet, find using haar detection
						dotList = pytracker.doHaarDetection(image,faceCascade,eyeLeftCascade,eyeRightCascade,faceDetectionScale,eyeDetectionScale)
					for i in range(len(dotList)): #update the dots given the new image
						dotList[i].update(img=image,fid=dotList[0])
						# print [dotList[i].xPixel,dotList[i].yPixel,dotList[i].radiusPixel]
					# print [imageNum,imageTime,dotList[1].blink,dotList[1].SDs[-1],dotList[1].medianSD,dotList[1].critSD,dotList[2].blink,dotList[2].SDs[-1],dotList[2].medianSD,dotList[2].critSD,dotList[1].lost,dotList[1].radii[-1],dotList[1].medianRadius,dotList[1].critRadius,dotList[2].lost,dotList[2].radii[-1],dotList[2].medianRadius,dotList[2].critRadius]
					qFrom.put([imageNum,imageTime,workerNum,dotList])




########
# Define a class for polling the camera as frequently as possible and queuing the resulting images
########
class cameraClass:
	def __init__(self,camIndex,camRes,timestampMethod):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=self.loop , args=(self.qTo,self.qFrom,camIndex,camRes,timestampMethod) )
	def start(self):
		self.process.start()
	def stop(self,):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		del self.qTo
		del self.qFrom
		return None
	def loop(self,qTo,qFrom,camIndex,camRes,timestampMethod):
		import cv2 #for interacting with the webcam
		import sys #for quitting
		if (timestampMethod==0) or (timestampMethod==1):
			import sdl2 #for timestamping images
			import sdl2.ext #to help sdl2
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
		#initialize the camera
		vc = cv2.VideoCapture(camIndex)
		vc.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,camRes[0])
		vc.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,camRes[1])
		#initialize some variables
		imageNum = 0
		#start the loop
		while True:
			t1 = getTime() #time right before requesting the image
			_,image = vc.read() #request the image
			t2 = getTime() #time right after requesting the image
			imageTime = t1+(t2-t1)/2.0 #timestamp the image as halfway between times before and after request
			# image = image.astype(numpy.float)
			# im01 = ((image[:,:,0]-image[:,:,1])+128).astype(numpy.uint8)
			# im10 = ((image[:,:,1]-image[:,:,0])+128).astype(numpy.uint8)
			# im02 = ((image[:,:,0]-image[:,:,2])+128).astype(numpy.uint8)
			# im20 = ((image[:,:,2]-image[:,:,0])+128).astype(numpy.uint8)
			# im12 = ((image[:,:,1]-image[:,:,2])+128).astype(numpy.uint8)
			# im21 = ((image[:,:,2]-image[:,:,1])+128).astype(numpy.uint8)
			# cv2.imwrite('images/'+str(imageNum)+'_01.png',im01)
			# cv2.imwrite('images/'+str(imageNum)+'_10.png',im10)
			# cv2.imwrite('images/'+str(imageNum)+'_02.png',im02)
			# cv2.imwrite('images/'+str(imageNum)+'_20.png',im20)
			# cv2.imwrite('images/'+str(imageNum)+'_12.png',im12)
			# cv2.imwrite('images/'+str(imageNum)+'_21.png',im21)
			image = image[:,:,2] #grab red channel (image is BGR)
			qFrom.put([imageNum,imageTime,image])
			imageNum += 1 #iterate the image number
			#check for messages from the tracker process
			if not qTo.empty():
				message = qTo.get()
				if message=='quit':
					break

########
# Define a class to manage the camera, workers and display
########
class trackerClass:
	def __init__(self,camIndex,camRes,numWorkers=0,previewDownsize=1,faceDetectionScale=4,eyeDetectionScale=2,timestampMethod=0):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=self.loop , args=(self.qTo,self.qFrom,camIndex,camRes,previewDownsize,numWorkers,faceDetectionScale,eyeDetectionScale,timestampMethod) )
	def start(self):
		self.process.start()
	def stop(self):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		return None
	def loop(self,qTo,qFrom,camIndex,camRes,previewDownsize,numWorkers,faceDetectionScale,eyeDetectionScale,timestampMethod):
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
		font = sdl2.sdlttf.TTF_OpenFont('pytracker/DejaVuSans.ttf', camRes[1]/previewDownsize/10)
		#initialize video
		sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
		window = sdl2.ext.Window("test",size=(camRes[0]/previewDownsize,camRes[1]/previewDownsize),position=(0,0),flags=sdl2.SDL_WINDOW_SHOWN)
		windowSurf = sdl2.SDL_GetWindowSurface(window.window)
		windowArray = sdl2.ext.pixels3d(windowSurf.contents)
		sdl2.ext.fill(windowSurf.contents,sdl2.pixels.SDL_Color(r=255, g=255, b=255, a=255))
		window.refresh()
		if numWorkers==0:
			faceCascade = cv2.CascadeClassifier('./pytracker/haarcascade_frontalface_alt2.xml')
			eyeLeftCascade = cv2.CascadeClassifier('./pytracker/LEye18x12.1.xml')
			eyeRightCascade = cv2.CascadeClassifier('./pytracker/REye18x12.1.xml')
		else:
			#initialize workers
			qToWorkers = billiard.Queue()
			qFromWorkers = billiard.Queue()
			workerList = []
			for i in range(numWorkers):
				workerList.append(pytracker.workerClass(workerNum=i,qTo=qToWorkers,qFrom=qFromWorkers,faceDetectionScale=faceDetectionScale,eyeDetectionScale=eyeDetectionScale))
				workerList[i].start()
		#initialize camera
		camera = pytracker.cameraClass(camIndex=camIndex,camRes=camRes,timestampMethod=timestampMethod)
		camera.start()
		#define a function to close down workers & camera for exit
		def exit_safely():
			camera.stop()
			print 'camera stopped'
			for i in range(numWorkers):
				workerList[i].stop()
				print 'worker'+str(i)+' stopped'
			qFrom.put('done')
			print 'tracker stopped'
			sys.exit()
		#define a function to update the screen
		def updateScreen(imageNum,dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime):
			imageNum,image,imageTime = imageDict[str(imageNum)]
			imageDict.pop(str(imageNum))
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
			return [dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime]
		#initialize variables	
		lastTime = 0
		imageDict = {}
		dotList = []
		displayLagList = []
		frameToFrameTimeList = []
		doDots = False
		#start the loop
		while True:
			#process input
			sdl2.SDL_PumpEvents()
			for event in sdl2.ext.get_events():
				if event.type==sdl2.SDL_KEYDOWN:
					key = sdl2.SDL_GetKeyName(event.key.keysym.sym).lower()
					if key=='escape': #exit
						exit_safely()
					elif key=='0': #start defining dots
						waitingforHaar = False
						doDots = True#not doDots
						dotList = [] #triggers haar detection for next frame
			#check for images from the camera
			if not camera.qFrom.empty():
				imageNum,imageTime,image = camera.qFrom.get()
				imageDict[str(imageNum)] = [imageNum,image,imageTime]
				if numWorkers==0:
					if len(dotList)==0: #no dots found yet, find using haar detection
						if doDots:
							dotList = pytracker.doHaarDetection(image,faceCascade,eyeLeftCascade,eyeRightCascade,faceDetectionScale,eyeDetectionScale)
					for i in range(len(dotList)): #update the dots given the new image
						dotList[i].update(img=image,fid=dotList[0])
					dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime = updateScreen(imageNum,dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime)
				else:
					if doDots:
						qToWorkers.put([imageNum,imageTime,image,dotList])
						if len(dotList)==0:
							waitingforHaar = True
							doDots = False
					else:
						dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime = updateScreen(imageNum,dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime)
			if numWorkers>0:
				#check for ouput from workers
				if not qFromWorkers.empty():
					imageNum,imageTime,workerNum,dotList = qFromWorkers.get()
					if waitingforHaar:
						doDots = True
						waitingforHaar = False
					dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime = updateScreen(imageNum,dotList,imageDict,frameToFrameTimeList,displayLagList,lastTime)
			#check for messages from the main process
			if not qTo.empty():
				message = qTo.get()
				if message=='quit':
					exit_safely()

