if __name__ == '__main__':
	import pytracker
	import time
	camIndex = 1
	camRes = [1920,1080]
	previewDownsize = 2
	faceDetectionScale = 4
	eyeDetectionScale = 2
	timestampMethod = 2
	viewingDistance = 53.0
	stimDisplayWidth = 59.5
	stimDisplayRes = [605,560]
	stimDisplayPosition = [(1344-1024)/2+213,(756-768)/2+113]
	mirrorDisplayPosition = [0,0]
	mirrorDownSize = 2
	previewLoc = [0,0]
	manualCalibrationOrder = False
	calibrationDotSizeInDegrees = 1
	saccadeAlertSizeInDegrees = 3
	tracker = pytracker.trackerClass(camIndex=camIndex,camRes=camRes,previewDownsize=previewDownsize,previewLoc=previewLoc,faceDetectionScale=faceDetectionScale,eyeDetectionScale=eyeDetectionScale,timestampMethod=timestampMethod,viewingDistance=viewingDistance,stimDisplayWidth=stimDisplayWidth,stimDisplayRes=stimDisplayRes,stimDisplayPosition=stimDisplayPosition,mirrorDisplayPosition=mirrorDisplayPosition,mirrorDownSize=mirrorDownSize,manualCalibrationOrder = manualCalibrationOrder, calibrationDotSizeInDegrees=calibrationDotSizeInDegrees,saccadeAlertSizeInDegrees=saccadeAlertSizeInDegrees)
	tracker.start()
	calibrated = False
	while True:
		if not tracker.qFrom.empty():
			message = tracker.qFrom.get()
			if message=='done':
				if calibrated:
					file.close()
				break
			elif message[0]=='calibrationComplete':
				calibrated = True
				file = open(time.strftime('%Y')+'_'+time.strftime('%m')+'_'+time.strftime('%d')+'_'+time.strftime('%H')+'_'+time.strftime('%M')+'.txt','w')
				file.write('calibation:\t'+'\t'.join(map(str,message[1]))+'\n')
			elif message[0]=='eyeData':
				#print message[1]
				message[1][0] = "%.3f" %message[1][0]
				file.write('\t'.join(map(str,message[1]))+'\n')
		else:
			time.sleep(1)

