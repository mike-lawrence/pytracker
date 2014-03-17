def loop(qTo,qFrom,camIndex,camRes,timestampMethod):
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
		image = image[:,:,2] #grab red channel (image is BGR)
		qFrom.put([imageNum,imageTime,image])
		imageNum += 1 #iterate the image number
		#check for messages from the tracker process
		if not qTo.empty():
			message = qTo.get()
			if message=='quit':
				break
