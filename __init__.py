import numpy
import cv2
import scipy.ndimage.filters
import billiard
billiard.forking_enable(0)

from . import trackerLoop
from . import cameraLoop

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
	def __init__(self,camIndex,camRes,previewDownsize=1,faceDetectionScale=4,eyeDetectionScale=2,timestampMethod=0):
		self.qTo = billiard.Queue()
		self.qFrom = billiard.Queue()
		self.process = billiard.Process( target=trackerLoop.loop , args=(self.qTo,self.qFrom,camIndex,camRes,previewDownsize,faceDetectionScale,eyeDetectionScale,timestampMethod) )
	def start(self):
		self.process.start()
	def stop(self):
		self.qTo.put('quit')
		self.process.join(timeout=1)
		if self.process.is_alive():
			self.process.terminate()
		return None

