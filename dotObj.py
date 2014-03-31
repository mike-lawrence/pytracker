import cv2
import numpy
import scipy.ndimage.filters

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
			print 'cv2.GaussianBlur failed'
			# cv2.imwrite('temp.png',img)
			return None
		try:
			dataMin = scipy.ndimage.filters.minimum_filter(smoothedImg, 3)
		except:
			print 'scipy.ndimage.filters.minimum_filter failed'
			# cv2.imwrite('temp.png',img)
			return None
		if dataMin!=None:
			try:
				minLocs = numpy.where(dataMin<(numpy.min(dataMin)+numpy.std(dataMin)))
			except:
				print 'numpy.where failed'
				# cv2.imwrite('temp.png',img)
				return None
			if len(minLocs[0])>=5:
				try:
					ellipse = cv2.fitEllipse(numpy.reshape(numpy.column_stack((minLocs[1],minLocs[0])),(len(minLocs[0]),1,2)))
				except:
					print 'cv2.fitEllipse failed'
					# cv2.imwrite('temp.png',img)
					return None
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
