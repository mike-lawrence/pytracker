import cv2
import numpy
import scipy.ndimage.filters
import time
import PupilTrackerPythonWrapper

class dotObj:
	def __init__(self,name,isFid,xPixel,yPixel,radiusPixel,blinkCriterion):
		self.name = name
		self.isFid = isFid
		self.xPixel = xPixel
		self.yPixel = yPixel
		self.radiusPixel = radiusPixel
		self.radius = int(self.radiusPixel)
		self.radii = []
		self.SDs = []
		self.lostCount = 0
		self.blinkCriterion = blinkCriterion
	def cropImage(self,img,cropSize):
		xLo = self.xPixel - cropSize
		if xLo<0:
			xLo = 0
		xHi = self.xPixel + cropSize
		if xHi>img.shape[1]:
			xHi = img.shape[1]
		yLo = self.yPixel - cropSize
		if yLo<0:
			yLo = 0
		yHi = self.yPixel + cropSize
		if yHi>img.shape[0]:
			yHi = img.shape[0]
		return [img[yLo:yHi,xLo:xHi],xLo,xHi,yLo,yHi]
	def search(self,img,ptParams):
		if self.radiusPixel<10:
			searchSize = 30
		else:
			searchSize = 3*self.radiusPixel
		img,xLo,xHi,yLo,yHi = self.cropImage(img=img,cropSize=searchSize)
		img = cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
		center_x, center_y, size_width, size_height, angle = PupilTrackerPythonWrapper.findPupil(img, int(self.radius/2), int(self.radius*1.5), ptParams['CannyBlur'], ptParams['CannyThreshold1'], ptParams['CannyThreshold2'], ptParams['StarburstPoints'], ptParams['PercentageInliers'], ptParams['InlierIterations'], ptParams['ImageAwareSupport'], ptParams['EarlyTerminationPercentage'], ptParams['EarlyRejection'], ptParams['Seed'])		
		if size_width == 0:
			self.lost = True
		else:
			self.ellipse = ((center_x+xLo,center_y+yLo),(size_width,size_height),angle)
			self.lost = False
			self.x = self.ellipse[0][0]
			self.y = self.ellipse[0][1]
			self.major = self.ellipse[1][0]
			self.minor = self.ellipse[1][1]
			self.angle = self.ellipse[2]
			self.xPixel = int(self.x)
			self.yPixel = int(self.y)
			if size_width>size_height:
				self.radius = size_width/2.0
			else:
				self.radius = size_height/2.0
			self.radiusPixel = int(self.radius)
	def checkSearch(self):
		self.medianRadius = numpy.median(self.radii)
		self.critRadius = 10*((numpy.median((self.radii-self.medianRadius)**2))**.5)
		#print [self.name, self.radius2,(self.radius2<(1/6)) , (self.radius2>2)]
		if len(self.radii)<30:
			self.radii.append(self.radius2)
		else:
			#fid diameter is 6mm, so range from 1mm to 12mm
			#if (self.radius2<(1/6)) or (self.radius2>2) or (self.radius2<(self.medianRadius - self.critRadius)) or (self.radius2>(self.medianRadius + self.critRadius)):
			if (self.radius2<(1/6)) or (self.radius2>2):
				self.lost = True
			else:
				self.radii.append(self.radius2)
			if len(self.radii)>=300:
				self.radii.pop()
	def makeRelativeToFid(self,fid):
		self.x2 = (self.x-fid.x)/fid.radius
		self.y2 = (self.y-fid.y)/fid.radius
		self.radius2 = self.radius/fid.radius
	def checkSD(self,img,fid):
		self.obsSD = numpy.std(self.cropImage(img=img,cropSize=5*fid.radiusPixel)[0])
		self.medianSD = numpy.median(self.SDs)
		self.critSD = self.medianSD*self.blinkCriterion
		#print [self.name,self.obsSD,self.medianSD,self.critSD,self.blinkCriterion]
		if len(self.SDs)<30:
			self.SDs.append(self.obsSD)	
		else:
			if (self.obsSD<self.critSD):
				self.blink = True
			else:
				self.SDs.append(self.obsSD)
			if len(self.SDs)>=300:
				self.SDs.pop()
	def update(self,img,ptParams,fid=None):
		lastPixels = [self.xPixel,self.yPixel,self.radiusPixel]
		self.blink = False
		self.lost = True
		if self.isFid:
			self.search(img=img,ptParams=ptParams)
		else:
			self.checkSD(img=img,fid=fid)
			if self.blink:
				self.xPixel,self.yPixel,self.radiusPixel = lastPixels
			else:
				self.search(img=img,ptParams=ptParams)
				if self.lost:
					self.xPixel,self.yPixel,self.radiusPixel = lastPixels
				else:
					self.makeRelativeToFid(fid=fid)
					self.checkSearch()
					if self.lost:
						self.xPixel,self.yPixel,self.radiusPixel = lastPixels
		if self.lost and not self.blink:
			self.lostCount += 1
		else:
			self.lostCount = 0
