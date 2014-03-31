import billiard
billiard.forking_enable(0)

from . import trackerLoop
from . import cameraLoop
from . import calibrationLoop

########
# Define a class that spawns a new process to poll the camera and queue images
########
class cameraClass:
	def __init__(self,camIndex,camRes,timestampMethod):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=cameraLoop.loop , args=(self.qTo,self.qFrom,camIndex,camRes,timestampMethod) )
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

########
# Define a class that spawns a new process to manage the camera, do tracking and display a preview window
########
class trackerClass:
	def __init__(self,camIndex,camRes,previewDownsize,faceDetectionScale,eyeDetectionScale,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,manualCalibrationOrder,calibrationDotSizeInDegrees,saccadeAlertSizeInDegrees):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=trackerLoop.loop , args=(self.qTo,self.qFrom,camIndex,camRes,previewDownsize,faceDetectionScale,eyeDetectionScale,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,manualCalibrationOrder,calibrationDotSizeInDegrees,saccadeAlertSizeInDegrees) )
	def start(self):
		self.process.start()
	def stop(self):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		return None

########
# Define a class that spawns a new process to manage the camera, do tracking and display a preview window
########
class calibrationClass:
	def __init__(self,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,calibrationDotSizeInDegrees,manualCalibrationOrder):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=calibrationLoop.loop , args=(self.qTo,self.qFrom,timestampMethod,viewingDistance,stimDisplayWidth,stimDisplayRes,stimDisplayPosition,mirrorDisplayPosition,calibrationDotSizeInDegrees,manualCalibrationOrder) )
	def start(self):
		self.process.start()
	def stop(self):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		return None

