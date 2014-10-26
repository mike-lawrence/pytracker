if __name__ == '__main__':
	import fileForker
	trackerChild = fileForker.childClass(childFile='pytracker/trackerChild')
	trackerChild.initDict['camIndex'] = 0
	trackerChild.initDict['camRes'] = [1920,1080]
	trackerChild.initDict['previewDownsize'] = 2
	trackerChild.initDict['previewLoc'] = [0,0]
	trackerChild.initDict['faceDetectionScale'] = 4
	trackerChild.initDict['eyeDetectionScale'] = 2
	trackerChild.initDict['timestampMethod'] = 0
	trackerChild.initDict['viewingDistance'] = 100
	trackerChild.initDict['stimDisplayWidth'] = 100
	trackerChild.initDict['stimDisplayRes'] = [1920,1080]
	trackerChild.initDict['stimDisplayPosition'] = [0,0]
	trackerChild.initDict['mirrorDisplayPosition'] = [0,0]
	trackerChild.initDict['mirrorDownSize'] = 2
	trackerChild.initDict['manualCalibrationOrder'] = True
	trackerChild.initDict['calibrationDotSizeInDegrees'] = 1
	trackerChild.start()
	import time
	while trackerChild.isAlive():
		time.sleep(1)
